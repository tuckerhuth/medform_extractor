# src/scanner.py
import os
import sys

# Define supported image extensions (case-insensitive)
SUPPORTED_EXTENSIONS = { '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.heic' }

def is_image_file(filename):
    """Check if a filename has a supported image extension."""
    # os.path.splitext splits "path/to/.hidden.png" into ("path/to/.hidden", ".png")
    _, ext = os.path.splitext(filename)
    return ext.lower() in SUPPORTED_EXTENSIONS

def scan_directory(root_dir):
    """Recursively scan a directory and yield paths to image files."""
    if not os.path.isdir(root_dir):
        raise ValueError(f"Invalid directory path: {root_dir}")

    for root, _, files in os.walk(root_dir):
        for filename in files:
            if is_image_file(filename):
                yield os.path.join(root, filename)

# Example usage (optional, for testing)
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scanner.py <directory_path>")
        sys.exit(1)

    target_directory = sys.argv[1]

    try:
        print(f"Scanning directory: {target_directory}")
        image_files = list(scan_directory(target_directory))
        if image_files:
            print("Found image files:")
            for img_path in image_files:
                print(f"- {img_path}")
        else:
            print("No image files found.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1) 