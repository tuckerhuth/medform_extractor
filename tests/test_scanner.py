# tests/test_scanner.py
import unittest
import os
import tempfile
import shutil

# Adjust the import path based on your project structure
# This assumes tests/ is at the same level as src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.scanner import scan_directory, is_image_file

class TestScanner(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory structure for testing
        self.test_dir = tempfile.mkdtemp()
        self.sub_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(self.sub_dir)

        # Create dummy files
        self.img1_path = os.path.join(self.test_dir, "image1.JPG")
        self.img2_path = os.path.join(self.sub_dir, "image2.png")
        self.txt_path = os.path.join(self.test_dir, "document.txt")
        self.hidden_img_path = os.path.join(self.test_dir, ".hidden_image.jpeg") # Example hidden

        with open(self.img1_path, "w") as f: f.write("dummy jpg")
        with open(self.img2_path, "w") as f: f.write("dummy png")
        with open(self.txt_path, "w") as f: f.write("dummy text")
        with open(self.hidden_img_path, "w") as f: f.write("dummy hidden jpeg")


    def tearDown(self):
        # Remove the temporary directory after tests
        shutil.rmtree(self.test_dir)

    def test_is_image_file(self):
        self.assertTrue(is_image_file("photo.jpg"))
        self.assertTrue(is_image_file("report.PNG"))
        self.assertTrue(is_image_file("scan.tiff"))
        self.assertTrue(is_image_file("archive.TIF"))
        self.assertTrue(is_image_file("image.jpeg"))
        self.assertTrue(is_image_file("bitmap.bmp"))
        self.assertFalse(is_image_file("document.txt"))
        self.assertFalse(is_image_file("archive.zip"))
        self.assertFalse(is_image_file("no_extension"))
        self.assertTrue(is_image_file(".hidden.png")) # Check hidden files

    def test_scan_directory_finds_images(self):
        found_files = list(scan_directory(self.test_dir))
        # Use set for order-independent comparison
        self.assertSetEqual(set(found_files), {self.img1_path, self.img2_path, self.hidden_img_path})

    def test_scan_directory_empty(self):
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)
        found_files = list(scan_directory(empty_dir))
        self.assertEqual(len(found_files), 0)

    def test_scan_directory_no_images(self):
        no_img_dir = os.path.join(self.test_dir, "no_images")
        os.makedirs(no_img_dir)
        with open(os.path.join(no_img_dir, "file.txt"), "w") as f: f.write("text")
        with open(os.path.join(no_img_dir, "another.dat"), "w") as f: f.write("data")
        found_files = list(scan_directory(no_img_dir))
        self.assertEqual(len(found_files), 0)

    def test_scan_directory_invalid_path(self):
        with self.assertRaises(ValueError):
            list(scan_directory("non_existent_directory_12345"))

    def test_scan_directory_is_file(self):
         with self.assertRaises(ValueError):
            list(scan_directory(self.txt_path))

if __name__ == '__main__':
    unittest.main() 