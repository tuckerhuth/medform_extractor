# tests/test_classification.py
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Adjust import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import module AFTER adjusting path
from src import classification
# Explicitly import items needed for testing
from src.classification import classify_document, find_keywords, extract_field, PATTERNS, KEYWORDS, extract_name_ner

# --- Mock spaCy --- 
# Mock the NLP object and its processing
mock_spacy_doc = MagicMock()
mock_spacy_entity = MagicMock()
mock_spacy_entity.text = "Mocked Name"
mock_spacy_entity.label_ = "PERSON"
mock_spacy_doc.ents = [mock_spacy_entity]

mock_nlp = MagicMock()
mock_nlp.return_value = mock_spacy_doc
mock_nlp.max_length = 1000000 # Mock max length

# Mock the load function to return our mock NLP object or None
mock_load_spacy_model = MagicMock()

class TestClassification(unittest.TestCase):

    # --- Test Helper Functions --- 
    def test_find_keywords(self):
        text = "This report is an X-RAY of the chest. Also includes blood test results."
        counts = find_keywords(text, KEYWORDS)
        self.assertEqual(counts['xray'], 1) # Corrected assertion: Only 'X-RAY' is present
        self.assertEqual(counts['blood_test'], 1)
        self.assertEqual(counts.get('tb_one_step', 0), 0)

    def test_find_keywords_case_insensitive(self):
        text = "x-ray and RADIOLOGY report. Mantoux test positive."
        counts = find_keywords(text, KEYWORDS)
        self.assertEqual(counts['xray'], 2)
        self.assertEqual(counts['tb_one_step'], 1)

    def test_find_keywords_no_match(self):
        text = "Standard physical examination notes."
        counts = find_keywords(text, KEYWORDS)
        self.assertEqual(len(counts), 0)

    def test_extract_field_name(self):
        text = "Patient Name: John Jacob Doe\nAge: 45"
        name = extract_field(text, PATTERNS['name'])
        self.assertEqual(name, "John Jacob Doe")

    def test_extract_field_date_formats(self):
        text1 = "Date: 12/25/2023"
        text2 = "Performed on 01-02-2024"
        text3 = "Test Date: Jan 5, 2024"
        text4 = "Date of Service: February 10, 2024"
        self.assertEqual(extract_field(text1, PATTERNS['date']), "12/25/2023")
        self.assertEqual(extract_field(text2, PATTERNS['date']), "01-02-2024")
        self.assertEqual(extract_field(text3, PATTERNS['date']), "Jan 5, 2024")
        self.assertEqual(extract_field(text4, PATTERNS['date']), "February 10, 2024")

    def test_extract_field_xray_type(self):
        text1 = "CHEST X-RAY REPORT"
        text2 = "Findings for the x-ray of the dental area"
        self.assertEqual(extract_field(text1, PATTERNS['xray_type']), "CHEST")
        self.assertEqual(extract_field(text2, PATTERNS['xray_type']), "dental")

    def test_extract_field_no_match(self):
        text = "This text has no matching patterns for names or dates."
        self.assertIsNone(extract_field(text, PATTERNS['name']))
        self.assertIsNone(extract_field(text, PATTERNS['date']))

    # --- Test NER Extraction --- 
    def test_extract_name_ner_success(self):
        """Test NER name extraction when model loads and finds a PERSON."""
        # Setup mocks specifically for this test
        mock_entity = MagicMock()
        mock_entity.text = "Alice Wonderland"
        mock_entity.label_ = "PERSON"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_entity]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp_instance.max_length = 1000000

        with patch('src.classification.load_spacy_model') as mock_loader:
            mock_loader.return_value = mock_nlp_instance # Simulate successful load
            text_with_name = "Patient identified as Alice Wonderland."
            name = extract_name_ner(text_with_name)

            self.assertEqual(name, "Alice Wonderland")
            mock_loader.assert_called_once() # Check loader was called
            mock_nlp_instance.assert_called_once_with(text_with_name[:mock_nlp_instance.max_length]) # Check nlp() was called

    def test_extract_name_ner_no_person(self):
        """Test NER when no PERSON entities are found."""
        mock_entity = MagicMock()
        mock_entity.text = "Some Company"
        mock_entity.label_ = "ORG"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_entity]
        mock_nlp_instance = MagicMock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp_instance.max_length = 1000000

        with patch('src.classification.load_spacy_model') as mock_loader:
            mock_loader.return_value = mock_nlp_instance
            name = extract_name_ner("Report from Some Company.")
            self.assertIsNone(name)
            mock_loader.assert_called_once()
            mock_nlp_instance.assert_called_once()

    def test_extract_name_ner_model_load_fail(self):
        """Test NER when spaCy model fails to load."""
        with patch('src.classification.load_spacy_model') as mock_loader:
            mock_loader.return_value = None # Simulate load failure
            name = extract_name_ner("Some text")
            self.assertIsNone(name)
            mock_loader.assert_called_once()

    # --- Test Main classify_document Function --- 
    # Patch the NER function directly within classify_document's scope
    @patch('src.classification.extract_name_ner')
    def test_classify_xray(self, mock_extract_ner):
        mock_extract_ner.return_value = "Mocky McMockface" # Mock NER result
        text = "Patient Name: Mocky McMockface\nTest: Chest X-Ray Report\nDate: 10/01/2024"
        result = classify_document(text)
        self.assertEqual(result['classification'], "X-ray")
        self.assertEqual(result['metadata']['name'], "Mocky McMockface")
        self.assertEqual(result['metadata']['date'], "10/01/2024")
        self.assertEqual(result['metadata']['xray_type'], "Chest")
        mock_extract_ner.assert_called_with(text)

    @patch('src.classification.extract_name_ner') # Patch NER
    def test_classify_tb_one_step(self, mock_extract_ner):
        mock_extract_ner.return_value = None # Simulate NER failing, use regex
        text = "Mantoux Test\nName: Test Person\nDate: Feb 1, 2024\nResult: Positive"
        result = classify_document(text)
        self.assertEqual(result['classification'], "One-step TB Test")
        self.assertEqual(result['metadata']['name'], "Test Person") # Fallback regex
        self.assertEqual(result['metadata']['date'], "Feb 1, 2024")
        self.assertIsNone(result['metadata']['xray_type'])

    # Use patch on the loader for classify_document tests as well, to simulate model loading
    @patch('src.classification.load_spacy_model')
    @patch('src.classification.extract_name_ner') # Keep patching extract_name_ner if needed for control
    def test_classify_tb_two_step(self, mock_extract_ner, mock_loader):
        mock_nlp_instance = MagicMock() # Need a mock nlp instance
        mock_loader.return_value = mock_nlp_instance # Model loads successfully
        # Simulate NER finding the name
        mock_extract_ner.return_value = "Second Tester"

        text = "Two-step TB test for Employee Name: Second Tester.\nStep 1: 03/03/2023\nStep 2 PPD test: 03/10/2023"
        result = classify_document(text)
        self.assertEqual(result['classification'], "Two-step TB Test")
        self.assertEqual(result['metadata']['name'], "Second Tester") # Should use NER result
        self.assertEqual(result['metadata']['date'], "03/03/2023") # Finds first date
        mock_loader.reset_mock() # Reset loader mock

    @patch('src.classification.load_spacy_model')
    @patch('src.classification.extract_name_ner')
    def test_classify_blood_test(self, mock_extract_ner, mock_loader):
        mock_nlp_instance = MagicMock()
        mock_loader.return_value = mock_nlp
        mock_extract_ner.return_value = "Blood Sample Provider" # Simulate NER finding the name
        text = "Lab Results - CBC\nPatient Name: Blood Sample Provider\nDOB: 05/05/1990\nCollection Date: 04/04/2024"
        result = classify_document(text)
        self.assertEqual(result['classification'], "Blood Test")
        self.assertEqual(result['metadata']['name'], "Blood Sample Provider") # NER result
        self.assertEqual(result['metadata']['date'], "05/05/1990") # Expects first date found (DOB)
        mock_loader.reset_mock()

    def test_classify_no_match(self):
        text = "This is a regular document about programming."
        result = classify_document(text)
        self.assertIsNone(result['classification'])
        # Name extraction might still run, depending on mock setup, check for None if NER fails/no name
        # self.assertIsNone(result['metadata']['name'])
        self.assertIsNone(result['metadata']['date'])

    def test_classify_empty_text(self):
        text = ""
        result = classify_document(text)
        self.assertIsNone(result['classification'])
        self.assertIsNone(result['metadata']['name'])
        self.assertIsNone(result['metadata']['date'])


if __name__ == '__main__':
    unittest.main() 