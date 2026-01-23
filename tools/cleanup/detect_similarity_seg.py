import os
import argparse
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as T
import torchvision.models as models
import segmentation_models_pytorch as smp
import psycopg2
import csv
from pathlib import Path

# -----------------------------
# Config
# -----------------------------

PG_DSN = "host=localhost port=5432 dbname=mintada_db user=admin password=mintada"
TOOLS_DIR = Path(__file__).parent
PROJECT_ROOT = TOOLS_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "coin_samples"
SEG_MODEL_PATH = PROJECT_ROOT / "tools" / "segmentation" / "best_coin_unet_resnet34.pth"
OUTPUT_REPORT = TOOLS_DIR / "suspected_flips_seg.csv"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

SEG_IMG_SIZE = 256
EMB_IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def build_file_map(root_dir):
    print(f"Indexing images in {root_dir}...")
    file_map = {}
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_map[file.lower()] = os.path.join(root, file)
    print(f"Indexed {len(file_map)} images.", flush=True)
    return file_map

# -----------------------------
# Helpers: models
# -----------------------------

def load_segmentation_model(seg_model_path):
    print(f"Loading segmentation model from {seg_model_path}...")
    model = smp.Unet(
        encoder_name="resnet34",
        encoder_weights=None,
        in_channels=3,
        classes=1,
    )
    state = torch.load(seg_model_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

def load_feature_extractor():
    print("Loading ResNet18 feature extractor...")
    resnet = models.resnet18(pretrained=True)
    backbone = nn.Sequential(*list(resnet.children())[:-1])

    for p in backbone.parameters():
        p.requires_grad = False

    backbone.to(DEVICE)
    backbone.eval()
    return backbone

# -----------------------------
# Helpers: transforms
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
# Segmentation + crop + normalize
# -----------------------------

def segment_and_crop(image_path, seg_model):
    try:
        if not os.path.exists(image_path):
            print(f"File not found: {image_path}")
            return None
            
        img = Image.open(image_path).convert("RGB")
        img_resized = img.resize((SEG_IMG_SIZE, SEG_IMG_SIZE), resample=Image.BILINEAR)

        x = seg_transform(img_resized).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            logits = seg_model(x)
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()   # (H, W)
        mask = (prob > 0.5).astype(np.uint8)               # binary mask 0/1
        print(f"  Mask sum for {image_path}: {mask.sum()}", flush=True)

        if mask.sum() == 0:
            print(f"  WARNING: Empty mask for {image_path}", flush=True)
            # Fallback if no mask: use whole image
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
        img_np_masked[~mask_3] = 0 # Black out background

        img_masked = Image.fromarray(img_np_masked)
        crop = img_masked.crop((x_min, y_min, x_max + 1, y_max + 1))

        crop_resized = emb_transform(crop)
        return crop_resized
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

# -----------------------------
# Embedding + similarity
# -----------------------------

def get_embedding(tensor_img, backbone):
    if tensor_img is None:
        return None
    with torch.no_grad():
        x = tensor_img.unsqueeze(0).to(DEVICE)
        feat = backbone(x)
        feat = feat.view(feat.size(0), -1)
    return feat[0]

def cosine_similarity(a, b):
    if a is None or b is None:
        return 0.0
    a = a / (a.norm(p=2) + 1e-8)
    b = b / (b.norm(p=2) + 1e-8)
    return float((a * b).sum().item())

# -----------------------------
# Database
# -----------------------------

def get_all_samples():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    # Fetch all coin samples
    sql = """
        SELECT "Id", "CoinTypeId", "SampleType", "ObverseImage", "ReverseImage"
        FROM coin_type_samples
        WHERE "ObverseImage" IS NOT NULL AND "ReverseImage" IS NOT NULL
        ORDER BY "CoinTypeId"
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows

# -----------------------------
# Main
# -----------------------------

def main():
    print(f"Using device: {DEVICE}")
    
    # 1. Load Models
    if not SEG_MODEL_PATH.exists():
        print(f"Error: Segmentation model not found at {SEG_MODEL_PATH}")
        return

    seg_model = load_segmentation_model(SEG_MODEL_PATH)
    backbone = load_feature_extractor()
    
    # NEW: Build File Map
    file_map = build_file_map(DATA_DIR)

    # 2. Get Data
    rows = get_all_samples()
    print(f"Loaded {len(rows)} samples from database.")

    # Group by CoinTypeId
    coins = {}
    for r in rows:
        sid, ctid, stype, obv, rev = r
        if ctid not in coins:
            coins[ctid] = []
        coins[ctid].append({
            'id': sid,
            'type': stype,
            'obv': obv,
            'rev': rev
        })

    print(f"Found {len(coins)} unique coin types.")

    # 3. Process
    suspects = []
    tested_flip = False # Flag for synthetic test
    
    for ctid, samples in coins.items():
        # Find Reference
        refs = [s for s in samples if s['type'] == 1]
        candidates = [s for s in samples if s['type'] != 1]
        
        if not refs or not candidates:
            # print(f"Skipping {ctid}: Refs={len(refs)}, Cands={len(candidates)}")
            continue
            
        print(f"Processing CoinType {ctid}: {len(refs)} Refs, {len(candidates)} Candidates")
        ref = refs[0]
        
        # Resolve Paths
        ref_obv_path = file_map.get(os.path.basename(ref['obv']).lower())
        ref_rev_path = file_map.get(os.path.basename(ref['rev']).lower())
        
        if not ref_obv_path or not ref_rev_path:
            print(f"Skipping CoinType {ctid}: Reference images not found in DATA_DIR.")
            continue
        
        # Precompute Reference Embeddings
        # Note: We re-compute for every coin type. Ideally we'd cache if referenced multiple times, 
        # but here each coin type is distinct.
        
        ref_obv_tensor = segment_and_crop(str(ref_obv_path), seg_model)
        ref_rev_tensor = segment_and_crop(str(ref_rev_path), seg_model)
        
        if ref_obv_tensor is None or ref_rev_tensor is None:
            print(f"Skipping CoinType {ctid}: Reference images failed to load/segment.")
            continue
            
        ref_obv_emb = get_embedding(ref_obv_tensor, backbone)
        ref_rev_emb = get_embedding(ref_rev_tensor, backbone)
        
        for cand in candidates:
            cand_obv_name = os.path.basename(cand['obv'])
            cand_rev_name = os.path.basename(cand['rev'])
            cand_obv_path = file_map.get(cand_obv_name.lower())
            cand_rev_path = file_map.get(cand_rev_name.lower())
            
            if not cand_obv_path or not cand_rev_path:
                print(f"Skipping Sample {cand['id']}: Images not found in output of build_file_map (Looked for {cand_obv_name.lower()}).", flush=True)
                # print(f"  Wanted: {cand_obv_name}, {cand_rev_name}")
                continue
            
            cand_obv_tensor = segment_and_crop(str(cand_obv_path), seg_model)
            cand_rev_tensor = segment_and_crop(str(cand_rev_path), seg_model)
            
            if cand_obv_tensor is None or cand_rev_tensor is None:
                print(f"Skipping Sample {cand['id']}: Failed to load/segment images.")
                continue
                
            # --- SYNTHETIC TEST: FLIP THE FIRST CANDIDATE ---
            was_injected = False
            if not tested_flip:
                print(f"*** INJECTING SYNTHETIC FLIP for Sample {cand['id']} ***", flush=True)
                cand_obv_tensor, cand_rev_tensor = cand_rev_tensor, cand_obv_tensor
                tested_flip = True
                was_injected = True
            # -----------------------------------------------
                
            cand_obv_emb = get_embedding(cand_obv_tensor, backbone)
            cand_rev_emb = get_embedding(cand_rev_tensor, backbone)
            
            # Compare
            # Standard Match: Obv-Obv, Rev-Rev
            sim_oo = cosine_similarity(cand_obv_emb, ref_obv_emb)
            sim_rr = cosine_similarity(cand_rev_emb, ref_rev_emb)
            score_match = sim_oo + sim_rr
            
            # Flipped Match: Obv-Rev, Rev-Obv
            sim_or = cosine_similarity(cand_obv_emb, ref_rev_emb)
            sim_ro = cosine_similarity(cand_rev_emb, ref_obv_emb)
            score_flip = sim_or + sim_ro

            if was_injected:
                print(f"DEBUG: Injected Flip Scores -> Match: {score_match:.4f} | Flip: {score_flip:.4f}", flush=True)
                print(f"DEBUG: Details -> OO:{sim_oo:.4f} RR:{sim_rr:.4f} | OR:{sim_or:.4f} RO:{sim_ro:.4f}", flush=True)
            
            # Decision
            # If Flip Score is significantly higher
            is_test_case = (tested_flip and suspects == [] and (score_flip > score_match) and False) # Logic tricky here because loop continues
            # clearer: we want to know if THIS loop iteration was the one we flipped.
            # actually we don't have a variable for that.
            
            if (tested_flip and not suspects): # This is weak logic, let's just print all scores for first few.
                 pass

            if score_flip > score_match + 0.1: # Margin 0.1
                print(f"FLIP DETECTED! CoinType {ctid} Sample {cand['id']}")
                print(f"  Match: {score_match:.4f} (OO:{sim_oo:.2f}, RR:{sim_rr:.2f})")
                print(f"  Flip : {score_flip:.4f} (OR:{sim_or:.2f}, RO:{sim_ro:.2f})")
                
                suspects.append({
                    'coin_type_id': ctid,
                    'sample_id': cand['id'],
                    'score_match': score_match,
                    'score_flip': score_flip,
                    'ref_obv': ref['obv'],
                    'ref_rev': ref['rev'],
                    'cand_obv': cand['obv'],
                    'cand_rev': cand['rev']
                })
            else:
                 # Logic to print the scores for the injected flip
                 pass

    # Save Report
    if suspects:
        with open(OUTPUT_REPORT, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['coin_type_id', 'sample_id', 'score_match', 'score_flip', 'ref_obv', 'ref_rev', 'cand_obv', 'cand_rev']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(suspects)
        print(f"\nSaved {len(suspects)} suspected flips to {OUTPUT_REPORT}")
    else:
        print("\nNo flips detected.")

if __name__ == "__main__":
    main()
