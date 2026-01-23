import os
import hashlib
import sqlite3
import glob
from PIL import Image, ImageOps
import numpy as np
from bs4 import BeautifulSoup
import argparse
import sys
import shutil

# --- Comparison Logic ---

def are_files_identical(path1, path2):
    """
    Method 1: File Hash Comparison
    Checks if two files are identical byte-for-byte.
    """
    def get_file_hash(filepath):
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()

    try:
        return get_file_hash(path1) == get_file_hash(path2)
    except Exception as e:
        print(f"Error checking hash for {path1} vs {path2}: {e}")
        return False

def are_pixels_identical(path1, path2):
    """
    Method 2: Pixel Data Comparison
    Checks if the actual image content is the same, ignoring metadata.
    """
    try:
        img1 = Image.open(path1)
        img2 = Image.open(path2)
    except Exception as e:
        print(f"Error opening images for pixel comparison: {e}")
        return False

    if img1.size != img2.size or img1.mode != img2.mode:
        return False

    arr1 = np.array(img1)
    arr2 = np.array(img2)
    
    return np.array_equal(arr1, arr2)

# --- Database & File Logic ---

def get_coin_type_id_from_folder(folder_name):
    """
    Extracts coin_type_id from folder name format: {slug}_{id}
    Returns None if parsing fails.
    """
    try:
        parts = folder_name.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
    except:
        pass
    return None

def get_image_sample_type(db_conn, coin_type_id, image_filename):
    """
    Returns the sample_type for a given image filename and coin_type_id.
    """
    if not image_filename or not coin_type_id:
        return None
    
    cursor = db_conn.cursor()
    # Check obverse
    cursor.execute("SELECT sample_type FROM coin_type_samples WHERE coin_type_id = ? AND obverse_image = ?", (coin_type_id, image_filename))
    row = cursor.fetchone()
    if row: return row[0]
    
    # Check reverse
    cursor.execute("SELECT sample_type FROM coin_type_samples WHERE coin_type_id = ? AND reverse_image = ?", (coin_type_id, image_filename))
    row = cursor.fetchone()
    if row: return row[0]
    
    return None

def soft_delete_image_from_db(db_conn, coin_type_id, image_filename):
    """
    Marks the image as removed=1 in the database.
    Does NOT delete the row.
    """
    if not image_filename or not coin_type_id:
        return
    
    cursor = db_conn.cursor()
    
    # Check if exists (for logging)
    cursor.execute("SELECT count(*) FROM coin_type_samples WHERE coin_type_id = ? AND (obverse_image = ? OR reverse_image = ?)", 
                   (coin_type_id, image_filename, image_filename))
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"  [DB] Updating {count} row(s) to removed=1 for coin_type_id={coin_type_id}, image={image_filename}")
        # Note: We update both obverse and reverse matches just in case the same filename is used for both (weird, but safe)
        cursor.execute("UPDATE coin_type_samples SET removed=1 WHERE coin_type_id = ? AND obverse_image = ?", (coin_type_id, image_filename))
        cursor.execute("UPDATE coin_type_samples SET removed=1 WHERE coin_type_id = ? AND reverse_image = ?", (coin_type_id, image_filename))
        db_conn.commit()
    else:
        print(f"  [DB] No references found for {image_filename} with id {coin_type_id}.")

def ensure_backup_dir(folder_path):
    """
    Creates 'bkp' directory inside folder_path if it doesn't exist.
    Returns the backup directory path.
    """
    bkp_dir = os.path.join(folder_path, 'bkp')
    if not os.path.exists(bkp_dir):
        os.makedirs(bkp_dir)
        print(f"  [FS] Created backup directory: {bkp_dir}")
    return bkp_dir

def backup_html_file(folder_path, bkp_dir):
    """
    Copies coin_type.html to bkp_dir if it's NOT already there.
    This preserves the original HTML before any modifications.
    """
    html_src = os.path.join(folder_path, 'coin_type.html')
    html_dst = os.path.join(bkp_dir, 'coin_type.html')
    
    if os.path.exists(html_src) and not os.path.exists(html_dst):
        try:
            shutil.copy2(html_src, html_dst)
            print(f"  [FS] Backed up coin_type.html to {html_dst}")
        except Exception as e:
            print(f"  [FS] Error backing up HTML: {e}")

def move_image_to_backup(image_path, bkp_dir):
    """
    Moves the image file into the backup directory.
    """
    if not os.path.exists(image_path):
        return

    filename = os.path.basename(image_path)
    dst = os.path.join(bkp_dir, filename)
    
    try:
        # Move (rename)
        shutil.move(image_path, dst)
        print(f"  [FS] Moved {filename} to {dst}")
    except Exception as e:
        print(f"  [FS] Error moving file to backup: {e}")

def update_html_references(html_path, deleted_image, survivor_image):
    """
    Updates coin_type.html references: deleted_image -> survivor_image.
    """
    if not os.path.exists(html_path):
        return

    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        changed = False
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.endswith(deleted_image):
                # Replace with survivor
                # Careful with paths if src is relative "images/foo.jpg"
                new_src = src.replace(deleted_image, survivor_image)
                img['src'] = new_src
                print(f"  [HTML] Updated local img src: {deleted_image} -> {survivor_image}")
                changed = True
                
                # Check parent anchor
                parent = img.find_parent('a')
                if parent:
                    href = parent.get('href', '')
                    if href.endswith(deleted_image):
                        new_href = href.replace(deleted_image, survivor_image)
                        parent['href'] = new_href
                        print(f"  [HTML] Updated parent anchor href: {deleted_image} -> {survivor_image}")

        if changed:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print("  [HTML] Saved changes.")

    except Exception as e:
        print(f"  [HTML] Error updating HTML: {e}")

