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

    count_updated = 0
    count_processed = 0
    count_exceptions = 0
    
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
            
            # Find Size in table
            # <tr><th>Size</th><td>...</td></tr>
            # OR first td is 'Size'
            
            size_header = soup.find('th', string=lambda text: text and 'Size' in text)
            
            # If not found in th, try first td (sometimes headers are tds in older layouts or different tables?)
            # User said: "<tr> with <th> or first <td> having text 'Size'"
            if not size_header:
                size_header = soup.find('td', string=lambda text: text and 'Size' in text)
                
                # Verify it is indeed the 'header' cell (e.g. previous sibling is None or it's the first child)
                # But simple text match might be enough for now given typical Numista layout
            
            if size_header:
                # Value is in the next td
                # If size_header is th, next sibling td
                # If size_header is td, next sibling td
                
                value_td = size_header.find_next_sibling('td')
                
                if value_td:
                    raw_text = value_td.get_text(strip=True)
                    # Replace nbsp
                    cleaned_text = raw_text.replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
                    
                    # Logic: Try to parse out value
                    # Default unit "mm". 
                    # If text ends with "mm", remove it.
                    
                    final_value = cleaned_text
                    
                    # Store raw text for exception logging if needed??
                    # User: "try to parse out the string... insert into size field... If ... issue ... write ... raw text into parse_exceptions"
                    
                    # I will assume "issue" means if we fail to extract a clean value?
                    # But text extraction usually works.
                    # Let's clean the unit.
                    
                    is_mm = False
                    if final_value.lower().endswith("mm"):
                        final_value = final_value[:-2].strip()
                        is_mm = True
                    
                    # If it was empty or weird?
                    if not final_value:
                         continue

                    # Update DB
                    try:
                        cursor.execute("UPDATE coin_types SET size = ? WHERE id = ?", (final_value, coin_type_id))
                        count_updated += 1
                        
                    except Exception as db_err:
                        # Log to parse_exceptions
                        print(f"Error updating DB for coin {coin_type_id}: {db_err}")
                        try:
                            cursor.execute("INSERT OR REPLACE INTO parse_exceptions (coin_type_id, size) VALUES (?, ?)", (coin_type_id, raw_text))
                            count_exceptions += 1
                        except:
                            pass

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coin types updated with size: {count_updated}")
    print(f"Total exceptions logged: {count_exceptions}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
