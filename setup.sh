#!/bin/bash

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Image Extractor Setup ===${NC}"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed${NC}"
    echo "Please install Miniconda or Anaconda first:"
    echo "https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "environment.yml" ]; then
    echo -e "${RED}Error: environment.yml not found${NC}"
    echo "Please run this script from the image_extract directory"
    exit 1
fi

echo -e "\n${YELLOW}Step 1: Creating conda environment...${NC}"
conda env create -f environment.yml

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to create conda environment${NC}"
    exit 1
fi

echo -e "\n${GREEN}Setup completed successfully!${NC}"
echo -e "\nTo run the Image Extractor:"
echo -e "1. Copy and paste this command into your terminal:"
echo -e "${YELLOW}cd ~/Documents/image_extract && conda activate image_extract_dpg && python launch.py${NC}"
echo -e "\nOr:"
echo -e "1. Open a new terminal"
echo -e "2. Run: ${YELLOW}conda activate image_extract_dpg${NC}"
echo -e "3. Navigate to the app directory: ${YELLOW}cd ~/Documents/image_extract${NC}"
echo -e "4. Launch the app: ${YELLOW}python launch.py${NC}" 