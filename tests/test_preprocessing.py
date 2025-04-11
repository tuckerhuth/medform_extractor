# tests/test_preprocessing.py
import unittest
import cv2
import numpy as np
from PIL import Image
import os
import sys

# Adjust import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.preprocessing import (
    preprocess_image,
    normalize_image,
    reduce_noise,
    apply_thresholding,
    # deskew_image # Add later if testing deskewing specifically
)

# Helper function to create a dummy PIL image
def create_dummy_pil_image(width=100, height=50, color=(128, 128, 128)):
    if color == 'gradient':
        img_array = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(width):
            img_array[:, i, :] = int(i / width * 255)
        return Image.fromarray(img_array, 'RGB')
    elif isinstance(color, tuple):
         # Ensure RGB format for consistency with cvtColor expectation
        img_array = np.full((height, width, 3), color, dtype=np.uint8)
        return Image.fromarray(img_array, 'RGB')
    elif color == 'grayscale':
        img_array = np.full((height, width), 128, dtype=np.uint8)
        return Image.fromarray(img_array, 'L') # L mode for grayscale


class TestPreprocessing(unittest.TestCase):

    def test_normalize_image_color(self):
        pil_img = create_dummy_pil_image(color=(50, 100, 150))
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        normalized = normalize_image(cv_img)
        self.assertEqual(len(normalized.shape), 2) # Should be grayscale
        self.assertEqual(normalized.dtype, np.uint8)

    def test_normalize_image_grayscale(self):
        pil_img = create_dummy_pil_image(color='grayscale')
        cv_img = np.array(pil_img) # No conversion needed for grayscale PIL
        normalized = normalize_image(cv_img)
        self.assertEqual(len(normalized.shape), 2)
        self.assertEqual(normalized.dtype, np.uint8)
        self.assertTrue(np.all(normalized == 128))

    # Add more specific tests for noise reduction and thresholding if needed
    # For now, focus on the main preprocess_image pipeline

    def test_preprocess_image_basic_rgb(self):
        pil_img = create_dummy_pil_image(color=(80, 120, 160))
        preprocessed = preprocess_image(pil_img)
        self.assertIsNotNone(preprocessed)
        self.assertEqual(len(preprocessed.shape), 2) # Expect grayscale output
        self.assertEqual(preprocessed.dtype, np.uint8)
        self.assertEqual(preprocessed.shape, (50, 100)) # Height, Width

    def test_preprocess_image_basic_grayscale(self):
        pil_img = create_dummy_pil_image(color='grayscale')
        preprocessed = preprocess_image(pil_img)
        self.assertIsNotNone(preprocessed)
        self.assertEqual(len(preprocessed.shape), 2)
        self.assertEqual(preprocessed.dtype, np.uint8)
        self.assertEqual(preprocessed.shape, (50, 100))
        # Check if values are reasonable (depends on normalization steps)
        # For current basic implementation, should be close to original gray value
        # self.assertTrue(np.mean(preprocessed) > 100) # Example check

    def test_preprocess_image_invalid_input(self):
        # Test with None input
        preprocessed_none = preprocess_image(None)
        self.assertIsNone(preprocessed_none)

        # Test with non-image input (though load_image should prevent this)
        # Simulating an error during conversion or processing
        # This requires mocking internal functions or setting up specific error conditions
        # For now, test the None case.

    # Add tests for deskewing, specific noise/thresholding effects later
    # when those features are finalized and enabled in the main pipeline.

if __name__ == '__main__':
    unittest.main() 