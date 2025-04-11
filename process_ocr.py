import os
import json
import re
import datetime
import pathlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
INPUT_DIR = "extracted_text"
OUTPUT_DIR = "extracted_fields"
KEYWORDS_FILE = "disease_keywords/tuberculosis.md"
OCR_TEXT_KEY = "extracted_text" # Key used by extract_text.py

# --- Parsing Functions ---

def parse_confidence(item_str):
    """Extracts keyword/pattern and confidence level."""
    confidence = 0.0
    match = re.search(r"<(\d+)%>$", item_str.strip())
    if match:
        confidence = float(match.group(1))
        # Remove confidence part for the actual keyword/pattern
        item_str = re.sub(r"\s*<\d+%>$", "", item_str).strip()
    # Remove potential surrounding quotes if any remain after regex
    item_str = item_str.strip('\'"')
    return item_str, confidence

def parse_md_section(md_content, variable_name):
    """
    Parses a Python dictionary definition (keywords or patterns)
    from a markdown code block.
    Returns a dictionary structured like:
    { "Category": [("item1", confidence1), ("item2", confidence2), ...], ... }
    """
    data_dict = {}
    # Regex to find the python dict definition for the variable
    # Making assumptions about formatting: starts with var_name =, ends with }
    pattern = re.compile(
        rf"^{re.escape(variable_name)}\s*=\s*{{(.*?)}}",
        re.DOTALL | re.MULTILINE
    )
    match = pattern.search(md_content)
    if not match:
        logging.warning(f"Could not find definition for '{variable_name}' in {KEYWORDS_FILE}")
        return data_dict

    dict_content = match.group(1).strip()

    # Regex to find categories and their items
    # Assumes categories are quoted strings followed by : [ ... ]
    category_pattern = re.compile(r"\"(\w+)\"\s*:\s*\[(.*?)\]", re.DOTALL)

    for cat_match in category_pattern.finditer(dict_content):
        category = cat_match.group(1)
        items_str = cat_match.group(2).strip()
        items_list = []

        # Split items, handling potential commas within strings (e.g. in regex)
        # This simple split might fail for complex list content but works for the current format
        raw_items = re.split(r',(?=\s*")', items_str) # Split only on commas followed by quote

        for item_raw in raw_items:
            item_clean = item_raw.strip()
            if item_clean:
                 # Remove potential leading/trailing quotes from the split
                item_clean = item_clean.strip('\'"')
                item, confidence = parse_confidence(item_clean)
                if item: # Ensure we have a non-empty item
                    items_list.append((item, confidence))

        if items_list:
            data_dict[category] = items_list

    return data_dict

# --- Analysis Function ---

def analyze_text(text, keywords_dict, patterns_dict):
    """
    Analyzes text for a specific test type using keywords and patterns.

    Args:
        text (str): The OCR text content.
        keywords_dict (dict): Parsed keywords {Category: [(keyword, confidence), ...]}.
        patterns_dict (dict): Parsed patterns {Category: [(pattern_str, confidence), ...]}.

    Returns:
        dict: {"Administered": bool, "Confidence": float, "Number of indicators": int}
    """
    max_confidence = 0.0
    indicator_count = 0
    administered = False
    text_lower = text.lower() # Search case-insensitively

    # Check keywords
    for category, items in keywords_dict.items():
        for keyword, confidence in items:
            if keyword.lower() in text_lower:
                logging.debug(f"Keyword match: '{keyword}' (Confidence: {confidence})")
                administered = True
                indicator_count += 1
                if confidence > max_confidence:
                    max_confidence = confidence

    # Check patterns
    for category, items in patterns_dict.items():
        for pattern_str, confidence in items:
            try:
                # Add word boundaries if not already present, unless it's a simple pattern
                # This is a heuristic and might need refinement
                processed_pattern = pattern_str
                if not pattern_str.startswith(r'\b') and not pattern_str.endswith(r'\b') and len(pattern_str) > 2:
                     if pattern_str.isalnum(): # Only add for simple alphanumeric patterns
                         processed_pattern = r'\b' + pattern_str + r'\b'

                regex = re.compile(processed_pattern, re.IGNORECASE)
                matches = regex.findall(text) # Find all non-overlapping matches
                if matches:
                    logging.debug(f"Pattern match: '{pattern_str}' found {len(matches)} times (Confidence: {confidence})")
                    administered = True
                    indicator_count += len(matches) # Count each match
                    if confidence > max_confidence:
                        max_confidence = confidence
            except re.error as e:
                logging.warning(f"Invalid regex pattern '{pattern_str}': {e}")
            except Exception as e:
                 logging.error(f"Error processing pattern '{pattern_str}': {e}")


    return {
        "Administered": administered,
        "Confidence": max_confidence / 100.0 if administered else 0.0, # Convert to 0.0-1.0 scale
        "Number of indicators": indicator_count
    }

