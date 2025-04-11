import re
import os
import json
import argparse
import sys
import glob
from collections import defaultdict
import traceback # For detailed error logging

# --- Constants ---
# Construct path relative to this script's location
DEFAULT_CRITERIA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'disease_keywords', 'tuberculosis.md'))

# --- Markdown Parsing Logic ---

def parse_confidence(item_str):
    """Extracts keyword/pattern and confidence level. Returns (item, confidence)."""
    # Regex: optional quotes/space, capture item (non-greedy), optional space, <digits%>, optional space
    match = re.match(r'^['"\s]*(.*?)['"\s]*<(\d+)%>', item_str.strip()) # Removed trailing $ for flexibility, fixed % escape
    if match:
        return match.group(1).strip(), int(match.group(2)) / 100.0
    else:
        # Default confidence 100% if pattern <...%> is not found
        return item_str.strip(''" '), 1.0

def parse_md_section(md_content, variable_name):
    """
    Parses a Python dictionary definition (like keyword lists) from a markdown code block.
    Returns a dictionary structured like:
    { "Category": [(item1, conf1), (item2, conf2), ...], ... }
    """
    data_dict = defaultdict(list)
    # Regex: variable_name = { content }
    pattern_str = r'^\s*' + re.escape(variable_name) + r'\s*=\s*{(.*?)^\s*}'
    pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE)
    match = pattern.search(md_content)

    if not match:
        print(f"Warning: Could not find definition block for '{variable_name}' in markdown.")
        return dict(data_dict)

    dict_content = match.group(1).strip()
    # Regex: "Category Name": [ list_content ]
    category_pattern = re.compile(r'^\s*['"]([\w\s]+)['"]\s*:\s*\[(.*?)\]', re.DOTALL | re.MULTILINE)

    for cat_match in category_pattern.finditer(dict_content):
        category = cat_match.group(1).strip()
        items_str = cat_match.group(2).strip()
        # Split items by comma, ONLY if the comma is followed by optional whitespace and then a quote
        raw_items = re.split(r',(?=\s*['"])', items_str)
        for item_raw in raw_items:
            item_clean = item_raw.strip()
            if item_clean:
                item, confidence = parse_confidence(item_clean)
                if item and item != '''' and item != '""':
                    data_dict[category].append((item, confidence))
    return dict(data_dict)

def load_criteria_from_md(md_file_path):
    """Loads all criteria (keywords and patterns) from the markdown file."""
    criteria = {
        "Skin Test": {"Keywords": {}, "Patterns": {}},
        "Blood Test": {"Keywords": {}, "Patterns": {}},
        "X-Ray": {"Keywords": {}, "Patterns": {}}
    }
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        sections = {
            "Skin Test": {"Keywords": "skin_test_keywords", "Patterns": "skin_test_patterns"},
            "Blood Test": {"Keywords": "blood_test_keywords", "Patterns": "blood_test_patterns"},
            "X-Ray": {"Keywords": "xray_keywords", "Patterns": "xray_patterns"}
        }

        for test_type, vars in sections.items():
            for criteria_type, var_name in vars.items():
                 criteria[test_type][criteria_type] = parse_md_section(md_content, var_name)

    except FileNotFoundError:
        print(f"ERROR: Criteria file not found at {md_file_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR parsing criteria file {md_file_path}: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr) # Print detailed traceback for parsing errors
        return None

    return criteria

# --- Matching Logic ---

def find_matches(text, criteria):
    """
    Finds keyword and pattern matches in the text based on the loaded criteria.
    Returns structured dictionary of matches.
    """
    matches = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    if not text or not criteria:
        return {}

    text_lower = text.lower()

    for test_type, test_criteria in criteria.items():
        # Match Keywords (case-insensitive)
        for category, items in test_criteria.get("Keywords", {}).items():
            for keyword, confidence in items:
                keyword_pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"
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
                    print(f"WARNING: Regex error compiling/matching keyword '{keyword}': {e}")

        # Match Patterns (case-insensitive, applied to original text)
        for category, items in test_criteria.get("Patterns", {}).items():
            for pattern_str, confidence in items:
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    for match in pattern.finditer(text):
                        matches[test_type][category]["Pattern"].append({
                            "pattern": pattern_str,
                            "match": match.group(0),
                            "confidence": confidence,
                            "start": match.start(),
                            "end": match.end()
                        })
                except re.error as e:
                    print(f"WARNING: Regex error compiling/matching pattern '{pattern_str}': {e}")
                except Exception as e:
                     print(f"WARNING: Unexpected error matching pattern '{pattern_str}': {e}")

    # Convert defaultdicts back to regular dicts
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract fields from text files based on markdown criteria.')
    parser.add_argument('input_dir', help='Directory containing the input text or JSON files (from OCR).')
    parser.add_argument('output_dir', help='Directory where the output JSON files with extracted fields will be saved.')
    parser.add_argument('--criteria', default=DEFAULT_CRITERIA_FILE, help=f'Path to the markdown file containing the criteria. Default: {DEFAULT_CRITERIA_FILE}')

    args = parser.parse_args()

    # --- Input Validation ---
    if not os.path.isdir(args.input_dir):
        print(f"ERROR: Input directory not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.output_dir):
        print(f"INFO: Output directory not found: {args.output_dir}. Creating it.")
        try:
             os.makedirs(args.output_dir, exist_ok=True)
        except OSError as e:
             print(f"ERROR: Could not create output directory {args.output_dir}: {e}", file=sys.stderr)
             sys.exit(1)
    if not os.path.isfile(args.criteria):
         print(f"ERROR: Criteria file not found: {args.criteria}", file=sys.stderr)
         sys.exit(1)

    # --- Load Criteria ---
    print(f"Loading criteria from: {args.criteria}")
    criteria_data = load_criteria_from_md(args.criteria)
    if criteria_data is None:
        print("FATAL: Failed to load criteria. Exiting.", file=sys.stderr)
        sys.exit(1)
    print("Criteria loaded successfully.")

    # --- Process Files ---
    print(f"Processing files from input directory: {args.input_dir}")
    print(f"Saving results to output directory: {args.output_dir}")

    input_files = glob.glob(os.path.join(args.input_dir, '*.txt')) + \
                  glob.glob(os.path.join(args.input_dir, '*.json'))

    if not input_files:
        print(f"WARNING: No .txt or .json files found in {args.input_dir}")
        sys.exit(0)

    print(f"Found {len(input_files)} files to process.")
    processed_count = 0

    for file_path in input_files:
        process_file(file_path, criteria_data, args.output_dir)
        processed_count += 1

    print(f"\nField extraction complete. Attempted processing for {processed_count} files.") 