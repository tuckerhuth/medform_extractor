"""
Tests for the YAML parser module.
"""
import pytest
import yaml
from pathlib import Path
from src.yaml_parser import load_yaml_criteria, extract_patterns

def test_yaml_loads():
    """Test basic YAML loading functionality."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    data = load_yaml_criteria(str(yaml_path))
    assert isinstance(data, dict)
    assert "metadata" in data
    assert "tuberculosis" in data

def test_yaml_structure():
    """Test that the YAML structure matches expected format."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    data = load_yaml_criteria(str(yaml_path))
    
    # Check metadata structure
    assert "metadata" in data
    assert "description" in data["metadata"]
    assert "structure" in data["metadata"]
    
    # Check tuberculosis data structure
    assert "tuberculosis" in data
    for test_type in ["skin_test", "blood_test", "radiography"]:
        assert test_type in data["tuberculosis"]
        for aspect in ["test_name", "procedure", "administration", "results_documentation"]:
            assert aspect in data["tuberculosis"][test_type]
            assert "keywords" in data["tuberculosis"][test_type][aspect]
            assert "regex_patterns" in data["tuberculosis"][test_type][aspect]

def test_confidence_scores():
    """Test that confidence scores are present and valid."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    data = load_yaml_criteria(str(yaml_path))
    
    def check_confidence(items):
        for item in items:
            assert "confidence" in item
            assert isinstance(item["confidence"], (int, float))
            assert 0 <= item["confidence"] <= 100
    
    for test_type in data["tuberculosis"].values():
        for aspect in test_type.values():
            if "keywords" in aspect:
                check_confidence(aspect["keywords"])
            if "regex_patterns" in aspect:
                check_confidence(aspect["regex_patterns"])

def test_pattern_extraction():
    """Test the pattern extraction functionality."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    data = load_yaml_criteria(str(yaml_path))
    patterns = extract_patterns(data)
    
    # Check basic structure
    assert isinstance(patterns, dict)
    for test_type in ["skin_test", "blood_test", "radiography"]:
        assert test_type in patterns
        assert "keywords" in patterns[test_type]
        assert "regex_patterns" in patterns[test_type]
        
        # Check that patterns are properly formatted
        for keyword in patterns[test_type]["keywords"]:
            assert "string" in keyword
            assert "confidence" in keyword
            assert isinstance(keyword["string"], str)
            assert isinstance(keyword["confidence"], float)
            assert 0 <= keyword["confidence"] <= 1
            
        for pattern in patterns[test_type]["regex_patterns"]:
            assert "string" in pattern
            assert "confidence" in pattern
            assert isinstance(pattern["string"], str)
            assert isinstance(pattern["confidence"], float)
            assert 0 <= pattern["confidence"] <= 1

def test_pattern_content():
    """Test that extracted patterns contain expected content."""
    yaml_path = Path("disease_keywords/tuberculosis.yaml")
    data = load_yaml_criteria(str(yaml_path))
    patterns = extract_patterns(data)
    
    # Test specific known patterns
    skin_test_patterns = patterns["skin_test"]
    assert any(k["string"] == "tuberculin skin test" for k in skin_test_patterns["keywords"])
    assert any(p["string"] == r"\btuberculin\s+skin\s+test\b" for p in skin_test_patterns["regex_patterns"])
    
    blood_test_patterns = patterns["blood_test"]
    assert any(k["string"] == "interferon gamma release assay" for k in blood_test_patterns["keywords"])
    assert any(p["string"] == r"\b(?:interferon[\s-]*gamma[\s-]*release[\s-]*assay|igra)\b(?!\s+not\s+performed)" 
              for p in blood_test_patterns["regex_patterns"])

def test_nonexistent_file():
    """Test handling of non-existent files."""
    with pytest.raises(FileNotFoundError):
        load_yaml_criteria("nonexistent.yaml")

def test_malformed_yaml():
    """Test handling of malformed YAML."""
    # Create a temporary malformed YAML file
    malformed_yaml = """
    bad:
      - unclosed bracket: [
      invalid indent
    """
    tmp_path = Path("tests/malformed.yaml")
    tmp_path.write_text(malformed_yaml)
    
    with pytest.raises(yaml.YAMLError):
        load_yaml_criteria(str(tmp_path))
    
    # Clean up
    tmp_path.unlink() 