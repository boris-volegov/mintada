import torch
from PIL import Image
import numpy as np
import torchvision.transforms as T
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 256

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ------------------------------------------
# 1. Load model
# ------------------------------------------

model = smp.Unet(
    encoder_name="resnet34",
    encoder_weights=None,
    in_channels=3,
    classes=1,
).to(device)

model.load_state_dict(torch.load("best_coin_unet_resnet34.pth", map_location=device))
model.eval()

# ------------------------------------------
# 2. Prepare transforms
# ------------------------------------------

transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

# ------------------------------------------
# 3. Load and predict
# ------------------------------------------

IMAGE_PATH = "c:\\projects\\mintada\\segmentation\\dataset\\test\\assam-1-8-rupee-1818.jpg"  # replace with your image path

img = Image.open(IMAGE_PATH).convert("RGB")
input_tensor = transform(img).unsqueeze(0).to(device)

with torch.no_grad():
    logits = model(input_tensor)
    prob = torch.sigmoid(logits)[0, 0].cpu().numpy()   # (H, W)
    mask = (prob > 0.5).astype(np.uint8)               # binary mask 0/1

# ------------------------------------------
# 4. Visualize
# ------------------------------------------

plt.figure(figsize=(12, 4))

# Original image (resized)
plt.subplot(1, 3, 1)
plt.title("Original (resized)")
plt.imshow(img.resize((IMG_SIZE, IMG_SIZE)))
plt.axis("off")

# Probability map
plt.subplot(1, 3, 2)
plt.title("Predicted Probability")
plt.imshow(prob, cmap="viridis")
plt.colorbar()
plt.axis("off")

# Binary mask
plt.subplot(1, 3, 3)
plt.title("Binary Mask (0/1)")
plt.imshow(mask, cmap="gray")
plt.axis("off")

plt.tight_layout()
plt.show()

# ------------------------------------------
# 5. (Optional) Save mask image
# ------------------------------------------

mask_img = Image.fromarray((mask * 255).astype(np.uint8))
mask_img.save("mask_output.png")
print("Saved mask to mask_output.png")
