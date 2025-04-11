# src/classification.py
import re
import spacy
import os
import sys
from collections import Counter

# --- Load spaCy Model --- 
# Load the small English model. Handle potential loading errors.
NLP = None
def load_spacy_model():
    global NLP
    if NLP is None:
        try:
            # Disable unnecessary pipes for efficiency if only using NER
            NLP = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
            print("spaCy model 'en_core_web_sm' loaded successfully.")
        except OSError:
            print(
                "\nError: spaCy model 'en_core_web_sm' not found. "
                "Please run: python -m spacy download en_core_web_sm\n",
                file=sys.stderr
            )
            NLP = "error" # Mark as error to avoid retrying
        except Exception as e:
             print(f"Error loading spaCy model: {e}", file=sys.stderr)
             NLP = "error"
    return NLP if NLP != "error" else None

# --- Constants and Keywords --- 
# Document Type Keywords (case-insensitive matching)
# Prioritize more specific terms
KEYWORDS = {
    "xray": ["x-ray", "radiograph", "radiology", "imaging", "chest x ray", "dental x ray"],
    "tb_one_step": ["one-step tb", "1-step tb", "single tb test", "tb skin test", "ppd test", "mantoux test"],
    "tb_two_step": ["two-step tb", "2-step tb", "second tb test", "follow-up tb"],
    "blood_test": ["blood test", "serology", "hematology", "cbc", "complete blood count", "blood work", "lab results"]
}

# Metadata Extraction Patterns (case-insensitive)
PATTERNS = {
    "name": [
        # Look for patterns ending with a newline or specific punctuation
        re.compile(r"patient name[:\s]+([A-Za-z\s,-]+(?:\s[A-Za-z]+)*?)(?=[\n\r.,;]|$)", re.IGNORECASE),
        re.compile(r"name[:\s]+([A-Za-z\s,-]+(?:\s[A-Za-z]+)*?)(?=[\n\r.,;]|$)", re.IGNORECASE),
        # Add more variations as needed
    ],
    "date": [
        # Common formats (MM/DD/YYYY, DD-MM-YYYY, Month D, YYYY etc.)
        re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"),
        re.compile(r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b", re.IGNORECASE),
        re.compile(r"date[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", re.IGNORECASE),
        re.compile(r"date of service[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", re.IGNORECASE),
        # Add more variations
    ],
    "xray_type": [
        re.compile(r"\b(chest|dental|spine|abdomen|pelvis|skull|extremity)\s+x-ray", re.IGNORECASE),
        re.compile(r"x-ray of the\s+(chest|dental|spine|abdomen|pelvis|skull|extremity)", re.IGNORECASE),
        # Add more specific patterns
    ]
}

# --- Helper Functions --- 

def find_keywords(text, keywords_dict):
    """Find occurrences of keywords from a dictionary in the text."""
    text_lower = text.lower()
    found_counts = Counter()
    for doc_type, terms in keywords_dict.items():
        for term in terms:
            # Use word boundaries but allow for punctuation immediately after
            # This regex looks for the term surrounded by non-word chars or start/end of string
            pattern = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
            matches = re.findall(pattern, text_lower)
            if matches:
                found_counts[doc_type] += len(matches)
    return found_counts

def extract_field(text, patterns):
    """Extract the first match for a list of regex patterns."""
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            # Return the first capturing group if it exists, else the full match
            return match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
    return None

def extract_name_ner(text):
    """Extract person names using spaCy NER."""
    nlp = load_spacy_model()
    if not nlp or not text:
        return None

    doc = nlp(text[:nlp.max_length]) # Process text up to model limit
    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

    # Basic filtering/prioritization (e.g., longer names, appearing early)
    if not names:
        return None
    # Simple heuristic: return the first longest name found
    names.sort(key=len, reverse=True)
    return names[0].strip()


# --- Main Classification Function --- 

def classify_document(text):
    """Classify the document type and extract metadata based on text content.

    Args:
        text (str): Extracted text from the OCR process.

    Returns:
        dict: A dictionary containing classification results:
              {'classification': str|None, 'confidence': float|None, 'metadata': dict}
    """
    results = {
        'classification': None,
        'confidence': None, # Placeholder for future scoring
        'metadata': {
            'name': None,
            'date': None,
            'xray_type': None
        }
    }

    if not text or not isinstance(text, str):
        print("Warning: Classification called with invalid text input.")
        return results # Return empty results if no text

    # 1. Document Type Classification based on Keywords
    keyword_counts = find_keywords(text, KEYWORDS)

    # Simple classification: highest count wins (needs refinement)
    if keyword_counts:
        # Prioritize two-step TB if both one-step and two-step keywords are present
        if keyword_counts["tb_two_step"] > 0 and keyword_counts["tb_one_step"] > 0:
            results['classification'] = "Two-step TB Test"
            # Optional: Calculate a simple confidence score
            # results['confidence'] = keyword_counts["tb_two_step"] / sum(keyword_counts.values())
        else:
            # Get the type with the highest count
            most_common_type, count = keyword_counts.most_common(1)[0]
            if most_common_type == "xray":
                results['classification'] = "X-ray"
            elif most_common_type == "tb_one_step":
                results['classification'] = "One-step TB Test"
            elif most_common_type == "tb_two_step":
                results['classification'] = "Two-step TB Test"
            elif most_common_type == "blood_test":
                results['classification'] = "Blood Test"
            # results['confidence'] = count / sum(keyword_counts.values())

    # 2. Metadata Extraction
    # Attempt NER first for name, fallback to regex
    extracted_name_ner = extract_name_ner(text)
    if extracted_name_ner:
         results['metadata']['name'] = extracted_name_ner
    else:
         # Fallback to regex if NER fails or model not loaded
         results['metadata']['name'] = extract_field(text, PATTERNS["name"])

    results['metadata']['date'] = extract_field(text, PATTERNS["date"])

    # Only extract xray_type if classified as X-ray
    if results['classification'] == "X-ray":
        results['metadata']['xray_type'] = extract_field(text, PATTERNS["xray_type"])

    return results

# --- Example Usage --- 
if __name__ == '__main__':
    # Example texts for testing
    test_texts = [
        "Patient Name: John Smith\nTest: Chest X-Ray\nDate: 11/15/2023\nFindings: Normal lung fields.",
        "Mantoux Test Result\nName: Jane Doe\nDate Administered: 01-01-2024\nResult: 5mm induration\nInterpretation: Negative",
        "Two-Step TB Test\nPatient: Robert Jones\nStep 1 Date: Jan 5, 2024 Result: 0mm\nStep 2 Date: Jan 12, 2024 Result: 2mm\nFinal: Negative",
        "LabCorp\nComplete Blood Count\nPatient: Alice Brown\nCollected: 10/20/2023\nWBC: 5.5 K/uL\nRBC: 4.5 M/uL",
        "This is a generic document with no medical keywords.",
        ""
    ]

    print("--- Running Classification Examples ---")
    for i, sample_text in enumerate(test_texts):
        print(f"\n--- Text {i+1} ---")
        print(sample_text)
        print("--- Classification Results ---")
        classification_result = classify_document(sample_text)
        import json
        print(json.dumps(classification_result, indent=2))
        print("-----------------------------") 