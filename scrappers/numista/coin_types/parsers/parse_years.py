import os
import sqlite3
import re
import html
import argparse
from bs4 import BeautifulSoup
from _coin_inputs import iter_coin_html_targets

def main():
    arg_parser = argparse.ArgumentParser(description="Parse years fields from coin_type.html")
    arg_parser.add_argument("--coin-type-id", type=int, default=None)
    arg_parser.add_argument("--coin-html-path", default=None)
    args, _ = arg_parser.parse_known_args()

    # Paths (relative to script location in parsers folder)
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

    count_processed = 0
    count_updated = 0
    
    print("Starting years scan...")
    
    # Regex for parsing
    # Pattern 1: Native (Gregorian) -> "1334 (1923-1924)"
    regex_paren = re.compile(r"(.+)\s+\((.+)\)")
    
    # Pattern 2: Gregorian Range -> "2002-2025" or "2005-Date"
    regex_range = re.compile(r"(\d+)\s*[-–]\s*(\d+|Date|date)") # Hyphen or En-dash
    
    # Pattern 3: Single Year -> "2002"
    regex_single = re.compile(r"(\d+)")

    for coin_type_id, coin_html_path in iter_coin_html_targets(
        html_root, args.coin_type_id, args.coin_html_path
    ):
        count_processed += 1
        if count_processed % 1000 == 0:
            print(f"Processed {count_processed} coins...")
            conn.commit()

        try:
            with open(coin_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            print(f"Error reading {coin_html_path}: {e}")
            continue
                
        soup = BeautifulSoup(html_content, 'html.parser')
            
        # --- Parsing Year ---
        # Search for "Year" or "Years" in th
        year_header = soup.find('th', string=lambda text: text and ('Year' in text or 'Years' in text))
        
        if not year_header:
            continue

        year_td = year_header.find_next_sibling('td')
        if not year_td:
            continue

        raw_text = year_td.get_text(" ", strip=True)
        # Clean up
        clean_text = raw_text.replace('\xa0', ' ').strip()
        
        start_date = None
        end_date = None
        start_native_date = None
        end_native_date = None
        ac_bc = 0 # 0 for AD, 1 for BC
        
        # Detect BC
        if "BC" in clean_text or "B.C." in clean_text:
            ac_bc = 1
            # Remove BC text for parsing numbers? 
            # Handling BC dates might be complex if they are negative or just marked.
            # User request: "For AC and BC set is_bc to 1" (Assuming AC is AD? Or simple toggle)
            # Usually AC means Ante Christum? Or After Christ? AD is Anno Domini.
            # Assuming BC flag is enough.
        
        # Parsing Logic
        # 1. Check Parentheses: "Native (Gregorian)"
        match_paren = regex_paren.match(clean_text)
        
        native_part = None
        gregorian_part = clean_text # Default if no parens
        
        if match_paren:
            native_part = match_paren.group(1).strip()
            gregorian_part = match_paren.group(2).strip()
        
        # helper to parse range
        def parse_gregorian_range(text):
            s, e = None, None
            match_range = regex_range.search(text)
            if match_range:
                s_str = match_range.group(1)
                e_str = match_range.group(2)
                
                if s_str.isdigit(): s = int(s_str)
                
                if e_str.lower() == "date":
                    e = None 
                elif e_str.isdigit():
                    e = int(e_str)
            else:
                match_single = regex_single.search(text)
                if match_single:
                    s = int(match_single.group(1))
                    e = s
            return s, e

        start_date, end_date = parse_gregorian_range(gregorian_part)
        
        if native_part:
            start_native_date, end_native_date = parse_gregorian_range(native_part)

        # Prepare Update
        try:
            # Update cols: start_date, end_date, start_native_date, end_native_date, ac_bc_designator
            cursor.execute("""
                UPDATE coin_types 
                SET start_date = ?, 
                    end_date = ?,
                    start_native_date = ?, 
                    end_native_date = ?,
                    ac_bc_designator = ?,
                    years_text = ?
                WHERE id = ?
            """, (start_date, end_date, start_native_date, end_native_date, ac_bc, clean_text, coin_type_id))
            count_updated += 1
        except Exception as db_err:
            print(f"Error updating DB for coin {coin_type_id}: {db_err}")

    conn.commit()
    conn.close()
    print(f"Done. Processed {count_processed}. Updated {count_updated}.")

if __name__ == "__main__":
    main()
