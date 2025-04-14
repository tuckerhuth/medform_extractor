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
import logging # Add logging import
from datetime import datetime # ADDED for timestamp

# --- VERY EARLY DIAGNOSTICS --- 
# Wrap in try..except just in case print itself fails somehow
try:
    print(f"DEBUG PROCESS_OCR: Script invoked. sys.argv: {sys.argv}", file=sys.stderr)
    # 1. Print Current Working Directory
    try:
        current_cwd = os.getcwd()
        print(f"DEBUG PROCESS_OCR: Current CWD: {current_cwd}", file=sys.stderr)
    except Exception as e:
        print(f"FATAL PROCESS_OCR: Failed to get CWD: {e}", file=sys.stderr)
        current_cwd = "<Error getting CWD>"
    
    # 2. Attempt Manual Log File Creation/Write
    manual_log_path = Path(current_cwd) / "process_ocr_cwd.log" # Use CWD explicitly
    print(f"DEBUG PROCESS_OCR: Attempting manual write to: {manual_log_path}", file=sys.stderr)
    try:
        with open(manual_log_path, 'a', encoding='utf-8') as f_test:
            f_test.write(f"{datetime.now().isoformat()} - Manual log test successful.\n")
        print(f"DEBUG PROCESS_OCR: Manual write to {manual_log_path} SUCCEEDED.", file=sys.stderr)
    except Exception as e:
        print(f"FATAL PROCESS_OCR: Manual write to {manual_log_path} FAILED: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        # Continue to attempt logging setup anyway, but it will likely fail
except Exception as early_e:
     print(f"FATAL PROCESS_OCR: Error during very early diagnostics: {early_e}", file=sys.stderr)
     print(traceback.format_exc(), file=sys.stderr)

# --- Setup Logging --- 
# Use the path determined above for consistency
log_file_path = manual_log_path 
print(f"DEBUG PROCESS_OCR: Proceeding to setup logging for: {log_file_path}", file=sys.stderr)
try:
    logging.basicConfig(filename=log_file_path, 
                        level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        filemode='a')
    logging.debug("--- process_ocr.py logging configured successfully ---")
    logging.error("--- process_ocr.py started ---") # Use ERROR level for start marker
    print(f"DEBUG PROCESS_OCR: Logging configured via basicConfig.", file=sys.stderr)
except Exception as log_setup_err:
    print(f"FATAL PROCESS_OCR: basicConfig failed for {log_file_path}: {log_setup_err}\n{traceback.format_exc()}", file=sys.stderr)

print("DEBUG PROCESS_OCR: Script proceeding after logging setup attempt.", file=sys.stderr)

# --- Constants ---

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        logging.debug(f"Running from PyInstaller bundle, _MEIPASS={base_path}")
    except Exception:
        # Not running in a bundle, use relative path from script
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        logging.debug(f"Running from script, base_path={base_path}")

    resource_path = os.path.join(base_path, relative_path)
    logging.debug(f"Resource path for '{relative_path}' resolved to '{resource_path}'")
    return resource_path

def ensure_criteria_file(yaml_file_path):
    """Ensures the criteria file exists, copying from resources if needed."""
    if os.path.exists(yaml_file_path):
        logging.debug(f"Criteria file found at {yaml_file_path}")
        return yaml_file_path

    # If the file doesn't exist at the specified path, try to copy from resources
    default_path = get_resource_path(os.path.join('disease_keywords', 'tuberculosis.yaml'))
    if os.path.exists(default_path):
        logging.debug(f"Found default criteria file at {default_path}")
        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(yaml_file_path), exist_ok=True)
            # Copy the file
            import shutil
            shutil.copy2(default_path, yaml_file_path)
            logging.info(f"Copied criteria file from {default_path} to {yaml_file_path}")
            return yaml_file_path
        except Exception as e:
            logging.error(f"Failed to copy criteria file: {e}")
            return default_path
    else:
        logging.error(f"Could not find criteria file at {yaml_file_path} or {default_path}")
        return None

