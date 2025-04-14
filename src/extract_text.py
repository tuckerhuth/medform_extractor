#!/usr/bin/env python3
import argparse
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import logging
import traceback
import shutil # Needed by rotate_logs
# import cv2 # No longer needed here unless preprocessing is re-enabled
from src.scanner import scan_directory
# from src.image_loader import load_image # Only needed if preprocessing
# from src.preprocessing import preprocess_image # Only needed if preprocessing
from src.ocr import extract_text_from_image

# --- Setup Logging Early --- 
try:
    APP_OUTPUT_BASE = get_app_output_base("extract_text") # Pass process name
    log_dir = APP_OUTPUT_BASE / "logs"
    log_file_path = rotate_logs(log_dir, "extract_text.log")
    
    # --- Add explicit checks and prints ---
    print(f"DEBUG EXTRACT_TEXT: Log dir target: {log_dir}", file=sys.stderr)
    print(f"DEBUG EXTRACT_TEXT: Log file path target: {log_file_path}", file=sys.stderr)
    
    log_dir.mkdir(parents=True, exist_ok=True) # Ensure log dir exists
    print(f"DEBUG EXTRACT_TEXT: Log dir exists check passed.", file=sys.stderr)
    
    if not os.access(str(log_dir), os.W_OK):
        print(f"FATAL EXTRACT_TEXT: Log directory {log_dir} is not writable.", file=sys.stderr)
        raise PermissionError(f"Log directory {log_dir} not writable")
        
    if not os.access(str(Path(log_file_path).parent), os.W_OK):
        print(f"FATAL EXTRACT_TEXT: Parent of log file {log_file_path} is not writable.", file=sys.stderr)
        raise PermissionError(f"Parent directory of {log_file_path} not writable")
        
    print(f"DEBUG EXTRACT_TEXT: Write permission checks passed. Creating FileHandler...", file=sys.stderr)
    # --- End checks ---

    # Use a basic file handler for this script
    file_handler = logging.FileHandler(log_file_path)
    print(f"DEBUG EXTRACT_TEXT: FileHandler created.", file=sys.stderr)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Get the specific logger and add the handler
    logger = logging.getLogger('ImageExtractor.extract_text') # Use specific logger name
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG) # Set level for this logger
    
    # Optional: Add handler to root logger if needed, but be careful
    # logging.getLogger().addHandler(file_handler)
    # logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("--- extract_text.py logging configured ---")
    
