import dearpygui.dearpygui as dpg
import yaml
import os
from collections import defaultdict

def _deep_convert_dict(layer):
    """Recursively converts defaultdicts to dicts."""
    if isinstance(layer, defaultdict):
        layer = {k: _deep_convert_dict(v) for k, v in layer.items()}
    return layer

class CriteriaPanel:
    def __init__(self, yaml_path, tag="criteria_panel_window"):
        self.tag = tag
        self.yaml_path = yaml_path
        self.data = None
        self.initial_data_str = "" # Store initial state for cancel
        self.input_widgets = defaultdict(dict) # Store references to input widgets

        # Define the grid structure
        self.test_methods = []
        self.detection_aspects = []
        self.pattern_types = ["keywords", "regex_patterns"] # Hardcoded as per requirement

    def _load_data(self):
        """Loads data from the YAML file."""
        try:
            # Use the instance's yaml_path
            with open(self.yaml_path, 'r') as f: 
                # Use FullLoader to handle potential Python object tags like defaultdict
                raw_data = yaml.load(f, Loader=yaml.FullLoader) 
                # Extract structure and data
                # Ensure raw_data is a dictionary before proceeding
                if not isinstance(raw_data, dict):
                    print(f"Error: YAML file {self.yaml_path} did not load as a dictionary.")
                    self.data = {}
                    self.initial_data_str = ""
                    return
                
                self.test_methods = list(raw_data.get('metadata', {}).get('test_methods', {}).keys())
                self.detection_aspects = list(raw_data.get('metadata', {}).get('detection_aspects', {}).keys())
                # Convert loaded data (potentially with defaultdicts) to plain dicts for internal use
                self.data = _deep_convert_dict(raw_data.get('tuberculosis', {})) 
                self.initial_data_str = self._get_current_data_as_str() # For cancel
                print("Data loaded successfully.")
                # print(f"Test Methods: {self.test_methods}")
                # print(f"Detection Aspects: {self.detection_aspects}")
        except FileNotFoundError:
            print(f"Error: YAML file not found at {self.yaml_path}")
            self.data = {}
            self.initial_data_str = ""
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            self.data = {}
            self.initial_data_str = ""
        except Exception as e:
            print(f"An unexpected error occurred during data loading: {e}")
            self.data = {}
            self.initial_data_str = ""

    def _format_patterns(self, patterns_list):
        """Formats a list of pattern dictionaries into a display string."""
        if not isinstance(patterns_list, list):
            return "" # Handle cases where data might be missing or malformed
        return "\n".join([f"{p.get('string', '')} <{p.get('confidence', '?')}%>" for p in patterns_list])

    def _parse_patterns(self, patterns_str):
        """Parses a display string back into a list of pattern dictionaries."""
        parsed_patterns = []
        lines = patterns_str.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                # Find the last occurrence of '<' and '>' to handle patterns containing these chars
                last_open_bracket = line.rfind('<')
                last_close_bracket = line.rfind('%>')
                if last_open_bracket != -1 and last_close_bracket != -1 and last_open_bracket < last_close_bracket:
                    pattern_string = line[:last_open_bracket].strip()
                    confidence_str = line[last_open_bracket + 1:last_close_bracket].strip()
                    confidence = int(confidence_str) # Validate confidence is an integer
                    if not pattern_string: # Skip if pattern string is empty
                        print(f"Warning: Skipping line with empty pattern string: '{line}'")
                        continue
                    parsed_patterns.append({"string": pattern_string, "confidence": confidence})
                else:
                    # If format is invalid, treat the whole line as a pattern with default confidence?
                    # Or raise an error? For now, let's warn and skip invalid lines.
                    print(f"Warning: Invalid format, skipping line: '{line}'")
                    # Alternative: Add with default confidence or raise error
                    # parsed_patterns.append({"string": line, "confidence": 0})
            except ValueError:
                print(f"Warning: Invalid confidence value, skipping line: '{line}'")
            except Exception as e:
                print(f"Error parsing line '{line}': {e}")
        return parsed_patterns

    def _save_data(self):
        """Parses data from input fields and saves back to YAML."""
        updated_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        validation_passed = True

        for method in self.test_methods:
            for aspect in self.detection_aspects:
                for p_type in self.pattern_types:
                    widget_tag = f"input_{method}_{aspect}_{p_type}"
                    if dpg.does_item_exist(widget_tag):
                        current_value = dpg.get_value(widget_tag)
                        try:
                            parsed = self._parse_patterns(current_value)
                            # Basic validation check (ensures list is returned)
                            if isinstance(parsed, list):
                                 updated_data[method][aspect][p_type] = parsed
                            else:
                                print(f"Error: Parsing failed for {method}/{aspect}/{p_type}. Data not saved correctly.")
                                validation_passed = False
                                dpg.configure_item(widget_tag, border_color=(255, 0, 0, 255)) # Indicate error
                        except Exception as e:
                            print(f"Error processing input for {widget_tag}: {e}")
                            validation_passed = False
                            dpg.configure_item(widget_tag, border_color=(255, 0, 0, 255)) # Indicate error
                    else:
                        # This case shouldn't happen if UI is built correctly
                        print(f"Warning: Widget {widget_tag} not found during save.")


        if not validation_passed:
             # Maybe show a popup error message
             print("Validation failed. Please correct the highlighted fields (e.g., 'pattern <int%>').")
             # Add a status bar or modal popup here in a real app
             if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", "Validation Failed! Check format.")
                 dpg.configure_item("save_status_text", color=(255, 0, 0, 255))
             return # Stop saving

        # If validation passes, structure the full YAML data
        try:
            # Convert the collected data from defaultdict to plain dict recursively
            plain_dict_data = _deep_convert_dict(updated_data)
            
            # Read existing file using instance path
            # Check if file exists, load if it does, otherwise start fresh
            full_yaml_data = {}
            if os.path.exists(self.yaml_path):
                 try:
                     with open(self.yaml_path, 'r') as f: 
                         full_yaml_data = yaml.safe_load(f)
                     if not isinstance(full_yaml_data, dict): # Handle empty or invalid file
                         print(f"Warning: Existing YAML file {self.yaml_path} is invalid or empty. Overwriting with new structure.")
                         full_yaml_data = {}
                 except Exception as load_err:
                     print(f"Warning: Could not load existing YAML file {self.yaml_path}: {load_err}. Will attempt to overwrite.")
                     full_yaml_data = {}
            else:
                 print(f"Info: YAML file {self.yaml_path} not found. Creating new file.")
                 # Define base structure if creating new file (ensure metadata exists if needed)
                 full_yaml_data = {'metadata': {'test_methods': {}, 'detection_aspects': {}}}
                 # Populate metadata based on current panel state
                 if hasattr(self, 'test_methods'):
                      full_yaml_data['metadata']['test_methods'] = {m: m for m in self.test_methods} # Example
                 if hasattr(self, 'detection_aspects'):
                      full_yaml_data['metadata']['detection_aspects'] = {d: d for d in self.detection_aspects} # Example

            # Update only the 'tuberculosis' part with the plain dictionary
            full_yaml_data['tuberculosis'] = plain_dict_data 

            # Write back to the same file using instance path
            with open(self.yaml_path, 'w') as f: 
                # Use explicit Dumper, avoid aliases for cleaner output
                yaml.dump(full_yaml_data, f, Dumper=yaml.SafeDumper, default_flow_style=False, sort_keys=False, indent=2, allow_unicode=True)
            print("Data saved successfully.")
            self.data = plain_dict_data # Update internal state with plain dict
            self.initial_data_str = self._get_current_data_as_str() # Update baseline for cancel
            # Update status
            if dpg.does_item_exist("save_status_text"):
                dpg.set_value("save_status_text", "Saved successfully!")
                dpg.configure_item("save_status_text", color=(0, 255, 0, 255))
            # Reset borders only if the window is still potentially visible
            # REMOVED call to _reset_widget_borders here, as it's causing issues and borders should be default on success.
            # if dpg.is_item_visible(self.tag):
            #      self._reset_widget_borders()
            # Decide whether to close the window after save
            # self._confirm_close_action(None, None, True) # Example: Auto-close on successful save

        except FileNotFoundError:
            print(f"Error: YAML file not found at {self.yaml_path} during save.")
            if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", "Error: File not found.")
                 dpg.configure_item("save_status_text", color=(255, 0, 0, 255))
        except yaml.YAMLError as e:
            print(f"Error writing YAML file: {e}")
            if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", "Error: Could not write YAML.")
                 dpg.configure_item("save_status_text", color=(255, 0, 0, 255))
        except Exception as e:
             print(f"An unexpected error occurred during save: {e}")
             if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", f"Error: {e}")
                 dpg.configure_item("save_status_text", color=(255, 0, 0, 255))


    def _get_current_data_as_str(self):
         """Gets the current state of the input fields as a concatenated string."""
         all_text = ""
         for method in self.test_methods:
             for aspect in self.detection_aspects:
                 for p_type in self.pattern_types:
                     widget_tag = f"input_{method}_{aspect}_{p_type}"
                     if dpg.does_item_exist(widget_tag):
                         all_text += dpg.get_value(widget_tag)
         return all_text

    def _cancel_changes(self):
        """Resets input fields to their state when the panel was opened or last saved."""
        print("Canceling changes...")
        for method in self.test_methods:
             for aspect in self.detection_aspects:
                 for p_type in self.pattern_types:
                     widget_tag = f"input_{method}_{aspect}_{p_type}"
                     original_patterns = self.data.get(method, {}).get(aspect, {}).get(p_type, [])
                     formatted_original = self._format_patterns(original_patterns)
                     if dpg.does_item_exist(widget_tag):
                         dpg.set_value(widget_tag, formatted_original)
        self._reset_widget_borders() # Clear any validation error highlights
        # Update status
        if dpg.does_item_exist("save_status_text"):
            dpg.set_value("save_status_text", "Changes canceled.")
            dpg.configure_item("save_status_text", color=(255, 255, 0, 255)) # Yellow for warning/info
        print("Changes canceled.")


    def _reset_widget_borders(self):
        """Resets the border color of all input widgets."""
        if not dpg.is_item_visible(self.tag): # Extra check: Don't proceed if window isn't visible
            return
        for method in self.test_methods:
            for aspect in self.detection_aspects:
                for p_type in self.pattern_types:
                    widget_tag = f"input_{method}_{aspect}_{p_type}"
                    # Check if item exists AND is visible/container is visible before configuring
                    if dpg.does_item_exist(widget_tag) and dpg.is_item_visible(widget_tag):
                         try:
                             # Resetting theme might be more robust if themes are used.
                              dpg.configure_item(widget_tag, border=False) # Or set to default theme color
                         except Exception as e:
                              print(f"Warning: Failed to reset border for {widget_tag}: {e}")


    def show(self):
        """Creates and shows the Dear PyGui window."""
        print("\nDEBUG: CriteriaPanel.show() called\n")
        self._load_data()
        if not self.data:
             print("Cannot show panel because data failed to load.")
             # Optionally show an error message in DPG
             if dpg.does_item_exist(self.tag):
                 dpg.delete_item(self.tag)
             with dpg.window(label="Error", tag=f"{self.tag}_error", width=300, height=100, modal=True, show=True):
                 dpg.add_text("Failed to load criteria data from:")
                 dpg.add_text(self.yaml_path, wrap=0)
                 dpg.add_button(label="OK", callback=lambda: dpg.delete_item(f"{self.tag}_error"))
             return

        # If window exists, just show it. Otherwise, create it.
        if dpg.does_item_exist(self.tag):
             dpg.show_item(self.tag)
             # Optionally re-load data or update fields if needed upon re-showing
             # self._load_data() # Re-load in case YAML changed externally? Consider implications.
             # self._cancel_changes() # Or maybe just reset to last saved state?
             if dpg.does_item_exist("save_status_text"): # Clear status on re-show
                 dpg.set_value("save_status_text", "")
             self._reset_widget_borders()
             return # Stop here, window is now shown

        # --- Create Window (only if it doesn't exist) --- 
        self.input_widgets.clear() # Clear references before rebuilding
        with dpg.window(label="Tuberculosis Criteria Panel", tag=self.tag, width=1200, height=700, 
                        on_close=self._on_close, no_saved_settings=True, modal=True):
            with dpg.group(horizontal=True):
                 dpg.add_button(label="Save Changes", callback=self._save_data)
                 dpg.add_button(label="Cancel", callback=self._cancel_changes)
                 dpg.add_text("", tag="save_status_text", color=(255, 255, 255, 255)) # Status text

            dpg.add_separator()

            # Define a theme for the table to reduce cell padding
            with dpg.theme() as table_theme:
                with dpg.theme_component(dpg.mvTable):
                    # Adjust cell padding (horizontal, vertical) - try vertical=2
                    dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, 2, category=dpg.mvThemeCat_Core)
                    
            # Create the table for the grid layout
            with dpg.table(header_row=True, borders_innerH=True, borders_outerH=True,
                           borders_innerV=True, borders_outerV=True, policy=dpg.mvTable_SizingStretchProp,
                           row_background=True, delay_search=True, # Removed clipper=True
                           width=-1, height=-1) as criteria_table: 
                
                # Apply the theme to the table
                dpg.bind_item_theme(criteria_table, table_theme)

                # Define Columns
                # Fixed width for first two columns
                dpg.add_table_column(label="Test Method", width_fixed=True)
                dpg.add_table_column(label="Pattern Type", width_fixed=True)
                # Stretched width for the rest, give equal weight
                for aspect in self.detection_aspects:
                    dpg.add_table_column(label=aspect.replace('_', ' ').title(), width_stretch=True, init_width_or_weight=1.0)

                # Populate Rows
                for method in self.test_methods:
                    for p_type_internal in self.pattern_types: # keywords, regex_patterns
                        # Make display name more friendly
                        p_type_display = "Keywords" if p_type_internal == "keywords" else "Regex Patterns"
                        
                        with dpg.table_row():
                            dpg.add_text(method) # Column 1: Test Method
                            dpg.add_text(p_type_display) # Column 2: Pattern Type
                            
                            # Add input widgets for each detection aspect
                            for aspect in self.detection_aspects:
                                patterns_list = self.data.get(method, {}).get(aspect, {}).get(p_type_internal, [])
                                formatted_patterns = self._format_patterns(patterns_list)
                                widget_tag = f"input_{method}_{aspect}_{p_type_internal}"
                                
                                # Add input text, no explicit height
                                self.input_widgets[method][aspect] = dpg.add_input_text(
                                    default_value=formatted_patterns,
                                    multiline=True,
                                    tag=widget_tag,
                                    width=-1, # Fill cell width
                                    callback=self._mark_unsaved, 
                                    user_data=method
                                )
                                
    def _mark_unsaved(self, sender, app_data, user_data):
        """Callback triggered when any input text changes."""
        current_str = self._get_current_data_as_str()
        if current_str != self.initial_data_str:
             if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", "Unsaved changes")
                 dpg.configure_item("save_status_text", color=(255, 255, 0, 255))
        else:
             if dpg.does_item_exist("save_status_text"):
                 dpg.set_value("save_status_text", "") # Clear status if back to original

    def _on_close(self):
        """Handles window close attempts. Always shows confirmation."""
        print("DEBUG: CriteriaPanel._on_close() called")
        current_str = self._get_current_data_as_str()
        unsaved = current_str != self.initial_data_str
        print(f"DEBUG: Unsaved changes status: {unsaved}")

        # Always show confirmation dialog, adjusting text based on state
        if dpg.does_item_exist("confirm_close_dialog"): 
            dpg.delete_item("confirm_close_dialog")
        
        confirm_text = "You have unsaved changes. Are you sure you want to close?" if unsaved else "Close Criteria Panel?"
        close_button_text = "Discard and Close" if unsaved else "Close"
        
        with dpg.window(label="Confirm Close", modal=True, show=True, tag="confirm_close_dialog", no_close=True, width=350, height=120):
            dpg.add_text(confirm_text)
            with dpg.group(horizontal=True):
                # Pass tuple: (is_confirm_action, has_unsaved_changes)
                dpg.add_button(label=close_button_text, width=150, callback=self._confirm_close_action, user_data=(True, unsaved))
                dpg.add_button(label="Cancel", width=75, callback=self._confirm_close_action, user_data=(False, unsaved))

    def _confirm_close_action(self, sender, app_data, user_data):
         """Action for the close confirmation dialog buttons."""
         dpg.delete_item("confirm_close_dialog") # Close the confirmation dialog
         
         is_confirm_action, has_unsaved_changes = user_data # Unpack data
         
         if is_confirm_action: # True if "Close" or "Discard and Close" was clicked
             if has_unsaved_changes:
                 print("DEBUG: Discarding changes and hiding criteria panel.")
             else:
                 print("DEBUG: Hiding criteria panel.")
             # Always hide the main panel if close action was confirmed
             dpg.hide_item(self.tag) 
         else: # False if "Cancel" was clicked
             print("DEBUG: Close cancelled.")
             # Do nothing, the main panel remains open

# Example usage (for testing)
# if __name__ == "__main__":
#     dpg.create_context()
#     panel = CriteriaPanel()
#     panel.show()
#     dpg.create_viewport(title='Criteria Panel Test', width=1250, height=750)
#     dpg.setup_dearpygui()
#     dpg.show_viewport()
#     dpg.start_dearpygui()
#     dpg.destroy_context() 