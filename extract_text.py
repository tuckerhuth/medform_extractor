#!/usr/bin/env python3
import argparse
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
# import cv2 # No longer needed here unless preprocessing is re-enabled

from src.scanner import scan_directory
# from src.image_loader import load_image # Only needed if preprocessing
# from src.preprocessing import preprocess_image # Only needed if preprocessing
from src.ocr import extract_text_from_image

PREPROCESSED_OUTPUT_DIR = "preprocessed_images" # Keep for now, might remove later

def process_image_file(file_path, output_dir):
    """Extract text from a single image file and save to JSON."""
    print(f"Processing: {file_path}")
    start_time = time.time()

    # Create output structure
    result = {
        'file_path': str(file_path),
        'extracted_text': None,
        'error': None,
        'image_last_modified': None,
        'preprocessed_image_path': None, # Keep field, but won't be populated by Vision
        'extraction_timestamp': datetime.now().isoformat(),
        'processing_time': None
    }

    try:
        # Get image modification time *before* processing
        result['image_last_modified'] = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

        # Load and process image
        # image = load_image(file_path)
        # if image is None:
        #     result['error'] = "Failed to load image"
        #     return result

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

        # Perform OCR using Vision framework (pass file path directly)
        extracted_text = extract_text_from_image(str(file_path)) # Pass the path

        if extracted_text is None:
            # If Vision failed, set an error. Empty string means no text found.
            if result['error'] is None: # Don't overwrite previous errors
                result['error'] = "OCR failed"
        else:
            result['extracted_text'] = extracted_text

    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"

    # Record processing time
    result['processing_time'] = time.time() - start_time
    return result

def save_result(result, output_dir):
    """Save extraction result to a JSON file."""
    # Create a filename based on the original file path
    input_path = Path(result['file_path'])
    relative_path = input_path.with_suffix('.json').name
    output_path = Path(output_dir) / relative_path
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

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