import csv
import re
import uuid
import pprint
import sys

from os import path
from pya2l import DB, model
from pya2l import utils
from sys import argv

def print_usage():
    print("Usage:")
    print("  CSV input:        python a2lmeasurement.py <a2l_file> --csv <csv_file> [--debug]")
    print("  Individual args:  python a2lmeasurement.py <a2l_file> <param1> [param2:CustomName] [param3] ... [--debug]")
    print("  Address lookup:   python a2lmeasurement.py <a2l_file> --addr <address1> [address2:CustomName] ... [--debug]")
    print("")
    print("Options:")
    print("  --debug           Enable debug output to troubleshoot issues")
    print("  --addr            Look up measurements by ECU address (hex format: 0x1234ABCD)")
    print("")
    print("Examples:")
    print("  python a2lmeasurement.py engine.a2l --csv measurements.csv")
    print("  python a2lmeasurement.py engine.a2l RPM MAP:ManifoldPressure LAMBDA")
    print("  python a2lmeasurement.py engine.a2l n_tcha:TurboSpeed --debug")
    print("  python a2lmeasurement.py engine.a2l --addr 0xb00095fc:TurboSpeed")
    print("  python a2lmeasurement.py engine.a2l --addr 0x12345678 0xABCDEF00:CustomName")

if len(argv) < 3:
    print_usage()
    sys.exit(1)

db = DB()
print("Opening A2l as database")

# Check if database exists, if so open it, otherwise try to import A2L file
if path.exists(f"{argv[1]}.a2ldb"):
    session = db.open_existing(argv[1])
elif path.exists(f"{argv[1]}.a2l"):
    session = db.import_a2l(argv[1])
else:
    print(f"Error: Neither {argv[1]}.a2ldb nor {argv[1]}.a2l found")
    sys.exit(1)

print("A2l Opened as database")

header = (
    "Name",
    "Unit",
    "Equation",
    "Format",
    "Address",
    "Length",
    "Signed",
    "ProgMin",
    "ProgMax",
    "WarnMin",
    "WarnMax",
    "Smoothing",
    "Enabled",
    "Tabs",
    "Assign To",
)


data_sizes = {
    "UWORD": 2,
    "UBYTE": 1,
    "SBYTE": 1,
    "SWORD": 2,
    "ULONG": 4,
    "SLONG": 4,
    "FLOAT32_IEEE": 4,
}


categories = []



# Helpers



# A2L to "normal" conversion methods


def fix_degree(bad_string):
    return re.sub(
        "\uFFFD", "\u00B0", bad_string
    )  # Replace Unicode "unknown" with degree sign


def coefficients_to_equation(coefficients):
    # Handle both dictionary-style and object-style coefficients
    if hasattr(coefficients, 'a'):
        # Object-style coefficients (pya2l.model.Coeffs)
        a, b, c, d, e, f = (
            str(coefficients.a),
            str(coefficients.b),
            str(coefficients.c),
            str(coefficients.d),
            str(coefficients.e),
            str(coefficients.f),
        )
    else:
        # Dictionary-style coefficients
        a, b, c, d, e, f = (
            str(coefficients["a"]),
            str(coefficients["b"]),
            str(coefficients["c"]),
            str(coefficients["d"]),
            str(coefficients["e"]),
            str(coefficients["f"]),
        )
    
    if a == "0.0" and d == "0.0":  # Polynomial is of order 1, ie linear
        return f"(({f} * x) - {c} ) / ({b} - ({e} * x))"
    else:
        return "Cannot handle polynomial ratfunc because we do not know how to invert!"


