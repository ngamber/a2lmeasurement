# A2L Measurement Processor

This script processes A2L measurement data and converts it to CSV format for use with tuning software.

## Features

- **Dual Input Methods**: Accept measurements from CSV files or command line arguments
- **Custom Names**: Support for custom parameter names using colon separator
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
# Using the wrapper script (recommended)
./run_a2lmeasurement.sh engine.a2l RPM MAP LAMBDA

# With custom names using colon separator
./run_a2lmeasurement.sh engine.a2l RPM MAP:ManifoldPressure LAMBDA:AirFuelRatio

# Direct python execution (requires virtual environment activation)
source venv/bin/activate
python a2lmeasurement.py engine.a2l RPM MAP:ManifoldPressure LAMBDA
```

### Method 2: CSV Input (Original)

```bash
# Using the wrapper script
./run_a2lmeasurement.sh engine.a2l --csv measurements.csv

# Direct python execution
source venv/bin/activate
python a2lmeasurement.py engine.a2l --csv measurements.csv
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
# Process specific measurements
./run_a2lmeasurement.sh my_ecu.a2l RPM LOAD TIMING

# Process with custom names
./run_a2lmeasurement.sh my_ecu.a2l RPM:EngineRPM LOAD:EngineLoad TIMING:IgnitionTiming

# Process from CSV file
./run_a2lmeasurement.sh my_ecu.a2l --csv my_measurements.csv
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
