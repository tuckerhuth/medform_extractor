import re
import os
import json
import argparse
import sys
import glob
from collections import defaultdict
import traceback # For detailed error logging
from typing import Dict, List, Any, Union
from pathlib import Path
import yaml # Add YAML import

# --- Constants ---

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # print(f"DEBUG: Running from PyInstaller bundle, _MEIPASS={base_path}")
    except Exception:
        # Not running in a bundle, use relative path from script
        # Go up one level from src to the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        # print(f"DEBUG: Running from script, base_path={base_path}")

    resource_path = os.path.join(base_path, relative_path)
    # print(f"DEBUG: Resource path for '{relative_path}' resolved to '{resource_path}'")
    return resource_path

# Use the helper function to define the path
# DEFAULT_CRITERIA_FILE = get_resource_path(os.path.join('disease_keywords', 'tuberculosis.yaml'))
# We will now get the criteria file path from the command-line argument

# --- YAML Loading Logic --- 

def load_criteria_from_yaml(yaml_file_path):
    """Loads criteria from the specified YAML file."""
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            criteria = yaml.safe_load(f)
        if not isinstance(criteria, dict): # Basic validation
             print(f"ERROR: YAML file {yaml_file_path} did not load as a dictionary.", file=sys.stderr)
             return None
        # Add more specific validation if the expected structure is known
        # Example: Check for top-level keys like 'Skin Test', 'Blood Test', 'X-Ray'
        # expected_keys = ["Skin Test", "Blood Test", "X-Ray"]
        # if not all(key in criteria for key in expected_keys):
        #     print(f"ERROR: YAML file {yaml_file_path} is missing expected top-level keys.", file=sys.stderr)
        #     return None
        return criteria
    except FileNotFoundError:
        print(f"ERROR: Criteria YAML file not found at {yaml_file_path}", file=sys.stderr)
        return None
    except yaml.YAMLError as e:
        print(f"ERROR parsing criteria YAML file {yaml_file_path}: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR loading criteria YAML file {yaml_file_path}: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return None

# --- Matching Logic (should work with dict loaded from YAML) ---

def find_matches(text, criteria):
    """
    Finds keyword and pattern matches in the text based on the loaded criteria.
    Returns structured dictionary of matches.
    (Assumes criteria is a dictionary structured appropriately, e.g., loaded from YAML)
    """
    matches = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    if not text or not criteria or not isinstance(criteria, dict):
        return {}

    text_lower = text.lower()

    # Example structure expected from YAML:
    # criteria = {
    #   'TestType1': {
    #     'Category1': {
    #       'Keywords': [{'term': 'kw1', 'confidence': 0.9}, ...],
    #       'Patterns': [{'pattern': 'regex1', 'confidence': 0.8}, ...]
    #     }, ...
    #   }, ...
    # }

    for test_type, test_categories in criteria.items():
        if not isinstance(test_categories, dict):
            print(f"WARNING: Skipping test type '{test_type}' as its value is not a dictionary.", file=sys.stderr)
            continue
            
        for category, match_types in test_categories.items():
            if not isinstance(match_types, dict):
                print(f"WARNING: Skipping category '{category}' under '{test_type}' as its value is not a dictionary.", file=sys.stderr)
                continue

            # Match Keywords (case-insensitive)
            keyword_list = match_types.get("Keywords", [])
            if isinstance(keyword_list, list):
                for item in keyword_list:
                    if isinstance(item, dict) and 'term' in item:
                        keyword = item['term']
                        confidence = item.get('confidence', 1.0)
                        keyword_pattern = r"(?<!\w)" + re.escape(str(keyword).lower()) + r"(?!\w)"
                        try:
                            for match in re.finditer(keyword_pattern, text_lower):
                                matches[test_type][category]["Keyword"].append({
                                    "term": keyword,
                                    "match": match.group(0),
                                    "confidence": confidence,
                                    "start": match.start(),
                                    "end": match.end()
                                })
                        except re.error as e:
                            print(f"WARNING: Regex error compiling/matching keyword '{keyword}': {e}", file=sys.stderr)
                    else:
                         print(f"WARNING: Skipping invalid keyword item under '{test_type}/{category}': {item}", file=sys.stderr)
            elif keyword_list: # If it exists but isn't a list
                 print(f"WARNING: 'Keywords' under '{test_type}/{category}' is not a list, skipping.", file=sys.stderr)

            # Match Patterns (case-insensitive, applied to original text)
            pattern_list = match_types.get("Patterns", [])
            if isinstance(pattern_list, list):
                for item in pattern_list:
                    if isinstance(item, dict) and 'pattern' in item:
                        pattern_str = item['pattern']
                        confidence = item.get('confidence', 1.0)
                        try:
                            pattern = re.compile(str(pattern_str), re.IGNORECASE)
                            for match in pattern.finditer(text):
                                matches[test_type][category]["Pattern"].append({
                                    "pattern": pattern_str,
                                    "match": match.group(0),
                                    "confidence": confidence,
                                    "start": match.start(),
                                    "end": match.end()
                                })
                        except re.error as e:
                            print(f"WARNING: Regex error compiling/matching pattern '{pattern_str}': {e}", file=sys.stderr)
                        except Exception as e:
                             print(f"WARNING: Unexpected error matching pattern '{pattern_str}': {e}", file=sys.stderr)
                    else:
                        print(f"WARNING: Skipping invalid pattern item under '{test_type}/{category}': {item}", file=sys.stderr)
            elif pattern_list:
                print(f"WARNING: 'Patterns' under '{test_type}/{category}' is not a list, skipping.", file=sys.stderr)

    # Convert defaultdicts back to regular dicts for cleaner JSON output
    final_matches = {}
    for test_type, categories in matches.items():
        final_matches[test_type] = {}
        for category, match_types in categories.items():
            final_matches[test_type][category] = dict(match_types)

    return final_matches

# --- Main Script Execution Logic ---

def process_file(text_file_path, criteria, output_dir):
    """Processes a single text file (or JSON containing text), finds matches, and saves the result."""
    base_name = os.path.basename(text_file_path)
    name_part = os.path.splitext(base_name)[0]
    output_filename = f"{name_part}_extracted.json"
    output_path = os.path.join(output_dir, output_filename)

    result = {
        "source_text_file": base_name,
        "matches": {},
        "error": None
    }

    try:
        text_content = None
        if text_file_path.lower().endswith('.json'):
            with open(text_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                possible_keys = ['extracted_text', 'text', 'content']
                for key in possible_keys:
                    if key in data and isinstance(data[key], str):
                         text_content = data[key]
                         break
                if text_content is None:
                    if isinstance(data, str):
                        text_content = data
                    else:
                        result["error"] = f"JSON file {base_name} lacks a recognized text key."
                        print(f"ERROR: {result['error']}") # Log error before saving
        elif text_file_path.lower().endswith('.txt'):
             with open(text_file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        else:
            print(f"INFO: Skipping unsupported file type: {base_name}")
            return # Don't process or save anything for this file

        # Perform matching only if text was found and no prior error
        if text_content and result["error"] is None:
            result["matches"] = find_matches(text_content, criteria)
        elif result["error"] is None:
             result["error"] = "No text content found or extracted from file."
             print(f"ERROR: {result['error']} for file {base_name}") # Log error

    except FileNotFoundError:
         result["error"] = "Input file not found"
         print(f"ERROR: {result['error']}: {text_file_path}")
    except json.JSONDecodeError as e:
         result["error"] = f"JSON Decode Error: {e}"
         print(f"ERROR decoding JSON from {base_name}: {e}")
    except Exception as e:
        result["error"] = f"Processing Error: {e}"
        print(f"ERROR processing file {base_name}: {e}")
        print(traceback.format_exc()) # Log detailed traceback

    # Save the result dictionary as JSON, including any errors
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        status = "(with error)" if result["error"] else ""
        print(f"Saved result {status} for {base_name} to {output_filename}")

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to save results for {base_name} to {output_path}: {e}")
        print(traceback.format_exc())

def process_text_with_patterns(text: str, patterns: Dict[str, List[Dict[str, Union[str, float]]]], confidence_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """
    Process text with the given patterns and return matches.
    
    Args:
        text: The text to process
        patterns: Dictionary containing keywords and regex patterns with confidence scores
        confidence_threshold: Minimum confidence score for matches (0.0 to 1.0)
        
    Returns:
        List of matches, each containing the matched text, position, and confidence score
    """
    matches = []
    
    # Process keywords
    for keyword in patterns.get('keywords', []):
        if keyword['confidence'] < confidence_threshold:
            continue
            
        string = keyword['string']
        confidence = keyword['confidence']
        
        # Find all non-overlapping matches
        start = 0
        while True:
            pos = text.find(string, start)
            if pos == -1:
                break
                
            matches.append({
                'text': string,
                'start': pos,
                'end': pos + len(string),
                'confidence': confidence,
                'type': 'keyword'
            })
            start = pos + len(string)
    
    # Process regex patterns
    for pattern in patterns.get('regex_patterns', []):
        if pattern['confidence'] < confidence_threshold:
            continue
            
        string = pattern['string']
        confidence = pattern['confidence']
        
        # Find all non-overlapping matches
        for match in re.finditer(string, text):
            matches.append({
                'text': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'confidence': confidence,
                'type': 'regex'
            })
    
    # Sort matches by position and handle overlaps
    matches.sort(key=lambda x: (x['start'], -x['confidence']))
    non_overlapping = []
    last_end = -1
    
    for match in matches:
        if match['start'] >= last_end:
            non_overlapping.append(match)
            last_end = match['end']
    
    return non_overlapping

def main():
    print("DEBUG: process_ocr.py main() started.", file=sys.stderr) # Add debug print
    parser = argparse.ArgumentParser(description="Extract fields from text files based on YAML criteria.")
    parser.add_argument("input_dir", help="Directory containing input text or JSON files.")
    parser.add_argument("output_dir", help="Directory to save the extracted field JSON files.")
    parser.add_argument("--keywords-file", required=True, help="Path to the YAML criteria file.")

    args = parser.parse_args()

    try: # Add broad exception handling
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        # Load criteria from YAML file using the correct argument name
        print(f"Loading criteria from: {args.keywords_file}")
        criteria = load_criteria_from_yaml(args.keywords_file)
        if criteria is None:
            print("ERROR: Failed to load criteria. Exiting.", file=sys.stderr)
            sys.exit(1) # Exit if criteria loading fails

        # Find all processable files (.txt, .json)
        processable_files = []
        extensions = ('*.txt', '*.json')
        for ext in extensions:
             # Use Path.glob for better path handling
             search_path = Path(args.input_dir) / ext
             processable_files.extend(search_path.glob('*'))

        total_files = len(processable_files)
        print(f"Found {total_files} processable files in {args.input_dir}")

        # Process each file
        for i, file_path in enumerate(processable_files):
            print(f"PROGRESS:{i+1}/{total_files}") # Progress indicator for GUI
            print(f"Processing file: {file_path.name}")
            # Pass the Path object directly
            process_file(str(file_path), criteria, args.output_dir)

        print("Processing complete.")
        
    except Exception as e:
        print(f"FATAL ERROR in process_ocr.py main: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(3) # Exit with a different code to indicate unexpected error

if __name__ == "__main__":
    main() 