def load_criteria_from_yaml(yaml_file_path):
    """Loads criteria from the specified YAML file."""
    try:
        # First ensure the file exists
        yaml_file_path = ensure_criteria_file(yaml_file_path)
        if not yaml_file_path:
            return None

        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            criteria = yaml.safe_load(f)
        
        if not isinstance(criteria, dict):
            logging.error(f"YAML file {yaml_file_path} did not load as a dictionary.")
            return None

        # Validate the expected structure
        if 'metadata' not in criteria:
            logging.warning(f"YAML file {yaml_file_path} is missing metadata section.")
        if 'tuberculosis' not in criteria:
            logging.error(f"YAML file {yaml_file_path} is missing tuberculosis section.")
            return None

        logging.info(f"Successfully loaded criteria from {yaml_file_path}")
        return criteria

    except FileNotFoundError:
        logging.error(f"Criteria YAML file not found at {yaml_file_path}")
        return None
    except yaml.YAMLError as e:
        logging.error(f"Error parsing criteria YAML file {yaml_file_path}: {e}")
        logging.debug(traceback.format_exc())
        return None
    except Exception as e:
        logging.error(f"Error loading criteria YAML file {yaml_file_path}: {e}")
        logging.debug(traceback.format_exc())
        return None

# --- Matching Logic (should work with dict loaded from YAML) ---

