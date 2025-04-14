#!/bin/bash

# Exit on error
set -e

echo "=== Starting ImageExtractor macOS Build Process ==="

# Ensure we're in the project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Ensure conda environment is active (Assuming it's named image_extract_dpg)
echo "Checking conda environment..."
if [[ "$CONDA_DEFAULT_ENV" != "image_extract_dpg" ]]; then
    echo "Activating conda environment: image_extract_dpg"
    # Try to activate - might need user setup if activation fails in script
    conda activate image_extract_dpg || { echo "Failed to activate conda environment. Please activate it manually and re-run."; exit 1; }
fi

# Install/upgrade required packages (use pip within conda env)
echo "Installing/updating build dependencies..."
# pip install --upgrade pip
# pip install pyinstaller
# pip install dearpygui # Ensure DPG is installed
# pip install pandas # Keep pandas
# pip install openpyxl # Keep openpyxl
# pip install PyYAML # Add PyYAML
# Recommended: Use requirements.txt or environment.yml for consistency
# Ensure build dependencies are met (pyinstaller should be installed)
command -v pyinstaller >/dev/null 2>&1 || { echo >&2 "PyInstaller not found. Please install it in the image_extract_dpg environment (pip install pyinstaller). Aborting."; exit 1; }
echo "Dependencies assumed to be installed via conda environment."


# Run PyInstaller using the correct spec file
echo "Building application using ImageExtractor.spec..."
pyinstaller ImageExtractor.spec

# Verify the build
if [ -d "dist/ImageExtractor.app" ]; then
    echo "=== Build Successful ==="
    echo "Application bundle created at: dist/ImageExtractor.app"
    echo ""
    echo "To install:"
    echo "1. Open Finder"
    echo "2. Navigate to: $(pwd)/dist"
    echo "3. Drag ImageExtractor.app to your Applications folder"
else
    echo "=== Build Failed ==="
    echo "Error: Application bundle was not created"
    exit 1
fi 