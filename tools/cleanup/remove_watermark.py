"""
Watermark/Text Removal Tool for Coin Images

This CLI tool removes watermark text from coin images using:
1. U-Net segmentation to detect the coin area
2. EasyOCR to detect text regions
3. Average background color filling to remove text

Designed for easy integration with C# desktop applications.

Usage:
    python remove_watermark.py --input <path> --output <path> [options]

Example:
    python remove_watermark.py --input coin.jpg --output cleaned.jpg --bottom-only
"""

import os
import sys
import argparse
import numpy as np
from PIL import Image
import cv2
import torch
import torchvision.transforms as T
import segmentation_models_pytorch as smp
import easyocr

# Configuration
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 256  # Size expected by segmentation model

class CoinSegmentor:
    """Handles coin segmentation using U-Net model."""
    
    def __init__(self, model_path, device):
        """
        Initialize the segmentation model.
        
        Args:
            model_path: Path to the trained model file
            device: torch device (cuda or cpu)
        """
        print(f"Loading segmentation model from: {model_path}")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")
        
        self.device = device
        self.model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        ).to(device)
        
        self.model.load_state_dict(torch.load(model_path, map_location=device))
        self.model.eval()
        
        self.transform = T.Compose([
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
        
        print("Segmentation model loaded successfully")
    
    def get_mask(self, pil_image):
        """
        Get binary segmentation mask for the coin.
        
        Args:
            pil_image: PIL Image in RGB format
            
        Returns:
            numpy array (H, W) with values 0 or 255
        """
        original_size = pil_image.size  # (width, height)
        
        # Transform and predict
        input_tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logits = self.model(input_tensor)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            mask_small = (prob > 0.5).astype(np.uint8)
        
        # Resize mask back to original image size
        mask_original = cv2.resize(
            mask_small,
            original_size,
            interpolation=cv2.INTER_NEAREST
        )
        
        return mask_original * 255


class TextDetector:
    """Handles text detection using EasyOCR."""
    
    def __init__(self, use_gpu=True):
        """
        Initialize the OCR reader.
        
        Args:
            use_gpu: Whether to use GPU for OCR
        """
        print("Loading OCR model (this may take a moment)...")
        self.reader = easyocr.Reader(['en'], gpu=use_gpu)
        print("OCR model loaded successfully")
    
    def detect_text_regions(self, image_np, bottom_only=False, bottom_fraction=0.2):
        """
        Detect text regions in the image.
        
        Args:
            image_np: numpy array (H, W, 3) in BGR format
            bottom_only: If True, only detect text in bottom portion
            bottom_fraction: Fraction of image height to consider as "bottom"
            
        Returns:
            List of bounding boxes [(x1,y1,x2,y2), ...]
        """
        h, w = image_np.shape[:2]
        
        # If bottom_only, crop the image
        if bottom_only:
            crop_y = int(h * (1 - bottom_fraction))
            image_to_scan = image_np[crop_y:, :, :]
            y_offset = crop_y
        else:
            image_to_scan = image_np
            y_offset = 0
        
        # Detect text
        results = self.reader.readtext(image_to_scan)
        
        # Convert to bounding boxes
        bboxes = []
        for (bbox, text, prob) in results:
            # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            points = np.array(bbox, dtype=np.int32)
            
            # Get bounding rectangle
            x_min = points[:, 0].min()
            x_max = points[:, 0].max()
            y_min = points[:, 1].min() + y_offset
            y_max = points[:, 1].max() + y_offset
            
            bboxes.append((x_min, y_min, x_max, y_max))
            print(f"  Detected text: '{text}' (confidence: {prob:.2f})")
        
        return bboxes


def create_text_mask(image_shape, bboxes, dilate_pixels=5):
    """
    Create a binary mask for text regions.
    
    Args:
        image_shape: (height, width) of the image
        bboxes: List of bounding boxes [(x1,y1,x2,y2), ...]
        dilate_pixels: Number of pixels to dilate the mask
        
    Returns:
        numpy array (H, W) with values 0 or 255
    """
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Draw all text boxes
    for (x1, y1, x2, y2) in bboxes:
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    
    # Dilate to ensure complete coverage
    if dilate_pixels > 0:
        kernel = np.ones((dilate_pixels, dilate_pixels), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
    
    return mask


def calculate_background_color(image_np, coin_mask, text_mask):
    """
    Calculate average background color (excluding coin and text).
    
    Args:
        image_np: numpy array (H, W, 3) in BGR format
        coin_mask: binary mask (H, W) with 255 for coin
        text_mask: binary mask (H, W) with 255 for text
        
    Returns:
        tuple (B, G, R) average color
    """
    # Create mask for background (neither coin nor text)
    background_mask = np.logical_and(coin_mask == 0, text_mask == 0)
    
    if not background_mask.any():
        # Fallback: use white
        print("  Warning: No background pixels found, using white")
        return (255, 255, 255)
    
    # Calculate mean color
    bg_pixels = image_np[background_mask]
    avg_color = bg_pixels.mean(axis=0)
    
    return tuple(avg_color.astype(np.uint8))


def remove_watermark(input_path, output_path, model_path, bottom_only=False,
                     dilate_coin=10, dilate_text=5, shrink_coin=0, debug=False):
    """
    Main function to remove watermark from coin image.
    
    Args:
        input_path: Path to input image
        output_path: Path to save cleaned image
        model_path: Path to segmentation model
        bottom_only: Only detect text in bottom 20% of image
        dilate_coin: Pixels to dilate coin mask (safety buffer, ignored if shrink_coin > 0)
        dilate_text: Pixels to dilate text mask (complete removal)
        shrink_coin: Pixels to erode/shrink coin mask (for text very close to coin)
        debug: Save intermediate masks for debugging
    """
    print(f"\nProcessing: {input_path}")
    
    # Check input file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Initialize models
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    segmentor = CoinSegmentor(model_path, device)
    detector = TextDetector(use_gpu=torch.cuda.is_available())
    
    # Load image
    print("Loading image...")
    pil_image = Image.open(input_path).convert("RGB")
    image_np = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    # Get coin mask
    print("Segmenting coin...")
    coin_mask = segmentor.get_mask(pil_image)
    
    # Modify coin mask: shrink if requested, otherwise dilate for safety buffer
    if shrink_coin > 0:
        # Shrink coin mask to allow text removal near coin edges
        kernel = np.ones((shrink_coin, shrink_coin), np.uint8)
        coin_mask_modified = cv2.erode(coin_mask, kernel, iterations=1)
        print(f"  Shrinking coin mask by {shrink_coin} pixels")
    elif dilate_coin > 0:
        # Dilate coin mask for safety buffer
        kernel = np.ones((dilate_coin, dilate_coin), np.uint8)
        coin_mask_modified = cv2.dilate(coin_mask, kernel, iterations=1)
        print(f"  Dilating coin mask by {dilate_coin} pixels")
    else:
        coin_mask_modified = coin_mask
    
    # Detect text
    print("Detecting text...")
    text_bboxes = detector.detect_text_regions(image_np, bottom_only=bottom_only)
    
    if not text_bboxes:
        print("No text detected. Saving original image.")
        cv2.imwrite(output_path, image_np)
        return
    
    print(f"Found {len(text_bboxes)} text region(s)")
    
    # Create text mask
    text_mask = create_text_mask(image_np.shape, text_bboxes, dilate_text)
    
    # Filter: only keep text outside the coin
    text_mask_filtered = cv2.bitwise_and(
        text_mask,
        text_mask,
        mask=cv2.bitwise_not(coin_mask_modified)
    )
    
    # Check if any text remains after filtering
    if np.count_nonzero(text_mask_filtered) == 0:
        print("All detected text is on the coin. No removal needed.")
        cv2.imwrite(output_path, image_np)
        return
    
    # Calculate background color
    print("Calculating background color...")
    bg_color = calculate_background_color(image_np, coin_mask_modified, text_mask_filtered)
    print(f"  Background color (BGR): {bg_color}")
    
    # Fill text regions with background color
    print("Removing text...")
    result = image_np.copy()
    result[text_mask_filtered > 0] = bg_color
    
    # Save result
    cv2.imwrite(output_path, result)
    print(f"Saved cleaned image to: {output_path}")
    
    # Save debug images if requested
    if debug:
        debug_dir = os.path.dirname(output_path) or "."
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        
        cv2.imwrite(os.path.join(debug_dir, f"{base_name}_debug_coin_mask.png"), coin_mask)
        cv2.imwrite(os.path.join(debug_dir, f"{base_name}_debug_text_mask.png"), text_mask)
        cv2.imwrite(os.path.join(debug_dir, f"{base_name}_debug_text_filtered.png"), text_mask_filtered)
        print(f"Debug masks saved to: {debug_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Remove watermark text from coin images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python remove_watermark.py --input coin.jpg --output cleaned.jpg
  python remove_watermark.py --input coin.jpg --output cleaned.jpg --bottom-only
  python remove_watermark.py --input coin.jpg --output cleaned.jpg --debug
        """
    )
    
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument(
        "--model-path",
        default=None,
        help="Path to segmentation model (default: ../segmentation/best_coin_unet_resnet34.pth)"
    )
    parser.add_argument(
        "--bottom-only",
        action="store_true",
        help="Only detect text in bottom 20%% of image (faster)"
    )
    parser.add_argument(
        "--dilate-coin",
        type=int,
        default=10,
        help="Pixels to dilate coin mask (safety buffer, default: 10, ignored if --shrink-coin is used)"
    )
    parser.add_argument(
        "--shrink-coin",
        type=int,
        default=0,
        help="Pixels to shrink coin mask (for text very close to coin edge, default: 0)"
    )
    parser.add_argument(
        "--dilate-text",
        type=int,
        default=5,
        help="Pixels to dilate text mask (complete removal, default: 5)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save intermediate masks for debugging"
    )
    
    args = parser.parse_args()
    
    # Determine model path
    if args.model_path:
        model_path = args.model_path
    else:
        # Default: ../segmentation/best_coin_unet_resnet34.pth relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, "..", "segmentation", "best_coin_unet_resnet34.pth")
    
    try:
        remove_watermark(
            input_path=args.input,
            output_path=args.output,
            model_path=model_path,
            bottom_only=args.bottom_only,
            dilate_coin=args.dilate_coin,
            dilate_text=args.dilate_text,
            shrink_coin=args.shrink_coin,
            debug=args.debug
        )
        print("\n✓ Success!")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
