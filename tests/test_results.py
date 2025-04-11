# tests/test_results.py
import unittest
import json
import os
import tempfile
import shutil

# Adjust import path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.results import ResultManager, define_output_structure

class TestResults(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.test_dir, 'results.json')
        self.result_manager = ResultManager(self.output_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_define_output_structure(self):
        file_path = "/path/to/image.png"
        data = define_output_structure(file_path)
        self.assertEqual(data['file_path'], file_path)
        self.assertIsNone(data['classification'])
        self.assertIsNone(data['confidence'])
        self.assertIsNone(data['extracted_text'])
        self.assertIsNone(data['error'])
        self.assertDictEqual(data['metadata'], {
            'name': None,
            'date': None,
            'xray_type': None
        })

    def test_add_result_new_file(self):
        data = define_output_structure("img1.jpg")
        data['classification'] = 'X-ray'

        self.result_manager.add_result(data)

        self.assertTrue(os.path.exists(self.output_file))
        with open(self.output_file, 'r') as f:
            results = json.load(f)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file_path'], "img1.jpg")
        self.assertEqual(results[0]['classification'], "X-ray")

    def test_add_result_append_file(self):
        # Add first result
        data1 = define_output_structure("img1.jpg")
        data1['classification'] = 'X-ray'
        self.result_manager.add_result(data1)

        # Add second result
        data2 = define_output_structure("img2.png")
        data2['classification'] = 'Blood Test'
        self.result_manager.add_result(data2)

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]['file_path'], "img2.png")
        self.assertEqual(results[1]['classification'], 'Blood Test')

    def test_add_result_with_error(self):
        data = define_output_structure("img_error.tiff")
        data['error'] = "OCR failed"
        self.result_manager.add_result(data)

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file_path'], "img_error.tiff")
        self.assertEqual(results[0]['error'], "OCR failed")
        self.assertIsNone(results[0]['classification'])

    def test_add_result_existing_malformed_json(self):
        # Create a malformed JSON file
        with open(self.output_file, 'w') as f:
            f.write('[{"key": "value"},') # Malformed: unclosed list, trailing comma

        data = define_output_structure("img_good.jpg")
        data['classification'] = 'TB Test'

        # Expect add_result to handle the error and overwrite/start fresh
        self.result_manager.add_result(data)

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file_path'], "img_good.jpg")
        self.assertEqual(results[0]['classification'], 'TB Test')

    def test_add_result_non_json_file(self):
        # Create a non-JSON file
        with open(self.output_file, 'w') as f:
            f.write("this is not json")

        data = define_output_structure("img_also_good.png")
        data['classification'] = 'X-ray'

        # Expect add_result to handle the error and overwrite/start fresh
        self.result_manager.add_result(data)

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file_path'], "img_also_good.png")
        self.assertEqual(results[0]['classification'], 'X-ray')


if __name__ == '__main__':
    unittest.main() 