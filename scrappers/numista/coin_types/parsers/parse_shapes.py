import os
import sqlite3
import re
from bs4 import BeautifulSoup

def main():
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # DB Path: ../../../../data/numista/coins.db
    db_path = os.path.abspath(os.path.join(current_dir, "../../../../data/numista/coins.db"))
    # HTML Root: ../html
    html_root = os.path.abspath(os.path.join(current_dir, "../html"))
    
    print(f"Script Location: {current_dir}")
    print(f"DB Path: {db_path}")
    print(f"HTML Root: {html_root}")

    if not os.path.exists(db_path):
        print("Error: Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Pre-load shapes into a dictionary for fast lookup
    # Case-insensitive lookup map: "round" -> id
    cursor.execute("SELECT id, name FROM shapes")
    shapes_map = {row[1].lower().strip(): row[0] for row in cursor.fetchall()}
    print(f"Loaded {len(shapes_map)} shapes from DB.")

    count_updated = 0
    count_processed = 0
    
    # Iterate issuer folders
    issuer_folders = [f for f in os.listdir(html_root) if os.path.isdir(os.path.join(html_root, f))]
    
    for issuer_folder in issuer_folders:
        issuer_path = os.path.join(html_root, issuer_folder)
        coin_folders = [f for f in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, f))]
        
        for coin_folder in coin_folders:
            count_processed += 1
            if count_processed % 1000 == 0:
                print(f"Processed {count_processed} coins...")
                conn.commit()

            # Parse coin_type_id
            try:
                coin_type_id_str = coin_folder.split('_')[-1]
                coin_type_id = int(coin_type_id_str)
            except ValueError:
                continue
                
            coin_html_path = os.path.join(issuer_path, coin_folder, "coin_type.html")
            
            if not os.path.exists(coin_html_path):
                continue
                
            try:
                with open(coin_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                print(f"Error reading {coin_html_path}: {e}")
                continue
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find Shape in table
            # Looking for <tr><th>Shape</th><td>Round</td></tr>
            # We can search for the 'th' with text "Shape" and get the next sibling 'td'
            
            shape_th = soup.find('th', string=lambda text: text and 'Shape' in text)
            if shape_th:
                shape_td = shape_th.find_next_sibling('td')
                if shape_td:
                    shape_text = shape_td.get_text(strip=True)
                    
                    if shape_text:
                        lookup_key = shape_text.lower()
                        
                        if lookup_key in shapes_map:
                            shape_id = shapes_map[lookup_key]
                            
                            # Update coin_types
                            cursor.execute("UPDATE coin_types SET shape_id = ? WHERE id = ?", (shape_id, coin_type_id))
                            count_updated += 1
                        else:
                            # Log exception to table
                            # Check if already exists to avoid dupes? Or just insert? User just said "write records".
                            # Let's simple insert.
                            cursor.execute("INSERT INTO shape_exceptions (coin_type_id, shape) VALUES (?, ?)", (coin_type_id, shape_text))

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coin types updated with shape: {count_updated}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
