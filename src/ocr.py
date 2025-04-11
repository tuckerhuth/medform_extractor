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

    # Process results using bounding boxes for layout
    # The coordinate system origin (0,0) is the bottom-left corner.
    # Y increases upwards.
    
    # Extract text and bounding box info (adjusting Y to be top-down)
    word_boxes = []
    for observation in results:
        top_candidate = observation.topCandidates_(1)[0]
        text = top_candidate.string()
        box = observation.boundingBox() # Returns a CGRect (origin: bottom-left, size: width, height)
        # Approximate center Y coordinate for sorting (inverted for top-down)
        center_y = 1.0 - (box.origin.y + box.size.height / 2.0)
        # Center X coordinate
        center_x = box.origin.x + box.size.width / 2.0
        word_boxes.append({
            'text': text,
            'box': box,
            'center_y': center_y,
            'center_x': center_x
        })

    # Sort primarily by vertical position (top-down), secondarily by horizontal (left-right)
    word_boxes.sort(key=lambda item: (item['center_y'], item['center_x']))

    # Reconstruct text trying to approximate layout
    reconstructed_lines = []
    current_line = []
    last_y = -1
    y_tolerance = 0.02 # Tolerance for considering words on the same line (adjust based on font size/image resolution)
    x_space_threshold_factor = 1.5 # How many times the width of a space char to consider adding space

    for i, word in enumerate(word_boxes):
        box = word['box']
        text = word['text']
        center_y = word['center_y']
        center_x = word['center_x']
        
        # Check if it's a new line (based on vertical position)
        if last_y != -1 and abs(center_y - last_y) > y_tolerance:
            reconstructed_lines.append(" ".join(current_line))
            current_line = []
            
        # Add spaces between words on the same line based on horizontal gap
        if current_line and i > 0:
            prev_word = word_boxes[i-1]
            prev_box = prev_word['box']
            gap = box.origin.x - (prev_box.origin.x + prev_box.size.width)
            
            # Estimate space width (heuristic - might need adjustment)
            # Use average character width of previous word as a rough guide
            avg_char_width = prev_box.size.width / max(1, len(prev_word['text']))
            space_threshold = avg_char_width * x_space_threshold_factor
            
            if gap > space_threshold:
                 # Add extra spaces based on gap size (optional refinement)
                 num_spaces = int(gap / avg_char_width)
                 # current_line.append(" " * max(1, num_spaces)) # Simple approach: add one space
                 current_line.append(" ") # Simplified
                 
        current_line.append(text)
        last_y = center_y
        
    # Add the last line
    if current_line:
        reconstructed_lines.append(" ".join(current_line))
        
    return "\n".join(reconstructed_lines).strip()

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