import os
import sqlite3
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

    count_updated = 0
    count_processed = 0
    
    # Iterate issuer folders
    if not os.path.exists(html_root):
        print("HTML root folder not found!")
        return
        
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
            
            # Find Composition in table
            # <tr><th>Composition</th><td>...</td></tr>
            
            composition_header = soup.find('th', string=lambda text: text and 'Composition' in text)
            
            # If not found in th, try first td
            if not composition_header:
                composition_header = soup.find('td', string=lambda text: text and 'Composition' in text)
            
            if composition_header:
                value_td = composition_header.find_next_sibling('td')
                
                if value_td:
                    raw_text = value_td.get_text(strip=True)
                    # Replace nbsp
                    cleaned_text = raw_text.replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
                    
                    if cleaned_text:
                        # Update DB
                        try:
                            cursor.execute("UPDATE coin_types SET composition = ? WHERE id = ?", (cleaned_text, coin_type_id))
                            count_updated += 1
                        except Exception as db_err:
                            print(f"Error updating DB for coin {coin_type_id}: {db_err}")

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coin types updated with composition: {count_updated}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
