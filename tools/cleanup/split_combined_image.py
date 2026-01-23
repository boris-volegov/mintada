import torch
import cv2
import numpy as np
import os
import glob
from pathlib import Path
from PIL import Image
import segmentation_models_pytorch as smp
import torchvision.transforms as T

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(SCRIPT_DIR, "work")
INPUT_DIR = os.path.join(WORK_DIR, "input")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
MODEL_PATH = os.path.join(SCRIPT_DIR, "best_coin_unet_resnet34.pth")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 256
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# --- 1. The Segmentation Class (Unchanged from your file) ---
class CoinSegmentor:
    def __init__(self, model_path):
        print(f"Loading Model...")
        self.model = smp.Unet(encoder_name="resnet34", in_channels=3, classes=1).to(DEVICE)
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=DEVICE))
        else:
            raise FileNotFoundError(f"Model not found at {model_path}")
        self.model.eval()
        self.transform = T.Compose([
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

    def get_mask(self, original_pil_image):
        w, h = original_pil_image.size
        input_tensor = self.transform(original_pil_image).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = self.model(input_tensor)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            mask_small = (prob > 0.5).astype(np.uint8)
        return cv2.resize(mask_small, (w, h), interpolation=cv2.INTER_NEAREST) * 255

# --- 2. The Stitch Line Finder (Helper) ---
def find_stitch_line(img_cv, search_start_x, search_end_x):
    """
    Looks for a vertical line artifact strictly within the given X-range.
    """
    if search_end_x <= search_start_x:
        return None

    # Crop to the search window
    roi = img_cv[:, search_start_x:search_end_x]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Sobel X (Vertical Edges)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    abs_sobelx = np.absolute(sobelx)
    
    # Vertical Projection (Sum columns)
    col_sums = np.sum(abs_sobelx, axis=0)

    max_val = np.max(col_sums)
    mean_val = np.mean(col_sums)

    # Threshold: The line must be significantly stronger (3x) than average noise
    if max_val > (mean_val * 3.0):
        # Return global X coordinate
        best_col_relative = np.argmax(col_sums)
        return search_start_x + best_col_relative
    
    return None

# --- 3. The Logic ---
def split_image_smart(image_path, segmentor, output_dir):
    filename = os.path.basename(image_path)
    file_id = Path(filename).stem
    print(f"\nProcessing ID: {file_id}...")

    try:
        pil_img = Image.open(image_path).convert("RGB")
        img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        img_h, img_w, _ = img_cv.shape
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # --- STEP A: Segmentation (Exactly as previous_split.py) ---
    mask = segmentor.get_mask(pil_img)
    kernel = np.ones((15, 15), np.uint8)
    eroded_mask = cv2.erode(mask, kernel, iterations=2)
    contours, _ = cv2.findContours(eroded_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    img_area = img_h * img_w
    valid_contours = [c for c in contours if cv2.contourArea(c) > (img_area * 0.05)]
    valid_contours.sort(key=lambda c: cv2.boundingRect(c)[0])

    # Calculate the "Rough" Split Point from Segmentation
    segmentation_split_x = img_w // 2 # Default fallback

    if len(valid_contours) >= 2:
        print("  Strategy: Found 2 separate coins (Segmentation).")
        x1, y1, w1, h1 = cv2.boundingRect(valid_contours[0])
        x2, y2, w2, h2 = cv2.boundingRect(valid_contours[1])
        
        left_coin_end = x1 + w1
        right_coin_start = x2
        segmentation_split_x = (left_coin_end + right_coin_start) // 2
    
    elif len(valid_contours) == 1:
        print("  Strategy: Found 1 giant blob (Segmentation).")
        x, y, w, h = cv2.boundingRect(valid_contours[0])
        segmentation_split_x = x + (w // 2)
    
    else:
        print("  Warning: No coins found. Fallback to center.")

    # --- STEP B: Refinement (The "Within 5%" Logic) ---
    # We define a narrow search window around the segmentation candidate.
    tolerance_pixels = int(img_w * 0.05) # 5% of width
    
    search_start = max(0, segmentation_split_x - tolerance_pixels)
    search_end = min(img_w, segmentation_split_x + tolerance_pixels)
    
    print(f"  -> Refining split near x={segmentation_split_x} (Window: {search_start}-{search_end})...")

    stitch_x = find_stitch_line(img_cv, search_start, search_end)

    if stitch_x:
        print(f"  -> SUCCESS: Snapped to visible stitch line at x={stitch_x}")
        final_split_x = stitch_x
    else:
        print(f"  -> No stitch line found nearby. Using segmentation split x={segmentation_split_x}")
        final_split_x = segmentation_split_x

    # --- STEP C: Save ---
    obverse_img = img_cv[:, :final_split_x]
    reverse_img = img_cv[:, final_split_x:]

    path_obv = os.path.join(output_dir, f"{file_id}_obverse.jpg")
    path_rev = os.path.join(output_dir, f"{file_id}_reverse.jpg")

    cv2.imwrite(path_obv, obverse_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    cv2.imwrite(path_rev, reverse_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    
    print(f"  - Saved: {os.path.basename(path_obv)}")
    print(f"  - Saved: {os.path.basename(path_rev)}")

def main():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        segmentor = CoinSegmentor(MODEL_PATH)
    except Exception as e:
        print(f"Model Error: {e}")
        print("Ensure 'best_coin_unet_resnet34.pth' is in the script folder.")
        return

    image_files = glob.glob(os.path.join(INPUT_DIR, "*.*"))
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        print(f"No images found in {INPUT_DIR}"); return

    for img_path in image_files:
        split_image_smart(img_path, segmentor, OUTPUT_DIR)

if __name__ == "__main__":
    main()