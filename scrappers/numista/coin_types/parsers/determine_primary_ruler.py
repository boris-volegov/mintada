import os
import sqlite3

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
    
    # 1. Reset is_primary to NULL (only mark 1/0 if competition exists)
    cursor.execute("UPDATE issuers_rulers_rel_new SET is_primary = NULL")
    conn.commit()

    # 2. Find all Coin Types that have MULTIPLE Ruling Authorities (for any issuer)
    # We want to analyze "competitions" inside coin types.
    print("Identifying coin types with multiple Ruling Authorities...")
    cursor.execute("""
        SELECT coin_type_id
        FROM coin_type_ruling_authorities
        GROUP BY coin_type_id
        HAVING COUNT(*) > 1
    """)
    multi_ra_coin_types = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(multi_ra_coin_types)} coin types with multiple RAs.")

    # Data structure to track pairwise stats per issuer
    pair_stats = {} 
    
    count_processed = 0
    
    for ct_id in multi_ra_coin_types:
        count_processed += 1
        if count_processed % 5000 == 0:
            print(f"Processed {count_processed} coin types...")
            
        cursor.execute("""
            SELECT ctra.ruling_authority_id, ctra.is_match, irr.issuer_id 
            FROM coin_type_ruling_authorities ctra
            JOIN issuers_rulers_rel_new irr ON irr.id = ctra.ruling_authority_id
            WHERE ctra.coin_type_id = ?
        """, (ct_id,))
        rows = cursor.fetchall()
        
        # Group by issuer
        issuers_in_ct = {}
        for r in rows:
            ra_id, is_match, issuer_id = r
            if issuer_id not in issuers_in_ct:
                issuers_in_ct[issuer_id] = []
            issuers_in_ct[issuer_id].append({'id': ra_id, 'match': is_match})
            
        for issuer_id, ras in issuers_in_ct.items():
            if len(ras) < 2:
                continue
                
            # Compare all pairs
            for i in range(len(ras)):
                for j in range(i + 1, len(ras)):
                    ra1 = ras[i]
                    ra2 = ras[j]
                    
                    id1, id2 = ra1['id'], ra2['id']
                    m1, m2 = ra1['match'], ra2['match']
                    
                    key = tuple(sorted((id1, id2)))
                    if key not in pair_stats:
                        pair_stats[key] = {'wins': {id1: 0, id2: 0}, 'ties': 0}
                        
                    if m1 == 1 and m2 == 0:
                        pair_stats[key]['wins'][id1] += 1
                    elif m1 == 0 and m2 == 1:
                        pair_stats[key]['wins'][id2] += 1
                    else:
                        pair_stats[key]['ties'] += 1

    print("Analyzing pairwise competitions...")
    
    # We need to ensure a Primary ruler wins ALL battles it participates in.
    # Logic:
    # 1. Track 'strict_winners': RAs that have at least one strict win against someone.
    # 2. Track 'non_perfect_results': RAs that participated in a pair but did NOT strictly win that specific pair.
    #    - If A strictly beats B: A is winner, B is non-perfect.
    #    - If A vs B is tie/mixed: A is non-perfect, B is non-perfect.
    # Final Primary = strict_winners - non_perfect_results
    # Final Secondary (0) = (All Participants) - Final Primary
    
    strict_winners = set()
    non_perfect_participants = set()
    all_participants = set()
    
    for (id1, id2), stats in pair_stats.items():
        all_participants.add(id1)
        all_participants.add(id2)
        
        wins1 = stats['wins'][id1]
        wins2 = stats['wins'][id2]
        ties = stats['ties']
        
        # Check dominance
        id1_dominates = (wins1 > 0 and wins2 == 0 and ties == 0)
        id2_dominates = (wins2 > 0 and wins1 == 0 and ties == 0)
        
        if id1_dominates:
            strict_winners.add(id1)
            # id2 lost, so it has a non-perfect result
            non_perfect_participants.add(id2)
        elif id2_dominates:
            strict_winners.add(id2)
            # id1 lost
            non_perfect_participants.add(id1)
        else:
            # Tie, mixed, or no wins - both have non-perfect results for this pair
            non_perfect_participants.add(id1)
            non_perfect_participants.add(id2)

    final_primaries = strict_winners - non_perfect_participants
    final_secondaries = all_participants - final_primaries
    
    print(f"Identified {len(final_primaries)} primary candidates (Perfect Winners) and {len(final_secondaries)} secondary candidates (Participants with at least one loss/tie).")
    
    # Update Primaries (1)
    for ra_id in final_primaries:
        cursor.execute("UPDATE issuers_rulers_rel_new SET is_primary = 1 WHERE id = ?", (ra_id,))
        count_updated += 1
        if count_updated % 100 == 0:
            conn.commit()
            print(f"Updated {count_updated} records (1)...")
            
    # Update Secondaries (0)
    for ra_id in final_secondaries:
        cursor.execute("UPDATE issuers_rulers_rel_new SET is_primary = 0 WHERE id = ?", (ra_id,))
        count_updated += 1
        if count_updated % 100 == 0:
            conn.commit()
            print(f"Updated {count_updated} records (0)...")


    conn.commit()
    print(f"Finished processing. Total primary rulers identified and updated: {count_updated}")
    conn.close()

if __name__ == "__main__":
    main()