def find_matches(text, criteria):
    """
    Finds keyword and pattern matches in the text based on the loaded criteria.
    Returns structured dictionary of matches.
    """
    logging.debug(f"\n{'='*80}\nStarting find_matches\n{'='*80}")
    logging.debug(f"Text length: {len(text) if text else 0}")
    logging.debug(f"First 200 chars of text: {text[:200] if text else 'None'}")
    logging.debug(f"Text content for matching:\n{text}")  # Add full text logging

    try:
        criteria_preview = json.dumps(criteria, indent=2, default=str)
        logging.debug(f"Criteria structure received:\n{criteria_preview}")
    except Exception as json_e:
        logging.error(f"Could not serialize criteria for logging: {json_e}")

    matches = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    if not text or not criteria or not isinstance(criteria, dict):
        logging.warning("find_matches returning empty: Text or criteria is missing or invalid.")
        return {}

    any_match_found_overall = False
    text_lower = text.lower()
    logging.debug("Converted text to lowercase for keyword search.")
    logging.debug(f"Lowercase text:\n{text_lower}")  # Add lowercase text logging

    # Skip the metadata section if present
    if "metadata" in criteria:
        del criteria["metadata"]
        logging.debug("Removed metadata section from criteria")

    for condition, test_methods in criteria.items():
        logging.debug(f"\nProcessing Condition: {condition}")
        if not isinstance(test_methods, dict):
            logging.warning(f"Skipping condition '{condition}' as its value is not a dictionary.")
            continue

        for test_method, detection_aspects in test_methods.items():
            logging.debug(f"\n  Processing Test Method: {condition}/{test_method}")
            if not isinstance(detection_aspects, dict):
                logging.warning(f"Skipping test method '{test_method}' as its value is not a dictionary.")
                continue

            for aspect, pattern_types in detection_aspects.items():
                logging.debug(f"\n    Processing Aspect: {condition}/{test_method}/{aspect}")
                if not isinstance(pattern_types, dict):
                    logging.warning(f"Skipping aspect '{aspect}' as its value is not a dictionary.")
                    continue

                # Match Keywords (case-insensitive)
                keyword_list = pattern_types.get("keywords", [])
                logging.debug(f"\n      Found {len(keyword_list) if isinstance(keyword_list, list) else 'N/A'} keyword entries")
                if isinstance(keyword_list, list):
                    for item_idx, item in enumerate(keyword_list):
                        if isinstance(item, dict) and 'string' in item:
                            keyword = item['string']
                            confidence = item.get('confidence', 1.0)
                            keyword_pattern = r"(?<!\w)" + re.escape(str(keyword).lower()) + r"(?!\w)"
                            logging.debug(f"        [Keyword {item_idx+1}] Checking: '{keyword}'")
                            logging.debug(f"        Pattern: {keyword_pattern}")
                            try:
                                match_iterator = list(re.finditer(keyword_pattern, text_lower))
                                if match_iterator:
                                    logging.info(f"        FOUND {len(match_iterator)} match(es) for keyword '{keyword}'")
                                    any_match_found_overall = True
                                    for match in match_iterator:
                                        match_text = text[match.start():match.end()]
                                        context_start = max(0, match.start() - 50)
                                        context_end = min(len(text), match.end() + 50)
                                        context = text[context_start:context_end]
                                        logging.debug(f"          Match: '{match_text}' at positions {match.start()}-{match.end()}")
                                        logging.debug(f"          Context: '...{context}...'")
                                        matches[condition][test_method][aspect]["keywords"].append({
                                            "term": keyword,
                                            "match": match_text,
                                            "confidence": confidence,
                                            "start": match.start(),
                                            "end": match.end()
                                        })
                                else:
                                    logging.debug(f"        No matches for keyword '{keyword}'")
                            except re.error as e:
                                logging.error(f"        Regex error for keyword '{keyword}': {e}")

                # Match Regex Patterns (case-insensitive)
                pattern_list = pattern_types.get("regex_patterns", [])
                logging.debug(f"\n      Found {len(pattern_list) if isinstance(pattern_list, list) else 'N/A'} pattern entries")
                if isinstance(pattern_list, list):
                    for item_idx, item in enumerate(pattern_list):
                        if isinstance(item, dict) and 'string' in item:
                            pattern_str = item['string']
                            confidence = item.get('confidence', 1.0)
                            logging.debug(f"        [Pattern {item_idx+1}] Checking regex: '{pattern_str}'")
                            try:
                                pattern = re.compile(str(pattern_str), re.IGNORECASE)
                                match_iterator = list(pattern.finditer(text))
                                if match_iterator:
                                    logging.info(f"        FOUND {len(match_iterator)} match(es) for pattern '{pattern_str}'")
                                    any_match_found_overall = True
                                    for match in match_iterator:
                                        match_text = text[match.start():match.end()]
                                        logging.debug(f"          Match: '{match_text}' at positions {match.start()}-{match.end()}")
                                        matches[condition][test_method][aspect]["regex_patterns"].append({
                                            "pattern": pattern_str,
                                            "match": match_text,
                                            "confidence": confidence,
                                            "start": match.start(),
                                            "end": match.end()
                                        })
                                else:
                                    logging.debug(f"        No matches for pattern '{pattern_str}'")
                            except re.error as e:
                                logging.error(f"        Regex error for pattern '{pattern_str}': {e}")

    if not any_match_found_overall:
        logging.info("\nfind_matches completed. NO MATCHES FOUND overall for any criteria.")
    else:
        logging.info("\nfind_matches completed. At least one match found overall.")

    # Convert defaultdicts to regular dicts
    final_matches = {}
    for condition, test_methods in matches.items():
        final_matches[condition] = {}
        for test_method, aspects in test_methods.items():
            final_matches[condition][test_method] = {}
            for aspect, pattern_types in aspects.items():
                final_matches[condition][test_method][aspect] = dict(pattern_types)

    try:
        matches_preview = json.dumps(final_matches, indent=2, default=str)
        if len(matches_preview) > 5000:
            matches_preview = matches_preview[:5000] + "... [truncated]"
        logging.debug(f"\nFinal matches structure:\n{matches_preview}")
    except Exception as e:
        logging.error(f"Error serializing matches preview: {e}")

    logging.debug(f"\n{'='*80}\nEnd find_matches\n{'='*80}\n")
    return final_matches

# --- Main Script Execution Logic ---

