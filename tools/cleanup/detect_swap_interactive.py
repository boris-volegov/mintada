import sys
import json
import torch
import torch.nn as nn
import torchvision.transforms as T
import torchvision.models as models
import segmentation_models_pytorch as smp
import numpy as np
from PIL import Image
import os

# -----------------------------
# Configuration & Helpers
# ImageNet stats
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

SEG_IMG_SIZE = 256
EMB_IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

seg_transform = T.Compose([
    T.Resize((SEG_IMG_SIZE, SEG_IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

emb_transform = T.Compose([
    T.Resize((EMB_IMG_SIZE, EMB_IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

def load_segmentation_model(seg_model_path: str):
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None, 
        in_channels=3,
        classes=1,
    )
    # Ensure file exists
    if not os.path.exists(seg_model_path):
        raise FileNotFoundError(f"Model not found: {seg_model_path}")
        
    state = torch.load(seg_model_path, map_location="cpu")
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

def load_feature_extractor():
    # Use standard resnet18
    # We set pretrained=True, but downloading might fail if no internet? 
    # Usually it's cached.
    resnet = models.resnet18(pretrained=True)
    backbone = nn.Sequential(*list(resnet.children())[:-1])
    for p in backbone.parameters():
        p.requires_grad = False
    backbone.to(DEVICE)
    backbone.eval()
    return backbone

def segment_and_crop(image_path: str, seg_model) -> torch.Tensor:
    img = Image.open(image_path).convert("RGB")
    img_resized = img.resize((SEG_IMG_SIZE, SEG_IMG_SIZE), resample=Image.BILINEAR)

    x = seg_transform(img_resized).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = seg_model(x)
        prob = torch.sigmoid(logits)[0, 0].cpu().numpy()

    mask = prob > 0.5

    if mask.sum() == 0:
        y_min, y_max = 0, SEG_IMG_SIZE - 1
        x_min, x_max = 0, SEG_IMG_SIZE - 1
    else:
        ys, xs = np.where(mask)
        y_min, y_max = ys.min(), ys.max()
        x_min, x_max = xs.min(), xs.max()

        margin = 5
        y_min = max(y_min - margin, 0)
        y_max = min(y_max + margin, SEG_IMG_SIZE - 1)
        x_min = max(x_min - margin, 0)
        x_max = min(x_max + margin, SEG_IMG_SIZE - 1)

    img_np = np.array(img_resized)
    mask_3 = np.stack([mask] * 3, axis=-1)
    img_np_masked = img_np.copy()
    img_np_masked[~mask_3] = 0

    img_masked = Image.fromarray(img_np_masked)
    crop = img_masked.crop((x_min, y_min, x_max + 1, y_max + 1))

    crop_resized = emb_transform(crop)
    return crop_resized

def get_embedding(tensor_img: torch.Tensor, backbone) -> torch.Tensor:
    with torch.no_grad():
        x = tensor_img.unsqueeze(0).to(DEVICE)
        feat = backbone(x)
        feat = feat.view(feat.size(0), -1)
    return feat[0]

def cosine_similarity(a: torch.Tensor, b: torch.Tensor) -> float:
    a = a / (a.norm(p=2) + 1e-8)
    b = b / (b.norm(p=2) + 1e-8)
    return float((a * b).sum().item())

def main():
    # Attempt to locate model file in current directory
    model_path = os.path.join(os.path.dirname(__file__), "best_coin_unet_resnet34.pth")
    
    try:
        seg_model = load_segmentation_model(model_path)
        backbone = load_feature_extractor()
        print("READY", flush=True)
    except Exception as e:
        # If failure, print error but don't crash yet
        print(f"INIT_ERROR: {e}", flush=True)
        return

    for line in sys.stdin:
        try:
            line = line.strip()
            if not line: continue
            data = json.loads(line)
            
            ref_obv = data.get('ref_obv')
            ref_rev = data.get('ref_rev')
            cand_obv = data.get('cand_obv')
            cand_rev = data.get('cand_rev')
            
            if not (ref_obv and ref_rev and cand_obv and cand_rev):
                 print(json.dumps({"is_flip": False, "error": "Missing input paths"}), flush=True)
                 continue

            # Check files exist
            missing_files = [p for p in [ref_obv, ref_rev, cand_obv, cand_rev] if not os.path.exists(p)]
            if missing_files:
                 print(json.dumps({"is_flip": False, "error": f"Files not found: {missing_files}"}), flush=True)
                 continue

            ref_obv_img = segment_and_crop(ref_obv, seg_model)
            ref_rev_img = segment_and_crop(ref_rev, seg_model)
            cand_obv_img = segment_and_crop(cand_obv, seg_model)
            cand_rev_img = segment_and_crop(cand_rev, seg_model)
            
            ref_obv_emb = get_embedding(ref_obv_img, backbone)
            ref_rev_emb = get_embedding(ref_rev_img, backbone)
            cand_obv_emb = get_embedding(cand_obv_img, backbone)
            cand_rev_emb = get_embedding(cand_rev_img, backbone)
            
            # Scores
            # Correct: CandObv ~ RefObv AND CandRev ~ RefRev
            s1_obv = cosine_similarity(cand_obv_emb, ref_obv_emb)
            s2_rev = cosine_similarity(cand_rev_emb, ref_rev_emb)
            correct_score = s1_obv + s2_rev
            
            # Swapped: CandObv ~ RefRev AND CandRev ~ RefObv
            s1_rev = cosine_similarity(cand_obv_emb, ref_rev_emb)
            s2_obv = cosine_similarity(cand_rev_emb, ref_obv_emb)
            swapped_score = s1_rev + s2_obv
            
            # Determination
            margin = 0.0
            is_flip = swapped_score > (correct_score + margin)
            
            print(json.dumps({
                "is_flip": is_flip, 
                "swapped_score": swapped_score, 
                "correct_score": correct_score,
                "debug": f"OO:{s1_obv:.3f} RR:{s2_rev:.3f} | OR:{s1_rev:.3f} RO:{s2_obv:.3f}"
            }), flush=True)
            
        except Exception as e:
            print(json.dumps({"is_flip": False, "error": str(e)}), flush=True)

if __name__ == "__main__":
    main()
