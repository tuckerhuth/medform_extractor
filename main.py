# main.py
import argparse
import os
import sys
import time

# Assume src is in the same directory or adjust sys.path accordingly
from src.scanner import scan_directory
from src.image_loader import load_image
from src.results import ResultManager, define_output_structure
from src.preprocessing import preprocess_image
from src.ocr import extract_text_from_image
from src.classification import classify_document, load_spacy_model
# Placeholder for future imports
# from src.classification import classify_document

# --- Constants ---
DEFAULT_OUTPUT_FILE = 'output/results.json'

# --- Main Processing Function ---
def process_image_file(file_path, result_manager):
    """Process a single image file: load, (preprocess, ocr, classify), save result."""
    print(f"Processing: {file_path}")
    start_time = time.time()

    # 1. Define initial result structure
    result_data = define_output_structure(file_path)

    # 2. Load Image
    image = load_image(file_path)
    if image is None:
        result_data['error'] = "Failed to load image"
        result_manager.add_result(result_data)
        print(f"Skipped (load error): {file_path}")
        return

    # 3. Preprocess Image
    processed_image = preprocess_image(image)
    if processed_image is None:
        result_data['error'] = "Preprocessing failed"
        result_manager.add_result(result_data)
        print(f"Skipped (preprocess error): {file_path}")
        return

    # 4. Perform OCR
    extracted_text = extract_text_from_image(processed_image) # Use preprocessed image
    if extracted_text is None:
        # If OCR failed, record error but maybe don't stop?
        # Depending on requirements, we might still want to record metadata or classify based on filename
        result_data['error'] = "OCR failed"
        # We will still save the result with the error below
        print(f"Warning: OCR failed for {file_path}")
    else:
        result_data['extracted_text'] = extracted_text

    # 5. Classify Document & Extract Metadata
    if result_data['extracted_text'] and not result_data['error']:
        try:
            # Ensure spaCy model is loaded (important if running multiple files)
            load_spacy_model()
            classification_result = classify_document(extracted_text)
            # Update main result dict with classification and metadata
            result_data['classification'] = classification_result.get('classification')
            result_data['confidence'] = classification_result.get('confidence')
            result_data['metadata'] = classification_result.get('metadata', {})
        except Exception as e:
            print(f"Error during classification for {file_path}: {e}", file=sys.stderr)
            # Decide if this should overwrite a previous OCR error or append
            if result_data['error']:
                result_data['error'] += "; Classification failed: {e}"
            else:
                 result_data['error'] = f"Classification failed: {e}"
    elif not result_data['error']: # Handle case where OCR produced no text but didn't error
         print(f"Skipping classification for {file_path} due to no extracted text.")

    # TEMP: Add dummy data until OCR/Classifier are implemented
    if result_data['extracted_text'] is None and result_data['error'] is None:
        result_data['extracted_text'] = "(OCR produced no text)"
    # END TEMP

    # 6. Save Result
    result_manager.add_result(result_data)

    end_time = time.time()
    print(f"Finished: {file_path} in {end_time - start_time:.2f} seconds")

# --- Command Line Interface --- 
def main():
    parser = argparse.ArgumentParser(description='Scan a directory for images, process them, and save results to JSON.')
    parser.add_argument('input_dir', type=str, help='Directory containing images to process.')
    parser.add_argument('-o', '--output', type=str, default=DEFAULT_OUTPUT_FILE,
                        help=f'Path to the output JSON file (default: {DEFAULT_OUTPUT_FILE})')
    # Add other arguments as needed (e.g., --force-reprocess, --log-level)

    args = parser.parse_args()

    input_directory = args.input_dir
    output_file = args.output

    # Validate input directory
    if not os.path.isdir(input_directory):
        print(f"Error: Input directory not found or is not a directory: {input_directory}", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir: # Only create if output_file includes a directory path
        os.makedirs(output_dir, exist_ok=True)

    print(f"Starting image processing.")
    print(f"Input Directory: {input_directory}")
    print(f"Output File: {output_file}")

    # Initialize result manager
    result_manager = ResultManager(output_file)

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
            process_image_file(file_path, result_manager)
            processed_files += 1
            # Output progress in a format the GUI can parse
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()  # Ensure output is sent immediately
        except Exception as e:
            # Catch unexpected errors during processing of a single file
            print(f"Critical error processing file {file_path}: {e}", file=sys.stderr)
            # Optionally log this error to the JSON result for the specific file
            error_result = define_output_structure(file_path)
            error_result['error'] = f"Unexpected processing error: {e}"
            result_manager.add_result(error_result)
            processed_files += 1
            print(f"PROGRESS:{processed_files}")
            sys.stdout.flush()

    print(f"\nProcessing complete. Results saved to {output_file}")


if __name__ == '__main__':
    main() 