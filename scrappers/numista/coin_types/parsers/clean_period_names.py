import os
import sqlite3
import re

def main():
    # Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # DB Path: ../../../../data/numista/coins.db
    db_path = os.path.abspath(os.path.join(current_dir, "../../../../data/numista/coins.db"))
    
    print(f"Script Location: {current_dir}")
    print(f"DB Path: {db_path}")

    if not os.path.exists(db_path):
        print("Error: Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    count_updated = 0
    
    # Select all records to check both fields
    cursor.execute("SELECT rowid, period_name, period_years FROM issuers_rulers_rel_new")
    rows = cursor.fetchall()
    
    print(f"Scanning {len(rows)} records...")

    for row in rows:
        rowid = row[0]
        period_name = row[1]
        period_years = row[2]
        
        updates = {}
        
        # 1. Clean period_name: Move content in () to alt_period_name
        current_period_name = period_name
        if current_period_name and current_period_name.strip().endswith(')'):
            match = re.search(r'^(.*)\(([^)]+)\)$', current_period_name.strip())
            if match:
                clean_name = match.group(1).strip()
                alt_name = match.group(2).strip()
                updates['period_name'] = clean_name
                updates['alt_period_name'] = alt_name
                current_period_name = clean_name
        
        # 2. Handle hierarchy separator: "Context › Name"
        # We use the current_period_name which might have been cleaned in step 1
        if current_period_name and '›' in current_period_name:
            parts = current_period_name.split('›')
            # Assuming the last part is the name, and everything before is context
            # The user example: "Principality of Brunswick-Wolfenbüttel › Rudolph Augustus"
            name_part = parts[-1].strip()
            context_part = '›'.join(parts[:-1]).strip()
            
            updates['period_name'] = name_part
            updates['extra'] = context_part
        
        # 3. Clean period_years: Remove surrounding ()
        if period_years:
            clean_years = period_years.strip()
            if clean_years.startswith('(') and clean_years.endswith(')'):
                clean_years = clean_years[1:-1].strip()
                updates['period_years'] = clean_years
        
        if updates:
            # Construct update query dynamically
            set_clauses = [f"{k} = ?" for k in updates.keys()]
            values = list(updates.values())
            values.append(rowid)
            
            sql = f"UPDATE issuers_rulers_rel_new SET {', '.join(set_clauses)} WHERE rowid = ?"
            cursor.execute(sql, values)
            
            count_updated += 1
            if count_updated % 1000 == 0:
                print(f"Updated {count_updated} records...")

    conn.commit()
    print(f"Finished processing. Total updated records: {count_updated}")
    conn.close()

if __name__ == "__main__":
    main()
