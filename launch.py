# launch.py
import os
import sys
import subprocess
import signal
import atexit
import time
import fcntl
import site
import re
import pathlib

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
PROCESS_OCR_SCRIPT = "process_ocr.py"
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
                              QLabel, QFileDialog, QWidget, QProgressBar, QDialog, QGridLayout, QTextEdit, QScrollArea, QMessageBox,
                              QFrame)
from PySide6.QtCore import Qt, QTimer, QProcess

# --- Helper Function for Parsing Markdown Criteria (adapted from process_ocr.py) ---

def parse_confidence_display(item_str):
    """Extracts keyword/pattern and confidence level for display."""
    # Simpler parsing just to get the string as stored
    return item_str.strip().strip('\'"')

def parse_md_section_display(md_content, variable_name):
    """
    Parses a Python dictionary definition (keywords or patterns)
    from a markdown code block for display purposes.
    Returns a dictionary structured like:
    { "Category": ["item1 <conf%>", "item2 <conf%>", ...], ... }
    """
    data_dict = {}
    pattern_str = rf'^\s*{re.escape(variable_name)}\s*=\s*{{(.*?)^\s*}}'
    pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE)
    match = pattern.search(md_content)
    if not match:
        print(f"Warning: Could not find definition block for '{variable_name}' in markdown content.")
        return data_dict

    dict_content = match.group(1).strip()
    category_pattern = re.compile(r'^\s*\"(\w+)\"\s*:\s*\[(.*?)\]', re.DOTALL | re.MULTILINE)

    for cat_match in category_pattern.finditer(dict_content):
        category = cat_match.group(1)
        items_str = cat_match.group(2).strip()
        items_list = []
        # Split items carefully
        raw_items = re.split(r',(?=\s*["\'])', items_str)
        for item_raw in raw_items:
            item_clean = item_raw.strip()
            if item_clean:
                parsed_item = parse_confidence_display(item_clean)
                if parsed_item:
                    items_list.append(parsed_item)
        if items_list:
            data_dict[category] = items_list
    return data_dict

def load_criteria_from_md(md_file_path):
    """Loads all criteria from the markdown file."""
    criteria = {
        "Skin Test": {"Keywords": {}, "Patterns": {}},
        "Blood Test": {"Keywords": {}, "Patterns": {}},
        "X-Ray": {"Keywords": {}, "Patterns": {}}
    }
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        criteria["Skin Test"]["Keywords"] = parse_md_section_display(md_content, "skin_test_keywords")
        criteria["Skin Test"]["Patterns"] = parse_md_section_display(md_content, "skin_test_patterns")
        criteria["Blood Test"]["Keywords"] = parse_md_section_display(md_content, "blood_test_keywords")
        criteria["Blood Test"]["Patterns"] = parse_md_section_display(md_content, "blood_test_patterns")
        criteria["X-Ray"]["Keywords"] = parse_md_section_display(md_content, "xray_keywords")
        criteria["X-Ray"]["Patterns"] = parse_md_section_display(md_content, "xray_patterns") # Attempt to parse, might be empty

    except FileNotFoundError:
        print(f"Error: Criteria file not found at {md_file_path}")
        return None # Indicate error
    except Exception as e:
        print(f"Error parsing criteria file {md_file_path}: {e}")
        return None # Indicate error

    return criteria

# --- Criteria Editor Dialog ---

