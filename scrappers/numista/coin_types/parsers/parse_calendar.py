import os
import sqlite3
import html
import unicodedata
import argparse
from bs4 import BeautifulSoup
from _coin_inputs import iter_coin_html_targets


def main():
    arg_parser = argparse.ArgumentParser(description="Parse calendar field from coin_type.html")
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
    unknown_calendars = set()

    cursor.execute("SELECT id, name FROM calendar_systems")
    calendar_map = {
        (row[1] or "").strip().lower(): row[0]
        for row in cursor.fetchall()
        if row[1]
    }

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

        calendar_header = soup.find("th", string=lambda text: text and "Calendar" in text)
        if not calendar_header:
            calendar_header = soup.find("td", string=lambda text: text and "Calendar" in text)

        if not calendar_header:
            continue

        value_td = calendar_header.find_next_sibling("td")
        if not value_td:
            continue

        raw_text = value_td.get_text(separator=" ", strip=True)
        cleaned_text = html.unescape(raw_text)
        cleaned_text = unicodedata.normalize("NFKC", cleaned_text)
        cleaned_text = cleaned_text.replace("\xa0", " ").strip()

        if cleaned_text:
            calendar_id = calendar_map.get(cleaned_text.lower())
            if calendar_id is None:
                unknown_calendars.add(cleaned_text)
                continue
            try:
                cursor.execute(
                    "UPDATE coin_types SET calendar_system_id = ? WHERE id = ?",
                    (calendar_id, coin_type_id),
                )
                count_updated += 1
            except Exception as db_err:
                print(f"Error updating DB for coin {coin_type_id}: {db_err}")

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coins updated: {count_updated}")
    if unknown_calendars:
        print(
            f"Skipped {len(unknown_calendars)} unknown calendar name(s): "
            + ", ".join(sorted(list(unknown_calendars))[:10])
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
