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

    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    count_updated = 0
    count_processed = 0
    
    # Iterate issuer folders
    if not os.path.exists(html_root):
        print(f"Error: HTML root not found at {html_root}")
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
            # Helper to parse fields
            def parse_field(field_name, unit_suffix):
                # Find th with text
                th = soup.find('th', string=lambda text: text and field_name in text)
                if not th:
                    return None, None, None

                td = th.find_next_sibling('td')
                if not td:
                    return None, None, None

                raw_text = td.get_text(strip=True)
                if not raw_text:
                    return None, None, None
                
                # Check for parenthesis info
                info_val = None
                numeric_val = None
                
                # Regex to find parenthesis content
                match_info = re.search(r'\((.*?)\)', raw_text)
                if match_info:
                    info_val = match_info.group(1).strip()
                    # Remove the info from raw text for numeric parsing
                    raw_text_clean = re.sub(r'\(.*?\)', '', raw_text).strip()
                else:
                    raw_text_clean = raw_text

                # Attempt to parse numeric
                # Remove unit suffix if present
                if unit_suffix and raw_text_clean.endswith(unit_suffix):
                    val_str = raw_text_clean[:-len(unit_suffix)].strip()
                else:
                    val_str = raw_text_clean.strip()

                try:
                    # Replace comma with dot just in case, though example showed 1.3
                    val_str = val_str.replace(',', '.')
                    if val_str:
                         numeric_val = float(val_str)
                except ValueError:
                    # Failed to parse numeric
                    pass
                
                return numeric_val, info_val, raw_text

            # 1. Weight (g)
            weight, weight_info, weight_raw = parse_field("Weight", "g")
            
            # 2. Diameter (mm) -> column 'diametre'
            diameter, diameter_info, diameter_raw = parse_field("Diameter", "mm")
            
            # 3. Thickness (mm)
            thickness, thickness_info, thickness_raw = parse_field("Thickness", "mm")

            # Update DB logic
            
            # Retrieve existing info to append if necessary
            cursor.execute("SELECT weight_info, diameter_info, thickness_info FROM coin_types WHERE id = ?", (coin_type_id,))
            row = cursor.fetchone()
            current_w_info, current_d_info, current_t_info = row if row else (None, None, None)
            
            def merge_info(new_info, current_info):
                if not new_info:
                    return current_info
                if current_info:
                    # Check if already present to avoid basic dupes? User said "If the values in those fields already exist, let us append them after '; '"
                    # We will simply append.
                    return f"{current_info}; {new_info}"
                return new_info

            final_w_info = merge_info(weight_info, current_w_info)
            final_d_info = merge_info(diameter_info, current_d_info)
            final_t_info = merge_info(thickness_info, current_t_info)
            
            # Only update if we have something to update
            # But we should always update numeric if found, and potentially update info
            
            try:
                msg = []
                if weight is not None:
                     cursor.execute("UPDATE coin_types SET weight = ? WHERE id = ?", (weight, coin_type_id))
                     msg.append("weight")
                if final_w_info != current_w_info:
                     cursor.execute("UPDATE coin_types SET weight_info = ? WHERE id = ?", (final_w_info, coin_type_id))
                     msg.append("weight_info")
                     
                if diameter is not None:
                     cursor.execute("UPDATE coin_types SET diameter = ? WHERE id = ?", (diameter, coin_type_id))
                     msg.append("diameter")
                if final_d_info != current_d_info:
                     cursor.execute("UPDATE coin_types SET diameter_info = ? WHERE id = ?", (final_d_info, coin_type_id))
                     msg.append("diameter_info")

                if thickness is not None:
                     cursor.execute("UPDATE coin_types SET thickness = ? WHERE id = ?", (thickness, coin_type_id))
                     msg.append("thickness")
                if final_t_info != current_t_info:
                     cursor.execute("UPDATE coin_types SET thickness_info = ? WHERE id = ?", (final_t_info, coin_type_id))
                     msg.append("thickness_info")
                
                if msg:
                    count_updated += 1
                    
            except Exception as e:
                print(f"Error updating ID {coin_type_id}: {e}")

            # Exception Logic
            # defined as: "If even after that we experience some issue with parsing let us write coin_type_id and the raw text... into parse_exceptions"
            # Basically if we found the row (raw_text is not None) but failed to parse numeric (numeric_val is None), log it.
            # AND there was no info extracted? Or just if numeric failed?
            # User said: "try to parse out the decimal... If even after that we experience some issue with parsing let us write..."
            # So if we found the row, but couldn't get a valid float, we log.
            
            ex_w = weight_raw if (weight_raw and weight is None) else None
            ex_d = diameter_raw if (diameter_raw and diameter is None) else None
            ex_t = thickness_raw if (thickness_raw and thickness is None) else None
            
            if ex_w or ex_d or ex_t:
                cursor.execute("INSERT INTO parse_exceptions (coin_type_id, weight, diameter, thickness) VALUES (?, ?, ?, ?)", 
                               (coin_type_id, ex_w, ex_d, ex_t))

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coin types updated: {count_updated}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
