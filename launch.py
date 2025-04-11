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
import codecs
import pandas as pd
import json
import glob # Import glob for file searching

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
                              QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QProcess

# --- Helper Function for Parsing Markdown Criteria (adapted from process_ocr.py) ---

def parse_confidence_display(item_str):
    """Extracts keyword/pattern and confidence level for display."""
    # Returns the string as it should appear in the text box
    # REVERTED: Simply strip outer quotes, display raw string from MD
    print(f"DEBUG [parse_confidence_display] Input: {repr(item_str)}")
    original_item_str = item_str.strip()
    # item_str_stripped = original_item_str.strip('\'"')
    # Just strip whitespace, keep original quotes from the list item
    final_str = original_item_str
    print(f"DEBUG [parse_confidence_display] Returning raw: {repr(final_str)}")
    return final_str

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
    def __init__(self, criteria_data, md_file_path, parent=None):
        super().__init__(parent)
        self.criteria_data = criteria_data
        self.md_file_path = md_file_path # Store path for saving
        self.text_edits = {} # Initialize the dictionary here
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

        # Add Save and Close buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # --- Re-add Save Button --- 
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_criteria)
        save_button.setDefault(True) # Make it the default button
        button_layout.addWidget(save_button)
        # --- End Re-add Save Button ---
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject) # Use reject for closing without saving
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

    # --- Save Logic Implementation (Validation Removed) ---

    # REMOVED: _parse_regex_for_validation
    # REMOVED: _validate_criteria
    # REMOVED: _update_borders

    def _get_data_from_widgets(self):
        """Extracts the current data from all QTextEdit widgets."""
        # Initialize the nested dictionary structure
        new_criteria_data = {tt: {st: {} for st in ["Keywords", "Patterns"]} for tt in ["Skin Test", "Blood Test", "X-Ray"]}
        
        # Iterate through the stored text edit widgets
        for key, widget in self.text_edits.items():
            test_type, source_type, category = key
            # Get text, split into lines, remove empty lines and strip whitespace
            lines = [line.strip() for line in widget.toPlainText().split('\n') if line.strip()]
            
            # Ensure nested dictionaries exist (should already from initialization)
            if test_type not in new_criteria_data:
                 new_criteria_data[test_type] = {st: {} for st in ["Keywords", "Patterns"]}
            if source_type not in new_criteria_data[test_type]:
                 new_criteria_data[test_type][source_type] = {}
                 
            # Assign the lines to the correct category
            new_criteria_data[test_type][source_type][category] = lines
            
        return new_criteria_data

    def _format_data_for_save(self, new_criteria_data):
        """Formats the extracted data into Python dictionary strings."""
        formatted_strings = {}
        # Define maps here, where they are used
        test_type_map = {"Skin Test": "skin_test", "Blood Test": "blood_test", "X-Ray": "xray"}
        source_type_map = {"Keywords": "keywords", "Patterns": "patterns"}
        categories = ["Test", "Process", "Administration", "Documentation"] # Fixed order

        for test_type_disp, test_type_var in test_type_map.items():
            for source_type_disp, source_type_var in source_type_map.items():
                variable_name = f"{test_type_var}_{source_type_var}"
                current_data = new_criteria_data.get(test_type_disp, {}).get(source_type_disp, {})
                
                lines_out = [] # Initialize list for the current variable block
                lines_out.append(f"{variable_name} = {{")
                
                category_added = False
                for category in categories: # Re-add loop over categories
                    items = current_data.get(category, []) # Fetch items for the category
                    
                    if category_added: # Add comma before next category if not the first
                         lines_out[-1] = lines_out[-1].rstrip(',') + ','
                    lines_out.append(f'    "{category}": [')
                    item_added = False
                    for item in items: # Now iterate through the fetched items
                        if item_added: # Add comma before next item
                            lines_out[-1] = lines_out[-1].rstrip(',') + ','
                        
                        # REVERTED: No special formatting, just use repr
                        lines_out.append(f'        {repr(item)},')
                        item_added = True
                    # Remove trailing comma from the last item if any items were added
                    if item_added:
                        lines_out[-1] = lines_out[-1].rstrip(',') 
                    lines_out.append('    ]') # Closing bracket for category list
                    category_added = True

                # Add trailing comma for the last category
                if category_added:
                     lines_out[-1] += ','

                lines_out.append(f"}}") # Closing brace for the variable
                formatted_strings[variable_name] = '\n'.join(lines_out)
        return formatted_strings

    def _write_to_markdown(self, formatted_strings):
        """Writes the formatted dictionary strings back to the markdown file, replacing existing blocks."""
        try:
            # Read the entire file content first
            with open(self.md_file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            original_content = md_content # Keep a copy for comparison

            # Iterate and replace each variable block
            for variable_name, new_dict_string in formatted_strings.items():
                print(f"Attempting to replace: {variable_name}")
                # Regex to find the specific variable assignment block precisely
                # Looks for variable_name = { potentially spanning multiple lines } including the outer braces
                pattern = re.compile(
                    rf'^{re.escape(variable_name)}\s*=\s*{{.*?^\s*}}',
                    re.DOTALL | re.MULTILINE
                )

                # Replace the entire matched block (including variable name and braces) with the new string
                md_content, num_replacements = pattern.subn(new_dict_string, md_content, count=1)

                if num_replacements == 0:
                     print(f"  Warning: Variable block for '{variable_name}' not found using pattern in {self.md_file_path}. Cannot update.")
                     # Consider appending if not found, but that could break structure. For now, skip.
                else:
                     print(f"  Successfully replaced block for {variable_name}.")

            # Only write if content actually changed to avoid unnecessary modification time updates
            if md_content != original_content:
                print(f"Content changed, writing to {self.md_file_path}")
                with open(self.md_file_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"Successfully saved changes.")
                return True
            else:
                 print("No changes detected. File not modified.")
                 return True # Still considered success as no save was needed

        except FileNotFoundError:
             print(f"Error: File not found for writing: {self.md_file_path}")
             return False
        except IOError as e:
            print(f"Error writing to file {self.md_file_path}: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during file write: {e}")
            return False

    def save_criteria(self):
        """Saves the criteria from the text edits to the markdown file (NO validation)."""
        print("Proceeding with save (no validation)...")
        # is_valid, invalid_widgets = self._validate_criteria() # REMOVED
        # self._update_borders(invalid_widgets) # REMOVED
        
        # Always assume valid and save
        try:
            current_data = self._get_data_from_widgets()
            formatted_data = self._format_data_for_save(current_data)
            
            if self._write_to_markdown(formatted_data):
                QMessageBox.information(self, "Save Successful", "Criteria successfully saved.")
                self.accept() # Close dialog on successful save
            else:
                QMessageBox.critical(self, "Save Failed", f"An error occurred while writing to the markdown file:\n{self.md_file_path}\n\nCheck console output for details.")
        except Exception as e:
             print(f"Error during save process: {e}")
             QMessageBox.critical(self, "Save Error", f"An unexpected error occurred during the save process:\n{e}")

    # --- End Save Logic ---

class ImageProcessorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_folder_path = None
        self.text_folder_path = None # Added to store optional text folder path
        self.text_output_dir = DEFAULT_TEXT_OUTPUT_DIR # Store default or selected dir
        self.fields_output_dir = DEFAULT_FIELDS_OUTPUT_DIR # Store default or selected dir
        self.text_process = QProcess(self)
        self.field_process = QProcess(self)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
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
        
        layout.addStretch(1) # Add stretch before bottom buttons

        # --- Bottom Buttons Layout ---
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch() # Push buttons to the right

        self.export_button = QPushButton("Export Results to Excel") # Export button
        self.export_button.clicked.connect(self.export_results_to_excel)
        self.export_button.setEnabled(False) # Disabled initially
        self.export_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed) # Prevent stretching
        bottom_button_layout.addWidget(self.export_button)

        quit_btn = QPushButton('Quit') # Quit button
        quit_btn.clicked.connect(self.quit_application)
        quit_btn.setStyleSheet('background-color: #ff6b6b;')
        quit_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed) # Prevent stretching
        bottom_button_layout.addWidget(quit_btn)

        layout.addLayout(bottom_button_layout) # Add the horizontal layout to the main vertical layout
        # --- End Bottom Buttons ---

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
        if self.text_process.state() == QProcess.Running:
            self.text_process.kill()
        if self.field_process.state() == QProcess.Running:
            self.field_process.kill()
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
        if not self.selected_image_folder or self.text_process.state() != QProcess.NotRunning:
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
            self.text_process.setWorkingDirectory(self.script_dir)
            
            # Connect signals
            self.text_process.readyReadStandardOutput.connect(self.handle_stdout)
            self.text_process.readyReadStandardError.connect(self.handle_stderr)
            self.text_process.finished.connect(self.text_extraction_finished)
            
            # Start text extraction
            extract_text_script = os.path.join(self.script_dir, EXTRACT_TEXT_SCRIPT)
            self.text_process.start(venv_python, [
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
        self.text_process.terminate()
        self.current_process_type = None # Reset process type
        
    def run_field_extraction(self):
        if self.field_process.state() != QProcess.NotRunning:
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
        self.field_process.setProcessChannelMode(QProcess.MergedChannels) # Merge stdout/stderr for simplicity
        self.field_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.field_process.finished.connect(self.field_extraction_finished)
        
        # Determine the python executable path
        python_executable = sys.executable
        print(f"Using Python executable: {python_executable}")

        # Construct the command for process_ocr.py
        # It reads from INPUT_DIR ("extracted_text") and writes to OUTPUT_DIR ("extracted_fields") by default
        # It doesn't require input/output directory arguments like the old script
        command = [python_executable, os.path.join(self.script_dir, PROCESS_OCR_SCRIPT)]
        print(f"Executing command: {' '.join(command)}")

        # Start the process
        self.field_process.start(command[0], command[1:])
        if not self.field_process.waitForStarted(5000): # Wait 5 seconds for start
             error_msg = "Field extraction process failed to start."
             print(f"Error: {error_msg}")
             self.handle_error(error_msg)

    def field_extraction_finished(self, exit_code, exit_status):
        """Handle completion of the field extraction process."""
        self.extract_text_btn.setEnabled(True)
        self.update_field_extraction_button_state()

        if exit_code == 0:
            self.status_label_fields.setText('Processing complete! Results saved in extracted_fields directory')
            # Enable export button if ANY .json files exist in the output directory
            json_files = []
            try:
                json_files = glob.glob(os.path.join(self.fields_output_dir, '*.json'))
            except Exception as e:
                print(f"Error during glob search for json files: {e}")
                # Keep export disabled if glob fails

            if json_files:
                print(f"Found {len(json_files)} JSON file(s) in {self.fields_output_dir}. Enabling export button.")
                self.export_button.setEnabled(True)
            else:
                print(f"Warning: Field extraction complete, but no .json files found in {self.fields_output_dir}. Export button remains disabled.")
                self.status_label_fields.setText('Processing complete! (No *.json files found)')
                self.export_button.setEnabled(False)
        else:
            self.handle_error(f'Field extraction failed with exit code {exit_code}')
            self.export_button.setEnabled(False) # Ensure disabled on error too

        self.copy_error_btn_fields.setVisible(exit_code != 0)
        self.progress_bar_fields.setVisible(False)
        self.field_process.terminate()
        self.current_process_type = None # Reset process type
        
    def handle_stdout(self):
        if self.field_process.state() == QProcess.NotRunning:
            return
        output = self.field_process.readAllStandardOutput().data().decode().strip()
        
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
        if self.field_process.state() == QProcess.NotRunning:
            return
        error = self.field_process.readAllStandardError().data().decode().strip()
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
        if self.field_process.state() == QProcess.Running:
            self.field_process.kill()
        self.field_process.terminate()
        self.export_button.setEnabled(False) # Also disable export on other errors

    # --- New method to open the criteria editor --- 
    def open_criteria_editor(self):
        print(f"Loading criteria from: {self.criteria_file_path}")
        criteria_data = load_criteria_from_md(self.criteria_file_path)
        if criteria_data:
            dialog = CriteriaEditorDialog(criteria_data, self.criteria_file_path, self) # Pass data, path, and parent
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

    # +++ New Methods for Export +++
    def export_results_to_excel(self):
        """Handles the 'Export Results' button click. Reads all *.json files in the output dir."""
        # Scan for all .json files in the designated output directory
        try:
            json_files = glob.glob(os.path.join(self.fields_output_dir, '*.json'))
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error scanning for JSON files:\n{e}")
            return

        if not json_files:
            QMessageBox.warning(self, "Export Error",
                                f"No .json result files found in directory:\\n{self.fields_output_dir}\\n\\nRun 'Extract Fields' first and ensure it produces output.")
            return

        all_data = []
        errors = []
        print(f"Found {len(json_files)} files to aggregate for export.")

        for file_path in json_files:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Assuming each JSON file contains a single dictionary object
                    json_data = json.load(f)
                    if isinstance(json_data, dict):
                        all_data.append(json_data)
                    else:
                         print(f"Warning: Skipping file {file_name} - content is not a dictionary.")
                         errors.append(f"Skipped {file_name}: Content not a dictionary")

            except json.JSONDecodeError:
                 print(f"Error: Failed to decode JSON from {file_name}")
                 errors.append(f"Decode Error: {file_name}")
            except Exception as e:
                 print(f"Error reading file {file_name}: {e}")
                 errors.append(f"Read Error: {file_name} - {e}")

        if not all_data:
            error_message = "No valid data could be loaded from the JSON files found."
            if errors:
                # Corrected error message formatting
                error_message += "\n\nErrors encountered:\n- " + "\n- ".join(errors)
            QMessageBox.critical(self, "Export Error", error_message)
            return

        if errors:
             # Corrected error message formatting
            QMessageBox.warning(self, "Export Warning",
                              f"Exporting {len(all_data)} records, but some errors occurred during reading:\n\n- " +
                              "\n- ".join(errors))

        # Propose a default filename (keep Excel as default)
        default_filename = os.path.join(os.getcwd(), "aggregated_fields_output.xlsx") # Updated default name

        # Open 'Save As' dialog with options for Excel and CSV
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        fileName, selected_filter = QFileDialog.getSaveFileName(self, "Save Aggregated Fields As", default_filename, # Updated title
                                                  "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)", options=options)

        if fileName:
            # Ensure filename has the correct extension based on the filter
            if selected_filter == "Excel Files (*.xlsx)" and not fileName.lower().endswith('.xlsx'):
                 fileName += '.xlsx'
            elif selected_filter == "CSV Files (*.csv)" and not fileName.lower().endswith('.csv'):
                 fileName += '.csv'
            elif '.' not in os.path.basename(fileName):
                 if selected_filter == "CSV Files (*.csv)":
                     fileName += '.csv'
                 else:
                     fileName += '.xlsx'

            # Call the actual export function with the aggregated data
            success = self._export_data_to_file(all_data, fileName)

            if success:
                QMessageBox.information(self, "Export Successful", f"Aggregated data successfully exported to:\\n{fileName}")
            # Error message is handled within _export_data_to_file

    def _export_data_to_file(self, data, output_filename):
        """Internal function to handle the pandas export logic for Excel or CSV."""
        try:
            # Create a pandas DataFrame
            if isinstance(data, dict):
                # If it's a dict, try to find a list within it or wrap it
                # Common patterns: results might be under a key like 'results' or 'data'
                potential_keys = ['results', 'data', 'extracted_fields']
                processed_data = None
                for key in potential_keys:
                    if key in data and isinstance(data[key], list):
                        processed_data = data[key]
                        print(f"Using data under key: '{key}'")
                        break

                if processed_data is None:
                     print("Warning: Input JSON is a dictionary, not a list. Exporting as single row.")
                     df = pd.DataFrame([data])
                elif not processed_data:
                     print("Warning: Found data list but it is empty. Creating an empty output file.")
                     df = pd.DataFrame()
                elif all(isinstance(item, dict) for item in processed_data):
                    df = pd.DataFrame(processed_data)
                else:
                     print("Warning: Data list contains non-dictionary items. Attempting direct conversion.")
                     df = pd.DataFrame(processed_data)

            elif isinstance(data, list):
                 if not data:
                     print("Warning: Input JSON data is an empty list. Creating an empty output file.")
                     df = pd.DataFrame()
                 elif all(isinstance(item, dict) for item in data):
                     df = pd.DataFrame(data)
                 else:
                     print("Warning: Input list contains non-dictionary items. Attempting conversion.")
                     df = pd.DataFrame(data)
            else:
                 msg = f"Input data type '{type(data).__name__}' not supported for direct export. Expected list or dict."
                 print(f"Error: {msg}")
                 QMessageBox.critical(self, "Export Error", msg)
                 return False

            # Export the DataFrame based on file extension
            file_ext = os.path.splitext(output_filename)[1].lower()

            if file_ext == '.xlsx':
                df.to_excel(output_filename, index=False, engine='openpyxl')
                print(f"Data successfully exported to Excel: {output_filename}")
            elif file_ext == '.csv':
                df.to_csv(output_filename, index=False, encoding='utf-8') # Use utf-8 for CSV
                print(f"Data successfully exported to CSV: {output_filename}")
            else:
                # Should not happen if file dialog logic is correct, but handle anyway
                 msg = f"Unsupported file extension: {file_ext}. Please use .xlsx or .csv."
                 print(f"Error: {msg}")
                 QMessageBox.critical(self, "Export Error", msg)
                 return False

            return True

        except ImportError:
            # ... (same error handling as before for pandas/openpyxl)
            msg = "The 'pandas' and 'openpyxl' libraries are required for Excel/CSV export.\\nPlease install them (e.g., conda install pandas openpyxl)" # Updated message
            print(f"Error: {msg}")
            QMessageBox.critical(self, "Export Error", msg)
            return False
        except Exception as e:
            # ... (same generic error handling)
            msg = f"An error occurred during export: {e}"
            print(f"Error: {msg}")
            QMessageBox.critical(self, "Export Error", msg)
            return False
    # --- End Methods ---

def main():
    # Try to acquire the lock
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("Another instance of the application is already running.")
        # Optionally show a message box to the user
        # app = QApplication.instance() # Check if an app instance exists
        # if not app: # Create one if needed for the message box
        #    app = QApplication(sys.argv)
        # QMessageBox.warning(None, "Application Running", "Another instance of the Image Text Extractor is already running.")
        sys.exit(1) # Exit if lock not acquired

    # Ensure cleanup releases the lock even if app creation fails
    try:
        app = QApplication(sys.argv)
        # Set stylesheet (optional, for better look and feel)
        # app.setStyleSheet("""
        # QPushButton { padding: 5px; }
        # QLabel { margin: 2px; }
        # QProgressBar { text-align: center; }
        # """)
        mainWin = ImageProcessorUI()
        mainWin.show()
        exit_code = app.exec()

    finally:
        # Explicitly release lock here, though atexit should also cover it
        release_lock(lock_fd)

    sys.exit(exit_code)

if __name__ == '__main__':
    main() 