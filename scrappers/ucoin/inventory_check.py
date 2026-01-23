import sqlite3
import os
import sys
from pathlib import Path

DB_PATH = "db/coins.db"
IMAGES_ROOT = "coin_images"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Fetching coin types and images from database...")
    
    # Join tables to get all necessary info for path construction
    # We need:
    # - issue_type (from coin_types)
    # - country_slug (from countries)
    # - coin_type_url (from coin_types, to extract url_part)
    # - coin_type_id (from coin_types)
    # - image_id (from coin_images)
    # - year (from coin_images)
    
    query = """
        SELECT 
            ct.issue_type,
            c.url_slug as country_slug,
            ct.url as coin_type_url,
            ct.id as coin_type_id,
            ci.id as image_id,
            ci.year
        FROM coin_images ci
        JOIN coin_types ct ON ci.coin_type_id = ct.id
        JOIN countries c ON ct.country_id = c.id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} image records. Verifying files...")
    
    missing_count = 0
    checked_count = 0
    
    with open("missing_images.log", "w", encoding="utf-8") as log:
        log.write("issue_type,country_slug,coin_type_id,image_id,side,expected_path\n")
        
        for row in rows:
            issue_type = row['issue_type']
            country_slug = row['country_slug']
            coin_type_id = row['coin_type_id']
            coin_type_url = row['coin_type_url']
            image_id = row['image_id']
            year = row['year']
            
            # Derive coin_type_folder name
            # Format: {url_part}-{id}
            # url_part is extracted from coin_types.url
            # Example url: /coin/albania-1-lek-1996/?tid=27102 -> albania-1-lek-1996
            
            try:
                # Extract url_part
                # Assuming url format like /coin/part/?tid=... or /coin/part
                parts = coin_type_url.split('/coin/')
                if len(parts) > 1:
                    sub = parts[1]
                    # Remove query params if any
                    if '?' in sub:
                        sub = sub.split('?')[0]
                    # Remove trailing slash
                    sub = sub.strip('/')
                    url_part = sub
                else:
                    print(f"Warning: Could not parse URL for coin_type_id {coin_type_id}: {coin_type_url}")
                    continue

                coin_type_folder = f"{url_part}-{coin_type_id}"
                
                # Construct base path
                base_dir = Path(IMAGES_ROOT) / str(issue_type) / country_slug / coin_type_folder
                
                # Check both sides (1 and 2)
                for side in [1, 2]:
                    filename = f"{year}-{image_id}-{side}.jpg"
                    file_path = base_dir / filename
                    
                    if not file_path.exists():
                        missing_count += 1
                        log.write(f"{issue_type},{country_slug},{coin_type_id},{image_id},{side},{file_path}\n")
            
            except Exception as e:
                print(f"Error processing row {dict(row)}: {e}")
                
            checked_count += 1
            if checked_count % 10000 == 0:
                print(f"Checked {checked_count} records...")

    print(f"Verification complete.")
    print(f"Total records checked: {checked_count}")
    print(f"Total missing files: {missing_count}")
    print(f"Missing files logged to missing_images.log")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    if not os.path.exists(IMAGES_ROOT):
        print(f"Error: Images root not found at {IMAGES_ROOT}")
        sys.exit(1)
        
    check_inventory()
