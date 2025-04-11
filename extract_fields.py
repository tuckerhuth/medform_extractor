#!/usr/bin/env python3
import argparse
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

from src.classification import classify_document, load_spacy_model

def process_text_file(file_path):
    """Process a single JSON file containing extracted text."""
    print(f"Processing: {file_path}")
    start_time = time.time()

    # Create output structure
    result = {
        'source_file': str(file_path),
        'classification': None,
        'confidence': None,
        'metadata': {},
        'extraction_timestamp': datetime.now().isoformat(),
        'error': None,
        'processing_time': None
    }

    try:
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            text_data = json.load(f)

        # Skip if no text was extracted
        if not text_data.get('extracted_text'):
            result['error'] = "No extracted text available"
            return result

        # Ensure spaCy model is loaded
        load_spacy_model()

        # Classify document and extract fields
        classification_result = classify_document(text_data['extracted_text'])
        
        # Update result with classification data
        result['classification'] = classification_result.get('classification')
        result['confidence'] = classification_result.get('confidence')
        result['metadata'] = classification_result.get('metadata', {})

    except json.JSONDecodeError as e:
        result['error'] = f"Failed to read JSON file: {str(e)}"
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"

    # Record processing time
    result['processing_time'] = time.time() - start_time
    return result

def save_result(result, output_dir):
    """Save field extraction result to a JSON file."""
    # Create output filename based on input filename
    input_path = Path(result['source_file'])
    output_filename = input_path.stem + '_fields.json'
    output_path = Path(output_dir) / output_filename
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description='Extract fields from text files.')
    parser.add_argument('input_dir', help='Directory containing JSON files with extracted text')
    parser.add_argument('-o', '--output-dir', default='extracted_fields',
                      help='Directory to save field extraction results (default: extracted_fields)')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.is_dir():
        print(f"Error: Input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON files in input directory (including subdirectories)
    json_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(Path(root) / file)

    if not json_files:
        print("No JSON files found.")
        sys.exit(0)

    print(f"Found {len(json_files)} JSON file(s) to process.")

    # Process each file
    processed_files = 0
    for file_path in json_files:
        try:
            # Process the file and get result
            result = process_text_file(file_path)
            
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