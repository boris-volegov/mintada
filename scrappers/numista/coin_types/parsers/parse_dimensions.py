import os
import sqlite3
import re
import argparse
from bs4 import BeautifulSoup
from _coin_inputs import iter_coin_html_targets


def main():
    arg_parser = argparse.ArgumentParser(description="Parse dimensions fields from coin_type.html")
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
        print(f"Error: HTML root not found at {html_root}")
        return

    conn = sqlite3.connect(db_path, timeout=30.0)
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

        def parse_field(field_name, unit_suffix):
            th = soup.find("th", string=lambda text: text and field_name in text)
            if not th:
                return None, None, None

            td = th.find_next_sibling("td")
            if not td:
                return None, None, None

            raw_text = td.get_text(strip=True)
            if not raw_text:
                return None, None, None

            info_val = None
            numeric_val = None

            match_info = re.search(r"\((.*?)\)", raw_text)
            if match_info:
                info_val = match_info.group(1).strip()
                raw_text_clean = re.sub(r"\(.*?\)", "", raw_text).strip()
            else:
                raw_text_clean = raw_text

            if unit_suffix and raw_text_clean.endswith(unit_suffix):
                val_str = raw_text_clean[: -len(unit_suffix)].strip()
            else:
                val_str = raw_text_clean.strip()

            try:
                val_str = val_str.replace(",", ".")
                if val_str:
                    numeric_val = float(val_str)
            except ValueError:
                pass

            return numeric_val, info_val, raw_text

        weight, weight_info, weight_raw = parse_field("Weight", "g")
        diameter, diameter_info, diameter_raw = parse_field("Diameter", "mm")
        thickness, thickness_info, thickness_raw = parse_field("Thickness", "mm")

        cursor.execute(
            "SELECT weight_info, diameter_info, thickness_info FROM coin_types WHERE id = ?",
            (coin_type_id,),
        )
        row = cursor.fetchone()
        current_w_info, current_d_info, current_t_info = row if row else (None, None, None)

        def merge_info(new_info, current_info):
            if not new_info:
                return current_info
            if current_info:
                return f"{current_info}; {new_info}"
            return new_info

        final_w_info = merge_info(weight_info, current_w_info)
        final_d_info = merge_info(diameter_info, current_d_info)
        final_t_info = merge_info(thickness_info, current_t_info)

        try:
            msg = []
            if weight is not None:
                cursor.execute("UPDATE coin_types SET weight = ? WHERE id = ?", (weight, coin_type_id))
                msg.append("weight")
            if final_w_info != current_w_info:
                cursor.execute(
                    "UPDATE coin_types SET weight_info = ? WHERE id = ?",
                    (final_w_info, coin_type_id),
                )
                msg.append("weight_info")

            if diameter is not None:
                cursor.execute("UPDATE coin_types SET diameter = ? WHERE id = ?", (diameter, coin_type_id))
                msg.append("diameter")
            if final_d_info != current_d_info:
                cursor.execute(
                    "UPDATE coin_types SET diameter_info = ? WHERE id = ?",
                    (final_d_info, coin_type_id),
                )
                msg.append("diameter_info")

            if thickness is not None:
                cursor.execute("UPDATE coin_types SET thickness = ? WHERE id = ?", (thickness, coin_type_id))
                msg.append("thickness")
            if final_t_info != current_t_info:
                cursor.execute(
                    "UPDATE coin_types SET thickness_info = ? WHERE id = ?",
                    (final_t_info, coin_type_id),
                )
                msg.append("thickness_info")

            if msg:
                count_updated += 1

        except Exception as e:
            print(f"Error updating ID {coin_type_id}: {e}")

        ex_w = weight_raw if (weight_raw and weight is None) else None
        ex_d = diameter_raw if (diameter_raw and diameter is None) else None
        ex_t = thickness_raw if (thickness_raw and thickness is None) else None

        if ex_w or ex_d or ex_t:
            cursor.execute(
                "INSERT INTO parse_exceptions (coin_type_id, weight, diameter, thickness) VALUES (?, ?, ?, ?)",
                (coin_type_id, ex_w, ex_d, ex_t),
            )

    print(f"Finished processing {count_processed} coins.")
    print(f"Total coin types updated: {count_updated}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
