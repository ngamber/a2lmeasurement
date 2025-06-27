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
    print("  CSV input:        python a2lmeasurement.py <a2l_file> --csv <csv_file>")
    print("  Individual args:  python a2lmeasurement.py <a2l_file> <param1> [param2:CustomName] [param3] ...")
    print("")
    print("Examples:")
    print("  python a2lmeasurement.py engine.a2l --csv measurements.csv")
    print("  python a2lmeasurement.py engine.a2l RPM MAP:ManifoldPressure LAMBDA")

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


def process_measurement(session, param_name, custom_name=""):
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

    # Access measurement properties directly
    try:
        # Get computation method for unit and coefficients
        compu_method = getattr(measurement, 'compuMethod', None)
        if compu_method is None:
            compu_method = getattr(measurement, 'conversion', None)
        
        if compu_method and hasattr(compu_method, 'coeffs'):
            math = coefficients_to_equation(compu_method.coeffs)
            unit = getattr(compu_method, 'unit', "")
        elif compu_method and hasattr(compu_method, 'coefficients'):
            math = coefficients_to_equation(compu_method.coefficients)
            unit = getattr(compu_method, 'unit', "")
        else:
            math = "No conversion available"
            unit = ""
        
        output_row = []
        
        if len(custom_name) > 0:
            output_row.append(custom_name)
        else: 
            output_row.append(measurement.name)
        output_row.append(unit)
        output_row.append(math)
        output_row.append(str(getattr(measurement, 'format', 0)) + "f")
        output_row.append(str(hex(getattr(measurement, 'ecuAddress', 0))))
        
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

        return output_row
        
    except Exception as e:
        print(f"Error processing measurement {param_name}: {e}")
        return None


def process_csv_input(session, csv_file):
    """Process measurements from CSV file"""
    measurements = []
    
    with open(csv_file, encoding="utf-8-sig") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            param_name = row["Param Name"]
            custom_name = row["Custom Name"]
            
            output_row = process_measurement(session, param_name, custom_name)
            if output_row is not None:
                measurements.append(output_row)
    
    return measurements


def process_individual_args(session, param_args):
    """Process measurements from individual command line arguments"""
    measurements = []
    
    for param_spec in param_args:
        # Split on colon to separate param name from custom name
        if ':' in param_spec:
            param_name, custom_name = param_spec.split(':', 1)
        else:
            param_name = param_spec
            custom_name = ""
        
        output_row = process_measurement(session, param_name, custom_name)
        if output_row is not None:
            measurements.append(output_row)
    
    return measurements


# Begin - Main processing logic

output_csv = []
output_csv.append(",".join(header))

# Determine input method and process accordingly
if len(argv) >= 3 and argv[2] == "--csv":
    if len(argv) < 4:
        print("Error: --csv option requires a CSV file argument")
        print_usage()
        sys.exit(1)
    
    print("Processing measurements from CSV file:", argv[3])
    measurements = process_csv_input(session, argv[3])
else:
    print("Processing measurements from command line arguments")
    param_args = argv[2:]  # All arguments after the A2L file
    measurements = process_individual_args(session, param_args)

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
