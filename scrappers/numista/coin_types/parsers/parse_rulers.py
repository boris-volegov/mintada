import os
import sqlite3
import re
from bs4 import BeautifulSoup

def main():
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Expected location: d:\projects\mintada\scrappers\numista\coin_types\parsers
    
    # DB Path: ../../../../data/numista/coins.db
    # Resolves to: d:\projects\mintada\data\numista\coins.db
    db_path = os.path.abspath(os.path.join(current_dir, "../../../../data/numista/coins.db"))
    
    # HTML Root: ../html
    # Resolves to: d:\projects\mintada\scrappers\numista\coin_types\html
    html_root = os.path.abspath(os.path.join(current_dir, "../html"))
    
    print(f"Script Location: {current_dir}")
    print(f"DB Path: {db_path}")
    print(f"HTML Root: {html_root}")

    if not os.path.exists(db_path):
        print("Error: Database not found!")
        return

    if not os.path.exists(html_root):
        print("Error: HTML root folder not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count_inserted = 0
    count_processed = 0
    
    # Iterate issuer folders
    issuer_folders = [f for f in os.listdir(html_root) if os.path.isdir(os.path.join(html_root, f))]
    
    print(f"Found {len(issuer_folders)} issuer folders. Starting processing...")

    for issuer_folder in issuer_folders:
        issuer_path = os.path.join(html_root, issuer_folder)
        coin_folders = [f for f in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, f))]
        
        for coin_folder in coin_folders:
            count_processed += 1
            if count_processed % 100 == 0:
                print(f"Processed {count_processed} coins...")
                conn.commit()

            # Parse coin_type_id
            try:
                # Folder format: name_id, e.g. 10_ducats_1571_415900 -> 415900
                coin_type_id_str = coin_folder.split('_')[-1]
                coin_type_id = int(coin_type_id_str)
            except ValueError:
                # print(f"Skipping folder with invalid format: {coin_folder}")
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
            
            # Find section id="fiche_caracteristiques"
            section = soup.find('section', id="fiche_caracteristiques")
            if not section:
                continue
                
            # Find table row with ruler link
            # Look for <a> with href containing "ruler.php?id=" inside the section
            # The structure is usually <tr><th>Title</th><td><a>...</a></td></tr>
            # We search specifically for the link.
            ruler_links = section.select('a[href*="/catalogue/ruler.php?id="]')
            
            for ruler_link in ruler_links:
                href = ruler_link.get('href')
                # Parse ruler_id
                match = re.search(r'id=(\d+)', href)
                if match:
                    ruler_id = int(match.group(1))
                    
                    # Parse period_years from span
                    # Example: <span dir="ltr">(<em>1901-1910</em>)</span>
                    # We need to find the span relative to the current ruler_link
                    # Note: BeautifulSoup object extraction modifies the tree, so finding span inside the element 
                    # before modifying it is important. However, 'ruler_link' is a tag object.
                    span = ruler_link.find('span')
                    period_years = ""
                    if span:
                        period_years = span.get_text(strip=True)
                        if period_years.startswith('(') and period_years.endswith(')'):
                            period_years = period_years[1:-1].strip()
                        # Remove the span from the link to extract just the ruler name
                        # Be careful if we are iterating, modifying the tree might affect things if not careful,
                        # but here we are modifying the 'ruler_link' subtree which is fine.
                        span.extract()
                        
                    ruler_name = ruler_link.get_text(strip=True)
                    alt_period_name = None
                    extra = None

                    # 1. Clean period_name: Move content in () to alt_period_name
                    if ruler_name and ruler_name.strip().endswith(')'):
                        match = re.search(r'^(.*)\(([^)]+)\)$', ruler_name.strip())
                        if match:
                            ruler_name = match.group(1).strip()
                            alt_period_name = match.group(2).strip()

                    # 2. Handle hierarchy separator: "Context › Name"
                    if ruler_name and '›' in ruler_name:
                        parts = ruler_name.split('›')
                        # Assuming the last part is the name, and everything before is context
                        ruler_name = parts[-1].strip()
                        extra = '›'.join(parts[:-1]).strip()
                    
                    
                    # Lookup issuer_id for this coin_type
                    cursor.execute("SELECT issuer_id FROM coin_types WHERE id = ?", (coin_type_id,))
                    row = cursor.fetchone()
                    
                    if row:
                        issuer_id = row[0]
                        if issuer_id is not None:
                            # --- 1. Insert/Get ID from issuers_rulers_rel_new ---
                            
                            # Check if record already exists in issuers_rulers_rel_new
                            # Use ruler_id, period_years
                            cursor.execute("SELECT id FROM issuers_rulers_rel_new WHERE issuer_id = ? AND ruler_id = ? AND period_years = ?", (issuer_id, ruler_id, period_years))
                            exists = cursor.fetchone()
                            
                            ruling_authority_id = None
                            
                            if exists:
                                ruling_authority_id = exists[0]
                            else:
                                cursor.execute("""
                                    INSERT INTO issuers_rulers_rel_new (issuer_id, ruler_id, ruling_authority, alt_ruling_authority, period_years, extra) 
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (issuer_id, ruler_id, ruler_name, alt_period_name, period_years, extra))
                                ruling_authority_id = cursor.lastrowid
                                count_inserted += 1
                                
                            # --- 2. Insert into coin_type_ruling_authorities ---
                            
                            if ruling_authority_id:
                                # Determine is_match
                                
                                is_match = 0
                                
                                # We need details from issuers table for the check
                                cursor.execute("SELECT name, numista_name, numista_territory_type FROM issuers WHERE id = ?", (issuer_id,))
                                issuer_row = cursor.fetchone()
                                
                                if issuer_row:
                                    i_name, i_numista_name, i_numista_territory_type = issuer_row
                                    
                                    # Construct variants for issuer_name
                                    variant1 = f"{i_numista_name}, {i_numista_territory_type}" if i_numista_territory_type else i_numista_name
                                    variant2 = i_numista_name
                                    variant3 = i_name
                                    
                                    # Check for match in old table
                                    # Logic:
                                    # ruler_id = ruler_id
                                    # AND (years_text = period_years OR period_years IS Empty)
                                    # AND (issuer_name IN variants)
                                    
                                    p_years_val = period_years if period_years else ""
                                    
                                    query_match = """
                                        SELECT 1 FROM issuers_rulers_rel 
                                        WHERE ruler_id = ? 
                                        AND (years_text = ? OR ? = '')
                                        AND (issuer_name = ? OR issuer_name = ? OR issuer_name = ?)
                                    """
                                    cursor.execute(query_match, (ruler_id, p_years_val, p_years_val, variant1, variant2, variant3))
                                    if cursor.fetchone():
                                        is_match = 1
                                
                                # Insert into coin_type_ruling_authorities
                                # Check existence first
                                cursor.execute("SELECT 1 FROM coin_type_ruling_authorities WHERE coin_type_id = ? AND ruling_authority_id = ?", (coin_type_id, ruling_authority_id))
                                if not cursor.fetchone():
                                    cursor.execute("""
                                        INSERT INTO coin_type_ruling_authorities (coin_type_id, ruling_authority_id, is_match)
                                        VALUES (?, ?, ?)
                                    """, (coin_type_id, ruling_authority_id, is_match))

    print(f"Finished processing {count_processed} coins.")
    print(f"Total new records inserted into issuers_rulers_rel_new: {count_inserted}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
