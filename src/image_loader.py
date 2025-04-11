from PIL import Image
import io
import pillow_heif

# Register the HEIF plugin with Pillow
pillow_heif.register_heif_opener()

def load_image(image_path):
    """Load an image file using Pillow.

    Args:
        image_path (str): The path to the image file.

    Returns:
        PIL.Image.Image or None: The loaded image object, or None if loading fails.
    """
    try:
        # Open the image file
        img = Image.open(image_path)
        # It's good practice to load the image data right away
        # This catches potential file corruption errors early
        img.load()
        return img
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        # Catch other PIL-related errors (corrupt file, unsupported format, etc.)
        print(f"Error loading image {image_path}: {e}")
        return None

# Example Usage (optional)
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python image_loader.py <image_path>")
        sys.exit(1)

    img_file = sys.argv[1]
    print(f"Attempting to load image: {img_file}")
    image_object = load_image(img_file)

    if image_object:
        print(f"Successfully loaded image:")
        print(f"- Format: {image_object.format}")
        print(f"- Size: {image_object.size}")
        print(f"- Mode: {image_object.mode}")
        # You can optionally display the image if you have a viewer configured
        # image_object.show()
    else:
        print("Failed to load image.") 