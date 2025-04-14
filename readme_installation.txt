Image Extractor - Installation Guide
================================

Prerequisites
------------
1. macOS 10.15 or later
2. Miniconda or Anaconda installed
   - If not installed, download from: https://docs.conda.io/en/latest/miniconda.html
   - Follow the installer instructions for your system

Installation Steps
----------------
1. Create the app directory in your Documents folder:
   ```
   mkdir -p ~/Documents/image_extract
   ```

2. Copy all application files to this directory:
   - Make sure all files are copied to: ~/Documents/image_extract/
   - Required files include:
     * environment.yml
     * setup.sh
     * launch.py
     * src/ directory
     * disease_keywords/ directory
     * (and all other app files)

3. Open Terminal:
   - Press Command (⌘) + Space
   - Type "Terminal"
   - Press Enter

4. Navigate to the app directory:
   ```
   cd ~/Documents/image_extract
   ```

5. Make the setup script executable:
   ```
   chmod +x setup.sh
   ```

6. Run the setup script:
   ```
   ./setup.sh
   ```
   - This will create the conda environment with all required dependencies
   - Wait for the setup to complete

Running the App
-------------
After installation, you can run the app using either method:

Method 1 (Single Command):
```
cd ~/Documents/image_extract && conda activate image_extract_dpg && python launch.py
```

Method 2 (Step by Step):
1. Open Terminal
2. Activate the conda environment:
   ```
   conda activate image_extract_dpg
   ```
3. Navigate to the app directory:
   ```
   cd ~/Documents/image_extract
   ```
4. Launch the app:
   ```
   python launch.py
   ```

Troubleshooting
--------------
1. If you see "conda: command not found":
   - Close and reopen your terminal
   - Or run: source ~/.bash_profile or source ~/.zshrc

2. If setup.sh fails:
   - Make sure you're in the correct directory
   - Verify all files are copied correctly
   - Check that environment.yml exists

3. If the app won't launch:
   - Ensure you've activated the conda environment
   - Verify you're in the correct directory
   - Check the terminal output for error messages

For additional help or to report issues, please contact the development team. 