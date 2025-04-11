# tests/test_ocr.py
import unittest
import numpy as np
import cv2
import os
import sys
from unittest.mock import patch, MagicMock

# Adjust import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ocr import extract_text_from_image
import pytesseract # Import to check for TesseractNotFoundError

# Helper to create a dummy OpenCV image (grayscale)
def create_dummy_cv_image(width=100, height=50, text="Test", font_scale=1, thickness=1):
    img = np.zeros((height, width), dtype=np.uint8)
    # Put white text on black background (common for OCR)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, font_scale, (255), thickness)
    return img

class TestOCR(unittest.TestCase):

    # We need to mock pytesseract.image_to_string unless Tesseract is guaranteed to be installed
    # and we have actual test images.

    @patch('pytesseract.image_to_string')
    def test_extract_text_success(self, mock_image_to_string):
        """Test successful text extraction using a mock."""
        dummy_img = create_dummy_cv_image(text="Hello World")
        expected_text = " Hello World " # Simulate potential padding
        mock_image_to_string.return_value = expected_text

        extracted = extract_text_from_image(dummy_img)

        mock_image_to_string.assert_called_once()
        self.assertEqual(extracted, expected_text.strip())
        # Check if called with numpy array, expected language, and config
        args, kwargs = mock_image_to_string.call_args
        self.assertIsInstance(args[0], np.ndarray)
        self.assertEqual(kwargs.get('lang'), 'eng')
        self.assertIn('--psm 6', kwargs.get('config', '')) # Check part of the config

    @patch('pytesseract.image_to_string')
    def test_extract_text_empty_result(self, mock_image_to_string):
        """Test OCR returning an empty string."""
        dummy_img = create_dummy_cv_image(text="") # Blank image essentially
        mock_image_to_string.return_value = "   \n " # Simulate empty/whitespace result

        extracted = extract_text_from_image(dummy_img)
        self.assertEqual(extracted, "")

    def test_extract_text_invalid_image(self):
        """Test passing None or an empty image to OCR."""
        self.assertIsNone(extract_text_from_image(None))
        empty_img = np.array([])
        self.assertIsNone(extract_text_from_image(empty_img))

    @patch('pytesseract.image_to_string')
    def test_extract_text_tesseract_error(self, mock_image_to_string):
        """Test handling of a generic exception during OCR."""
        dummy_img = create_dummy_cv_image(text="Error Case")
        mock_image_to_string.side_effect = Exception("Simulated OCR error")

        extracted = extract_text_from_image(dummy_img)
        self.assertIsNone(extracted)

    @patch('pytesseract.image_to_string')
    def test_extract_text_tesseract_not_found(self, mock_image_to_string):
        """Test handling of TesseractNotFoundError."""
        dummy_img = create_dummy_cv_image(text="Not Found")
        mock_image_to_string.side_effect = pytesseract.TesseractNotFoundError

        # Expect the function to re-raise the exception
        with self.assertRaises(pytesseract.TesseractNotFoundError):
            extract_text_from_image(dummy_img)

    # Note: To perform *real* OCR tests, you would need:
    # 1. Tesseract installed and accessible.
    # 2. Sample image files (e.g., PNGs with known text).
    # 3. Load these images (using cv2.imread or Pillow+conversion) and pass them.
    # 4. Assert the extracted text matches the known text (allowing for minor variations).
    # These tests would not use the @patch decorator.

    # Example of a potential real test (requires Tesseract & test image):
    # def test_extract_text_real_image(self):
    #     script_dir = os.path.dirname(__file__)
    #     test_image_path = os.path.join(script_dir, 'test_data', 'sample_ocr.png')
    #     if not os.path.exists(test_image_path):
    #         self.skipTest("Test image 'sample_ocr.png' not found.")
    #     try:
    #         img = cv2.imread(test_image_path, cv2.IMREAD_GRAYSCALE)
    #         if img is None:
    #              self.fail(f"Failed to load test image: {test_image_path}")
    #         text = extract_text_from_image(img)
    #         self.assertIsNotNone(text)
    #         self.assertIn("ExpectedTextInImage", text)
    #     except pytesseract.TesseractNotFoundError:
    #          self.skipTest("Tesseract not found, skipping real OCR test.")


if __name__ == '__main__':
    unittest.main() 