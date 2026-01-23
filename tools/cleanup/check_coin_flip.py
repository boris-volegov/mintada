import os
import argparse
import json
import torch
import numpy as np
from PIL import Image
import torchvision.transforms as T
import torchvision.models as models
import segmentation_models_pytorch as smp
import sys

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")

# Config matches detect_similarity_seg.py
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
SEG_IMG_SIZE = 256
EMB_IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Assuming model is in ../segmentation/ relative to this script or in a fixed known path.
# User said best_coin_unet_resnet34.pth is in tools\segmentation\
MODEL_PATH = os.path.join(SCRIPT_DIR, "..", "segmentation", "best_coin_unet_resnet34.pth")

if not os.path.exists(MODEL_PATH):
    # Fallback to local
    MODEL_PATH = "best_coin_unet_resnet34.pth"

# -----------------------------
# Transforms
# -----------------------------
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

# -----------------------------
# Models
# -----------------------------
def load_segmentation_model():
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=3,
        classes=1,
    )
    if os.path.exists(MODEL_PATH):
        state = torch.load(MODEL_PATH, map_location=DEVICE)
        model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

def load_feature_extractor():
    resnet = models.resnet18(pretrained=True)
    backbone = torch.nn.Sequential(*list(resnet.children())[:-1])
    for p in backbone.parameters():
        p.requires_grad = False
    backbone.to(DEVICE)
    backbone.eval()
    return backbone

# -----------------------------
# Logic
# -----------------------------
def segment_and_crop(image_path, seg_model):
    if not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGB")
        img_resized = img.resize((SEG_IMG_SIZE, SEG_IMG_SIZE), resample=Image.BILINEAR)
        x = seg_transform(img_resized).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            logits = seg_model(x)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            
        mask = (prob > 0.5).astype(np.uint8)
        
        if mask.sum() == 0:
            # Fallback: Use whole image
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
        img_np_masked[~mask_3] = 0 # Black background
        
        img_masked = Image.fromarray(img_np_masked)
        crop = img_masked.crop((x_min, y_min, x_max + 1, y_max + 1))
        return emb_transform(crop)
    except Exception:
        return None

def get_embedding(tensor_img, backbone):
    if tensor_img is None: return None
    with torch.no_grad():
        x = tensor_img.unsqueeze(0).to(DEVICE)
        feat = backbone(x)
        feat = feat.view(feat.size(0), -1)
    return feat[0]

def cosine_similarity(a, b):
    if a is None or b is None: return 0.0
    a = a / (a.norm(p=2) + 1e-8)
    b = b / (b.norm(p=2) + 1e-8)
    return float((a * b).sum().item())

def process_request(data, seg_model, backbone):
    # Data is dict with keys: ref_obv, ref_rev, cand_obv, cand_rev
    try:
        paths = [data.get("ref_obv"), data.get("ref_rev"), data.get("cand_obv"), data.get("cand_rev")]
        if not all(paths) or not all(os.path.exists(p) for p in paths):
             return {"error": "Files missing"}

        # Process Reference
        ref_obv_emb = get_embedding(segment_and_crop(paths[0], seg_model), backbone)
        ref_rev_emb = get_embedding(segment_and_crop(paths[1], seg_model), backbone)
        
        # Process Candidate
        cand_obv_emb = get_embedding(segment_and_crop(paths[2], seg_model), backbone)
        cand_rev_emb = get_embedding(segment_and_crop(paths[3], seg_model), backbone)
        
        if any(x is None for x in [ref_obv_emb, ref_rev_emb, cand_obv_emb, cand_rev_emb]):
             return {"error": "Failed to process images"}

        # Scores
        sim_oo = cosine_similarity(cand_obv_emb, ref_obv_emb)
        sim_rr = cosine_similarity(cand_rev_emb, ref_rev_emb)
        score_match = sim_oo + sim_rr
        
        sim_or = cosine_similarity(cand_obv_emb, ref_rev_emb)
        sim_ro = cosine_similarity(cand_rev_emb, ref_obv_emb)
        score_flip = sim_or + sim_ro
        
        is_flip = score_flip > (score_match + 0.0)
        
        return {
            "is_flip": is_flip,
            "score_match": score_match,
            "score_flip": score_flip,
            "details": {
                "oo": sim_oo, "rr": sim_rr, "or": sim_or, "ro": sim_ro
            }
        }
    except Exception as e:
        return {"error": str(e)}

def interactive_loop(seg_model, backbone):
    # Signal ready
    print("READY")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            data = json.loads(line)
            result = process_request(data, seg_model, backbone)
            print(json.dumps(result))
            sys.stdout.flush()
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true", help="Run in daemon mode")
    parser.add_argument("--ref_obv")
    parser.add_argument("--ref_rev")
    parser.add_argument("--cand_obv")
    parser.add_argument("--cand_rev")
    args = parser.parse_args()
    
    # Load Models Once
    try:
        seg_model = load_segmentation_model()
        backbone = load_feature_extractor()
    except Exception as e:
        print(json.dumps({"error": f"Model load failed: {e}"}))
        return

    if args.interactive:
        interactive_loop(seg_model, backbone)
    else:
        # One-shot mode
        if not all([args.ref_obv, args.ref_rev, args.cand_obv, args.cand_rev]):
            print(json.dumps({"error": "Missing arguments for one-shot mode"}))
            return
            
        data = {
            "ref_obv": args.ref_obv, "ref_rev": args.ref_rev,
            "cand_obv": args.cand_obv, "cand_rev": args.cand_rev
        }
        
        # Debug Logging for One-Shot
        with open(os.path.join(SCRIPT_DIR, "neural_debug.log"), "a", encoding="utf-8") as f:
            f.write(f"\n--- Run at {os.times()} ---\n")
            f.write(f"Args: {args}\n")
            
        result = process_request(data, seg_model, backbone)
        
        with open(os.path.join(SCRIPT_DIR, "neural_debug.log"), "a") as f: 
            f.write(f"Result: {json.dumps(result)}\n")
            
        print(json.dumps(result))

if __name__ == "__main__":
    main()