# --- Main Execution ---

def main():
    logging.info("Starting OCR text processing...")
    start_time = datetime.datetime.now()

    input_path = pathlib.Path(INPUT_DIR)
    output_path = pathlib.Path(OUTPUT_DIR)
    keywords_file_path = pathlib.Path(KEYWORDS_FILE)

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Read keywords and patterns file
    if not keywords_file_path.is_file():
        logging.error(f"Keywords file not found: {KEYWORDS_FILE}")
        return
    try:
        with open(keywords_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        logging.error(f"Error reading keywords file {KEYWORDS_FILE}: {e}")
        return

    # Parse keywords and patterns for each test type
    logging.info("Parsing keywords and patterns...")
    skin_keywords = parse_md_section(md_content, "skin_test_keywords")
    skin_patterns = parse_md_section(md_content, "skin_test_patterns")
    blood_keywords = parse_md_section(md_content, "blood_test_keywords")
    blood_patterns = parse_md_section(md_content, "blood_test_patterns")
    xray_keywords = parse_md_section(md_content, "xray_keywords")
    # Note: xray_patterns are missing in the provided example, so we parse it
    # but expect it might be empty or fail gracefully if not found.
    xray_patterns = parse_md_section(md_content, "xray_patterns")
    if not xray_patterns:
        logging.warning("No 'xray_patterns' found or parsed from the markdown file. X-ray detection will rely only on keywords.")


    logging.info(f"Processing files from: {input_path}")
    processed_files = 0
    error_files = 0

    for json_file in input_path.glob("*.json"):
        logging.info(f"Processing file: {json_file.name}")
        # Generate relative path from workspace root if possible, otherwise use absolute path
        # We will overwrite this later with the path from the JSON content
        try:
            rel_path = str(json_file.relative_to(pathlib.Path.cwd()))
        except ValueError:
            rel_path = str(json_file.resolve())

        output_data = {
            "file_path": rel_path, # Placeholder, will be overwritten
            "error": None,
            "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "skin_test": {"Administered": False, "Confidence": 0.0, "Number of indicators": 0},
            "blood_test": {"Administered": False, "Confidence": 0.0, "Number of indicators": 0},
            "x_ray": {"Administered": False, "Confidence": 0.0, "Number of indicators": 0} # Renamed for consistency
        }

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # --- Get the original image file path from the input JSON --- 
            original_image_path = data.get('file_path')
            if original_image_path:
                output_data["file_path"] = original_image_path # Overwrite with the correct path
            else:
                logging.warning(f"Key 'file_path' not found in {json_file.name}. Output will contain path to JSON.")
                # Keep the placeholder path (path to the json file) if original not found

            # --- Check for OCR text key --- 
            if OCR_TEXT_KEY not in data:
                raise KeyError(f"Expected key '{OCR_TEXT_KEY}' not found in JSON.")

            ocr_text = data[OCR_TEXT_KEY]
            if not isinstance(ocr_text, str) or not ocr_text.strip():
                 logging.warning(f"No valid text found in {json_file.name} under key '{OCR_TEXT_KEY}'. Skipping analysis.")
                 output_data["error"] = f"No valid text found under key '{OCR_TEXT_KEY}'"
            else:
                # Analyze for each test type
                output_data["skin_test"] = analyze_text(ocr_text, skin_keywords, skin_patterns)
                output_data["blood_test"] = analyze_text(ocr_text, blood_keywords, blood_patterns)
                output_data["x_ray"] = analyze_text(ocr_text, xray_keywords, xray_patterns) # Pass potentially empty patterns

            processed_files += 1

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {json_file.name}: {e}")
            output_data["error"] = f"JSON Decode Error: {e}"
            error_files += 1
        except KeyError as e:
             logging.error(f"Data structure error in {json_file.name}: {e}")
             output_data["error"] = f"Data Structure Error: {e}"
             error_files += 1
        except Exception as e:
            logging.error(f"Unexpected error processing {json_file.name}: {e}")
            output_data["error"] = f"Unexpected Error: {e}"
            error_files += 1

        # Write output JSON
        output_filename = output_path / f"{json_file.stem}_extracted.json"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4)
        except Exception as e:
            logging.error(f"Error writing output file {output_filename}: {e}")
            error_files += 1 # Count error writing as an error case

    end_time = datetime.datetime.now()
    duration = end_time - start_time
    logging.info(f"Processing finished in {duration}.")
    logging.info(f"Total files processed: {processed_files + error_files}")
    logging.info(f"Files successfully analyzed: {processed_files}")
    logging.info(f"Files with errors: {error_files}")

if __name__ == "__main__":
    main() 