except Exception as log_setup_e:
    # Fallback to stderr if logging setup fails
    print(f"FATAL EXTRACT_TEXT: Error setting up logging to {log_file_path}: {log_setup_e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    logger = logging.getLogger('ImageExtractor.extract_text') # Get logger instance anyway
    # Add NullHandler to prevent "No handlers could be found" warnings if setup fails
    logger.addHandler(logging.NullHandler())
# --- End Logging Setup ---

PREPROCESSED_OUTPUT_DIR = "preprocessed_images" # Keep for now, might remove later

def rotate_logs(log_dir: Path, log_name: str, max_backups: int = 5):
    """Rotate log files, keeping the specified number of backups with timestamps."""
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        archive_dir = log_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        # Current log file
        current_log = log_dir / log_name
        
        if current_log.exists():
            # Generate timestamp for archive name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived_name = f"{log_name}.{timestamp}"
            archived_path = archive_dir / archived_name
            
            # Move current log to archive
            shutil.move(str(current_log), str(archived_path))
            
            # Get list of archived logs sorted by modification time
            archived_logs = sorted(
                archive_dir.glob(f"{log_name}.*"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Remove oldest logs if we have too many
            for old_log in archived_logs[max_backups:]:
                old_log.unlink()
                
        return str(current_log)
    except Exception as e:
        print(f"Error rotating logs: {e}", file=sys.stderr)
        return str(current_log)

def get_app_output_base(process_name="unknown"):
    """Determines the base directory for application output."""
    # Added process_name parameter for debug context
    try:
        base_path_str = os.environ.get("APP_OUTPUT_BASE")
        if base_path_str:
            print(f"DEBUG [{process_name}]: Using APP_OUTPUT_BASE from env: {base_path_str}", file=sys.stderr)
            output_path = Path(base_path_str)
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                print(f"DEBUG [{process_name}]: Ensured directory from env var exists: {output_path}", file=sys.stderr)
            except Exception as mkdir_e:
                 print(f"Warning [{process_name}]: Could not create directory from APP_OUTPUT_BASE {output_path}: {mkdir_e}", file=sys.stderr)
            return output_path

        print(f"DEBUG [{process_name}]: APP_OUTPUT_BASE not set, falling back to ~/Documents/ImageExtractorOutput", file=sys.stderr)
        user_docs = Path.home() / "Documents"
        output_path = user_docs / "ImageExtractorOutput"
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG [{process_name}]: Ensured fallback directory exists: {output_path}", file=sys.stderr)
            return output_path
        except Exception as mkdir_e:
             print(f"Error [{process_name}]: creating primary fallback directory {output_path}: {mkdir_e}", file=sys.stderr)
             fallback_path = Path.home() / "ImageExtractorOutput_Fallback"
             print(f"DEBUG [{process_name}]: Trying secondary fallback: {fallback_path}", file=sys.stderr)
             try:
                 fallback_path.mkdir(parents=True, exist_ok=True)
                 print(f"DEBUG [{process_name}]: Ensured secondary fallback directory exists: {fallback_path}", file=sys.stderr)
                 return fallback_path
             except Exception as fallback_mkdir_e:
                 print(f"FATAL [{process_name}]: Could not create secondary fallback directory {fallback_path}: {fallback_mkdir_e}", file=sys.stderr)
                 return fallback_path

    except Exception as e:
        print(f"Error [{process_name}]: determining app output directory: {e}", file=sys.stderr)
        final_fallback = Path.home() / "ImageExtractorOutput_Fallback"
        print(f"DEBUG [{process_name}]: Using final fallback due to exception: {final_fallback}", file=sys.stderr)
        try:
            final_fallback.mkdir(parents=True, exist_ok=True)
            print(f"DEBUG [{process_name}]: Ensured final fallback directory exists: {final_fallback}", file=sys.stderr)
        except Exception as final_mkdir_e:
             print(f"FATAL [{process_name}]: Could not create ANY output directory: {final_mkdir_e}", file=sys.stderr)
        return final_fallback

def process_image_file(file_path, output_dir):
    """Extract text from a single image file and save to JSON."""
    logger.info(f"Starting processing of file: {file_path}")
    start_time = time.time()

    # Create output structure
    result = {
        'file_path': str(file_path),
        'extracted_text': None,
        'error': None,
        'image_last_modified': None,
        'preprocessed_image_path': None, # Keep field, but won't be populated by Vision
        'extraction_timestamp': datetime.now().isoformat(),
        'processing_time': None,
        'error_details': None
    }

    try:
        # Log file details
        file_stats = os.stat(file_path)
        logger.debug(f"File stats: size={file_stats.st_size}, modified={datetime.fromtimestamp(file_stats.st_mtime)}")
        
        # Get image modification time *before* processing
        result['image_last_modified'] = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

        # Verify file exists and is readable
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"Cannot read image file: {file_path}")

        # --- Preprocessing Skipped --- 
        # processed_image = preprocess_image(image)
        # if processed_image is None:
        #     result['error'] = "Preprocessing failed"
        #     return result
        # Use the original loaded image instead
        # processed_image = image # Pass the original Pillow image object
        # --- End Skip --- 

        # --- Save preprocessed image --- 
        # try:
        #     preprocessed_dir = Path(output_dir).parent / PREPROCESSED_OUTPUT_DIR
        #     preprocessed_dir.mkdir(parents=True, exist_ok=True)
        #     input_path = Path(file_path)
        #     preprocessed_filename = input_path.stem + "_preprocessed.png"
        #     preprocessed_save_path = preprocessed_dir / preprocessed_filename
        #     
        #     # Note: Saving the *original* image here if preprocessing is skipped
        #     # This saving step needs re-evaluation if using Vision framework
        #     # if cv2.imwrite(str(preprocessed_save_path), processed_image):
        #     #     result['preprocessed_image_path'] = str(preprocessed_save_path)
        #     # else:
        #     #     print(f"Warning: Failed to save preprocessed image for {file_path}")
        # except Exception as save_err:
        #     print(f"Warning: Error saving preprocessed image for {file_path}: {save_err}")
        # --- End save --- 

        # Perform OCR using Vision framework
        logger.debug(f"Initiating OCR for file: {file_path}")
        extracted_text = extract_text_from_image(str(file_path))

        if extracted_text is None:
            error_msg = "OCR failed to extract any text"
            logger.error(error_msg)
            result['error'] = error_msg
            result['error_details'] = "Vision framework returned None"
        else:
            logger.info(f"Successfully extracted {len(extracted_text)} characters of text")
            result['extracted_text'] = extracted_text

    except FileNotFoundError as e:
        error_msg = f"File not found: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
        result['error_details'] = traceback.format_exc()
    except PermissionError as e:
        error_msg = f"Permission error: {str(e)}"
        logger.error(error_msg)
        result['error'] = error_msg
        result['error_details'] = traceback.format_exc()
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result['error'] = error_msg
        result['error_details'] = traceback.format_exc()

    # Record processing time
    result['processing_time'] = time.time() - start_time
    logger.info(f"Completed processing {file_path} in {result['processing_time']:.2f} seconds")
    return result

def save_result(result, output_dir):
    """Save extraction result to a JSON file."""
    try:
        # Create a filename based on the original file path
        input_path = Path(result['file_path'])
        relative_path = input_path.with_suffix('.json').name
        output_path = Path(output_dir) / relative_path
        
        logger.debug(f"Saving results to: {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the result
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='Extract text from images in a directory and save results.')
    parser.add_argument('input_dir', help='Directory containing images to process')
    parser.add_argument('-o', '--output-dir', default='extracted_text',
                      help='Directory to save extracted text JSON files (default: extracted_text)')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.is_dir():
        print(f"Error: Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Scan for image files (including subdirectories)
    try:
        image_files = list(scan_directory(str(input_dir)))
        print(f"Found {len(image_files)} image(s) to process.")
    except ValueError as e:
        print(f"Error scanning directory: {e}", file=sys.stderr)
        sys.exit(1)

    if not image_files:
        print("No image files found.")
        sys.exit(0)

    # Process each image
    processed_files = 0
    for file_path in image_files:
        try:
            # Process the image and get result
            result = process_image_file(file_path, output_dir)
            
            # Save the result
            save_result(result, output_dir)
            
            # Update progress
            processed_files += 1
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()
            
            # Print status
            status = "Success" if not result['error'] else f"Error: {result['error']}"
            print(f"Processed {file_path}: {status}")
            
        except Exception as e:
            print(f"Failed to process {file_path}: {e}", file=sys.stderr)
            processed_files += 1
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()

    print(f"\nProcessing complete. Results saved in {output_dir}")

if __name__ == '__main__':
    main() 