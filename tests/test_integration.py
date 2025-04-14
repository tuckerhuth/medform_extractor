"""
Integration tests for the YAML-based pattern matching system.
"""
import pytest
from pathlib import Path
from src.yaml_parser import load_yaml_criteria, extract_patterns
from src.process_ocr import process_text_with_patterns

def test_pattern_matching_integration():
    """Test the full pipeline from YAML loading to pattern matching."""
    # Load and extract patterns
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    yaml_data = load_yaml_criteria(str(yaml_path))
    patterns = extract_patterns(yaml_data)
    
    # Test cases for each test type
    test_cases = {
        "skin_test": [
            ("Patient received tuberculin skin test on 2024-03-15.", True),
            ("TST administered, awaiting results.", True),
            ("No skin test was performed.", False)
        ],
        "blood_test": [
            ("IGRA test completed on 2024-03-15.", True),
            ("QuantiFERON-TB Gold Plus results pending.", True),
            ("No blood work done.", False)
        ],
        "radiography": [
            ("Chest x-ray shows no abnormalities.", True),
            ("CXR completed on 2024-03-15.", True),
            ("No imaging performed.", False)
        ]
    }
    
    # Run test cases
    for test_type, cases in test_cases.items():
        type_patterns = patterns[test_type]
        for text, should_match in cases:
            matches = process_text_with_patterns(text, type_patterns)
            if should_match:
                assert len(matches) > 0, f"Expected match for '{text}' in {test_type}"
            else:
                assert len(matches) == 0, f"Expected no match for '{text}' in {test_type}"

def test_confidence_threshold():
    """Test that confidence thresholds are respected in pattern matching."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    yaml_data = load_yaml_criteria(str(yaml_path))
    patterns = extract_patterns(yaml_data)
    
    text = "Patient received tuberculin skin test and IGRA test."
    
    # Test with different confidence thresholds
    thresholds = [0.0, 0.5, 0.9, 1.0]
    for threshold in thresholds:
        matches = process_text_with_patterns(text, patterns["skin_test"], confidence_threshold=threshold)
        high_confidence_matches = [m for m in matches if m["confidence"] >= threshold]
        assert len(high_confidence_matches) == len(matches), \
            f"Found matches below threshold {threshold}"

def test_pattern_overlap():
    """Test handling of overlapping pattern matches."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    yaml_data = load_yaml_criteria(str(yaml_path))
    patterns = extract_patterns(yaml_data)
    
    # Text with potentially overlapping matches
    text = "tuberculin skin test TST PPD test"
    
    matches = process_text_with_patterns(text, patterns["skin_test"])
    
    # Check that matches don't overlap
    match_ranges = [(m["start"], m["end"]) for m in matches]
    for i, range1 in enumerate(match_ranges):
        for range2 in match_ranges[i+1:]:
            assert not (range1[0] <= range2[1] and range2[0] <= range1[1]), \
                "Found overlapping matches" 