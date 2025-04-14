# launch.py
import os
import sys
import subprocess
import signal
import atexit
import time
import fcntl
# import site # Not used currently
import re
import pathlib
# import codecs # Not used currently
import pandas as pd
import json
import glob # Import glob for file searching
from pathlib import Path # Add pathlib
import threading # Added
import queue # Added
import dearpygui.dearpygui as dpg # Added
# import traceback # Added for traceback handling
import shutil # Import shutil for file copying

# --- Add import for CriteriaPanel --- 
# YAML_PATH is now defined globally in launch.py
from src.criteria_panel import CriteriaPanel

# --- Global Reference for Cleanup ---
app_instance_ref = None

def cleanup(app_instance=None):
    """Cleanup function, now accepts app instance."""
    print("Cleanup: Starting cleanup process")
    global app_instance_ref
    app = app_instance if app_instance else app_instance_ref 
    
    if app and hasattr(app, 'current_process') and app.current_process and app.current_process.poll() is None:
        print("Cleanup: Terminating active process...")
        try:
            app.current_process.terminate()
            app.current_process.wait(timeout=2)
            app.current_process = None
        except subprocess.TimeoutExpired:
            print("Cleanup: Process did not terminate gracefully, killing.")
            app.current_process.kill()
            app.current_process = None
        except Exception as e:
            print(f"Cleanup: Error terminating process - {e}")
            app.current_process = None

    try:
        if hasattr(cleanup, 'lock_file') and cleanup.lock_file:
            if hasattr(cleanup.lock_file, 'fileno'):
                try:
                    fcntl.flock(cleanup.lock_file, fcntl.LOCK_UN)
                    cleanup.lock_file.close()
                    try:
                        os.unlink(LOCK_FILE)
                    except FileNotFoundError:
                        pass
                    except OSError as unlink_err:
                        print(f"Cleanup: Error unlinking lock file {LOCK_FILE} - {unlink_err}")
                except ValueError:
                    print("Cleanup: Lock file already closed.")
                except Exception as flock_err:
                    print(f"Cleanup: Error unlocking/closing lock file - {flock_err}")
            else:
                print("Cleanup: cleanup.lock_file is not a valid file descriptor.")
        else:
            try:
                if LOCK_FILE.exists():
                    os.unlink(LOCK_FILE)
                    print(f"Cleanup: Removed existing lock file {LOCK_FILE} as descriptor was not available.")
            except FileNotFoundError:
                pass
            except OSError as unlink_err:
                print(f"Cleanup: Error removing lock file {LOCK_FILE} without descriptor - {unlink_err}")
    except Exception as e:
        print(f"Cleanup: Error during cleanup - {e}")
    
    print("Cleanup: Finished cleanup process")

# Register cleanup (without app instance initially, will be re-registered in main)
# atexit.register(cleanup)

# Handle signals (signal handler calls cleanup without args, relying on global ref)
def signal_handler(signum, frame):
    print(f"Signal {signum} received. Cleaning up...")
    cleanup() # Relies on app_instance_ref being set
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- Configuration ---
VENV_DIR = ".venv"
EXTRACT_TEXT_SCRIPT = "extract_text.py"
PROCESS_OCR_SCRIPT = "process_ocr.py"

