import cv2
import numpy as np

# --- Image Preprocessing Functions ---

def normalize_image(image):
    """Convert image to grayscale and normalize pixel values."""
    # Convert to grayscale if it's not already
    if len(image.shape) == 3 and image.shape[2] == 3:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif len(image.shape) == 3 and image.shape[2] == 4: # Handle BGRA/RGBA
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray_image = image # Assume already grayscale

    # Optional: Apply contrast enhancement (e.g., CLAHE)
    # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    # enhanced_image = clahe.apply(gray_image)
    # return enhanced_image

    return gray_image # Return grayscale for now

def reduce_noise(image):
    """Apply noise reduction techniques."""
    # Gaussian blur is common for general noise
    # Parameters (kernel size, sigmaX) might need tuning
    denoised_image = cv2.GaussianBlur(image, (5, 5), 0)

    # Median blur is good for salt-and-pepper noise
    # denoised_image = cv2.medianBlur(image, 5)

    return denoised_image

def apply_thresholding(image):
    """Apply adaptive thresholding to binarize the image."""
    # Adaptive thresholding often works better than global thresholding
    # for varying lighting conditions found in photos/scans.
    binary_image = cv2.adaptiveThreshold(
        image, # Input image (grayscale)
        255,   # Max value to assign
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # Thresholding method
        cv2.THRESH_BINARY, # Threshold type
        11,    # Block size (size of pixel neighborhood)
        2      # Constant subtracted from the mean
    )
    # Optional: Invert if text is white on black background
    # binary_image = cv2.bitwise_not(binary_image)
    return binary_image

def deskew_image(image):
    """Correct skew (rotation) in the image (Basic implementation)."""
    # Convert to binary if not already, necessary for finding contours/lines
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Ensure image is binary (black background, white text/features)
    # This might need adjustment based on thresholding output
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Calculate skew angle using Hough Line Transform (can be slow)
    # Alternative: Minimum Area Rectangle
    coords = np.column_stack(np.where(binary > 0))
    if coords.size == 0:
        # Handle empty binary image case (no features found)
        print("Warning: No features found for deskewing. Returning original image.")
        return image

    try:
        angle = cv2.minAreaRect(coords)[-1]
    except cv2.error as e:
        # Handle other cases where minAreaRect fails
        print(f"Warning: cv2.minAreaRect failed during deskewing: {e}. Returning original image.")
        return image # Return original if angle detection fails

    # Adjust angle interpretation from minAreaRect
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ignore very small angles
    if abs(angle) < 0.1:
        return image

    # Rotate the original image (grayscale or color) to correct skew
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h),
                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    print(f"Deskewing image by {angle:.2f} degrees")
    return rotated

# --- Main Preprocessing Pipeline ---

def preprocess_image(image_pil):
    """Applies a standard preprocessing pipeline to a PIL image.

    Args:
        image_pil (PIL.Image.Image): Input image loaded by Pillow.

    Returns:
        numpy.ndarray: Preprocessed image in OpenCV format (grayscale, ready for OCR).
                       Returns None if preprocessing fails.
    """
    if image_pil is None:
        print("Error: Cannot preprocess a None image.")
        return None
    try:
        # 1. Convert PIL Image to OpenCV format (NumPy array)
        # Ensure conversion handles color spaces correctly (Pillow uses RGB, OpenCV uses BGR)
        # Handle different PIL modes
        if image_pil.mode == 'RGBA':
            open_cv_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGBA2BGR)
        elif image_pil.mode == 'RGB':
             open_cv_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        elif image_pil.mode == 'L': # Grayscale
            open_cv_image = np.array(image_pil)
            # Add a check to ensure it's treated as grayscale downstream if needed
        elif image_pil.mode == 'P': # Palette-based
            # Convert palette images to RGB first
            image_pil = image_pil.convert('RGB')
            open_cv_image = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        else:
             print(f"Warning: Unsupported PIL image mode '{image_pil.mode}'. Attempting direct conversion.")
             # Try direct conversion, might fail or be incorrect
             open_cv_image = np.array(image_pil)
             # If it has 3 channels, assume BGR, otherwise might need explicit handling
             if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] != 3:
                 print(f"Error: Conversion from mode '{image_pil.mode}' resulted in unexpected channels.")
                 return None

        # 2. Normalize (includes grayscale conversion)
        normalized = normalize_image(open_cv_image)

        # 3. Deskew (optional but recommended)
        # Deskewing might be applied before or after noise reduction/thresholding
        # Applying on normalized image is common
        # Use normalized image if deskewing is disabled or fails
        deskewed = deskew_image(normalized)
        # deskewed = normalized # Temporarily disable deskewing if causing issues

        # 4. Noise Reduction (Optional - can sometimes hurt OCR)
        # denoised = reduce_noise(deskewed)
        denoised = deskewed # Temporarily disable noise reduction

        # 5. Thresholding (Binarization - crucial for Tesseract)
        # Thresholding is often the final step before OCR
        binary = apply_thresholding(denoised)
        # binary = denoised # Use grayscale if thresholding causes issues

        # Final check: Ensure the output is a 2D NumPy array (grayscale/binary)
        if len(binary.shape) != 2:
             print("Warning: Preprocessing output is not a 2D array. Attempting grayscale conversion.")
             if len(binary.shape) == 3:
                 binary = cv2.cvtColor(binary, cv2.COLOR_BGR2GRAY)
             else:
                  print("Error: Cannot convert preprocessed image to grayscale.")
                  return None # Indicate failure

        return binary

    except Exception as e:
        print(f"Error during image preprocessing: {e}")
        # Optionally log the full traceback
        import traceback
        print(traceback.format_exc())
        return None # Indicate failure

# Example Usage (optional)
if __name__ == '__main__':
    import sys
    from src.image_loader import load_image # Assuming image_loader.py is in src

    if len(sys.argv) < 2:
        print("Usage: python preprocessing.py <image_path> [output_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Loading image: {input_path}")
    pil_image = load_image(input_path)

    if pil_image:
        print("Preprocessing image...")
        preprocessed = preprocess_image(pil_image)

        if preprocessed is not None:
            print("Preprocessing successful.")
            # Display the preprocessed image (requires GUI environment)
            try:
                cv2.imshow('Preprocessed Image', preprocessed)
                print("Press any key to close the image window.")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except cv2.error as e:
                 print(f"Could not display image (likely no GUI available): {e}")

            # Save the preprocessed image if an output path is provided
            if output_path:
                try:
                    cv2.imwrite(output_path, preprocessed)
                    print(f"Preprocessed image saved to: {output_path}")
                except Exception as e:
                    print(f"Error saving preprocessed image: {e}")
        else:
            print("Preprocessing failed.")
    else:
        print(f"Failed to load image {input_path}.") 