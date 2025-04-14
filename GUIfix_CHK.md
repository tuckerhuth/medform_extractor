# Checklist: Migrating ImageExtractor GUI to Dear PyGui

This checklist guides the implementation of the plan outlined in `GUIfix_IMP.md`, focusing on an iterative development and testing cycle.

**Editor:** vim
**Test Directory:** `tests/`

---

**Phase 1: Environment and Basic DPG Setup**

*   [X] **Implement:** Modify `environment.yml`: Remove `pyside6`, add `dearpygui`. Ensure `conda-forge` is the primary channel.
*   [X] **Implement:** Remove old `image_extract...` conda environments.
*   [X] **Implement:** Create and activate the new `image_extract_dpg` environment using the modified `environment.yml`.
    *   Command: `conda create -n image_extract_dpg python=3.11 -y && conda activate image_extract_dpg && conda env update -f environment.yml --prune`
*   [X] **Test:** Verify environment creation succeeded without errors (check terminal output). Check `dearpygui` is installed (`pip show dearpygui` or `conda list dearpygui`).
*   [X] **Implement:** Refactor `launch.py`:
    *   Remove all `PySide6` imports.
    *   Add required imports: `dearpygui.dearpygui as dpg`, `threading`, `subprocess`, `queue`, `time`, `sys`, `os`, `pathlib`.
    *   Remove `QMainWindow` inheritance from `ImageProcessorUI` (if it's still a class).
    *   Implement the basic DPG lifecycle (`create_context`, `create_viewport`, placeholder `_build_ui` function, `setup_dearpygui`, `show_viewport`, main loop, `destroy_context`) in `main()`.
*   [X] **Test:** Run `python launch.py`.
    *   **Expected:** An empty DPG window titled "Image Extractor" should appear without crashing. No Qt/plugin errors should occur. The window should be closable.

**Phase 2: Basic UI Layout & Static Elements**

*   [X] **Implement:** Define `_build_ui()` function in `launch.py`.
*   [X] **Implement:** Inside `_build_ui()`, create the primary DPG window (`dpg.add_window`).
*   [X] **Implement:** Add basic static layout elements using `dpg.add_text`, `dpg.add_separator`, `dpg.add_group`, `dpg.add_spacer` to mimic the two main sections ("Step 1: Extract Text", "Step 2: Extract Fields"). Focus on structure, not dynamic content yet. Add the static "Quit" button (without callback initially).
*   [X] **Test:** Run `python launch.py`.
    *   **Expected:** The DPG window should show the basic structure with text headers and separators, resembling the original layout conceptually. The Quit button should be visible.

**Phase 3: File/Folder Selection & Display**

*   [X] **Implement:** Add the "Select Image Folder" button (`dpg.add_button`) and the text label for displaying the selected path (`dpg.add_text(tag="image_folder_label")`).
*   [X] **Implement:** Add the "Select Text Folder (Optional)" button and its corresponding display label (`dpg.add_text(tag="text_folder_label")`). Set the initial text for the text folder label based on `DEFAULT_TEXT_OUTPUT_DIR`.
*   [X] **Implement:** Add the DPG directory dialogs (`dpg.add_directory_dialog`), one for image folder selection (`tag="image_dialog"`) and one for text folder selection (`tag="text_dialog"`), initially hidden (`show=False`).
*   [X] **Implement:** Create callback functions (`_select_image_folder_callback`, `_select_text_folder_callback`) for the *buttons*. These callbacks should simply show the corresponding dialog (`dpg.show_item("image_dialog")`, etc.). Assign these callbacks to the buttons.
*   [X] **Implement:** Create callback functions (`_image_folder_selected_callback`, `_text_folder_selected_callback`) for the *dialogs*. These callbacks receive `app_data` containing the selected path.
    *   Store the selected path in an appropriate variable (e.g., `self.selected_image_folder`).
    *   Update the corresponding text label using `dpg.set_value("image_folder_label", ...)`.
    *   Enable the "Extract Text" button (`dpg.configure_item("extract_text_btn", enabled=True)`) in the image folder callback.
    *   Update the state for the field extraction button (`update_field_extraction_button_state()`) in the text folder callback.
*   [ ] **Test:** Run `python launch.py`.
    *   **Expected:** Click "Select Image Folder", dialog appears, select folder, dialog closes, path is displayed in the label, "Extract Text" button becomes enabled.
    *   **Expected:** Click "Select Text Folder", dialog appears, select folder, dialog closes, path is displayed in the label, "Extract Fields" button state updates correctly.

**Phase 4: Background Process Execution (Text Extraction)**

*   [X] **Implement:** Add the "Extract Text" button (`tag="extract_text_btn"`, initially disabled) and its status label (`tag="status_label_text"`). Add the corresponding progress bar (`tag="progress_bar_text"`, initially hidden).
*   [X] **Implement:** Create the `_execute_script` worker function (as described in the plan) using `subprocess.Popen`, `threading`, and `queue.Queue`. Include basic parsing for `PROGRESS:` lines.
*   [X] **Implement:** Create the `_run_text_extraction_callback` function for the "Extract Text" button.
    *   It should disable buttons, show the progress bar, construct the command list for `extract_text.py` (using `sys.executable`, `BASE_PATH`, `self.selected_image_folder`, `self.text_output_dir`), create a queue, store the `Popen` object, and start `_execute_script` in a daemon thread.
*   [X] **Implement:** Create the `_check_script_queue` function (called in the main DPG loop). Implement logic to read from the queue and update the status label and progress bar based on `"stdout"`, `"stderr"`, and `"finished"` messages. Re-enable buttons on `"finished"`.
*   [X] **Implement:** Add basic non-GUI unit tests for `_execute_script` (if feasible) or helper functions to `tests/`. Mock `subprocess.Popen`.
*   [X] **Test:** Run `python launch.py`. Select an image folder. Click "Extract Text".
    *   **Expected:** Buttons disable, progress bar appears (may not show accurate progress yet). Status label updates with messages from the script (or "Processing..."). `DEBUG` logs (if added) show subprocess starting. Check `~/Documents/ImageExtractorOutput/extracted_text` for JSON files being created. Upon completion, status updates, progress bar hides, buttons re-enable. Check terminal for errors.

**Phase 5: Background Process Execution (Field Extraction)**

*   [X] **Implement:** Add the "Extract Fields" button (`tag="extract_fields_btn"`, initially disabled), its status label (`tag="status_label_fields"`), and progress bar (`tag="progress_bar_fields"`, initially hidden).
*   [X] **Implement:** Create the `_run_field_extraction_callback` function for the "Extract Fields" button.
    *   Similar logic to text extraction: disable buttons, show progress bar, construct command for `process_ocr.py` (passing `--input-dir`, `--output-dir`, `--keywords-file`), create queue, store `Popen`, start `_execute_script` in a daemon thread.
*   [X] **Implement:** Ensure `_check_script_queue` correctly handles messages when `self.current_process_type == 'fields'` (updates the correct status label and progress bar).
*   [X] **Implement:** Add logic in the `"finished"` handler within `_check_script_queue` to enable the "Export Results" button (`tag="export_button"`) if field extraction was successful (`exit_code == 0`) and JSON files exist in `self.fields_output_dir`.
*   [X] **Test:** Run `python launch.py`. Run Step 1 (Text Extraction). Run Step 2 (Field Extraction).
    *   **Expected:** Similar behavior as Step 1 for button states, progress bar, and status updates, but using the Step 2 UI elements. Check `~/Documents/ImageExtractorOutput/extracted_fields` for JSON files. Check terminal for errors. "Export Results" button should enable upon success.

**Phase 6: Export and Final Buttons**

*   [X] **Implement:** Add the "Export Results to Excel" button (`tag="export_button"`, initially disabled).
*   [X] **Implement:** Add the DPG file dialog for saving (`dpg.add_file_dialog(..., tag="save_export_dialog", show=False)`).
*   [X] **Implement:** Create `_export_results_callback` for the export button. This function should:
    *   Check if JSON files exist in `self.fields_output_dir`. Show an error popup (using a modal DPG window) if not.
    *   If files exist, show the "save_export_dialog".
*   [X] **Implement:** Create `_save_export_callback` for the save dialog. This function receives the chosen filename (`app_data`).
    *   Call the existing `_export_data_to_file` logic (which needs the loaded `all_data` from `export_results_to_excel` - refactor slightly to separate finding files/loading data from initiating the save dialog).
    *   Show a success/error popup (modal DPG window) based on the export result.
*   [X] **Implement:** Add the "View Criteria" button (`tag="view_criteria_btn"`). Implement its callback `_view_criteria_callback` to use `subprocess.run(['open', self.criteria_file_path])`.
*   [X] **Implement:** Add the Quit button callback (`_quit_callback`) which calls `dpg.stop_dearpygui()`.
*   [X] **Implement:** Add the post-loop cleanup logic (terminating subprocesses, releasing lock file).
*   [X] **Test:** Run the full workflow: Step 1 -> Step 2 -> Export.
    *   **Expected:** Select folder, extract text, extract fields. Export button enables. Click Export, save dialog appears. Save file. Verify Excel file is created correctly.
    *   **Expected:** Click "View Criteria", the `.md` file opens in the default editor.
    *   **Expected:** Click Quit, the application closes cleanly. Check terminal for cleanup messages and no errors. Verify lock file is removed.

**Phase 7: Packaging and Final Testing**

*   [X] **Implement:** Review and update `ImageExtractor.spec` according to plan step 8. Ensure `dearpygui` is handled and `datas` are correct.
*   [X] **Implement:** Run the build script (`build_macos.sh` or `pyinstaller ImageExtractor.spec`).
*   [X] **Test:** Check the `dist` folder for `ImageExtractor.app`.
    *   **Expected:** Build completes without PyInstaller errors. `.app` bundle exists.
*   [X] **Test:** Copy `.app` to `/Applications`. Run the bundled application.
    *   **Expected:** Application launches, icon is correct.
    *   **Expected:** Perform full workflow testing (select folder, step 1, step 2, view criteria, export, quit) within the bundled app. Verify all functionality works as expected and output files are created in `~/Documents/ImageExtractorOutput`. Check for any crashes or unexpected behavior.