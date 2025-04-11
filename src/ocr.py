# src/ocr.py
# import pytesseract # No longer needed
# import cv2 # No longer needed unless used elsewhere
import sys

# --- Use macOS Vision Framework via PyObjC ---
import objc
from Foundation import NSData, NSURL, NSError
from Vision import VNImageRequestHandler, VNRecognizeTextRequest
# --- End Vision Framework Imports ---


def extract_text_from_image(image_path):
    """Extract text from an image file using macOS Vision Framework.

    Args:
        image_path (str): Path to the image file.

    Returns:
        str: The extracted text, or None if extraction fails.
    """
    # If the imports at the top of the file succeeded, PyObjC and frameworks are loaded.
    # The previous check using objc.getClass was incorrect.
         
    # Use error pointers for Objective-C methods
    error_ptr = objc.nil

    # Create a URL for the image file
    url = NSURL.fileURLWithPath_(image_path)
    if not url:
        print(f"Error: Could not create URL for path: {image_path}")
        return None

    # Create a text recognition request
    request = VNRecognizeTextRequest.alloc().init()
    # You might experiment with recognition level: .accurate() or .fast()
    # request.setRecognitionLevel_(VNRecognizeTextRequest.accurate())
    # Add language support if needed, e.g., request.setRecognitionLanguages_(["en-US", "fr-FR"])

    # Create an image request handler
    handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    if not handler:
        print(f"Error: Could not create VNImageRequestHandler for URL: {url}")
        return None

    # Perform the request
    success, error = handler.performRequests_error_([request], error_ptr)

    if not success or error:
        error_msg = error.localizedDescription() if error else "Unknown error"
        print(f"Error performing Vision request for {image_path}: {error_msg}")
        return None

    # Get the results
    results = request.results()
    if not results:
        print(f"No text recognized in {image_path}.")
        return "" # Return empty string if no text found, not None

    # Extract the recognized text
    # The results are VNRecognizedTextObservation objects
    # Each observation can contain multiple candidates (VNRecognizedText)
    # We'll take the top candidate (most confident) for each observation
    lines = []
    for observation in results:
        top_candidate = observation.topCandidates_(1)[0] # Get the most confident candidate
        lines.append(top_candidate.string())

    return "\n".join(lines).strip()

# --- Example Usage --- 
if __name__ == '__main__':
    # Note: This example usage doesn't use preprocessing anymore
    # from src.image_loader import load_image # No longer needed here
    # from src.preprocessing import preprocess_image # No longer needed here

    if len(sys.argv) < 2:
        print("Usage: python ocr.py <image_path>")
        sys.exit(1)

    input_path = sys.argv[1]

    print(f"Performing OCR on original image: {input_path}")
    extracted_text = extract_text_from_image(input_path)

    if extracted_text is not None:
        print("\n--- Extracted Text ---")
        print(extracted_text)
        print("--- End of Text ---")
    else:
        print("OCR failed.") 