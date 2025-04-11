# main.py
import argparse
import os
import sys
import time

# Assume src is in the same directory or adjust sys.path accordingly
from src.scanner import scan_directory
from src.image_loader import load_image
# from src.results import ResultManager, define_output_structure # Commented out
from src.preprocessing import preprocess_image
from src.ocr import extract_text_from_image
from src.classification import classify_document, load_spacy_model
# Placeholder for future imports
# from src.classification import classify_document

# --- Constants ---
# DEFAULT_OUTPUT_FILE = 'output/results.json' # Commented out - no longer writing this file from here
DEFAULT_OUTPUT_FILE = None # Or set to None if the variable is checked elsewhere

# --- Main Processing Function ---
# def process_image_file(file_path, result_manager): # Commented out result_manager argument
def process_image_file(file_path): # Removed result_manager argument
    """Process a single image file: load, (preprocess, ocr, classify). Does NOT save result via ResultManager anymore."""
    print(f"Processing: {file_path}")
    start_time = time.time()

    # 1. Define initial result structure (Locally, not for saving via ResultManager)
    # result_data = define_output_structure(file_path) # Commented out
    # Store intermediate results if needed locally
    processing_status = {'file_path': file_path, 'error': None, 'extracted_text': None, 'classification': None, 'metadata': {}}

    # 2. Load Image
    image = load_image(file_path)
    if image is None:
        # result_data['error'] = "Failed to load image" # Commented out
        # result_manager.add_result(result_data) # Commented out
        processing_status['error'] = "Failed to load image"
        print(f"Skipped (load error): {file_path}")
        return # No need to return data if not saving

    # 3. Preprocess Image
    processed_image = preprocess_image(image)
    if processed_image is None:
        # result_data['error'] = "Preprocessing failed" # Commented out
        # result_manager.add_result(result_data) # Commented out
        processing_status['error'] = "Preprocessing failed"
        print(f"Skipped (preprocess error): {file_path}")
        return # No need to return data if not saving

    # 4. Perform OCR
    extracted_text = extract_text_from_image(processed_image) # Use preprocessed image
    if extracted_text is None:
        # If OCR failed, record error but maybe don't stop?
        # Depending on requirements, we might still want to record metadata or classify based on filename
        # result_data['error'] = "OCR failed" # Commented out
        processing_status['error'] = "OCR failed"
        # We will still save the result with the error below
        print(f"Warning: OCR failed for {file_path}")
    else:
        # result_data['extracted_text'] = extracted_text # Commented out
        processing_status['extracted_text'] = extracted_text

    # 5. Classify Document & Extract Metadata
    # if result_data['extracted_text'] and not result_data['error']: # Check local status instead
    if processing_status['extracted_text'] and not processing_status['error']:
        try:
            # Ensure spaCy model is loaded (important if running multiple files)
            load_spacy_model()
            classification_result = classify_document(extracted_text)
            # Update main result dict with classification and metadata
            # result_data['classification'] = classification_result.get('classification') # Commented out
            # result_data['confidence'] = classification_result.get('confidence') # Commented out
            # result_data['metadata'] = classification_result.get('metadata', {}) # Commented out
            processing_status['classification'] = classification_result.get('classification')
            processing_status['confidence'] = classification_result.get('confidence')
            processing_status['metadata'] = classification_result.get('metadata', {}) # Store locally if needed
        except Exception as e:
            print(f"Error during classification for {file_path}: {e}", file=sys.stderr)
            # Decide if this should overwrite a previous OCR error or append
            # if result_data['error']: # Commented out
            #     result_data['error'] += f"; Classification failed: {e}" # Commented out
            if processing_status['error']:
                processing_status['error'] += f"; Classification failed: {e}"
            else:
                 processing_status['error'] = f"Classification failed: {e}"
    # elif not result_data['error']: # Handle case where OCR produced no text but didn't error
    elif not processing_status['error']: # Check local status
         print(f"Skipping classification for {file_path} due to no extracted text.")

    # TEMP: Add dummy data until OCR/Classifier are implemented
    # if result_data['extracted_text'] is None and result_data['error'] is None: # Commented out
    if processing_status['extracted_text'] is None and processing_status['error'] is None:
        # This part doesn't seem necessary anymore if we're not saving the structure
        pass # Or log locally: print("OCR produced no text but no error recorded.")
    # END TEMP

    # 6. Save Result
    # result_manager.add_result(result_data) # Commented out

    end_time = time.time()
    print(f"Finished: {file_path} in {end_time - start_time:.2f} seconds (results not saved by this function)")
    # Optionally return the processed data if needed by the caller
    # return processing_status

# --- Command Line Interface ---
def main():
    parser = argparse.ArgumentParser(description='Scan a directory for images, process them (OCR, Classify). Does NOT save structured results to JSON anymore.')
    parser.add_argument('input_dir', type=str, help='Directory containing images to process.')
    # parser.add_argument('-o', '--output', type=str, default=DEFAULT_OUTPUT_FILE, # Commented out
    #                     help=f'Path to the output JSON file (default: {DEFAULT_OUTPUT_FILE})') # Commented out
    # Add other arguments as needed (e.g., --force-reprocess, --log-level)

    args = parser.parse_args()

    input_directory = args.input_dir
    # output_file = args.output # Commented out

    # Validate input directory
    if not os.path.isdir(input_directory):
        print(f"Error: Input directory not found or is not a directory: {input_directory}", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists (No longer needed for ResultManager)
    # output_dir = os.path.dirname(output_file) # Commented out
    # if output_dir: # Only create if output_file includes a directory path # Commented out
    #     os.makedirs(output_dir, exist_ok=True) # Commented out

    print(f"Starting image processing.")
    print(f"Input Directory: {input_directory}")
    # print(f"Output File: {output_file}") # Commented out

    # Initialize result manager (Commented out)
    # result_manager = ResultManager(output_file) # Commented out

    # Scan for image files
    try:
        image_files = list(scan_directory(input_directory))
        print(f"Found {len(image_files)} image(s) to process.")
    except ValueError as e:
        print(f"Error scanning directory: {e}", file=sys.stderr)
        sys.exit(1)

    if not image_files:
        print("No image files found in the specified directory.")
        sys.exit(0)

    # Process each image file
    total_files = len(image_files)
    processed_files = 0

    for file_path in image_files:
        try:
            # process_image_file(file_path, result_manager) # Pass result_manager
            process_image_file(file_path) # Don't pass result_manager
            processed_files += 1
            # Output progress in a format the GUI can parse
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()  # Ensure output is sent immediately
        except Exception as e:
            # Catch unexpected errors during processing of a single file
            print(f"Critical error processing file {file_path}: {e}", file=sys.stderr)
            # Optionally log this error to the JSON result for the specific file (Commented out)
            # error_result = define_output_structure(file_path) # Commented out
            # error_result['error'] = f"Unexpected processing error: {e}" # Commented out
            # result_manager.add_result(error_result) # Commented out
            processed_files += 1 # Still count as processed (with error) for progress
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()

    # print(f"\nProcessing complete. Results saved to {output_file}") # Commented out
    print(f"\nProcessing complete. {processed_files}/{total_files} files attempted.")

if __name__ == '__main__':
    main() 