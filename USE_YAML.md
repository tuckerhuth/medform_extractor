# Migration to YAML-based Criteria File

## Implementation and Testing Checklist

### Phase 1: Initial Setup and Basic Parsing
- [x] Install PyYAML dependency
  - Add to requirements.txt
  - Test: `import yaml` works in Python environment

- [x] Create YAML parser module
  - Create src/yaml_parser.py
  - Implement basic YAML loading function
  - Test: Can load tuberculosis.yaml without errors

### Phase 2: File Reference Updates
- [x] Update DEFAULT_CRITERIA_FILE in process_ocr.py
  ```python
  DEFAULT_CRITERIA_FILE = get_resource_path(os.path.join('disease_keywords', 'tuberculosis.yaml'))
  ```
  - Test: Print file path and verify it exists

- [x] Update criteria_file_path in launch.py
  ```python
  self.criteria_file_path = APP_OUTPUT_BASE / "disease_keywords" / "tuberculosis.yaml"
  ```
  - Test: Launch application and verify path is correct

### Phase 3: Parser Implementation
- [x] Implement YAML to Dictionary Conversion
  ```python
  def load_yaml_criteria(file_path):
      with open(file_path, 'r') as f:
          return yaml.safe_load(f)
  ```
  - Test: Load file and verify structure matches expected format

- [x] Create Test Cases
  - Create tests/test_yaml_parser.py
  - Add test for basic YAML loading
  - Add test for structure validation
  - Test: Run pytest and verify tests pass

### Phase 4: Data Structure Adaptation
- [x] Implement Pattern Extraction
  ```python
  def extract_patterns(yaml_data):
      patterns = {}
      for test_type in ['skin_test', 'blood_test', 'radiography']:
          patterns[test_type] = {
              'keywords': [],
              'regex_patterns': []
          }
          # Extract patterns from YAML structure
      return patterns
  ```
  - Test: Verify pattern extraction matches expected format

- [x] Add Pattern Extraction Tests
  - Add test cases for each test type
  - Verify confidence scores are correctly extracted
  - Test: Run pattern extraction tests

### Phase 5: Integration Testing
- [ ] Create Integration Test Suite
  - Test full pipeline from YAML to pattern matching
  - Verify results match expected output
  - Test: Process sample images with new YAML format

### Phase 6: Cleanup and Documentation
- [ ] Remove Old MD Parser Code
  - Remove markdown-specific parsing functions
  - Remove old test cases
  - Test: Verify no broken references

- [ ] Update Documentation
  - Update README.md with YAML format information
  - Add example YAML structure
  - Test: Verify documentation accuracy

### Phase 7: Error Handling
- [ ] Add Error Handling
  ```python
  def safe_load_yaml(file_path):
      try:
          return load_yaml_criteria(file_path)
      except yaml.YAMLError as e:
          logging.error(f"Error loading YAML file: {e}")
          raise
  ```
  - Test: Verify error handling with malformed YAML

### Test Cases to Create
1. Basic YAML Loading
   ```python
   def test_yaml_loads():
       data = load_yaml_criteria('tuberculosis.yaml')
       assert isinstance(data, dict)
       assert 'metadata' in data
   ```

2. Pattern Extraction
   ```python
   def test_pattern_extraction():
       data = load_yaml_criteria('tuberculosis.yaml')
       patterns = extract_patterns(data)
       assert 'skin_test' in patterns
       assert 'keywords' in patterns['skin_test']
   ```

3. Confidence Score Handling
   ```python
   def test_confidence_scores():
       data = load_yaml_criteria('tuberculosis.yaml')
       patterns = extract_patterns(data)
       assert all(0 <= p['confidence'] <= 1 for p in patterns['skin_test']['keywords'])
   ```

4. Integration Test
   ```python
   def test_full_pipeline():
       # Test image processing with new YAML format
       result = process_image('test_image.png')
       assert result is not None
   ```

### Test Cases to Remove
- Remove all markdown-specific parser tests
- Remove confidence extraction tests for MD format
- Remove old file path tests for .md files

## Final Verification
- [ ] Run full test suite
- [ ] Process sample images
- [ ] Verify all patterns are correctly matched
- [ ] Check logging output for any warnings/errors 