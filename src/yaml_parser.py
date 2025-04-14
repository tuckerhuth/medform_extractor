"""
YAML parser module for loading and processing disease criteria files.
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Union

def load_yaml_criteria(file_path: str) -> Dict[str, Any]:
    """
    Load and parse a YAML criteria file.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Dictionary containing the parsed YAML data
        
    Raises:
        yaml.YAMLError: If the YAML file is malformed
        FileNotFoundError: If the file doesn't exist
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {file_path}: {e}")
        raise
    except FileNotFoundError:
        logging.error(f"Criteria file not found: {file_path}")
        raise

def extract_patterns(yaml_data: Dict[str, Any]) -> Dict[str, Dict[str, List[Dict[str, Union[str, float]]]]]:
    """
    Extract patterns and keywords from the YAML data structure.
    
    Args:
        yaml_data: Parsed YAML data
        
    Returns:
        Dictionary containing organized patterns and keywords with their confidence scores
    """
    patterns = {}
    
    # Extract patterns for each test type
    for test_type in ['skin_test', 'blood_test', 'radiography']:
        patterns[test_type] = {
            'keywords': [],
            'regex_patterns': []
        }
        
        if test_type not in yaml_data['tuberculosis']:
            continue
            
        test_data = yaml_data['tuberculosis'][test_type]
        
        # Process each aspect (test_name, procedure, etc.)
        for aspect_name, aspect_data in test_data.items():
            # Extract keywords
            if 'keywords' in aspect_data:
                patterns[test_type]['keywords'].extend([
                    {
                        'string': keyword['string'],
                        'confidence': keyword['confidence'] / 100.0  # Convert to 0-1 range
                    }
                    for keyword in aspect_data['keywords']
                ])
            
            # Extract regex patterns
            if 'regex_patterns' in aspect_data:
                patterns[test_type]['regex_patterns'].extend([
                    {
                        'string': pattern['string'],
                        'confidence': pattern['confidence'] / 100.0  # Convert to 0-1 range
                    }
                    for pattern in aspect_data['regex_patterns']
                ])
    
    return patterns 