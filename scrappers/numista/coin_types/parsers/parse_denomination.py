import os
import sqlite3
import re
import html
import unicodedata
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
        
    if not os.path.exists(html_root):
        print("HTML root folder not found!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Unicode fraction mapping for normalization
    unicode_fractions = {
        '¼': '1/4', '½': '1/2', '¾': '3/4',
        '⅐': '1/7', '⅑': '1/9', '⅒': '1/10',
        '⅓': '1/3', '⅔': '2/3',
        '⅕': '1/5', '⅖': '2/5', '⅗': '3/5', '⅘': '4/5',
        '⅙': '1/6', '⅚': '5/6',
        '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8'
    }

    # Pre-compile Regex
    # Issue 1: '/' character with preceding and following letters
    slash_regex = re.compile(r'[a-zA-Z]\s*/\s*[a-zA-Z]')
    
    # Issue 2: Starts with digit or unicode fraction (for exception logging)
    start_digit_regex = re.compile(r'^(\d|' + '|'.join(re.escape(k) for k in unicode_fractions.keys()) + r')')

    count_processed = 0
    count_updated = 0
    
    # Iterate over HTML folders
    issuer_folders = [f for f in os.listdir(html_root) if os.path.isdir(os.path.join(html_root, f))]
    
    print(f"Found {len(issuer_folders)} issuer folders. Starting scan...")
    
    for issuer_folder in issuer_folders:
        issuer_path = os.path.join(html_root, issuer_folder)
        coin_folders = [f for f in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, f))]
        
        for coin_folder in coin_folders:
            count_processed += 1
            if count_processed % 1000 == 0:
                print(f"Processed {count_processed} coins...")
                conn.commit()

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
            
            # --- Parsing from HTML ---
            
            value_header = soup.find('th', string=lambda text: text and 'Value' in text)
            if not value_header:
                value_header = soup.find('td', string=lambda text: text and 'Value' in text)
            
            main_value = None
            info_1 = None
            info_2 = None
            alt_value = None
            
            # If we find the Value cell
            if value_header:
                value_td = value_header.find_next_sibling('td')
                
                if value_td:
                    raw_text = value_td.get_text(separator='\n', strip=True)
                    
                    # 1. Unescape HTML
                    cleaned_text = html.unescape(raw_text)
                    
                    # 2. Normalize Unicode using NFC (Critical for preserving ½)
                    cleaned_text = unicodedata.normalize("NFC", cleaned_text)
                    
                    # 3. Clean spaces
                    cleaned_text = cleaned_text.replace('\xa0', ' ').strip()
                    
                    # 4. Extract Parenthesis Content -> info_1
                    match = re.search(r'\((.*?)\)', cleaned_text, re.DOTALL)
                    if match:
                        info_1 = match.group(1).strip()
                        cleaned_text = cleaned_text.replace(match.group(0), ' ').strip()
                    
                    # 5. Split lines -> info_2
                    lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
                    if lines:
                        main_value = lines[0]
                        if len(lines) > 1:
                            info_2 = ' '.join(lines[1:])
            
            # If no value found in HTML, main_value remains None.
            # We skip validation/calc if main_value is None, BUT
            # we might want to carry over existing DB value? 
            # No, if we are re-parsing from HTML, we trust HTML. 
            # If HTML has nothing, we update to NULL? 
            # Previous script: "CASE WHEN ? IS NOT NULL... ELSE value END" - preserved existing if scrape failed.
            # We will follow that.
            
            normalized_text = main_value
            final_decimal = None
            
            # Only process if we successfully parsed a value
            if main_value:
                # Prepend "1 " if not numeric start (e.g. "Daler")
                # But be careful with fractions. "½ Dollar" is numeric enough for us?
                # The logic in previous script: if main_value and not main_value[0].isnumeric(): prepend "1 "
                # fraction chars are NOT numeric in str.isnumeric() usually (depends).
                # '½'.isnumeric() is True.
                if main_value and not main_value[0].isnumeric():
                     main_value = f"1 {main_value}"
                     normalized_text = main_value
                
                if '=' in main_value:
                    parts = main_value.split('=', 1)
                    main_value = parts[0].strip()
                    alt_value = parts[1].strip()
                    normalized_text = main_value

                # --- Validation & Processing (From parse_denomination.py) ---
                
                # 0. Replace Fraction Slash '⁄' -> '/'
                normalized_text = normalized_text.replace('⁄', '/')
                
                # 1. Slash Issue Check
                has_slash_issue = bool(slash_regex.search(normalized_text))
                
                # 2. Non-digit start Check
                # Check if it starts with digit or unicode fraction
                text_stripped = normalized_text.strip()
                is_valid_start = False
                if text_stripped:
                    first_char = text_stripped[0]
                    if first_char.isdigit() or first_char in unicode_fractions:
                        is_valid_start = True
                
                has_non_digit_start_issue = not is_valid_start

                # Update parse_exceptions
                if has_slash_issue or has_non_digit_start_issue:
                    cursor.execute("SELECT 1 FROM parse_exceptions WHERE coin_type_id = ?", (coin_type_id,))
                    exists = cursor.fetchone()
                    if exists:
                        cursor.execute("""
                            UPDATE parse_exceptions 
                            SET "has_slash" = ?, "non-digit_value" = ?
                            WHERE coin_type_id = ?
                        """, (1 if has_slash_issue else 0, 1 if has_non_digit_start_issue else 0, coin_type_id))
                    else:
                        cursor.execute("""
                            INSERT INTO parse_exceptions (coin_type_id, "has_slash", "non-digit_value")
                            VALUES (?, ?, ?)
                        """, (coin_type_id, 1 if has_slash_issue else 0, 1 if has_non_digit_start_issue else 0))

                # 3. Unicode Fraction Normalization (ASCII + Space)
                for u_char, ascii_val in unicode_fractions.items():
                    if u_char in normalized_text:
                        # Add space if preceded by digit: "12½" -> "12 1/2"
                        normalized_text = re.sub(f'(?<=\\d){u_char}', f' {ascii_val}', normalized_text)
                        # Replace char: "½" -> "1/2"
                        normalized_text = normalized_text.replace(u_char, ascii_val)
                        
                # 4. Calculate Decimal Value
                # Clean spaces for calc
                calc_text = " ".join(normalized_text.split()).strip()
                
                value_match = re.match(r'^(\d+)?\s*(\d+)/(\d+)', calc_text)
                simple_match = re.match(r'^(\d+(\.\d+)?)', calc_text)
                
                if value_match:
                    whole_str = value_match.group(1)
                    numer_str = value_match.group(2)
                    denom_str = value_match.group(3)
                    whole = float(whole_str) if whole_str else 0.0
                    if denom_str and float(denom_str) != 0:
                        final_decimal = whole + (float(numer_str) / float(denom_str))
                elif simple_match:
                    final_decimal = float(simple_match.group(1))

            # Update DB (Merging update logic)
            # We proceed if main_value found OR we have info updates
            if main_value or info_1 or info_2:
                try:
                    cursor.execute("""
                        UPDATE coin_types 
                        SET denomination_text = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE denomination_text END, 
                            denomination_value = CASE WHEN ? IS NOT NULL THEN ? ELSE denomination_value END,
                            denomination_info_1 = ?, 
                            denomination_info_2 = ?,
                            denomination_alt = ?
                        WHERE id = ?
                    """, (main_value, main_value, normalized_text, # If new text, update to NORMALIZED text
                          main_value, final_decimal, # If new value parsed, update decimal
                          info_1, info_2, alt_value, coin_type_id))
                    count_updated += 1
                except Exception as db_err:
                    print(f"Error updating DB for coin {coin_type_id}: {db_err}")

    conn.commit()
    conn.close()
    print(f"Done. Processed {count_processed}. Updated {count_updated}.")

if __name__ == "__main__":
    main()
