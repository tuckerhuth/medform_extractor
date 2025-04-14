# Implementation Plan: Migrating ImageExtractor GUI from PySide6 to Dear PyGui

**Goal:** Replace the PySide6/Qt GUI framework with Dear PyGui (DPG) in `launch.py` to resolve persistent environment/packaging issues related to Qt dependencies, while retaining the core application logic for image processing and data handling.

**Core Strategy:** Rewrite the UI presentation and interaction layer using DPG components, replace `QProcess` with standard Python `subprocess` and `threading` for background tasks, and simplify the overall application structure where possible.

---

**1. Dependency & Environment Setup**

*   **Update `environment.yml`:**
    *   Remove the `pyside6` dependency line.
    *   Add `dearpygui` as a dependency (likely from `conda-forge`).
    *   Verify other dependencies (`python=3.11`, `pip`, `pandas`, `pillow`, `numpy<2`, `openpyxl`, `importlib_resources`, `requests`, `nltk`, `spacy`, the pip-installed `en_core_web_sm`) are still appropriate.
*   **Create New Conda Environment:**
    *   Remove any previous `image_extract...` environments (`conda env remove -n ...`).
    *   Create a fresh environment using the modified `environment.yml` file (`conda create -n image_extract_dpg python=3.11 -y && conda activate image_extract_dpg && conda env update -f environment.yml --prune`).

**2. Refactor `launch.py` - Core Application Structure**

*   **Remove Qt Imports:** Delete all imports from `PySide6`.
*   **Add New Imports:** Import `dearpygui.dearpygui as dpg`, `threading`, `subprocess`, `queue`, `time`, `sys`, `os`, `pathlib`.
*   **Refactor `ImageProcessorUI` Class:**
    *   Remove `QMainWindow` inheritance.
    *   The `__init__` method will primarily initialize state variables (paths, process handles, etc.) rather than building the Qt UI structure.
    *   UI creation logic will move to separate functions called after DPG initialization.
*   **Implement DPG Lifecycle in `main()`:**
    *   Remove `QApplication` setup.
    *   Add `dpg.create_context()`.
    *   Add `dpg.create_viewport(title="Image Extractor", width=600, height=500)`.
    *   Call a function (e.g., `_build_ui()`) to define the DPG windows and items.
    *   Add `dpg.setup_dearpygui()`.
    *   Add `dpg.show_viewport()`.
    *   Replace `app.exec()` with the main render loop: `while dpg.is_dearpygui_running(): dpg.render_dearpygui_frame()`.
    *   Call cleanup code (see step 6) *after* the loop.
    *   Add `dpg.destroy_context()` at the very end.

**3. Refactor `launch.py` - UI Layout and Elements (Inside `_build_ui`)**

*   **Primary Window:** Create the main application window using `dpg.add_window(tag="Primary Window")`.
*   **Layout:** Use `dpg.add_group(...)` and `dpg.group(horizontal=True)` to structure sections roughly equivalent to the previous `QVBoxLayout` and `QHBoxLayout`. Use `dpg.add_spacer`, `dpg.add_separator`, `dpg.add_indent` as needed for spacing and alignment.
*   **Replace Widgets:**
    *   `QLabel` -> `dpg.add_text("Static text")` or `dpg.add_text("Default status", tag="status_label_tag")` for dynamic labels.
    *   `QPushButton` -> `dpg.add_button(label="...", tag="button_tag", callback=callback_function, enabled=False)`.
    *   `QProgressBar` -> `dpg.add_progress_bar(tag="progress_tag", overlay="0%", default_value=0.0, width=-1)`. Show/hide using `dpg.configure_item("progress_tag", show=True/False)`.
    *   Text sections (`hr`, bold headers) -> Use `dpg.add_separator()` and `dpg.add_text("Step 1: ...")`. DPG doesn't directly support rich text like Qt's labels, keep it simple.
*   **Assign Unique Tags:** Assign meaningful string tags to all items that need to be referenced dynamically (status labels, progress bars, buttons).

**4. Refactor `launch.py` - Interaction and Callbacks**

*   **Button Callbacks:** Define standard Python functions (e.g., `_select_folder_callback`, `_run_text_extraction_callback`) and assign them to the `callback` argument of `dpg.add_button`.
*   **File/Folder Dialogs:**
    *   Use `dpg.add_file_dialog(...)` and `dpg.add_directory_dialog(...)`.
    *   Set `show=False` initially.
    *   The "Select Folder" button callbacks will call `dpg.show_item(dialog_tag)`.
    *   Define callback functions for the dialogs themselves (`callback=dialog_callback_function`). These callbacks receive the selection data (path). Store the selected path in an instance variable and update relevant text labels (e.g., `dpg.set_value("folder_label_tag", f"Selected: {path}")`).
*   **State Updates:** Button callbacks and dialog callbacks will update application state (stored paths) and enable/disable other UI elements using `dpg.configure_item(tag, enabled=True/False)`.
*   **Criteria Editor Simplification:**
    *   The "View Criteria" button callback will simply use `subprocess.run(['open', self.criteria_file_path])` (macOS) or equivalent (`os.startfile` on Windows) to open the `.md` file in the default text editor. Avoid reimplementing the editor dialog initially.
