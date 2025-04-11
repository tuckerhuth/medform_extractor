# launch.py
import os
import sys
import subprocess
import signal
import atexit
import time
import fcntl
import site

def cleanup():
    print("Cleanup: Starting cleanup process")
    try:
        if QApplication.instance():
            # Process any pending events before cleanup
            QApplication.instance().processEvents()
            QApplication.instance().closeAllWindows()
            
        # Clean up lock file
        if hasattr(cleanup, 'lock_file') and cleanup.lock_file:
            fcntl.flock(cleanup.lock_file, fcntl.LOCK_UN)
            cleanup.lock_file.close()
            try:
                os.unlink('.qt_lock')
            except FileNotFoundError:
                pass
    except Exception as e:
        print(f"Cleanup: Error during cleanup - {e}")
    print("Cleanup: Finished cleanup process")

# Register cleanup for normal program termination
atexit.register(cleanup)

# Handle signals
def signal_handler(signum, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- Configuration ---
VENV_DIR = ".venv"
EXTRACT_TEXT_SCRIPT = "extract_text.py"
EXTRACT_FIELDS_SCRIPT = "extract_fields.py"
DEFAULT_TEXT_OUTPUT_DIR = "extracted_text"
DEFAULT_FIELDS_OUTPUT_DIR = "extracted_fields"
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.qt_lock')

def acquire_lock():
    """Try to acquire the lock file"""
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        cleanup.lock_file = lock_fd  # Store the file descriptor in cleanup function
        return lock_fd
    except (IOError, OSError):
        return None

def release_lock(lock_fd):
    """Release the lock file"""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            try:
                os.unlink(LOCK_FILE)
            except FileNotFoundError:
                pass
        except (IOError, OSError) as e:
            print(f"Error releasing lock: {e}")

from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                              QLabel, QFileDialog, QWidget, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QProcess

class ImageProcessorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.text_output_dir = os.path.join(self.script_dir, DEFAULT_TEXT_OUTPUT_DIR)
        self.fields_output_dir = os.path.join(self.script_dir, DEFAULT_FIELDS_OUTPUT_DIR)
        self.current_total_files = 0 # To store total files for progress display
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Image Text Extractor')
        self.setGeometry(300, 300, 550, 350)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # --- Text Extraction Section ---
        text_layout = QVBoxLayout()
        text_layout.addWidget(QLabel("<b>Step 1: Extract Text from Images</b>"))
        
        # Selected folder label
        self.image_folder_label = QLabel('No image folder selected')
        self.image_folder_label.setAlignment(Qt.AlignCenter)
        text_layout.addWidget(self.image_folder_label)
        
        # Button layout
        text_button_layout = QHBoxLayout()
        
        # Select folder button
        select_btn = QPushButton('Select Image Folder')
        select_btn.clicked.connect(self.select_folder)
        select_btn.setMinimumWidth(200)
        text_button_layout.addWidget(select_btn)
        
        # Process button
        self.extract_text_btn = QPushButton('Extract Text')
        self.extract_text_btn.clicked.connect(self.run_text_extraction)
        self.extract_text_btn.setEnabled(False)
        self.extract_text_btn.setStyleSheet('background-color: #4a9eff; color: white;')
        self.extract_text_btn.setFixedWidth(120)
        text_button_layout.addWidget(self.extract_text_btn)
        
        text_layout.addLayout(text_button_layout)

        # Progress Bar - Moved under Step 1
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        text_layout.addWidget(self.progress_bar) # Add to text_layout
        
        layout.addLayout(text_layout)
        
        # --- Field Extraction Section ---
        fields_layout = QVBoxLayout()
        fields_layout.addWidget(QLabel("<hr>")) # Separator
        fields_layout.addWidget(QLabel("<b>Step 2: Extract Fields from Text</b>"))
        
        # Text folder label (defaults to output of step 1)
        self.text_folder_label = QLabel(f'Using text files from: {DEFAULT_TEXT_OUTPUT_DIR}')
        self.text_folder_label.setAlignment(Qt.AlignCenter)
        fields_layout.addWidget(self.text_folder_label)
        
        # Button layout for fields
        fields_button_layout = QHBoxLayout()
        
        # Select Text Folder button (optional override)
        select_text_btn = QPushButton('Select Text Folder (Optional)')
        select_text_btn.clicked.connect(self.select_text_folder)
        select_text_btn.setMinimumWidth(200)
        fields_button_layout.addWidget(select_text_btn)
        
        # Extract Fields button
        self.extract_fields_btn = QPushButton('Extract Fields')
        self.extract_fields_btn.clicked.connect(self.run_field_extraction)
        self.extract_fields_btn.setEnabled(False) # Enabled when text dir exists
        self.extract_fields_btn.setStyleSheet('background-color: #2ecc71; color: white;') # Green button
        self.extract_fields_btn.setFixedWidth(120)
        fields_button_layout.addWidget(self.extract_fields_btn)
        
        fields_layout.addLayout(fields_button_layout)
        layout.addLayout(fields_layout)

        # Status Area (Label + Copy Button)
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel('Select a folder to begin')
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status_layout.addWidget(self.status_label, 1)
        
        self.copy_error_btn = QPushButton('Copy Error')
        self.copy_error_btn.clicked.connect(self.copy_error_to_clipboard)
        self.copy_error_btn.setVisible(False)
        self.copy_error_btn.setFixedWidth(100)
        status_layout.addWidget(self.copy_error_btn)
        
        layout.addLayout(status_layout)
        
        # Add Quit button
        quit_btn = QPushButton('Quit')
        quit_btn.clicked.connect(self.quit_application)
        quit_btn.setStyleSheet('background-color: #ff6b6b;')
        layout.addWidget(quit_btn)
        
        self.selected_image_folder = None
        self.selected_text_folder = self.text_output_dir # Default
        self.update_field_extraction_button_state() # Initial check

    def update_field_extraction_button_state(self):
        """Enable field extraction if the text folder exists."""
        can_extract = os.path.isdir(self.selected_text_folder)
        self.extract_fields_btn.setEnabled(can_extract)
        if not can_extract:
            self.status_label.setText("Run Step 1 or select a valid text folder for Step 2.")
        
    def quit_application(self):
        """Cleanly quit the application"""
        print("Quitting application...")
        if self.process is not None:
            self.process.kill()
            self.process = None
        # Process any pending events
        QApplication.processEvents()
        # Clean up and quit
        cleanup()
        QApplication.instance().quit()
        
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Image Folder')
        if folder:
            self.selected_image_folder = folder
            self.image_folder_label.setText(f'Selected: {folder}')
            self.extract_text_btn.setEnabled(True)
            self.status_label.setText('Ready to process')
            self.copy_error_btn.setVisible(False)
            
    def select_text_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder with Extracted Text JSONs', self.text_output_dir)
        if folder:
            self.selected_text_folder = folder
            self.text_folder_label.setText(f'Using text files from: {os.path.basename(folder)}')
            self.update_field_extraction_button_state()
            if self.extract_fields_btn.isEnabled():
                self.status_label.setText('Ready to extract fields')
            self.copy_error_btn.setVisible(False)
            
    def copy_error_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.status_label.text())
        
    def closeEvent(self, event):
        """Handle window close button click"""
        print("Window close requested...")
        self.quit_application()
        event.accept()
        
    def run_text_extraction(self):
        if not self.selected_image_folder or self.process is not None:
            return
            
        # Get the Python executable from virtual environment
        venv_python = sys.executable
        os.makedirs(self.text_output_dir, exist_ok=True)
        
        try:
            # Count total files (scan recursively)
            from src.scanner import scan_directory
            total_files = len(list(scan_directory(self.selected_image_folder)))
            self.current_total_files = total_files # Store for status display
            
            if total_files == 0:
                self.status_label.setText('No image files found in the selected folder or subfolders')
                return
                
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(total_files)
            self.progress_bar.setValue(0)
            
            self.status_label.setText('Extracting text from images...')
            self.copy_error_btn.setVisible(False)
            self.extract_text_btn.setEnabled(False)
            self.extract_fields_btn.setEnabled(False)
            
            # Step 1: Extract text
            self.process = QProcess()
            self.process.setWorkingDirectory(self.script_dir)
            
            # Connect signals
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)
            self.process.finished.connect(self.text_extraction_finished)
            
            # Start text extraction
            extract_text_script = os.path.join(self.script_dir, EXTRACT_TEXT_SCRIPT)
            self.process.start(venv_python, [
                extract_text_script,
                self.selected_image_folder,
                '--output-dir', self.text_output_dir
            ])
            
        except Exception as e:
            self.handle_error(f'An unexpected error occurred: {str(e)}')
            
    def text_extraction_finished(self, exit_code, exit_status):
        """Handle completion of text extraction step."""
        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()

        if exit_code != 0:
            self.handle_error(f'Text extraction failed with exit code {exit_code}')
        else:
            self.status_label.setText('Text extraction complete. Ready for Step 2.')
            
        self.progress_bar.setVisible(False)
        self.process = None
        
    def run_field_extraction(self):
        if not self.selected_text_folder or self.process is not None:
            return
         
        # Count total files
        try:
            json_files = [f for f in os.listdir(self.selected_text_folder) if f.endswith('.json')]
            total_files = len(json_files)
            self.current_total_files = total_files # Store for status display
            if total_files == 0:
                self.status_label.setText('No text JSON files found in the selected folder')
                return
        except FileNotFoundError:
            self.status_label.setText(f'Error: Text folder not found: {self.selected_text_folder}')
            return

        venv_python = sys.executable # Use the current executable
        os.makedirs(self.fields_output_dir, exist_ok=True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total_files)
        self.progress_bar.setValue(0)

        # Start field extraction
        self.status_label.setText('Extracting fields from text...')
        self.copy_error_btn.setVisible(False)
        self.extract_text_btn.setEnabled(False)
        self.extract_fields_btn.setEnabled(False)
        
        self.process = QProcess()
        self.process.setWorkingDirectory(self.script_dir)
        
        # Connect signals
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.field_extraction_finished)
        
        # Start field extraction
        extract_fields_script = os.path.join(self.script_dir, EXTRACT_FIELDS_SCRIPT)
        self.process.start(venv_python, [
            extract_fields_script,
            self.selected_text_folder,
            '--output-dir', self.fields_output_dir
        ])
        
    def field_extraction_finished(self, exit_code, exit_status):
        """Handle completion of field extraction step."""
        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()

        if exit_code == 0:
            self.status_label.setText('Processing complete! Results saved in extracted_fields directory')
        else:
            self.handle_error(f'Field extraction failed with exit code {exit_code}')
            
        self.copy_error_btn.setVisible(exit_code != 0)
        self.progress_bar.setVisible(False)
        self.process = None
        
    def handle_stdout(self):
        if self.process is None:
            return
        output = self.process.readAllStandardOutput().data().decode().strip()
        
        # Store the last non-progress message
        last_status_message = ""
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('PROGRESS:'):
                try:
                    current = int(line.split(':')[1])
                    self.progress_bar.setValue(current)
                    # Update status label with combined progress and last status
                    progress_text = f"Processing file {current}/{self.current_total_files}"
                    self.status_label.setText(f"{progress_text}: {last_status_message}")
                except (IndexError, ValueError):
                    self.status_label.setText("Error parsing progress update.")
            elif line:
                last_status_message = line # Store the latest status
                # Update status label, potentially combining with current progress if available
                if self.progress_bar.isVisible():
                    current = self.progress_bar.value()
                    progress_text = f"Processing file {current}/{self.current_total_files}"
                    self.status_label.setText(f"{progress_text}: {last_status_message}")
                else:
                    self.status_label.setText(last_status_message)
                
    def handle_stderr(self):
        if self.process is None:
            return
        error = self.process.readAllStandardError().data().decode().strip()
        if error:
            self.handle_error(f'Error during processing: {error}')
            
    def handle_error(self, error_msg):
        self.status_label.setText(error_msg)
        self.copy_error_btn.setVisible(True)
        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()
        self.progress_bar.setVisible(False)
        if self.process is not None:
            self.process.kill()
            self.process = None

def main():
    # Try to acquire the lock
    lock_fd = acquire_lock()
    if not lock_fd:
        print("Another instance is already running or didn't clean up properly.")
        print("Cleaning up old lock file...")
        try:
            os.unlink(LOCK_FILE)
            lock_fd = acquire_lock()
            if not lock_fd:
                print("Still cannot acquire lock. Please try again.")
                sys.exit(1)
        except (IOError, OSError):
            print("Failed to clean up lock file. Please try again.")
            sys.exit(1)

    try:
        # Launch GUI
        app = QApplication(sys.argv)
        ex = ImageProcessorUI()
        ex.show()
        return_code = app.exec()
        cleanup()
        sys.exit(return_code)
    finally:
        # The atexit handler takes care of releasing the lock on normal exit
        # We no longer need to explicitly call release_lock here.
        # release_lock(lock_fd)
        pass

if __name__ == '__main__':
    main() 