class CriteriaEditorDialog(QDialog):
    def __init__(self, criteria_data, parent=None):
        super().__init__(parent)
        self.criteria_data = criteria_data
        self.setWindowTitle("View/Edit Detection Criteria")
        self.setMinimumSize(800, 600)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # --- Title and Info Button ---
        title_layout = QHBoxLayout()
        title_label = QLabel("<b>Test Match Criteria</b>")
        title_label.setStyleSheet("font-size: 16pt;") # Make title larger
        title_layout.addWidget(title_label)
        
        info_button = QPushButton("?")
        info_button.setFixedSize(25, 25) # Small square button
        info_button.setToolTip("Click for explanation of the grid")
        info_button.clicked.connect(self.show_info)
        title_layout.addWidget(info_button)
        title_layout.addStretch() # Push title/button left
        main_layout.addLayout(title_layout)
        # --- End Title --- 

        # Use QScrollArea for potentially large content
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        
        content_widget = QWidget()
        grid_layout = QGridLayout(content_widget)
        grid_layout.setSpacing(10)

        # Define rows and columns
        test_types = ["Skin Test", "Blood Test", "X-Ray"]
        source_types = ["Keywords", "Patterns"]
        categories = ["Test", "Process", "Administration", "Documentation"]

        # Create column headers
        for col_idx, category in enumerate(categories):
            header_label = QLabel(f"<b>{category}</b>")
            # Center the header label horizontally and place in correct column (starting at 3)
            grid_layout.addWidget(header_label, 0, col_idx + 3, Qt.AlignCenter)

        current_row = 1
        for test_type in test_types:
            # Center the test type label vertically
            test_type_label = QLabel(f"<b>{test_type}</b>")
            grid_layout.addWidget(test_type_label, current_row, 0, 2, 1, Qt.AlignVCenter | Qt.AlignRight)
            
            # Add vertical separator after the first column (only once per test type)
            if current_row == 1: # Add only for the first test type initially
                 v_separator = QFrame()
                 v_separator.setFrameShape(QFrame.VLine)
                 v_separator.setFrameShadow(QFrame.Sunken)
                 grid_layout.addWidget(v_separator, current_row, 1, 2, 1) # Span 2 rows, column index 1
            else:
                 # Reuse separator logic or ensure it spans correctly
                 v_separator = QFrame()
                 v_separator.setFrameShape(QFrame.VLine)
                 v_separator.setFrameShadow(QFrame.Sunken)
                 grid_layout.addWidget(v_separator, current_row, 1, 2, 1)

            for source_type in source_types:
                grid_layout.addWidget(QLabel(f"<i>{source_type}</i>"), current_row, 2, Qt.AlignRight) # This stays in column 2
                for col_idx, category in enumerate(categories):
                    # Get the list of items for this cell
                    items_list = self.criteria_data.get(test_type, {}).get(source_type, {}).get(category, [])
                    # Format as a multi-line string
                    cell_text = "\n".join(items_list)
                    
                    text_edit = QTextEdit()
                    text_edit.setPlainText(cell_text)
                    text_edit.setLineWrapMode(QTextEdit.WidgetWidth) # Wrap text
                    text_edit.setMinimumHeight(100) # Give some initial height
                    grid_layout.addWidget(text_edit, current_row, col_idx + 3) # Correct column index (starting at 3)
                current_row += 1
            
            # Add horizontal separator after each test type block (except the last one)
            if test_type != test_types[-1]:
                h_separator = QFrame()
                h_separator.setFrameShape(QFrame.HLine)
                h_separator.setFrameShadow(QFrame.Sunken)
                # Span across the keyword/pattern label column and the category columns
                grid_layout.addWidget(h_separator, current_row, 2, 1, len(categories) + 1) 
                current_row += 1 # Increment row for the separator
                
        grid_layout.setRowStretch(current_row, 1) # Allow last row to stretch if needed
        # Set equal stretch for the text edit columns (3, 4, 5, 6)
        for i in range(len(categories)):
             grid_layout.setColumnStretch(i + 3, 1)
        # grid_layout.setColumnStretch(len(categories)+2, 1) # Remove old stretch setting

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Add a close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept) # QDialog's accept() closes it
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)

    def show_info(self):
        """Displays an informational message box explaining the grid."""
        explanation = ( "This grid displays the keywords and regular expression patterns used to detect "
                        "different types of Tuberculosis tests in the extracted text.<br><br>"
                        "<b>Rows:</b><br>"
                        "  • <b>Test Type</b> (Skin Test, Blood Test, X-Ray): The overall category of the test.<br>"
                        "  • <b>Source</b> (Keywords, Patterns):<br>"
                        "      - Keywords: Simple text strings searched for in the document.<br>"
                        "      - Patterns: Regular expressions used for more complex matching (e.g., specific formats, results).<br><br>"
                        "<b>Columns:</b><br>"
                        "  • <b>Test:</b> Terms directly naming the test (e.g., \"PPD\", \"Quantiferon\").<br>"
                        "  • <b>Process:</b> Terms describing how the test is performed (e.g., \"intradermal injection\", \"blood drawn\").<br>"
                        "  • <b>Administration:</b> Terms related to giving or ordering the test (e.g., \"administered\", \"performed\", \"ordered\").<br>"
                        "  • <b>Documentation:</b> Terms related to recording results or findings (e.g., \"mm induration\", \"positive result\", \"chest x-ray findings\").<br><br>"
                        "Confidence values (e.g., &lt;95%&gt;) indicate the estimated reliability of that specific keyword or pattern."
                      )
        # Create QMessageBox instance to allow setting rich text format
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Criteria Grid Explanation")
        msg_box.setTextFormat(Qt.RichText) # Interpret the text as HTML (Set *before* setText)
        # msg_box.setText("Explanation of the criteria grid:") # Remove short main text
        # msg_box.setDetailedText(explanation) # Remove detailed text
        msg_box.setText(explanation) # Set the full explanation directly
        msg_box.setStandardButtons(QMessageBox.Ok)
        # Set a larger minimum size
        msg_box.setMinimumSize(600, 400) 
        msg_box.exec()

class ImageProcessorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.text_output_dir = os.path.join(self.script_dir, DEFAULT_TEXT_OUTPUT_DIR)
        self.fields_output_dir = os.path.join(self.script_dir, DEFAULT_FIELDS_OUTPUT_DIR)
        self.criteria_file_path = os.path.join(self.script_dir, "disease_keywords", "tuberculosis.md") # Path to criteria
        self.current_process_type = None # Track which process is running ('text' or 'fields')
        self.current_total_files = 0
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Image Text Extractor')
        self.setGeometry(300, 300, 550, 400) # Adjusted size slightly more
        
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
        
        # Progress Bar - Step 1
        self.progress_bar_text = QProgressBar() # Renamed
        self.progress_bar_text.setVisible(False)
        text_layout.addWidget(self.progress_bar_text)
        
        # Status Area - Step 1
        status_layout_text = QHBoxLayout()
        self.status_label_text = QLabel('Select an image folder to begin') # Renamed
        self.status_label_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status_layout_text.addWidget(self.status_label_text, 1)
        self.copy_error_btn_text = QPushButton('Copy Error') # Renamed
        self.copy_error_btn_text.clicked.connect(lambda: self.copy_to_clipboard(self.status_label_text.text()))
        self.copy_error_btn_text.setVisible(False)
        self.copy_error_btn_text.setFixedWidth(100)
        status_layout_text.addWidget(self.copy_error_btn_text)
        text_layout.addLayout(status_layout_text)
        
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
        
        # View Criteria button
        self.view_criteria_btn = QPushButton('View Criteria')
        self.view_criteria_btn.clicked.connect(self.open_criteria_editor)
        self.view_criteria_btn.setFixedWidth(120) # Match other button
        fields_button_layout.addWidget(self.view_criteria_btn)

        # Extract Fields button
        self.extract_fields_btn = QPushButton('Extract Fields')
        self.extract_fields_btn.clicked.connect(self.run_field_extraction)
        self.extract_fields_btn.setEnabled(False)
        self.extract_fields_btn.setStyleSheet('background-color: #2ecc71; color: white;')
        self.extract_fields_btn.setFixedWidth(120)
        fields_button_layout.addWidget(self.extract_fields_btn)
        
        fields_layout.addLayout(fields_button_layout)
        
        # Progress Bar - Step 2
        self.progress_bar_fields = QProgressBar()
        self.progress_bar_fields.setVisible(False)
        fields_layout.addWidget(self.progress_bar_fields)
        
        # Status Area - Step 2
        status_layout_fields = QHBoxLayout()
        self.status_label_fields = QLabel('Run Step 1 or select a text folder')
        self.status_label_fields.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        status_layout_fields.addWidget(self.status_label_fields, 1)
        self.copy_error_btn_fields = QPushButton('Copy Error')
        self.copy_error_btn_fields.clicked.connect(lambda: self.copy_to_clipboard(self.status_label_fields.text()))
        self.copy_error_btn_fields.setVisible(False)
        self.copy_error_btn_fields.setFixedWidth(100)
        status_layout_fields.addWidget(self.copy_error_btn_fields)
        fields_layout.addLayout(status_layout_fields)
        
        layout.addLayout(fields_layout)
        
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
            self.status_label_fields.setText("Run Step 1 or select a valid text folder for Step 2.")
        
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
            self.status_label_text.setText('Ready to extract text')
            self.copy_error_btn_text.setVisible(False)
            self.copy_error_btn_fields.setVisible(False) # Hide other error button
            
    def select_text_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder with Extracted Text JSONs', self.text_output_dir)
        if folder:
            self.selected_text_folder = folder
            self.text_folder_label.setText(f'Using text files from: {os.path.basename(folder)}')
            self.update_field_extraction_button_state()
            if self.extract_fields_btn.isEnabled():
                self.status_label_fields.setText('Ready to extract fields')
            self.copy_error_btn_fields.setVisible(False)
            self.copy_error_btn_text.setVisible(False) # Hide other error button
            
    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
    def closeEvent(self, event):
        """Handle window close button click"""
        print("Window close requested...")
        self.quit_application()
        event.accept()
        
    def run_text_extraction(self):
        if not self.selected_image_folder or self.process is not None:
            return
        self.current_process_type = 'text' # Set current process type
        
        # Get the Python executable from virtual environment
        venv_python = sys.executable
        os.makedirs(self.text_output_dir, exist_ok=True)
        
        try:
            # Count total files (scan recursively)
            from src.scanner import scan_directory
            total_files = len(list(scan_directory(self.selected_image_folder)))
            self.current_total_files = total_files # Store for status display
            
            if total_files == 0:
                self.status_label_text.setText('No image files found in the selected folder or subfolders')
                return
                
            self.progress_bar_text.setVisible(True)
            self.progress_bar_text.setMaximum(total_files)
            self.progress_bar_text.setValue(0)
            
            self.status_label_text.setText('Extracting text from images...')
            self.copy_error_btn_text.setVisible(False)
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
            self.status_label_text.setText('Text extraction complete. Ready for Step 2.')
            
        self.progress_bar_text.setVisible(False)
        self.process = None
        self.current_process_type = None # Reset process type
        
    def run_field_extraction(self):
        if self.process:
            return
        
        print("Starting field extraction process...")
        self.current_process_type = 'fields'
        self.progress_bar_fields.setVisible(True)
        self.progress_bar_fields.setValue(0)
        self.status_label_fields.setText('Processing... Finding text files...')
        self.copy_error_btn_fields.setVisible(False)
        self.extract_fields_btn.setEnabled(False)
        self.extract_text_btn.setEnabled(False) # Disable text extraction button too
        
        # Set up the process
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels) # Merge stdout/stderr for simplicity
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.field_extraction_finished)
        
        # Determine the python executable path
        python_executable = sys.executable
        print(f"Using Python executable: {python_executable}")

        # Construct the command for process_ocr.py
        # It reads from INPUT_DIR ("extracted_text") and writes to OUTPUT_DIR ("extracted_fields") by default
        # It doesn't require input/output directory arguments like the old script
        command = [python_executable, os.path.join(self.script_dir, PROCESS_OCR_SCRIPT)]
        print(f"Executing command: {' '.join(command)}")

        # Start the process
        self.process.start(command[0], command[1:])
        if not self.process.waitForStarted(5000): # Wait 5 seconds for start
             error_msg = "Field extraction process failed to start."
             print(f"Error: {error_msg}")
             self.handle_error(error_msg)

    def field_extraction_finished(self, exit_code, exit_status):
        """Handle completion of the field extraction process."""
        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()

        if exit_code == 0:
            self.status_label_fields.setText('Processing complete! Results saved in extracted_fields directory')
        else:
            self.handle_error(f'Field extraction failed with exit code {exit_code}')
            
        self.copy_error_btn_fields.setVisible(exit_code != 0)
        self.progress_bar_fields.setVisible(False)
        self.process = None
        self.current_process_type = None # Reset process type
        
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
                    if self.current_process_type == 'text':
                        self.progress_bar_text.setValue(current)
                        self.status_label_text.setText(f"{current}/{self.current_total_files}")
                    elif self.current_process_type == 'fields':
                        self.progress_bar_fields.setValue(current)
                        self.status_label_fields.setText(f"{current}/{self.current_total_files}")
                except (IndexError, ValueError):
                    if self.current_process_type == 'text':
                        self.status_label_text.setText("Error parsing progress update.")
                    elif self.current_process_type == 'fields':
                        self.status_label_fields.setText("Error parsing progress update.")
            elif line:
                last_status_message = line # Store the latest status
                # Update status label, potentially combining with current progress if available
                if self.current_process_type == 'text' and self.progress_bar_text.isVisible():
                    current = self.progress_bar_text.value()
                    progress_text = f"Processing file {current}/{self.current_total_files}"
                    self.status_label_text.setText(f"{progress_text}: {last_status_message}")
                elif self.current_process_type == 'fields' and self.progress_bar_fields.isVisible():
                    current = self.progress_bar_fields.value()
                    progress_text = f"Processing file {current}/{self.current_total_files}"
                    self.status_label_fields.setText(f"{progress_text}: {last_status_message}")
                else:
                    # If progress bar isn't visible, just show the message in the appropriate label
                    if self.current_process_type == 'text':
                        self.status_label_text.setText(last_status_message)
                    elif self.current_process_type == 'fields':
                        self.status_label_fields.setText(last_status_message)
                
    def handle_stderr(self):
        if self.process is None:
            return
        error = self.process.readAllStandardError().data().decode().strip()
        if error:
            self.handle_error(f'Error during processing: {error}')
            
    def handle_error(self, error_msg):
        if self.current_process_type == 'text':
            self.status_label_text.setText(error_msg)
            self.copy_error_btn_text.setVisible(True)
            self.progress_bar_text.setVisible(False)
        elif self.current_process_type == 'fields':
            self.status_label_fields.setText(error_msg)
            self.copy_error_btn_fields.setVisible(True)
            self.progress_bar_fields.setVisible(False)
        else: # Error occurred before process type was set
            self.status_label_text.setText(error_msg)
            self.copy_error_btn_text.setVisible(True)

        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()
        if self.process is not None:
            self.process.kill()
        self.process = None

    # --- New method to open the criteria editor --- 
    def open_criteria_editor(self):
        print(f"Loading criteria from: {self.criteria_file_path}")
        criteria_data = load_criteria_from_md(self.criteria_file_path)
        if criteria_data:
            dialog = CriteriaEditorDialog(criteria_data, self) # Pass data and parent
            dialog.setWindowState(Qt.WindowFullScreen) # Set to fullscreen
            dialog.exec() # Show as modal dialog
        else:
            # Handle error (e.g., show a message box)
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Warning)
            error_dialog.setWindowTitle("Criteria Error")
            error_dialog.setText(f"Could not load or parse criteria from:\n{self.criteria_file_path}")
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec()
            print("Failed to load criteria data for editor.")

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