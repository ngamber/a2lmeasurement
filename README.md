# A2L Measurement Processor

This script processes A2L measurement data and converts it to CSV format for use with tuning software.

## Features

- **Multiple Input Methods**: Accept measurements from CSV files, command line arguments, or ECU addresses
- **ECU Address Lookup**: Find measurements by their ECU memory address with automatic name generation
- **Custom Names**: Support for custom parameter names using colon separator
- **Human-Readable Names**: Automatic generation of readable names from technical parameter names
- **Backward Compatibility**: Existing CSV workflows continue to work unchanged
- **Error Handling**: Robust error handling with clear feedback

## Installation

The script requires the `pya2l` library. A virtual environment has been set up with all dependencies:

```bash
# The virtual environment is already created in the 'venv' directory
# Use the wrapper script to run with proper environment
```

## Usage

### Method 1: Individual Arguments (New)

```bash
# Using the wrapper script (recommended) - use database name without extension if .a2ldb exists
./run_a2lmeasurement.sh SCGA05_OEM n_tcha Air_tIn_VW tps

# With custom names using colon separator
./run_a2lmeasurement.sh SCGA05_OEM n_tcha:TurboSpeed Air_tIn_VW:IntakeTemp tps:ThrottlePosition

# Direct python execution (requires virtual environment activation)
source venv/bin/activate
python a2lmeasurement.py SCGA05_OEM n_tcha:TurboSpeed Air_tIn_VW:IntakeTemp tps
```

### Method 2: ECU Address Lookup (New)

```bash
# Look up measurements by ECU memory address
./run_a2lmeasurement.sh SCGA05_OEM --addr 0xb0009908

# With custom names
./run_a2lmeasurement.sh SCGA05_OEM --addr 0xb0009908:"Lambda"

# Multiple addresses
./run_a2lmeasurement.sh SCGA05_OEM --addr 0xb0009908:"Lambda" 0x12345678:"Another Param"

# Mix of addresses with and without custom names
./run_a2lmeasurement.sh SCGA05_OEM --addr 0xb0009908:"Lambda" 0x87654321
```

**ECU Address Format:**
- Addresses must be in hexadecimal format: `0x1234ABCD`
- Custom names are optional and specified with colon separator: `0xADDRESS:CustomName`
- If no custom name is provided, a human-readable name is automatically generated
- The script searches the A2L database to find the measurement at the specified address

### Method 3: CSV Input (Original)

```bash
# Using the wrapper script
./run_a2lmeasurement.sh SCGA05_OEM.a2l --csv measurements.csv

# Direct python execution
source venv/bin/activate
python a2lmeasurement.py SCGA05_OEM.a2l --csv measurements.csv
```

## CSV Input Format

When using CSV input, the file should have these columns:
- `Param Name`: The parameter name to look up in the A2L file
- `Custom Name`: Optional custom name to use instead of the parameter name

## Output

The script generates a CSV file named `<a2l_file>_params.csv` with the following columns:
- Name, Unit, Equation, Format, Address, Length, Signed, ProgMin, ProgMax, WarnMin, WarnMax, Smoothing, Enabled, Tabs, Assign To

## Examples

```bash
# Process specific measurements from SCGA05_OEM database
./run_a2lmeasurement.sh SCGA05_OEM.a2l n_tcha Air_tIn_VW gear

# Process with custom names
./run_a2lmeasurement.sh SCGA05_OEM.a2l n_tcha:TurboSpeed Air_tIn_VW:IntakeTemp gear:GearPosition

# Process from CSV file
./run_a2lmeasurement.sh SCGA05_OEM.a2l --csv measurements.csv

# Process using ECU addresses
./run_a2lmeasurement.sh SCGA05_OEM.a2l --addr 0xb0009908:Lambda
```

## Changes Made

1. **Added argument parsing** to support both CSV and individual parameter inputs
2. **Refactored code** into reusable functions for better maintainability
3. **Enhanced error handling** with detailed error messages
4. **Added usage instructions** that display when arguments are insufficient
5. **Created wrapper script** for easy execution with virtual environment
6. **Updated API calls** to work with current pya2l library version
7. **Maintained backward compatibility** with existing CSV workflows

## Files

- `a2lmeasurement.py`: Main script with enhanced functionality
- `run_a2lmeasurement.sh`: Wrapper script for easy execution
- `venv/`: Virtual environment with required dependencies
- `README.md`: This documentation file