# --- Determine Base Path ---
def determine_base_path():
    """Determine the base path for resources whether running as script or bundled app."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return Path(sys._MEIPASS)
    else:
        # Running as a script
        return Path(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = determine_base_path() # Define base path globally

# --- User-Specific Output Directories ---
try:
    user_docs = Path.home() / "Documents"
    APP_OUTPUT_BASE = user_docs / "ImageExtractorOutput"
except Exception:
    # Fallback if Documents folder is not standard or accessible
    APP_OUTPUT_BASE = BASE_PATH / "ImageExtractorOutput_Fallback"

DEFAULT_TEXT_OUTPUT_DIR = APP_OUTPUT_BASE / "extracted_text"
DEFAULT_FIELDS_OUTPUT_DIR = APP_OUTPUT_BASE / "extracted_fields"
# Define the path for disease keywords within the user's output directory
DISEASE_KEYWORDS_DIR = APP_OUTPUT_BASE / "disease_keywords"
CRITERIA_YAML_PATH = DISEASE_KEYWORDS_DIR / "tuberculosis.yaml"

LOCK_FILE_DIR = APP_OUTPUT_BASE # Place lock file in the app's output dir
LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True) # Ensure lock file dir exists
LOCK_FILE = LOCK_FILE_DIR / '.qt_lock' # Use Path object

# Ensure disease keywords directory exists
DISEASE_KEYWORDS_DIR.mkdir(parents=True, exist_ok=True)

# --- Ensure default criteria file exists in user directory --- 
if not CRITERIA_YAML_PATH.exists():
    print(f"Criteria file not found at {CRITERIA_YAML_PATH}. Attempting to copy default...")
    source_yaml_path = BASE_PATH / "disease_keywords" / "tuberculosis.yaml"
    if source_yaml_path.exists():
        try:
            shutil.copy2(source_yaml_path, CRITERIA_YAML_PATH)
            print(f"Successfully copied default criteria to {CRITERIA_YAML_PATH}")
        except Exception as e:
            print(f"ERROR: Failed to copy default criteria from {source_yaml_path} to {CRITERIA_YAML_PATH}: {e}")
            # Application might fail later if criteria is essential
    else:
        print(f"ERROR: Default criteria source file not found at {source_yaml_path}. Cannot initialize criteria.")
        # Application might fail later

# --- Configuration (using determined paths) ---
EXTRACT_TEXT_SCRIPT = "extract_text.py" # Script name remains the same
PROCESS_OCR_SCRIPT = "process_ocr.py" # Script name remains the same
# DEFAULT_TEXT_OUTPUT_DIR and DEFAULT_FIELDS_OUTPUT_DIR defined above
# LOCK_FILE defined above

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
    if lock_fd and not lock_fd.closed:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            try:
                os.unlink(LOCK_FILE)
            except FileNotFoundError:
                pass
        except (IOError, OSError, ValueError) as e:
            print(f"Error releasing lock: {e}")
    elif lock_fd and lock_fd.closed:
        print("Lock file descriptor already closed when release_lock was called.")
        try:
            if LOCK_FILE.exists():
                os.unlink(LOCK_FILE)
        except FileNotFoundError:
            pass
        except (IOError, OSError) as e:
            print(f"Error removing lock file after finding fd closed: {e}")

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

# --- Main Application UI Class ---
# Removed QMainWindow inheritance
class ImageProcessorUI: # (QMainWindow):
    def __init__(self):
        # Removed super().__init__()
        self.selected_image_folder = None
        # Default to the calculated user-specific directory
        self.text_output_dir = DEFAULT_TEXT_OUTPUT_DIR
        # Initialize fields output dir as well
        self.fields_output_dir = DEFAULT_FIELDS_OUTPUT_DIR
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # Update the criteria file path to use .yaml extension - Ensure YAML path consistency
        # The CriteriaPanel uses a relative path from its location, so we don't strictly need it here
        # self.criteria_file_path = APP_OUTPUT_BASE / "disease_keywords" / "tuberculosis.yaml" # Path used by process_ocr? Check usage.

        # --- Instantiate Criteria Panel, passing the correct YAML path ---
        # CRITERIA_YAML_PATH is defined globally above
        self.criteria_panel = CriteriaPanel(yaml_path=str(CRITERIA_YAML_PATH))

        # Process handling attributes (will be adapted for DPG)
        self.current_process = None
        self.output_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = None
        self.process_running = False # State flag

        # DPG specific state
        self.image_files = []
        self.text_files = []
        self.field_data = {} # Store extracted field data {filename: {field: value}}

        # Build the UI
        self._build_ui()

    def _select_image_folder_callback(self, sender, app_data):
        """Show the image folder selection dialog."""
        if dpg.does_item_exist("image_folder_dialog"):
            dpg.show_item("image_folder_dialog")
        else:
            print("Error: Image folder dialog not found")

    def _on_viewport_resize(self, sender, app_data):
        """Handle viewport resize to keep the window full size."""
        if dpg.does_item_exist("Primary Window"):
            viewport_width = dpg.get_viewport_width()
            viewport_height = dpg.get_viewport_height()
            dpg.configure_item("Primary Window", width=viewport_width, height=viewport_height)

    def _build_ui(self):
        # --- Define File Dialogs --- 
        # Moved back outside the main window definition for clarity, ensure tags are unique
        # If issues persist, they might need unique tags per instance or careful management
        if not dpg.does_item_exist("image_folder_dialog"):
            with dpg.file_dialog(
                directory_selector=True,
                show=False,
                callback=self._image_folder_selected_callback,
                tag="image_folder_dialog",
                width=700,
                height=400,
                default_path=str(Path.home())
            ):
                dpg.add_file_extension(".*")
        if not dpg.does_item_exist("text_folder_dialog"):
            with dpg.file_dialog(
                directory_selector=True,
                show=False,
                callback=self._text_folder_selected_callback,
                tag="text_folder_dialog",
                width=700,
                height=400,
                default_path=str(Path.home())
            ):
                dpg.add_file_extension(".*")
        if not dpg.does_item_exist("excel_save_dialog"):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self._save_export_callback,
                tag="excel_save_dialog",
                width=700,
                height=400,
                default_path=str(Path.home())
            ):
                 dpg.add_file_extension(".xlsx")
                 dpg.add_file_extension(".*")

        # --- Main Application Window --- 
        with dpg.window(tag="Primary Window", no_title_bar=True, no_move=True, no_resize=True, no_collapse=True, no_close=True, width=800, height=600, pos=(0,0)):
            dpg.add_text("Image Text and Field Extractor")
            dpg.add_separator()

            # --- Folder Selection --- 
            with dpg.group(horizontal=True):
                dpg.add_button(label="Select Image Folder", callback=self._select_image_folder_callback, tag="select_image_button")
                dpg.add_text("No folder selected", tag="image_folder_display")
            
            # --- Text Extraction Section --- 
            dpg.add_text(f"Text Output Dir: {self.text_output_dir}", tag="text_output_display_label")
            dpg.add_button(label="Run Text Extraction", callback=self.run_text_extraction, tag="run_text_extraction_button", enabled=False)
            dpg.add_progress_bar(tag="text_progress_bar", overlay="", width=-1, show=False)
            dpg.add_text("", tag="text_status_label") # Dedicated status for text extraction
            dpg.add_separator()

            # --- Field Extraction Section --- 
            dpg.add_text(f"Fields Output Dir: {self.fields_output_dir}", tag="fields_output_display_label")
            with dpg.group(horizontal=True):
                dpg.add_button(label="View/Edit Criteria", callback=self.criteria_panel.show, tag="view_criteria_button")
                dpg.add_button(label="Run Field Extraction", callback=self.run_field_extraction, tag="run_field_extraction_button", enabled=False)
            dpg.add_progress_bar(tag="field_progress_bar", overlay="", width=-1, show=False)
            dpg.add_text("Status: Idle", tag="field_status_label") # Dedicated status for field extraction/general
            dpg.add_separator()

            # --- Bottom Buttons (Moved Below) --- 
            with dpg.group(horizontal=True):
                # Removed Spacer - Buttons will align left
                dpg.add_button(label="Export to Excel", callback=self.export_results_to_excel, tag="export_excel_button", enabled=False)
                dpg.add_button(label="Quit", callback=self._quit_callback, tag="quit_button")
            
            # Removed Results Table Section

        # Initialize button states
        self.update_field_extraction_button_state()

    def _image_folder_selected_callback(self, sender, app_data):
        """Handle the image folder selection dialog callback."""
        print(f"Image Folder Dialog Callback: Sender='{sender}', AppData='{app_data}'")
        # For directory selection, the path is usually in file_path_name
        selected_path_str = app_data.get('file_path_name') if isinstance(app_data, dict) else None

        if selected_path_str:
            self.selected_image_folder = Path(selected_path_str)
            # Verify the path is actually a directory
            if self.selected_image_folder.is_dir():
                print(f"Image Folder Selected: {self.selected_image_folder}")
                # Update the simple text display
                if dpg.does_item_exist("image_folder_display"):
                    dpg.set_value("image_folder_display", f"Selected: {self.selected_image_folder.name}")
                # Enable Text Extraction
                if dpg.does_item_exist("run_text_extraction_button"):
                    dpg.configure_item("run_text_extraction_button", enabled=True)
                self.update_field_extraction_button_state()
            else:
                # Handle case where the selected path isn't a directory
                print(f"Error: Selected path is not a directory: {selected_path_str}")
                self.selected_image_folder = None # Ensure it's reset
                if dpg.does_item_exist("image_folder_display"):
                     dpg.set_value("image_folder_display", "Invalid selection (not a folder)")
                if dpg.does_item_exist("run_text_extraction_button"):
                    dpg.configure_item("run_text_extraction_button", enabled=False)
                self.update_field_extraction_button_state()
        else:
            # Handle case where dialog is closed without selection or invalid data
            print("Image folder selection cancelled or failed.")
            self.selected_image_folder = None # Ensure it's reset
            if dpg.does_item_exist("image_folder_display"):
                 dpg.set_value("image_folder_display", "No folder selected")
            if dpg.does_item_exist("run_text_extraction_button"):
                dpg.configure_item("run_text_extraction_button", enabled=False)
            self.update_field_extraction_button_state()
            
    # --- Callback for Text Folder Selection Dialog --- 
    def _text_folder_selected_callback(self, sender, app_data):
        print(f"Text Folder Dialog Callback: Sender='{sender}', AppData='{app_data}'")
        selections = app_data.get('selections', {}) if isinstance(app_data, dict) else {}
        if selections:
            selected_path_str = list(selections.values())[0]
            print(f"Text Output Folder selected (currently display only): {selected_path_str}")
            if dpg.does_item_exist("text_output_display_label"):
                 dpg.set_value("text_output_display_label", f"Text Output Dir: {selected_path_str}")
            self.update_field_extraction_button_state()
        else:
            print("Text folder selection cancelled or failed.")
            if dpg.does_item_exist("text_output_display_label"):
                 dpg.set_value("text_output_display_label", f"Text Output Dir: {self.text_output_dir}")
            self.update_field_extraction_button_state()

    def _save_export_callback(self, sender, app_data):
        """Handle the Excel file save dialog callback."""
        print(f"Excel Save Dialog Callback: Sender='{sender}', AppData='{app_data}'")
        # For single file save, check 'file_path_name'
        save_path_str = app_data.get('file_path_name') if isinstance(app_data, dict) else None
        
        if save_path_str:
            save_path = Path(save_path_str)
            
            # Ensure the file has a .xlsx extension
            if not save_path.suffix.lower() == '.xlsx':
                print(f"Adding .xlsx extension to {save_path.name}")
                save_path = save_path.with_suffix('.xlsx')
            
            try:
                json_files = list(self.fields_output_dir.glob('*.json'))
                if not json_files:
                    print("No JSON files found to export")
                    if dpg.does_item_exist("status_label"):
                        dpg.set_value("status_label", "Status: No data to export")
                    return
                
                all_data = []
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Use filename stem from JSON source as Source_File
                            data['Source_File'] = data.get('source_text_file', json_file.stem).replace('_extracted','') # Get source from JSON if present
                            all_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Error reading {json_file}: {e}")
                        continue
                    except KeyError:
                         print(f"Warning: Missing 'source_text_file' key in {json_file.name}, using filename stem.")
                         data['Source_File'] = json_file.stem.replace('_extracted','') 
                         all_data.append(data) # Still append even if key is missing
                
                if all_data:
                    # Create a new DataFrame with just the columns we want
                    new_data = []
                    for data in all_data:
                        row = {
                            'Source_File': data.get('Source_File', ''),
                            'file_path': data.get('file_path', ''),
                            'error': data.get('error', ''),
                            'extraction_timestamp': data.get('extraction_timestamp', '')
                        }
                        
                        # Map test method fields to their column names
                        test_method_mapping = {
                            'tuberculosis_skin_test': 'Skin Test',
                            'tuberculosis_blood_test': 'Blood Test',
                            'tuberculosis_radiography': 'X-Ray'
                        }
                        
                        # Add test method specific columns
                        for json_field, column_prefix in test_method_mapping.items():
                            if json_field in data:
                                method_data = data[json_field]
                                row[f"{column_prefix} Administered"] = method_data.get('Administered', False)
                                row[f"{column_prefix} Confidence"] = method_data.get('Confidence', 0)
                                row[f"{column_prefix} Number of indicators"] = method_data.get('Number of indicators', 0)
                            else:
                                # Initialize with default values if method not present
                                row[f"{column_prefix} Administered"] = False
                                row[f"{column_prefix} Confidence"] = 0
                                row[f"{column_prefix} Number of indicators"] = 0
                        
                        new_data.append(row)
                    
                    # Create new DataFrame with the processed data
                    df = pd.DataFrame(new_data)
                    
                    # Define column order
                    standard_columns = [
                        'Source_File',
                        'file_path',
                        'error',
                        'extraction_timestamp'
                    ]
                    
                    dynamic_columns = []
                    for column_prefix in test_method_mapping.values():
                        dynamic_columns.extend([
                            f"{column_prefix} Administered",
                            f"{column_prefix} Confidence",
                            f"{column_prefix} Number of indicators"
                        ])
                    
                    cols_in_order = standard_columns + dynamic_columns
                    
                    # Ensure all columns exist and are in the right order
                    for col in cols_in_order:
                        if col not in df.columns:
                            df[col] = None
                    
                    # Reorder columns
                    df = df[cols_in_order]
                    
                    # Export to Excel
                    df.to_excel(save_path, index=False)
                    print(f"Successfully exported data to {save_path}")
                    if dpg.does_item_exist("status_label"):
                        dpg.set_value("status_label", f"Status: Exported to {save_path.name}")
                else:
                    print("No valid data to export")
                    if dpg.does_item_exist("status_label"):
                        dpg.set_value("status_label", "Status: No valid data to export")
            
            except Exception as e:
                error_msg = f"Error exporting to Excel: {str(e)}"
                print(error_msg)
                print(traceback.format_exc()) # Print full traceback for export errors
                if dpg.does_item_exist("status_label"):
                    dpg.set_value("status_label", f"Status: {error_msg}")
        else:
            print("Excel save dialog cancelled or no selection made")

    def _read_stream(self, stream, stream_type, process_type):
        """Helper function to read lines from a stream (stdout/stderr) and put them in the queue."""
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                self.output_queue.put({"type": stream_type, "line": line.strip(), "process_type": process_type})
        except ValueError:
            # Ignore "I/O operation on closed file" error which can happen
            # if the process terminates abruptly while reading.
            pass 
        except Exception as e:
            # Log other unexpected errors during stream reading
            print(f"ERROR reading stream [{stream_type}] for [{process_type}]: {e}")
        finally:
            stream.close()

    def _execute_script(self, command, process_type):
        """Executes the script in a subprocess, reads stdout/stderr concurrently, and puts output/status in the queue."""
        print(f"Worker [{process_type}]: Starting command: {' '.join(command)}")
        self.process_running = True
        stdout_thread = None
        stderr_thread = None
        try:
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True, # Recommended for text mode
                encoding='utf-8',
                errors='replace'
            )

            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(target=self._read_stream, args=(self.current_process.stdout, 'stdout', process_type), daemon=True)
            stderr_thread = threading.Thread(target=self._read_stream, args=(self.current_process.stderr, 'stderr', process_type), daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to complete
            exit_code = self.current_process.wait()
            print(f"Worker [{process_type}]: Process finished with exit code {exit_code}")

            # Wait for reader threads to finish (they will exit when streams close)
            if stdout_thread: stdout_thread.join(timeout=1)
            if stderr_thread: stderr_thread.join(timeout=1)
            
            # Send final status message
            self.output_queue.put({"type": "finished", "exit_code": exit_code, "process_type": process_type})

        except Exception as e:
            error_msg = f"Error executing script or reading output: {str(e)}"
            print(f"Worker [{process_type}]: {error_msg}")
            # Ensure process is terminated if it's still running
            if self.current_process and self.current_process.poll() is None:
                 try:
                     self.current_process.terminate()
                     self.current_process.wait(timeout=1)
                 except Exception as term_err:
                     print(f"Worker [{process_type}]: Error terminating process after exception: {term_err}")
            self.output_queue.put({"type": "error", "message": error_msg, "process_type": process_type})
            
            # Ensure state is reset even if error happens before finished message
            self.process_running = False
            self.current_process = None
            self.thread = None # Assuming self.thread holds the _execute_script thread

        finally:
             # Ensure threads are joined even if process finished normally but threads hung?
             if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=0.5)
             if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=0.5)
             print(f"Worker [{process_type}]: Execute script function finished.")
             # Note: self.process_running should be set to False in the _check_script_queue when 'finished' or 'error' is received

    def run_text_extraction(self):
        """Run the text extraction process on the selected image folder."""
        if not self.selected_image_folder or self.process_running:
            return

        # Get the Python executable path
        python_executable = sys.executable
        os.makedirs(self.text_output_dir, exist_ok=True)

        try:
            # Count total files for progress tracking
            from src.scanner import scan_directory
            total_files = len(list(scan_directory(self.selected_image_folder)))
            if total_files == 0:
                if dpg.does_item_exist("text_status_label"):
                    dpg.set_value("text_status_label", "Status: No image files found in the selected folder")
                return

            # Update UI state
            if dpg.does_item_exist("text_status_label"):
                dpg.set_value("text_status_label", "Status: Starting text extraction...")
            if dpg.does_item_exist("field_status_label"):
                dpg.set_value("field_status_label", "") # Clear other status
            if dpg.does_item_exist("text_progress_bar"):
                dpg.configure_item("text_progress_bar", overlay="0%", show=True)
                dpg.set_value("text_progress_bar", 0)
            if dpg.does_item_exist("field_progress_bar"):
                dpg.configure_item("field_progress_bar", show=False)

            # Disable buttons during processing
            if dpg.does_item_exist("run_text_extraction_button"):
                dpg.configure_item("run_text_extraction_button", enabled=False)
            if dpg.does_item_exist("run_field_extraction_button"):
                dpg.configure_item("run_field_extraction_button", enabled=False)

            # Prepare command
            extract_text_script = os.path.join(self.script_dir, EXTRACT_TEXT_SCRIPT)
            command = [
                python_executable,
                extract_text_script,
                str(self.selected_image_folder),
                '--output-dir', str(self.text_output_dir)
            ]

            # Start processing in a new thread
            self.thread = threading.Thread(
                target=self._execute_script,
                args=(command, 'text'),
                daemon=True
            )
            self.thread.start()

        except Exception as e:
            error_msg = f"Failed to start text extraction: {str(e)}"
            print(f"Error: {error_msg}")
            if dpg.does_item_exist("text_status_label"):
                dpg.set_value("text_status_label", f"Status: {error_msg}")
            # Re-enable buttons on error
            if dpg.does_item_exist("run_text_extraction_button"):
                dpg.configure_item("run_text_extraction_button", enabled=True)

    def run_field_extraction(self):
        """Run the field extraction process on the text files."""
        if self.process_running:
            return

        print("Starting field extraction process...")
        os.makedirs(self.fields_output_dir, exist_ok=True)

        try:
            # Update UI state
            if dpg.does_item_exist("field_status_label"):
                dpg.set_value("field_status_label", "Status: Starting field extraction...")
            if dpg.does_item_exist("text_status_label"):
                dpg.set_value("text_status_label", "") # Clear other status
            if dpg.does_item_exist("field_progress_bar"):
                dpg.configure_item("field_progress_bar", overlay="0%", show=True)
                dpg.set_value("field_progress_bar", 0)
            if dpg.does_item_exist("text_progress_bar"):
                dpg.configure_item("text_progress_bar", show=False)

            # Disable buttons during processing
            if dpg.does_item_exist("run_text_extraction_button"):
                dpg.configure_item("run_text_extraction_button", enabled=False)
            if dpg.does_item_exist("run_field_extraction_button"):
                dpg.configure_item("run_field_extraction_button", enabled=False)

            # Prepare command - Use BASE_PATH for script location
            # Determine the correct path based on running mode (script vs bundle)
            # Define PROCESS_OCR_SCRIPT name
            PROCESS_OCR_SCRIPT = "process_ocr.py" # Make sure this is defined
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Bundled: Script was added to root using --add-data src/process_ocr.py:.
                # Therefore, it should be directly under BASE_PATH in the bundle.
                process_ocr_script_path = BASE_PATH / PROCESS_OCR_SCRIPT 
            else:
                # Script: Script is inside the 'src' directory relative to BASE_PATH
                process_ocr_script_path = BASE_PATH / "src" / PROCESS_OCR_SCRIPT
            
            print(f"DEBUG [run_field_extraction]: Determined process_ocr_script_path = {process_ocr_script_path}")

            # Check if the resolved script path actually exists
            if not process_ocr_script_path.exists():
                print(f"ERROR: Field extraction script not found at calculated path: {process_ocr_script_path}")
                # Update UI and re-enable buttons
                if dpg.does_item_exist("field_status_label"): dpg.set_value("field_status_label", f"Status: Error - Script not found.")
                if dpg.does_item_exist("run_text_extraction_button"): dpg.configure_item("run_text_extraction_button", enabled=self.selected_image_folder is not None)
                if dpg.does_item_exist("run_field_extraction_button"): dpg.configure_item("run_field_extraction_button", enabled=True) # Allow retry?
                return

            # CRITERIA_YAML_PATH is already an absolute path
            if not Path(CRITERIA_YAML_PATH).exists():
                print(f"ERROR: Criteria YAML file not found at {CRITERIA_YAML_PATH}")
                # Update UI to show error and re-enable buttons
                if dpg.does_item_exist("field_status_label"):
                    dpg.set_value("field_status_label", f"Status: Criteria file missing: {Path(CRITERIA_YAML_PATH).name}")
                if dpg.does_item_exist("run_text_extraction_button"):
                    dpg.configure_item("run_text_extraction_button", enabled=self.selected_image_folder is not None)
                if dpg.does_item_exist("run_field_extraction_button"):
                    dpg.configure_item("run_field_extraction_button", enabled=any(self.text_output_dir.glob('*.json')))
                return # Stop execution if criteria file is missing
                 
            # Re-apply fix: Arguments for process_ocr.py are positional, not flags
            command = [
                sys.executable, # Use sys.executable to ensure using the same python env
                str(process_ocr_script_path),
                # Positional arguments for input/output directories
                str(self.text_output_dir),     # Input dir (positional)
                str(self.fields_output_dir),    # Output dir (positional)
                # Flag for keywords file
                '--keywords-file', str(CRITERIA_YAML_PATH)
            ]

            # Start processing in a new thread
            self.thread = threading.Thread(
                target=self._execute_script,
                args=(command, 'fields'),
                daemon=True
            )
            self.thread.start()

        except Exception as e:
            error_msg = f"Failed to start field extraction: {str(e)}"
            print(f"Error: {error_msg}")
            if dpg.does_item_exist("field_status_label"):
                dpg.set_value("field_status_label", f"Status: {error_msg}")
            # Re-enable buttons on error
            if dpg.does_item_exist("run_field_extraction_button"):
                dpg.configure_item("run_field_extraction_button", enabled=True)
            if dpg.does_item_exist("run_text_extraction_button"):
                dpg.configure_item("run_text_extraction_button", enabled=True)

    def export_results_to_excel(self):
        """Show the Excel save dialog to export results."""
        if dpg.does_item_exist("excel_save_dialog"):
            dpg.show_item("excel_save_dialog")
        else:
            print("Error: Excel save dialog not found")
            if dpg.does_item_exist("status_label"):
                dpg.set_value("status_label", "Status: Error - Excel save dialog not found")

    def _check_script_queue(self):
        """ Check the queue for messages from the worker thread and update UI. """
        try:
            while not self.output_queue.empty():
                message = self.output_queue.get_nowait()
                msg_type = message.get("type")
                process_type = message.get("process_type", "unknown") # text or fields
                line = message.get("line", "")
                exit_code = message.get("exit_code")
                error_message = message.get("message")

                # Update Log Area (if it exists and is used)
                # if dpg.does_item_exist("log_area") and line:
                #     current_log = dpg.get_value("log_area")
                #     prefix = "STDOUT" if msg_type == "stdout" else "STDERR" if msg_type == "stderr" else "INFO"
                #     dpg.set_value("log_area", current_log + f"[{prefix}][{process_type}] {line}\n")
                #     dpg.configure_item("log_area", scroll_y=-1.0) # Auto-scroll

                # Update Progress Bar based on stdout
                if msg_type == "stdout" and line:
                    match = re.search(r"PROGRESS:(\d+)/(\d+)", line)
                    status_label_tag = "text_status_label" if process_type == 'text' else "field_status_label"
                    progress_bar_tag = "text_progress_bar" if process_type == 'text' else "field_progress_bar"
                    
                    if match:
                        current, total = int(match.group(1)), int(match.group(2))
                        progress = current / total if total > 0 else 0
                        overlay_text = f"{current}/{total} ({progress:.0%})"
                        if dpg.does_item_exist(progress_bar_tag): 
                            dpg.configure_item(progress_bar_tag, overlay=overlay_text, show=True)
                            dpg.set_value(progress_bar_tag, progress)
                    elif "Processing file:" in line: # Simple status update
                         if dpg.does_item_exist(status_label_tag): dpg.set_value(status_label_tag, line)
                         if dpg.does_item_exist(progress_bar_tag): dpg.configure_item(progress_bar_tag, show=True) # Show bar even without percentage
                
                elif msg_type == "stderr" and line:
                     status_label_tag = "text_status_label" if process_type == 'text' else "field_status_label"
                     # Log stderr to console for debugging
                     print(f"STDERR [{process_type}]: {line}")
                     # Optionally update status label on error
                     if dpg.does_item_exist(status_label_tag): dpg.set_value(status_label_tag, f"Error: {line[:50]}...") 

                elif msg_type == "error" and error_message:
                    status_label_tag = "text_status_label" if process_type == 'text' else "field_status_label"
                    progress_bar_tag = "text_progress_bar" if process_type == 'text' else "field_progress_bar"
                    print(f"ERROR [{process_type}]: {error_message}")
                    if dpg.does_item_exist(status_label_tag): dpg.set_value(status_label_tag, f"Error: {error_message}")
                    if dpg.does_item_exist(progress_bar_tag): dpg.configure_item(progress_bar_tag, overlay="Error", show=True)
                    # No state reset here, wait for 'finished' message
                
                elif msg_type == "finished":
                    print(f"Processing 'finished' message for {process_type} with exit code {exit_code}")
                    self.process_running = False # Reset flag *here*
                    self.current_process = None # Clear process reference
                    final_status = ""
                    progress_overlay = "Complete"
                    status_label_tag = "text_status_label" if process_type == 'text' else "field_status_label"
                    progress_bar_tag = "text_progress_bar" if process_type == 'text' else "field_progress_bar"
                    
                    # --- Reset UI Elements --- 
                    if dpg.does_item_exist(progress_bar_tag): 
                        # Ensure bar looks full on success, hide on error
                        if exit_code == 0:
                            dpg.set_value(progress_bar_tag, 1.0)
                            dpg.configure_item(progress_bar_tag, overlay="Complete", show=True)
                        else:
                             dpg.configure_item(progress_bar_tag, overlay="Failed", show=True) # Keep showing bar on fail?
                             # Or hide it: dpg.configure_item(progress_bar_tag, show=False, overlay="")
                    
                    # --- Update Status and Button States Based on Outcome --- 
                    if process_type == 'text':
                        text_files_exist = any(self.text_output_dir.glob('*.json')) if self.text_output_dir else False
                        if exit_code == 0:
                            final_status = "Text extraction complete." + ("" if text_files_exist else " (No output files found)")
                        else:
                            final_status = f"Text extraction failed (Code: {exit_code}). Check console."
                        
                        if dpg.does_item_exist("run_field_extraction_button"): 
                             dpg.configure_item("run_field_extraction_button", enabled=text_files_exist)
                        # Always re-enable text extraction button if a folder is selected
                        text_btn_enabled = self.selected_image_folder is not None
                        if dpg.does_item_exist("run_text_extraction_button"): 
                            dpg.configure_item("run_text_extraction_button", enabled=text_btn_enabled)

                    elif process_type == 'fields':
                        field_files_exist = any(self.fields_output_dir.glob('*.json')) if self.fields_output_dir else False
                        if exit_code == 0:
                            final_status = "Field extraction complete." + ("" if field_files_exist else " (No output files found)")
                        else:
                            final_status = f"Field extraction failed (Code: {exit_code}). Check console."
                        
                        if dpg.does_item_exist("export_excel_button"): 
                            dpg.configure_item("export_excel_button", enabled=field_files_exist)
                        # Re-enable field extraction button if text files exist
                        text_files_exist = any(self.text_output_dir.glob('*.json')) if self.text_output_dir else False
                        if dpg.does_item_exist("run_field_extraction_button"): 
                            dpg.configure_item("run_field_extraction_button", enabled=text_files_exist)
                        # Always re-enable text extraction button if folder selected
                        text_btn_enabled = self.selected_image_folder is not None
                        if dpg.does_item_exist("run_text_extraction_button"): 
                             dpg.configure_item("run_text_extraction_button", enabled=text_btn_enabled)

                    # Update final status label
                    if dpg.does_item_exist(status_label_tag): dpg.set_value(status_label_tag, f"Status: {final_status}")
                    
                    # Clean up thread reference
                    self.thread = None

        except queue.Empty:
            pass # No messages, normal operation
        except Exception as e:
            print(f"Error processing script queue: {e}")
            print(traceback.format_exc()) # Add traceback for queue errors
            # Attempt to reset state on error
            self.process_running = False
            self.current_process = None
            self.thread = None
            # Re-enable buttons cautiously
            text_btn_enabled = self.selected_image_folder is not None
            text_files_exist = any(self.text_output_dir.glob('*.json')) if self.text_output_dir else False
            if dpg.does_item_exist("run_text_extraction_button"): dpg.configure_item("run_text_extraction_button", enabled=text_btn_enabled)
            if dpg.does_item_exist("run_field_extraction_button"): dpg.configure_item("run_field_extraction_button", enabled=text_files_exist)
            if dpg.does_item_exist("export_excel_button"): dpg.configure_item("export_excel_button", enabled=False)
            # Update the *field* status label on general queue error
            if dpg.does_item_exist("field_status_label"): dpg.set_value("field_status_label", "Status: Error processing results.") 
            if dpg.does_item_exist("text_progress_bar"): dpg.configure_item("text_progress_bar", show=False, overlay="Error")
            if dpg.does_item_exist("field_progress_bar"): dpg.configure_item("field_progress_bar", show=False, overlay="Error")

    def update_field_extraction_button_state(self):
        """Update the field extraction button state based on the presence of text files."""
        text_files_exist = any(self.text_output_dir.glob('*.json')) if self.text_output_dir else False
        if dpg.does_item_exist("run_field_extraction_button"):
            dpg.configure_item("run_field_extraction_button", enabled=text_files_exist)
            if dpg.does_item_exist("field_status_label"):
                if not text_files_exist:
                    dpg.set_value("field_status_label", "Status: Run text extraction first or select a folder with text files")

    def _quit_callback(self):
        """Callback method to handle the quit button click."""
        print("Quit button clicked. Stopping Dear PyGui loop...")
        dpg.stop_dearpygui() # Only stop the DPG loop
        # Let the application exit naturally after the loop finishes

def main():
    lock_fd = acquire_lock()
    if not lock_fd:
        print("Another instance of ImageExtractor is already running. Exiting.")
        # TODO: Show a DPG message box here before exiting?
        # dpg.create_context()
        # dpg.add_window(label="Error", modal=True, show=True, tag="instance_error_modal", width=400)
        # dpg.add_text("Another instance of ImageExtractor is already running.", parent="instance_error_modal")
        # dpg.add_button(label="OK", callback=lambda: dpg.stop_dearpygui(), parent="instance_error_modal")
        # dpg.setup_dearpygui() # Need setup to show modal? Check DPG docs.
        # dpg.start_dearpygui() # Need start to show modal? Check DPG docs.
        # dpg.destroy_context()
        sys.exit(1) # Exit after showing message (or immediately if GUI part fails)

    # Store lock_fd in cleanup function's scope ONLY after successful acquisition
    cleanup.lock_file = lock_fd

    # --- DPG Application Setup ---
    dpg.create_context()

    # Setup application instance (we'll manage state here for now)
    app = ImageProcessorUI()
    app_instance_ref = app # Set global reference for signal handler
    
    # Register cleanup with the app instance *after* it's created
    atexit.register(cleanup, app_instance=app)
    
    # Create and configure viewport
    dpg.create_viewport(title="Image Extractor", width=1024, height=768)
    dpg.configure_viewport(0, x_pos=100, y_pos=100)  # Position the window on screen
    dpg.set_viewport_resize_callback(app._on_viewport_resize)
    
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Trigger initial resize to ensure window fills viewport
    app._on_viewport_resize(None, None)

    # --- DPG Main Loop ---
    while dpg.is_dearpygui_running():
        # Check queue for messages from background processes
        app._check_script_queue() # Call the queue check method

        # Dynamically adjust spacer width for right alignment
        try:
            # Check if items exist before getting width
            if dpg.does_item_exist("Primary Window") and dpg.does_item_exist("export_excel_button") and dpg.does_item_exist("quit_button") and dpg.does_item_exist("bottom_align_spacer"):
                primary_width = dpg.get_item_width("Primary Window")
                export_width = dpg.get_item_width("export_excel_button")
                quit_width = dpg.get_item_width("quit_button")

                # Ensure widths are valid numbers
                if primary_width is not None and export_width is not None and quit_width is not None:
                    # Add some padding between elements
                    total_button_width = export_width + quit_width + 30 # Adjust padding as needed
                    spacer_width = primary_width - total_button_width # Renamed dummy_width
                    if spacer_width > 0:
                        dpg.set_item_width(item="bottom_align_spacer", width=spacer_width)
                else:
                        dpg.set_item_width(item="bottom_align_spacer", width=1) # Ensure it has some width (prevents negative)
        except Exception as e:
            # Can happen if window is resizing or items not fully rendered yet
            # print(f"Debug: Error adjusting spacer width: {e}")
            pass

        # Render the frame
        dpg.render_dearpygui_frame()

    # --- DPG Cleanup ---
    print("DPG loop finished. Cleaning up context...")
    dpg.destroy_context()

    # Explicit cleanup call might be redundant due to atexit, but ensures lock release
    # cleanup(app_instance=app) # atexit should cover this now
    print("Application finished.")
    sys.exit(0)


if __name__ == "__main__":
    main() 