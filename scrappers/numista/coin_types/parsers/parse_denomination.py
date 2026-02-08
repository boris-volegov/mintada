import argparse
import html
import os
import re
import sqlite3
import unicodedata

from bs4 import BeautifulSoup

from _coin_inputs import iter_coin_html_targets


UNICODE_FRACTIONS = {
    "\u00bc": "1/4",
    "\u00bd": "1/2",
    "\u00be": "3/4",
    "\u2150": "1/7",
    "\u2151": "1/9",
    "\u2152": "1/10",
    "\u2153": "1/3",
    "\u2154": "2/3",
    "\u2155": "1/5",
    "\u2156": "2/5",
    "\u2157": "3/5",
    "\u2158": "4/5",
    "\u2159": "1/6",
    "\u215a": "5/6",
    "\u215b": "1/8",
    "\u215c": "3/8",
    "\u215d": "5/8",
    "\u215e": "7/8",
    "Ã‚Â¼": "1/4",
    "Ã‚Â½": "1/2",
    "Ã‚Â¾": "3/4",
}


def _normalize_text(text: str) -> str:
    normalized = html.unescape(text)
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.replace("\xa0", " ")
    normalized = normalized.replace("\u2044", "/").replace("Ã¢Ââ€ž", "/")

    for fraction_char, fraction_text in UNICODE_FRACTIONS.items():
        if fraction_char in normalized:
            normalized = re.sub(
                f"(?<=\\d){re.escape(fraction_char)}",
                f" {fraction_text}",
                normalized,
            )
            normalized = normalized.replace(fraction_char, fraction_text)

    return " ".join(normalized.split()).strip()


def _starts_with_numeric_or_fraction(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[0].isdigit():
        return True
    return any(stripped.startswith(fraction_char) for fraction_char in UNICODE_FRACTIONS)


def _extract_denomination_text(soup: BeautifulSoup) -> str | None:
    value_header = soup.find("th", string=lambda text: text and "Value" in text)
    if not value_header:
        value_header = soup.find("td", string=lambda text: text and "Value" in text)
    if not value_header:
        return None

    value_td = value_header.find_next_sibling("td")
    if not value_td:
        return None

    raw_text = value_td.get_text(separator="\n", strip=True)
    if not raw_text:
        return None

    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    if not lines:
        return None

    main_value = lines[0]
    main_value = re.sub(r"\s*\([^)]*\)\s*", " ", main_value).strip()
    if "=" in main_value:
        main_value = main_value.split("=", 1)[0].strip()

    if not main_value:
        return None

    if not _starts_with_numeric_or_fraction(main_value):
        main_value = f"1 {main_value}"

    return _normalize_text(main_value)


def main():
    arg_parser = argparse.ArgumentParser(
        description="Populate denomination_text from coin_type.html"
    )
    arg_parser.add_argument("--coin-type-id", type=int, default=None)
    arg_parser.add_argument("--coin-html-path", default=None)
    args, _ = arg_parser.parse_known_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, "../../../../data/numista/coins.db"))
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

    count_processed = 0
    count_updated = 0

    print("Starting denomination_text scan...")

    for coin_type_id, coin_html_path in iter_coin_html_targets(
        html_root, args.coin_type_id, args.coin_html_path
    ):
        count_processed += 1
        if count_processed % 1000 == 0:
            print(f"Processed {count_processed} coins...")
            conn.commit()

        try:
            with open(coin_html_path, "r", encoding="utf-8") as html_file:
                html_content = html_file.read()
        except Exception as ex:
            print(f"Error reading {coin_html_path}: {ex}")
            continue

        soup = BeautifulSoup(html_content, "html.parser")
        denomination_text = _extract_denomination_text(soup)
        if not denomination_text:
            continue

        try:
            cursor.execute(
                "UPDATE coin_types SET denomination_text = ? WHERE id = ?",
                (denomination_text, coin_type_id),
            )
            count_updated += 1
        except Exception as db_ex:
            print(f"Error updating DB for coin {coin_type_id}: {db_ex}")

    conn.commit()
    conn.close()
    print(f"Done. Processed {count_processed}. Updated {count_updated}.")


if __name__ == "__main__":
    main()
