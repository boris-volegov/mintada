import torch
import cv2
import numpy as np
import easyocr
import segmentation_models_pytorch as smp
import torchvision.transforms as T
from PIL import Image
import os

# --- Configuration ---
MODEL_PATH = "best_coin_unet_resnet34.pth" # Your trained model
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 256 # The size your model expects

# ImageNet stats for normalization (matches your training)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

class CoinSegmentor:
    def __init__(self, model_path):
        print("Loading Segmentation Model...")
        self.model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        ).to(DEVICE)
        
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
        """
        Returns a binary mask (0 or 255) of the coin, 
        resized to match the ORIGINAL image dimensions.
        """
        w, h = original_pil_image.size
        
        # Transform for model
        input_tensor = self.transform(original_pil_image).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            logits = self.model(input_tensor)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            mask_small = (prob > 0.5).astype(np.uint8)

        # Resize mask back to original image size
        # cv2.resize expects (width, height)
        mask_original_size = cv2.resize(
            mask_small, 
            (w, h), 
            interpolation=cv2.INTER_NEAREST
        )
        
        return mask_original_size * 255 # Scale to 0-255

def remove_background_text(image_path, segmentor, reader, output_path):
    print(f"Processing: {os.path.basename(image_path)}")
    
    # 1. Load Image
    try:
        pil_img = Image.open(image_path).convert("RGB")
        # Convert to BGR for OpenCV processing
        img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Error loading image: {e}")
        return

    # 2. Get Coin Mask (Protected Area)
    coin_mask = segmentor.get_mask(pil_img)
    
    # Dilate the coin mask slightly to create a safety buffer.
    # We don't want to accidentally inpaint the very edge of the coin.
    kernel = np.ones((5, 5), np.uint8)
    coin_mask_dilated = cv2.dilate(coin_mask, kernel, iterations=3)

    # 3. Detect Text using OCR
    print("  - Detecting text...")
    # Read text returns [(bbox, text, prob), ...]
    results = reader.readtext(img_cv)

    if not results:
        print("  - No text detected.")
        return

    # 4. Create Text Mask
    text_mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)
    
    for (bbox, text, prob) in results:
        # bbox is a list of 4 points [[x,y], [x,y], [x,y], [x,y]]
        tl, tr, br, bl = bbox
        
        # Convert points to integer for OpenCV
        pts = np.array([tl, tr, br, bl], dtype=np.int32)
        
        # Draw the text box onto the mask
        cv2.fillPoly(text_mask, [pts], 255)

    # 5. Filter Text Mask: Only remove text NOT inside the coin
    # Logic: Text_Mask AND (NOT Coin_Mask)
    # If text overlaps the coin, this removes that part from the deletion mask
    background_text_mask = cv2.bitwise_and(text_mask, text_mask, mask=cv2.bitwise_not(coin_mask_dilated))

    # Dilate the text mask slightly to ensure we catch the pixel edges of the letters
    background_text_mask = cv2.dilate(background_text_mask, kernel, iterations=2)

    # 6. Inpaint (Erase Text)
    # Radius 3 is usually good for text. INPAINT_TELEA is generally faster/smoother.
    if np.count_nonzero(background_text_mask) > 0:
        print("  - Removing text...")
        cleaned_img = cv2.inpaint(img_cv, background_text_mask, 3, cv2.INPAINT_TELEA)
        
        # Save
        cv2.imwrite(output_path, cleaned_img)
        print(f"  - Saved to {output_path}")
    else:
        print("  - Text detected, but it was inside the coin boundaries. No changes made.")

def main():
    # --- Setup ---
    WORK_DIR = "work"
    INPUT_DIR = os.path.join(WORK_DIR, "input")
    OUTPUT_DIR = os.path.join(WORK_DIR, "output")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Initialize Models (Loaded once)
    try:
        segmentor = CoinSegmentor(MODEL_PATH)
        # Initialize EasyOCR Reader (English). Add other languages if needed ['en', 'fr']
        print("Loading OCR Model...")
        reader = easyocr.Reader(['en'], gpu=(torch.cuda.is_available()))
    except Exception as e:
        print(f"Initialization Failed: {e}")
        return

    # 2. Process Images
    extensions = ['*.jpg', '*.jpeg', '*.png']
    import glob
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(INPUT_DIR, ext)))

    for file_path in files:
        filename = os.path.basename(file_path)
        output_path = os.path.join(OUTPUT_DIR, f"cleaned_{filename}")
        
        remove_background_text(file_path, segmentor, reader, output_path)

if __name__ == "__main__":
    main()