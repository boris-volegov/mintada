import argparse
import html
import os
import re
import sqlite3
import unicodedata


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

MIXED_FRACTION_RE = re.compile(
    r"^(?P<whole>(?:\d{1,3}(?:[ ,]\d{3})+|\d+))\s+(?P<numer>\d+)/(?P<denom>\d+)\s+(?P<unit>.+)$"
)
FRACTION_RE = re.compile(r"^(?P<numer>\d+)/(?P<denom>\d+)\s+(?P<unit>.+)$")
NUMBER_RE = re.compile(
    r"^(?P<number>(?:\d{1,3}(?:[ ,]\d{3})+|\d+)(?:\.\d+)?)\s+(?P<unit>.+)$"
)


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


def _normalize_numeric_token(token: str) -> str:
    return token.replace(" ", "").replace(",", "")


def _escape_like(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _pick_default_unit_from_similar_rows(
    cursor: sqlite3.Cursor,
    coin_id: int,
    parsed_unit: str,
) -> str:
    normalized_unit = parsed_unit.strip()
    if not normalized_unit:
        return parsed_unit

    pattern = f"%{_escape_like(normalized_unit)}%"
    cursor.execute(
        """
        SELECT denomination_unit, COUNT(*) AS usage_count
        FROM coin_types
        WHERE id != ?
          AND denomination_text IS NOT NULL
          AND denomination_text != ''
          AND denomination_unit IS NOT NULL
          AND TRIM(denomination_unit) != ''
          AND LOWER(denomination_text) LIKE LOWER(?) ESCAPE '\\'
        GROUP BY denomination_unit
        ORDER BY usage_count DESC,
                 CASE WHEN LOWER(denomination_unit) = LOWER(?) THEN 0 ELSE 1 END ASC,
                 LENGTH(denomination_unit) ASC,
                 denomination_unit ASC
        LIMIT 1
        """,
        (coin_id, pattern, normalized_unit),
    )
    row = cursor.fetchone()
    if row and row["denomination_unit"]:
        return row["denomination_unit"].strip()
    return parsed_unit


def _parse_derived_fields(denomination_text: str) -> tuple[str, str] | None:
    text = _normalize_text(denomination_text)
    if not text:
        return None

    mixed_match = MIXED_FRACTION_RE.match(text)
    if mixed_match:
        whole = _normalize_numeric_token(mixed_match.group("whole"))
        numer = mixed_match.group("numer")
        denom = mixed_match.group("denom")
        unit = mixed_match.group("unit").strip()
        if not unit:
            return None
        if whole == "0":
            value_amount = f"{numer}/{denom}"
        else:
            value_amount = f"{whole} {numer}/{denom}"
        return value_amount, unit

    fraction_match = FRACTION_RE.match(text)
    if fraction_match:
        numer = fraction_match.group("numer")
        denom = fraction_match.group("denom")
        unit = fraction_match.group("unit").strip()
        if not unit:
            return None
        value_amount = f"{numer}/{denom}"
        return value_amount, unit

    number_match = NUMBER_RE.match(text)
    if number_match:
        value_amount = _normalize_numeric_token(number_match.group("number"))
        unit = number_match.group("unit").strip()
        if not unit:
            return None
        return value_amount, unit

    return None


def main():
    arg_parser = argparse.ArgumentParser(
        description="Parse denomination_unit and value_amount from denomination_text"
    )
    arg_parser.add_argument("--coin-type-id", type=int, default=None)
    arg_parser.add_argument("--coin-html-path", default=None)
    args, _ = arg_parser.parse_known_args()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(current_dir, "../../../../data/numista/coins.db"))

    print(f"Script Location: {current_dir}")
    print(f"DB Path: {db_path}")

    if not os.path.exists(db_path):
        print("Error: Database not found!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    count_processed = 0
    count_updated = 0

    print("Fetching coins with denomination_text...")
    if args.coin_type_id is not None:
        cursor.execute(
            """
            SELECT id, denomination_text
            FROM coin_types
            WHERE id = ? AND denomination_text IS NOT NULL AND denomination_text != ''
            """,
            (args.coin_type_id,),
        )
    else:
        cursor.execute(
            """
            SELECT id, denomination_text
            FROM coin_types
            WHERE denomination_text IS NOT NULL AND denomination_text != ''
            """
        )
    rows = cursor.fetchall()
    print(f"Found {len(rows)} coins to process.")

    for row in rows:
        count_processed += 1
        coin_id = row["id"]
        denomination_text = row["denomination_text"]

        parsed = _parse_derived_fields(denomination_text)
        if not parsed:
            continue

        value_amount, parsed_unit = parsed
        denomination_unit = _pick_default_unit_from_similar_rows(
            cursor=cursor,
            coin_id=coin_id,
            parsed_unit=parsed_unit,
        )
        try:
            cursor.execute(
                """
                UPDATE coin_types
                SET denomination_unit = ?, value_amount = ?
                WHERE id = ?
                """,
                (denomination_unit, value_amount, coin_id),
            )
            count_updated += 1
        except Exception as ex:
            print(f"Error updating coin {coin_id}: {ex}")

        if count_processed % 5000 == 0:
            print(f"Processed {count_processed} coins...")
            conn.commit()

    conn.commit()
    conn.close()
    print(
        f"Done. Processed {count_processed}. Updated {count_updated} denomination-derived fields."
    )


if __name__ == "__main__":
    main()
