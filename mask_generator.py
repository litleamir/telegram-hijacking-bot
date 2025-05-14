import cv2
import numpy as np
from PIL import Image

def create_smart_mask(image_path, output_path=None):
    """
    Create a smart mask for watermark detection using image processing techniques.
    
    Args:
        image_path: Path to the input image
        output_path: Optional path to save the mask
    
    Returns:
        mask: numpy array of the mask
    """
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Dilate the mask to ensure we cover the entire watermark
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    # If output path is provided, save the mask
    if output_path:
        cv2.imwrite(output_path, mask)
    
    return mask

def create_mask_from_watermark(image_path, watermark_color_threshold=200, output_path=None):
    """
    Create a mask based on watermark color intensity.
    
    Args:
        image_path: Path to the input image
        watermark_color_threshold: Threshold for watermark color (0-255)
        output_path: Optional path to save the mask
    
    Returns:
        mask: numpy array of the mask
    """
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Create mask based on color intensity
    mask = np.zeros_like(gray)
    mask[gray > watermark_color_threshold] = 255
    
    # Apply morphological operations
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # If output path is provided, save the mask
    if output_path:
        cv2.imwrite(output_path, mask)
    
    return mask

def combine_masks(mask1, mask2):
    """
    Combine two masks using logical OR operation.
    
    Args:
        mask1: First mask
        mask2: Second mask
    
    Returns:
        Combined mask
    """
    return cv2.bitwise_or(mask1, mask2)

if __name__ == "__main__":
    # Example usage
    image_path = "test_image.jpg"
    
    # Create mask using edge detection
    mask1 = create_smart_mask(image_path, "mask1.jpg")
    
    # Create mask using color thresholding
    mask2 = create_mask_from_watermark(image_path, 200, "mask2.jpg")
    
    # Combine masks
    final_mask = combine_masks(mask1, mask2)
    cv2.imwrite("final_mask.jpg", final_mask) 