# --- Processing Logic ---

def process_coin_type_folder(folder_path, db_conn, dry_run=False):
    images_dir = os.path.join(folder_path, 'images')
    if not os.path.isdir(images_dir):
        return

    # Determine coin_type_id
    folder_name = os.path.basename(folder_path)
    coin_type_id = get_coin_type_id_from_folder(folder_name)
    if not coin_type_id:
        # print(f"Skipping {folder_name} - cannot parse ID")
        return

    # Gather images
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(images_dir, ext)))
    
    image_files.sort()
    
    if len(image_files) < 2:
        return

    deleted_files = set()
    
    # Pairwise check
    for i in range(len(image_files)):
        f1 = image_files[i]
        if f1 in deleted_files:
            continue
            
        for j in range(i + 1, len(image_files)):
            f2 = image_files[j]
            if f2 in deleted_files:
                continue

            # Check exact match
            is_exact = False
            if are_files_identical(f1, f2):
                is_exact = True
            elif are_pixels_identical(f1, f2):
                is_exact = True
            
            if is_exact:
                name1 = os.path.basename(f1)
                name2 = os.path.basename(f2)
                
                type1 = get_image_sample_type(db_conn, coin_type_id, name1)
                type2 = get_image_sample_type(db_conn, coin_type_id, name2)
                
                # Priority Logic: Keep 1 > 3 > others
                # If types are None, treat as lowest priority (e.g. 99)
                p1 = type1 if type1 is not None else 99
                p2 = type2 if type2 is not None else 99
                
                keep_f1 = True
                
                if p1 == 1 and p2 != 1:
                    keep_f1 = True
                elif p2 == 1 and p1 != 1:
                    keep_f1 = False
                elif p1 == 3 and p2 != 3:
                     # e.g. T3 vs T99 -> Keep T3
                    keep_f1 = True
                elif p2 == 3 and p1 != 3:
                    keep_f1 = False
                else:
                    # Tie-break: Keep larger file size or alphabetical
                    size1 = os.path.getsize(f1)
                    size2 = os.path.getsize(f2)
                    if size1 >= size2:
                        keep_f1 = True
                    else:
                        keep_f1 = False

                if keep_f1:
                    keep, delete = f1, f2
                    keep_name, delete_name = name1, name2
                    t_keep, t_del = p1, p2
                else:
                    keep, delete = f2, f1
                    keep_name, delete_name = name2, name1
                    t_keep, t_del = p2, p1
                
                print(f"DUPLICATE FOUND in {folder_name}:")
                print(f"  Keep:   {keep_name} (Type {t_keep})")
                print(f"  Delete: {delete_name} (Type {t_del})")
                
                if not dry_run:
                    # 1. Soft DB Delete
                    soft_delete_image_from_db(db_conn, coin_type_id, delete_name)
                    
                    # Ensure Backup Directory
                    bkp_dir = ensure_backup_dir(folder_path)
                    
                    # 2. Backup HTML (Original state before ANY modification in this run potentially)
                    # NOTE: If multiple duplicates are found, the first modification happens here.
                    # We only want to backup the *original* once. 
                    # The helper backup_html_file checks logic to not overwrite existing backup.
                    backup_html_file(folder_path, bkp_dir)
                    
                    # 3. HTML Update
                    html_path = os.path.join(folder_path, 'coin_type.html')
                    update_html_references(html_path, delete_name, keep_name)
                    
                    # 4. Move File to Backup
                    move_image_to_backup(delete, bkp_dir)
                    
                else:
                    print("  [DRY RUN] Actions skipped (Soft delete DB, move file to bkp, update HTML).")
                
                deleted_files.add(delete)
                
                if delete == f1:
                    break


def main():
    parser = argparse.ArgumentParser(description="Remove duplicate coin images via Issuer -> CoinType iteration.")
    parser.add_argument("--root", default="scrappers/numista/coin_types/html", help="Root folder (html)")
    parser.add_argument("--db", default="scrappers/numista/db/coins.db", help="Path to SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    if not os.path.exists(args.root):
        print(f"Root path not found: {args.root}")
        return
    
    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        return

    print(f"Connecting to DB: {args.db}")
    conn = sqlite3.connect(args.db)
    
    # Iterate Issuers
    try:
        issuers = sorted([d for d in os.listdir(args.root) if os.path.isdir(os.path.join(args.root, d))])
        print(f"Found {len(issuers)} issuers.")
        
        for issuer in issuers:
            issuer_path = os.path.join(args.root, issuer)
            
            # Iterate Coin Types
            coin_types = sorted([d for d in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, d))])
            
            for ct in coin_types:
                ct_path = os.path.join(issuer_path, ct)
                process_coin_type_folder(ct_path, conn, dry_run=args.dry_run)
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
        print("Done.")

if __name__ == "__main__":
    main()
