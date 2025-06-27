#!/bin/bash
# Wrapper script to run a2lmeasurement.py with the virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment and run the Python script
cd "$SCRIPT_DIR"
source venv/bin/activate
python a2lmeasurement.py "$@"