def process_measurement(session, param_name, custom_name="", debug=False):
    """Process a single measurement and return the output row data"""
    measurement = (
        session.query(model.Measurement)
        .order_by(model.Measurement.name)
        .filter(model.Measurement.name == param_name)
        .first()
    )
    
    if measurement is None:
        print("******** Could not find ! ", param_name)
        return None

    if debug:
        print(f"\n=== Debug info for {param_name} ===")
        print(f"Available attributes: {[attr for attr in dir(measurement) if not attr.startswith('_')]}")
        
        # Debug ECU address attributes
        print(f"ecu_address value: {getattr(measurement, 'ecu_address', 'NOT_FOUND')}")
        print(f"ecu_address type: {type(getattr(measurement, 'ecu_address', None))}")
        
        # Debug conversion method
        conversion = getattr(measurement, 'conversion', None)
        if conversion:
            print(f"Conversion object type: {type(conversion)}")
            print(f"Conversion attributes: {[attr for attr in dir(conversion) if not attr.startswith('_')]}")

    # Access measurement properties directly
    try:
        # Get computation method for unit and coefficients
        compu_method = None
        unit = ""
        math = "No conversion available"
        
        # Try multiple attribute names for computation method
        for attr_name in ['compuMethod', 'conversion', 'compu_method', 'conversionMethod']:
            compu_method = getattr(measurement, attr_name, None)
            if compu_method is not None:
                if debug:
                    print(f"Found computation method via: {attr_name}")
                break
        
        if compu_method:
            # If conversion is a string, it's likely a reference to a CompuMethod
            if isinstance(compu_method, str):
                if debug:
                    print(f"Conversion is string reference: {compu_method}")
                # Try to find the actual CompuMethod object
                try:
                    actual_compu_method = (
                        session.query(model.CompuMethod)
                        .filter(model.CompuMethod.name == compu_method)
                        .first()
                    )
                    if actual_compu_method:
                        compu_method = actual_compu_method
                        if debug:
                            print(f"Found CompuMethod object: {compu_method.name}")
                    else:
                        if debug:
                            print(f"Could not find CompuMethod: {compu_method}")
                        compu_method = None
                except Exception as e:
                    if debug:
                        print(f"Error looking up CompuMethod: {e}")
                    compu_method = None
            
            if compu_method and not isinstance(compu_method, str):
                # Try to get unit
                for unit_attr in ['unit', 'unitRef', 'physUnit']:
                    unit = getattr(compu_method, unit_attr, "")
                    if unit:
                        if debug:
                            print(f"Found unit via: {unit_attr} = '{unit}'")
                        break
                
                # Try to get coefficients for equation
                coeffs = None
                for coeff_attr in ['coeffs', 'coefficients', 'ratFunc', 'formula']:
                    coeffs = getattr(compu_method, coeff_attr, None)
                    if coeffs is not None:
                        if debug:
                            print(f"Found coefficients via: {coeff_attr}")
                            print(f"Coefficients type: {type(coeffs)}")
                            print(f"Coefficients value: {coeffs}")
                        break
                
                if coeffs:
                    try:
                        math = coefficients_to_equation(coeffs)
                    except Exception as e:
                        if debug:
                            print(f"Error processing coefficients: {e}")
                        math = "Conversion error"
        
        if debug:
            print(f"Unit: '{unit}', Math: '{math}'")
        
        output_row = []
        
        if len(custom_name) > 0:
            output_row.append(custom_name)
        else: 
            output_row.append(measurement.name)
        output_row.append(unit)
        output_row.append(math)
        
        # Handle format - try to extract clean format string
        format_val = getattr(measurement, 'format', None)
        if format_val is not None:
            if hasattr(format_val, 'formatString'):
                # Extract format string from format object
                format_str = getattr(format_val, 'formatString', '%7.0')
                # Clean up format string - remove % and add f
                clean_format = format_str.replace('%', '').replace('f', '') + 'f'
                output_row.append(clean_format)
            else:
                # If it's already a string or number
                output_row.append(str(format_val) + "f")
        else:
            output_row.append("0f")
        
        # Try multiple attribute names for ECU address
        ecu_address = 0
        
        # First try direct attributes
        for addr_attr in ['ecuAddress', 'address', 'memoryAddress', 'ecuAddr', 'addr', 'ecu_address']:
            addr_val = getattr(measurement, addr_attr, None)
            if addr_val is not None and addr_val != 0:
                # Handle EcuAddress objects
                if hasattr(addr_val, 'address'):
                    ecu_address = addr_val.address
                    if debug:
                        print(f"Found ECU address via: {addr_attr}.address = {hex(ecu_address)}")
                else:
                    ecu_address = addr_val
                    if debug:
                        print(f"Found ECU address via: {addr_attr} = {hex(ecu_address)}")
                break
        
        # If still no address, try to get it from nested objects
        if ecu_address == 0:
            for nested_attr in ['ecuAddressExtension', 'memLayout', 'layout', 'ecu_address_extension']:
                nested_obj = getattr(measurement, nested_attr, None)
                if nested_obj:
                    for addr_attr in ['address', 'ecuAddress', 'offset']:
                        addr_val = getattr(nested_obj, addr_attr, None)
                        if addr_val is not None and addr_val != 0:
                            if hasattr(addr_val, 'address'):
                                ecu_address = addr_val.address
                            else:
                                ecu_address = addr_val
                            if debug:
                                print(f"Found ECU address via: {nested_attr}.{addr_attr} = {hex(ecu_address)}")
                            break
                    if ecu_address != 0:
                        break
        
        output_row.append(str(hex(ecu_address)))
        
        # Get datatype and determine size
        datatype = getattr(measurement, 'datatype', 'UWORD')
        output_row.append(str(data_sizes.get(datatype, 2)))
        
        # Determine if signed based on datatype
        if datatype and datatype.startswith('S'):
            output_row.append("TRUE")
        else:
            output_row.append("FALSE")
            
        # Get limits
        lower_limit = getattr(measurement, 'lowerLimit', 0)
        upper_limit = getattr(measurement, 'upperLimit', 0)
        output_row.append(str(lower_limit))
        output_row.append(str(upper_limit))
        output_row.append(str(lower_limit))
        output_row.append(str(upper_limit))
        output_row.append("0")
        output_row.append("TRUE")
        output_row.append("")
        output_row.append("")

        if debug:
            print(f"Final output row: {output_row}")
            print("=== End debug info ===\n")

        return output_row
        
    except Exception as e:
        print(f"Error processing measurement {param_name}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None


def process_csv_input(session, csv_file, debug=False):
    """Process measurements from CSV file"""
    measurements = []
    
    with open(csv_file, encoding="utf-8-sig") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            param_name = row["Param Name"]
            custom_name = row["Custom Name"]
            
            output_row = process_measurement(session, param_name, custom_name, debug)
            if output_row is not None:
                measurements.append(output_row)
    
    return measurements


def process_individual_args(session, param_args, debug=False):
    """Process measurements from individual command line arguments"""
    measurements = []
    
    for param_spec in param_args:
        # Skip debug flag if it appears in arguments
        if param_spec == '--debug':
            continue
            
        # Split on colon to separate param name from custom name
        if ':' in param_spec:
            param_name, custom_name = param_spec.split(':', 1)
        else:
            param_name = param_spec
            custom_name = ""
        
        output_row = process_measurement(session, param_name, custom_name, debug)
        if output_row is not None:
            measurements.append(output_row)
    
    return measurements


def find_measurement_by_address(session, target_address, debug=False):
    """Find a measurement by its ECU address"""
    if debug:
        print(f"Searching for measurement at address: {hex(target_address)}")
    
    # Query all measurements and check their addresses
    measurements = session.query(model.Measurement).all()
    
    for measurement in measurements:
        # Try to get ECU address from the measurement
        for addr_attr in ['ecu_address', 'ecuAddress', 'address']:
            addr_val = getattr(measurement, addr_attr, None)
            if addr_val is not None:
                # Handle EcuAddress objects
                if hasattr(addr_val, 'address'):
                    ecu_address = addr_val.address
                else:
                    ecu_address = addr_val
                
                if ecu_address == target_address:
                    if debug:
                        print(f"Found measurement: {measurement.name} at address {hex(ecu_address)}")
                    return measurement.name
    
    if debug:
        print(f"No measurement found at address {hex(target_address)}")
    return None


def generate_human_readable_name(param_name):
    """Convert technical parameter names to human-readable names"""
    # Common automotive parameter name mappings
    name_mappings = {
        'n_tcha': 'TurboSpeed',
        'n_mot': 'EngineRPM',
        'n_eng': 'EngineRPM',
        'rpm': 'EngineRPM',
        'p_map': 'ManifoldPressure',
        'p_boost': 'BoostPressure',
        'p_rail': 'FuelRailPressure',
        't_air': 'IntakeAirTemp',
        't_cool': 'CoolantTemp',
        't_oil': 'OilTemp',
        't_exh': 'ExhaustTemp',
        'lambda': 'AirFuelRatio',
        'afr': 'AirFuelRatio',
        'maf': 'MassAirFlow',
        'map': 'ManifoldPressure',
        'tps': 'ThrottlePosition',
        'ign_adv': 'IgnitionAdvance',
        'timing': 'IgnitionTiming',
        'inj_time': 'InjectorPulseWidth',
        'fuel_flow': 'FuelFlow',
        'boost': 'BoostPressure',
        'vvt': 'VariableValveTiming',
        'knock': 'KnockSensor',
        'o2': 'OxygenSensor',
        'egt': 'ExhaustGasTemp',
        'baro': 'BarometricPressure',
        'vss': 'VehicleSpeed',
        'gear': 'GearPosition',
        'clutch': 'ClutchPosition',
        'brake': 'BrakePressure',
        'acc_ped': 'AcceleratorPedal',
        'turbo': 'TurbochargerSpeed',
        'wastegate': 'WastegatePosition',
        'intercooler': 'IntercoolerTemp',
        'dpf': 'DieselParticulateFilter',
        'egr': 'ExhaustGasRecirculation'
    }
    
    # Convert to lowercase for matching
    param_lower = param_name.lower()
    
    # Check for exact matches first
    if param_lower in name_mappings:
        return name_mappings[param_lower]
    
    # Check for partial matches
    for key, readable_name in name_mappings.items():
        if key in param_lower or param_lower in key:
            return readable_name
    
    # If no match found, try to make it more readable by capitalizing and removing underscores
    readable = param_name.replace('_', ' ').title()
    return readable


def process_address_args(session, addr_args, debug=False):
    """Process measurements from ECU address arguments"""
    measurements = []
    
    for addr_spec in addr_args:
        # Skip debug flag if it appears in arguments
        if addr_spec == '--debug':
            continue
            
        # Split on colon to separate address from custom name
        if ':' in addr_spec:
            addr_str, custom_name = addr_spec.split(':', 1)
        else:
            addr_str = addr_spec
            custom_name = ""
        
        # Parse the address (handle both hex and decimal)
        try:
            if addr_str.startswith('0x') or addr_str.startswith('0X'):
                target_address = int(addr_str, 16)
            else:
                target_address = int(addr_str)
        except ValueError:
            print(f"Error: Invalid address format: {addr_str}")
            continue
        
        # Find the measurement by address
        param_name = find_measurement_by_address(session, target_address, debug)
        
        if param_name:
            # If no custom name provided, generate a human-readable one
            if not custom_name:
                custom_name = generate_human_readable_name(param_name)
            
            output_row = process_measurement(session, param_name, custom_name, debug)
            if output_row is not None:
                measurements.append(output_row)
        else:
            print(f"******** Could not find measurement at address {hex(target_address)}")
    
    return measurements


# Begin - Main processing logic

# Check for debug flag
debug_mode = '--debug' in argv

output_csv = []
output_csv.append(",".join(header))

# Determine input method and process accordingly
if len(argv) >= 3 and argv[2] == "--csv":
    if len(argv) < 4:
        print("Error: --csv option requires a CSV file argument")
        print_usage()
        sys.exit(1)
    
    print("Processing measurements from CSV file:", argv[3])
    if debug_mode:
        print("Debug mode enabled")
    measurements = process_csv_input(session, argv[3], debug_mode)
elif len(argv) >= 3 and argv[2] == "--addr":
    if len(argv) < 4:
        print("Error: --addr option requires at least one address argument")
        print_usage()
        sys.exit(1)
    
    print("Processing measurements from ECU addresses")
    if debug_mode:
        print("Debug mode enabled")
    addr_args = argv[3:]  # All arguments after --addr
    measurements = process_address_args(session, addr_args, debug_mode)
else:
    print("Processing measurements from command line arguments")
    if debug_mode:
        print("Debug mode enabled")
    param_args = argv[2:]  # All arguments after the A2L file
    measurements = process_individual_args(session, param_args, debug_mode)

# Convert measurements to CSV format
for measurement in measurements:
    output_csv.append(",".join(measurement))

# Write output file
output_filename = argv[1] + "_params.csv"
with open(output_filename, 'w') as output_file:
    for row in output_csv:
        output_file.write(row + "\n")

print(f"Output written to: {output_filename}")
print(f"Processed {len(measurements)} measurements")