def process_file(text_file_path, criteria, output_dir):
    """Processes a single text file (or JSON containing text), finds matches, and saves the result."""
    logging.debug(f"Starting process_file for: {text_file_path}")
    
    input_path = Path(text_file_path) # Convert to Path object early
    output_filename = f"{input_path.stem}_extracted.json"
    output_path = Path(output_dir) / output_filename # Use Path object
    logging.debug(f"Determined output path: {output_path}")

    # Initialize the final result structure
    result = {
        "file_path": str(input_path), # Use full path string
        "error": None,
        "extraction_timestamp": datetime.now().isoformat() # Add timestamp
        # Test method keys will be added below
    }

    try:
        text_content = None
        logging.debug(f"Checking file type for {input_path}")
        # Use Path object attributes for checking suffix
        if input_path.suffix.lower() == '.json': 
            logging.debug(f"Reading JSON file: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                possible_keys = ['extracted_text', 'text', 'content']
                logging.debug(f"Searching for text keys {possible_keys} in JSON data.")
                for key in possible_keys:
                    if key in data and isinstance(data[key], str):
                        text_content = data[key]
                        logging.debug(f"Found text content under key '{key}'. Length: {len(text_content)}")
                        break
                if text_content is None:
                    if isinstance(data, str):
                        text_content = data
                        logging.debug("JSON data itself is a string. Using it as text content.")
                    else:
                        result["error"] = f"JSON file {input_path.name} lacks a recognized text key."
                        logging.error(result["error"]) # Log error
        elif input_path.suffix.lower() == '.txt': 
            logging.debug(f"Reading TXT file: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
                logging.debug(f"Read {len(text_content)} characters from TXT file.")
        else:
            logging.warning(f"Skipping unsupported file type: {input_path.name}")
            return 

        # --- Perform matching and structure the output --- 
        matches_result = {} # Default to empty if no text or error
        if text_content and result["error"] is None:
            logging.debug(f"Calling find_matches for {input_path.name}")
            matches_result = find_matches(text_content, criteria)
            logging.info(f"Matching complete for {input_path.name}.")
        elif result["error"] is None:
            result["error"] = "No text content found or extracted from file."
            logging.error(f"{result['error']} for file {input_path.name}")
        
        # --- Populate results for each test method defined in criteria --- 
        logging.debug("Populating final result structure for each test method.")
        
        # Iterate through conditions and their test methods
        for condition, test_methods in criteria.items():
            if condition == "metadata":
                continue
                
            if isinstance(test_methods, dict):
                for test_method, aspects in test_methods.items():
                    # Create a result key combining condition and test method
                    result_key = f"{condition}_{test_method}"
                    num_indicators = 0
                    max_confidence = 0.0
                    
                    # Check matches found for this test method
                    condition_matches = matches_result.get(condition, {})
                    method_matches = condition_matches.get(test_method, {})
                    
                    if isinstance(method_matches, dict):
                        for aspect, match_groups in method_matches.items():
                            if isinstance(match_groups, dict):
                                for match_kind, match_list in match_groups.items(): # Keywords, Patterns
                                    if isinstance(match_list, list):
                                        num_indicators += len(match_list)
                                        for match in match_list:
                                            if isinstance(match, dict):
                                                max_confidence = max(max_confidence, match.get('confidence', 0.0))
                    
                    is_administered = num_indicators > 0
                    
                    # Add the test method result to the main result dictionary
                    result[result_key] = {
                        "Administered": is_administered,
                        "Confidence": max_confidence,
                        "Number of indicators": num_indicators
                    }
                    logging.debug(f"Added/Updated result for {result_key}: {result[result_key]}")

    except FileNotFoundError:
        result["error"] = "Input file not found"
        logging.error(f"{result['error']}: {input_path}")
        # Ensure default test method structures are added
        for condition, test_methods in criteria.items():
            if condition != "metadata" and isinstance(test_methods, dict):
                for test_method in test_methods:
                    result_key = f"{condition}_{test_method}"
                    if result_key not in result:
                        result[result_key] = {"Administered": False, "Confidence": 0.0, "Number of indicators": 0}

    except json.JSONDecodeError as e:
        result["error"] = f"JSON Decode Error: {e}"
        logging.error(f"Error decoding JSON from {input_path.name}: {e}\n{traceback.format_exc()}")
        # Ensure default test method structures are added
        for condition, test_methods in criteria.items():
            if condition != "metadata" and isinstance(test_methods, dict):
                for test_method in test_methods:
                    result_key = f"{condition}_{test_method}"
                    if result_key not in result:
                        result[result_key] = {"Administered": False, "Confidence": 0.0, "Number of indicators": 0}
                 
    except Exception as e:
        result["error"] = f"Processing Error: {e}"
        logging.error(f"Error processing file {input_path.name}: {e}\n{traceback.format_exc()}")
        # Ensure default test method structures are added
        for condition, test_methods in criteria.items():
            if condition != "metadata" and isinstance(test_methods, dict):
                for test_method in test_methods:
                    result_key = f"{condition}_{test_method}"
                    if result_key not in result:
                        result[result_key] = {"Administered": False, "Confidence": 0.0, "Number of indicators": 0}

    # --- Save the result dictionary as JSON ---
    output_path_obj = Path(output_dir) / output_filename 
    absolute_output_path = output_path_obj.resolve()
    logging.debug(f"Attempting to save final structured results for {input_path.name} to ABSOLUTE path: {absolute_output_path}")
    
    try:
        absolute_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.debug(f"Executing open() for: {absolute_output_path}")
        with open(absolute_output_path, 'w', encoding='utf-8') as f:
            logging.debug(f"File opened. Executing json.dump() for: {input_path.name}")
            json.dump(result, f, indent=4)
            logging.debug(f"json.dump() completed for: {input_path.name}")
            
        status = "(with error)" if result["error"] else ""
        logging.info(f"Successfully completed save block for {input_path.name} to {output_filename} {status}")

    except Exception as e:
        logging.critical(f"CRITICAL ERROR during final save block for {input_path.name} to {absolute_output_path}: {e}\n{traceback.format_exc()}")

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
    print("DEBUG: process_ocr.py main() started.", file=sys.stderr)
    parser = argparse.ArgumentParser(description="Extract fields from text files based on YAML criteria.")
    parser.add_argument("input_dir", help="Directory containing input text or JSON files.")
    parser.add_argument("output_dir", help="Directory to save the extracted field JSON files.")
    parser.add_argument("--keywords-file", required=True, help="Path to the YAML criteria file.")

    args = parser.parse_args()

    try:
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        # Load criteria from YAML file
        logging.info(f"Loading criteria from: {args.keywords_file}")
        criteria = load_criteria_from_yaml(args.keywords_file)
        if criteria is None:
            logging.error("Failed to load criteria. Exiting.")
            sys.exit(1)

        # Find all processable files (.txt, .json)
        input_dir = Path(args.input_dir)
        processable_files = []
        processable_files.extend(input_dir.glob("*.txt"))  # Find all .txt files
        processable_files.extend(input_dir.glob("*.json")) # Find all .json files
        
        total_files = len(processable_files)
        logging.info(f"Found {total_files} processable files in {args.input_dir}")
        
        if total_files == 0:
            logging.warning(f"No .txt or .json files found in {args.input_dir}")
            return

        # Process each file
        errors = 0
        for i, file_path in enumerate(processable_files, 1):
            logging.info(f"Processing file {i}/{total_files}: {file_path.name}")
            try:
                process_file(str(file_path), criteria, args.output_dir)
            except Exception as e:
                logging.error(f"Error processing {file_path.name}: {e}")
                errors += 1

        logging.info(f"Processing complete. Processed: {total_files}, Errors: {errors}")
        
    except Exception as e:
        logging.critical(f"FATAL ERROR in process_ocr.py main: {e}\n{traceback.format_exc()}")
        sys.exit(3)

if __name__ == "__main__":
    main() 