*   **Export:** The "Export" button callback will trigger the existing `export_results_to_excel` logic (which reads from `self.fields_output_dir`). The file save dialog will be implemented using `dpg.add_file_dialog(..., default_filename="aggregated_fields_output.xlsx", callback=...)`.

**5. Refactor `launch.py` - Background Process Management**

*   **Remove `QProcess`:** Delete `self.text_process`, `self.field_process`, and associated signal connections (`readyRead...`, `finished`).
*   **Worker Thread Function (`_execute_script`):**
    *   Accepts `command` (list), `output_queue` (`queue.Queue`), `process_type` ("text" or "fields"), optional `total_files`.
    *   Uses `subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore', bufsize=1)` to start the script. Store the `Popen` object.
    *   Define helper functions `_read_stream(stream, queue, type)` to read lines from stdout/stderr and put them on the queue with type information (e.g., `queue.put(("stdout", line))` ). Start these readers in separate threads.
    *   Wait for the process to complete: `exit_code = process.wait()`.
    *   Wait for the reader threads to finish (`join()`).
    *   Put a final completion message on the queue: `queue.put(("finished", exit_code))`.
*   **Button Callbacks (`_run_text_extraction_callback`, `_run_field_extraction_callback`):**
    *   Disable relevant buttons (`dpg.configure_item(...)`).
    *   Show progress bar.
    *   Create a `queue.Queue()`.
    *   Construct the `command` list for the appropriate script (using `sys.executable`, `BASE_PATH`, required arguments like input/output directories from instance variables).
    *   Store the script's Popen object: `self.current_process_popen = subprocess.Popen(...)`.
    *   Start the `_execute_script` function in a `threading.Thread(..., daemon=True)`.
    *   Store the queue: `self.current_queue = output_queue`.
*   **GUI Update in Main Loop:**
    *   Add `_check_script_queue()` function called inside the main DPG `while` loop.
    *   `_check_script_queue()` tries to get messages from `self.current_queue` (use `queue.get_nowait()`).
    *   Processes messages:
        *   `("stdout", line)`: Parse line. If it's a progress update (`PROGRESS:`), update progress bar (`dpg.set_value(progress_tag, value)`). Update status text label (`dpg.set_value(status_tag, line)`).
        *   `("stderr", line)`: Update status text label with error, show copy button (if implemented).
        *   `("finished", exit_code)`: Update status label (success/failure). Hide progress bar. Re-enable buttons. Clear `self.current_process_popen` and `self.current_queue`. Enable export button if field extraction succeeded and files exist.

**6. Refactor `launch.py` - Cleanup and Quit Logic**

*   **Quit Button:** Callback calls `dpg.stop_dearpygui()`.
*   **Post-Loop Cleanup:** After the `while dpg.is_dearpygui_running():` loop:
    *   Check `self.current_process_popen` (and potentially separate variables for text/field processes if needed). If a process exists and `popen.poll() is None` (still running), call `popen.terminate()`, wait briefly (`popen.wait(timeout=1)`), and call `popen.kill()` if it didn't terminate.
    *   Call `release_lock(...)`.
    *   Call `dpg.destroy_context()`.

**7. Preserve Core Non-GUI Logic**

*   Ensure `determine_base_path()` and `BASE_PATH` logic works.
*   Ensure user output directory creation (`APP_OUTPUT_BASE`, `DEFAULT_TEXT_OUTPUT_DIR`, `DEFAULT_FIELDS_OUTPUT_DIR`) occurs correctly (likely early in `main` or `__init__`).
*   Ensure `acquire_lock()` is called at the start and `release_lock()` is called reliably before exit (see step 6).
*   Keep the `export_results_to_excel` and `_export_data_to_file` logic largely unchanged, just trigger it from the new DPG export button callback and file dialog.

**8. Update Packaging (`ImageExtractor.spec`)**

*   Remove PySide6/Qt specific hidden imports or hooks.
*   Ensure `dearpygui` is included (PyInstaller usually handles this, but check).
*   Verify the `datas` section still correctly includes:
    *   `('extract_text.py', '.')`
    *   `('process_ocr.py', '.')`
    *   `('src', 'src')`
    *   `('disease_keywords', 'disease_keywords')`
    *   `('MyAppIcon.icns', '.')`
*   Ensure the `icon='MyAppIcon.icns'` parameter is still set in the `BUNDLE` section.
*   Run the build script (`build_macos.sh`) and verify it completes successfully.

**9. Testing**

*   **Incremental Testing:** Run `python launch.py` frequently during development to test UI layout, basic callbacks, and process launching.
*   **Functionality Testing:** Test the full workflow: selecting folders, text extraction, field extraction, export, quitting. Check terminal `DEBUG` output (if added) and the contents of the `~/Documents/ImageExtractorOutput/` directories.
*   **Error Handling:** Test cases like selecting empty folders, invalid file types, interrupting processes.
*   **Bundle Testing:** Test the final `.app` bundle created by PyInstaller thoroughly on macOS.

--- 