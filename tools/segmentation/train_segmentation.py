import os
from glob import glob

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from PIL import Image

import torchvision.transforms as T
from torchvision.transforms import InterpolationMode

import segmentation_models_pytorch as smp

# ----------------------------
# 1. Config
# ----------------------------

DATASET_ROOT = "dataset"  # contains "images" and "masks"
IMAGE_DIR = os.path.join(DATASET_ROOT, "images")
MASK_DIR = os.path.join(DATASET_ROOT, "masks")

IMG_SIZE = 256          # images/masks resized to (256, 256)
BATCH_SIZE = 4
NUM_EPOCHS = 30
LR = 1e-3
VAL_SPLIT = 0.2
LAMBDA_DICE = 0.5       # weight for dice loss

NUM_WORKERS = 2         # set to 0 on Windows if you get dataloader issues

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", DEVICE)

# ImageNet normalization (because encoder is ImageNet-pretrained)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# ----------------------------
# 2. Dataset
# ----------------------------

class CoinSegmentationDataset(Dataset):
    def __init__(self, images_dir, masks_dir, img_size=256, augment=False):
        self.images_dir = images_dir
        self.masks_dir = masks_dir
        self.img_size = img_size
        self.augment = augment
        self.mask_exts = [".png", ".jpg", ".jpeg"]  # add more if needed

        self.image_paths = sorted(glob(os.path.join(images_dir, "*.*")))
        if len(self.image_paths) == 0:
            raise RuntimeError(f"No images found in {images_dir}")

        # base transforms (resize + to tensor + normalize for images)
        self.img_base = T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

        self.mask_base = T.Compose([
            T.Resize((img_size, img_size), interpolation=InterpolationMode.NEAREST),
            T.ToTensor(),  # 0..1
        ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        filename = os.path.basename(img_path)
        stem, _ = os.path.splitext(filename)

        # --- NEW: search for a matching mask with common extensions ---
        mask_path = None
        for ext in self.mask_exts:
            candidate = os.path.join(self.masks_dir, stem + ext)
            if os.path.exists(candidate):
                mask_path = candidate
                break

        if mask_path is None:
            raise RuntimeError(f"Mask not found for image {filename} (searched {self.mask_exts})")

        # load as before
        img = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        # optional simple augmentations (on PIL before ToTensor)
        if self.augment:
            # random horizontal flip
            if torch.rand(1).item() < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                mask = mask.transpose(Image.FLIP_LEFT_RIGHT)
            # random vertical flip
            if torch.rand(1).item() < 0.2:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                mask = mask.transpose(Image.FLIP_TOP_BOTTOM)

        img = self.img_base(img)
        mask = self.mask_base(mask)

        mask = (mask > 0).float()

        return img, mask

# ----------------------------
# 3. Loss function: BCE + Dice
# ----------------------------

def dice_loss_from_logits(pred, target, epsilon=1e-6):
    """
    pred: raw logits, shape (B, 1, H, W)
    target: binary masks, shape (B, 1, H, W)
    """
    prob = torch.sigmoid(pred)
    # flatten per sample
    prob = prob.view(prob.size(0), -1)
    target = target.view(target.size(0), -1)

    intersection = (prob * target).sum(dim=1)
    union = prob.sum(dim=1) + target.sum(dim=1)

    dice = (2 * intersection + epsilon) / (union + epsilon)
    return 1 - dice.mean()


# ----------------------------
# 4. Training / validation loops
# ----------------------------

def train_one_epoch(model, loader, optimizer, bce_loss_fn):
    model.train()
    total_loss = 0.0

    for imgs, masks in loader:
        imgs = imgs.to(DEVICE)
        masks = masks.to(DEVICE)

        preds = model(imgs)  # (B, 1, H, W) logits

        bce = bce_loss_fn(preds, masks)
        dsc = dice_loss_from_logits(preds, masks)
        loss = bce + LAMBDA_DICE * dsc

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * imgs.size(0)

    return total_loss / len(loader.dataset)


def validate(model, loader, bce_loss_fn):
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for imgs, masks in loader:
            imgs = imgs.to(DEVICE)
            masks = masks.to(DEVICE)

            preds = model(imgs)
            bce = bce_loss_fn(preds, masks)
            dsc = dice_loss_from_logits(preds, masks)
            loss = bce + LAMBDA_DICE * dsc

            total_loss += loss.item() * imgs.size(0)

    return total_loss / len(loader.dataset)


# ----------------------------
# 5. Main training entry
# ----------------------------

def main():
    # full dataset
    full_dataset = CoinSegmentationDataset(
        IMAGE_DIR,
        MASK_DIR,
        img_size=IMG_SIZE,
        augment=True,   # enable simple flips; helps with small dataset
    )

    # train/val split
    val_size = int(len(full_dataset) * VAL_SPLIT)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # for validation, you may want to disable augmentations:
    # but since we applied augmentations inside dataset init, we’ll just reuse:
    # simplest approach for now: use same dataset object split (augment only affects training, practically)

    print(f"Total images: {len(full_dataset)}")
    print(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}")

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
    )

    # model: U-Net with ResNet34 encoder pretrained on ImageNet
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1,          # binary segmentation
    ).to(DEVICE)

    bce_loss_fn = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_val_loss = float("inf")

    for epoch in range(1, NUM_EPOCHS + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, bce_loss_fn)
        val_loss = validate(model, val_loader, bce_loss_fn)

        print(f"Epoch {epoch:02d}/{NUM_EPOCHS} "
              f"- train_loss: {train_loss:.4f}  val_loss: {val_loss:.4f}")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), "best_coin_unet_resnet34.pth")
            print("  -> Saved new best model")

    print("Training finished. Best val loss:", best_val_loss)


if __name__ == "__main__":
    main()
