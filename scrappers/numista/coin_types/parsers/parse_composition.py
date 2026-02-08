import os
import sqlite3
import argparse
from bs4 import BeautifulSoup
from _coin_inputs import iter_coin_html_targets


def main():
    arg_parser = argparse.ArgumentParser(description="Parse composition field from coin_type.html")
    arg_parser.add_argument("--coin-type-id", type=int, default=None)
    arg_parser.add_argument("--coin-html-path", default=None)
    args, _ = arg_parser.parse_known_args()

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
    cursor = conn.cursor()

    count_updated = 0
    count_processed = 0

    for coin_type_id, coin_html_path in iter_coin_html_targets(
        html_root, args.coin_type_id, args.coin_html_path
    ):
        count_processed += 1
        if count_processed % 1000 == 0:
            print(f"Processed {count_processed} coins...")
            conn.commit()

        try:
            with open(coin_html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except Exception as e:
            print(f"Error reading {coin_html_path}: {e}")
            continue

        soup = BeautifulSoup(html_content, "html.parser")

        composition_header = soup.find("th", string=lambda text: text and "Composition" in text)
        if not composition_header:
            composition_header = soup.find("td", string=lambda text: text and "Composition" in text)

        if not composition_header:
            continue

        value_td = composition_header.find_next_sibling("td")
        if not value_td:
            continue

        raw_text = value_td.get_text(strip=True)
        cleaned_text = raw_text.replace("\xa0", " ").replace("&nbsp;", " ").strip()

        if cleaned_text:
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
