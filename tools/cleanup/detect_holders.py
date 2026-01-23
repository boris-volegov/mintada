import sqlite3
import os
import sys
from PIL import Image
import numpy as np
import time

# Paths
DB_PATH = r"d:\projects\mintada\scrappers\numista\db\coins.db"
# We need to reconstruct the full image path from coin_type_slug and filenames
# Assume standard structure: d:\projects\mintada\scrappers\numista\coin_types\html\{issuer_slug}\{coin_type_slug}_{id}\{obverse_image}
HTML_ROOT = r"d:\projects\mintada\scrappers\numista\coin_types\html"

def get_image_path(issuer_slug, coin_slug, coin_id, filename):
    if not filename: return None
    # Folder pattern: {issuer_slug}\{coin_slug}_{id}\images\{filename}
    folder = os.path.join(HTML_ROOT, issuer_slug, f"{coin_slug}_{coin_id}", "images")
    return os.path.join(folder, filename)

def is_holder(image_path):
    try:
        img = Image.open(image_path).convert('RGB')
    except Exception as e:
        # print(f"Error loading {image_path}: {e}")
        return False

    w, h = img.size
    ar = w / h
    
    # Heuristic 1: Aspect Ratio
    # Slabs are typically 0.65 - 0.85 (Tall)
    # Some older slabs might be wider, but generally they are not square.
    # Coins are usually cropped square (AR ~ 1.0)
    
    # Score based on AR deviation from 1.0
    # If AR is < 0.85, high chance of holder
    if ar > 0.88 and ar < 1.12:
        return False # Likely a square crop = Coin

    # If extremely wide or tall, might be holder or weird crop
    if ar < 0.5 or ar > 2.0:
        return False # Probably noise or banner

    # Heuristic 2: Corner Variance (Uniformity)
    arr = np.array(img)
    corners = [
        arr[0:20, 0:20], arr[0:20, w-20:w],
        arr[h-20:h, 0:20], arr[h-20:h, w-20:w]
    ]
    corner_stds = []
    for corner in corners:
        corner_stds.append(np.std(corner)) # RGB std
    
    avg_corner_std = np.mean(corner_stds)

    # Primary indicator: Aspect Ratio
    # If AR < 0.85, it's almost certainly a holder
    if ar < 0.85:
        return True
    
    # If AR is borderline (0.85-0.88) and corners are very uniform (masked coin)
    if ar < 0.88 and avg_corner_std < 2.0:
        return False
    
    return False

def main():
    print("Connecting to DB...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch all samples that are NOT YET marked (or re-scan all?)
    # Let's re-scan all non-removed samples
    # We need issuer_slug and coin info to build paths
    # LIMIT to 1000 most recent for testing
    query = """
    SELECT cts.coin_type_id, cts.obverse_image, cts.is_holder, 
           ct.coin_type_slug, i.numista_url_slug, ct.id
    FROM coin_type_samples cts
    JOIN coin_types ct ON cts.coin_type_id = ct.id
    JOIN issuers i ON ct.issuer_id = i.id
    WHERE (cts.removed IS NULL OR cts.removed = 0)
    ORDER BY ct.date_time_inserted ASC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    print(f"Scanning {len(rows)} samples...")

    to_update = []
    
    count = 0
    holders_found = 0
    skipped_no_file = 0
    skipped_no_obverse = 0
    processed = 0

    for row in rows:
        coin_type_id = row[0]
        obverse = row[1]
        current_is_holder = row[2]
        coin_slug = row[3]
        issuer_slug = row[4]
        real_id = row[5] # Same as coin_type_id but let's be safe

        if not obverse:
            skipped_no_obverse += 1
            continue
        
        path = get_image_path(issuer_slug, coin_slug, real_id, obverse)
        
        # Print first few paths for debugging
        if count < 3:
            print(f"Sample path: {path}")
        
        if not os.path.exists(path):
            skipped_no_file += 1
            continue

        processed += 1
        detected = is_holder(path)
        
        # Update if changed (or just update all identified holders)
        # Assuming we want to SET is_holder=1 if detected, and 0 if not
        newValue = 1 if detected else 0
        
        if newValue != (current_is_holder if current_is_holder is not None else 0):
            to_update.append((newValue, coin_type_id, obverse))
            if detected:
                holders_found += 1
                print(f"[HOLDER] {coin_slug} ({obverse})")

        count += 1
        if count % 1000 == 0:
            print(f"Processed {count}/{len(rows)}")

    print(f"Finished scanning. Found {holders_found} new holders (or status changes).")
    print(f"Statistics:")
    print(f"  Total samples: {len(rows)}")
    print(f"  Skipped (no obverse): {skipped_no_obverse}")
    print(f"  Skipped (file not found): {skipped_no_file}")
    print(f"  Actually processed: {processed}")
    
    if to_update:
        print(f"Updating {len(to_update)} records in DB...")
        cursor.executemany(
            "UPDATE coin_type_samples SET is_holder = ? WHERE coin_type_id = ? AND obverse_image = ?",
            to_update
        )
        conn.commit()
        print("DB Updated.")
    else:
        print("No changes needed.")

    conn.close()

if __name__ == "__main__":
    main()
