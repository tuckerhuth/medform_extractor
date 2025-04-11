#!/bin/bash

# Launch script for the Medical Image OCR & Classification System

# --- Configuration ---
# Path to the virtual environment (relative to this script)
VENV_PATH=".venv"
# Path to the main Python script (relative to this script)
MAIN_SCRIPT="main.py"

# --- Script Logic ---
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit 1

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at '$VENV_PATH'"
    echo "Please run the setup steps first (e.g., python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)"
    exit 1
fi

# Activate virtual environment
# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"

# Check if main script exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Error: Main script not found at '$MAIN_SCRIPT'"
    deactivate
    exit 1
fi

# Check if input directory argument is provided
if [ -z "$1" ]; then
    echo "Usage: ./launch.sh <input_directory> [output_file]"
    echo "  <input_directory>: Path to the folder containing images."
    echo "  [output_file]: Optional path for the JSON output (default: output/results.json)"
    deactivate
    exit 1
fi

# Run the main script with all provided arguments
echo "Launching $MAIN_SCRIPT..."
python "$MAIN_SCRIPT" "$@" # Pass all script arguments to main.py

# Deactivate virtual environment
deactivate

echo "Script finished." 