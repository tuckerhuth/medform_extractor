# src/ocr.py
import pytesseract
import cv2
import sys
from PIL import Image # Import Image from Pillow

# --- Tesseract Configuration (Optional) ---
# If Tesseract is not in your PATH, you might need to specify its location:
# Example for Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Example for macOS (if installed via Homebrew):
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract' or '/opt/homebrew/bin/tesseract'
# Example for Linux:
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- OCR Function ---

def extract_text_from_image(image_obj):
    """Extract text from an image object (Pillow format) using Tesseract.

    Args:
        image_obj (PIL.Image.Image): Image object loaded by Pillow.

    Returns:
        str: The extracted text.
        Returns None if OCR fails or the image is invalid.
    """
    if image_obj is None:
        print("Error: Cannot perform OCR on an empty or invalid image object.")
        return None

    # --- Skipping internal grayscale conversion --- 
    # Pytesseract can accept Pillow images directly
    # gray_image = image_obj # Assuming pytesseract handles conversion if needed
    # --- End Skip --- 

    try:
        # Perform OCR using pytesseract
        # Configuration options can be added: '--psm 6' for assuming a single uniform block of text
        # '--oem 3' for default OCR engine mode
        # Use lang='eng' for English
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image_obj, lang='eng', config=custom_config)
        return text.strip() # Remove leading/trailing whitespace
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract is not installed or not found in your PATH.")
        print("Please install Tesseract and configure the path in ocr.py if necessary.")
        # Re-raise the error or handle it as needed for the main script
        raise # Or return None / specific error message
    except Exception as e:
        print(f"Error during Tesseract OCR processing: {e}")
        # Optionally log the full traceback
        # import traceback
        # print(traceback.format_exc())
        return None # Indicate OCR failure

# --- Example Usage --- 
if __name__ == '__main__':
    from src.image_loader import load_image
    from src.preprocessing import preprocess_image

    if len(sys.argv) < 2:
        print("Usage: python ocr.py <image_path>")
        sys.exit(1)

    input_path = sys.argv[1]

    print(f"Loading image: {input_path}")
    pil_image = load_image(input_path)

    if pil_image:
        # Skipping preprocessing for example usage
        print("Performing OCR on original image...")
        extracted_text = extract_text_from_image(pil_image)

        if extracted_text is not None:
            print("\n--- Extracted Text ---")
            print(extracted_text)
            print("--- End of Text ---")
        else:
            print("OCR failed or produced no text.")
    else:
        print(f"Failed to load image {input_path}.") 