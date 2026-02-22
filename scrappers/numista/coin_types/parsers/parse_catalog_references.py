import argparse
import html
import os
import re
import sqlite3
from collections.abc import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from _coin_inputs import iter_coin_html_targets


CATALOG_PATH_TOKEN_PATTERN = re.compile(r"^[A-Za-z](\d+)$")
NBSP_CHARS = ("\u00A0", "\u202F", "\u2009", "\u2007", "\u2060", "\uFEFF")
MAX_SQLITE_PARAMS = 900


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = html.unescape(value)
    for ch in NBSP_CHARS:
        normalized = normalized.replace(ch, " ")
    return " ".join(normalized.split())


def extract_catalog_id_from_href(href: str | None) -> int | None:
    if not href:
        return None
    token = urlparse(href).path.rstrip("/").split("/")[-1]
    match = CATALOG_PATH_TOKEN_PATTERN.match(token)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def normalize_catalog_number(value: str | None) -> str | None:
    cleaned = clean_text(value)
    if not cleaned or not cleaned.startswith("#"):
        return None
    cleaned = re.sub(r"^#\s*", "", cleaned)
    cleaned = cleaned.rstrip(",;")
    if not cleaned:
        return None
    return cleaned


def _extract_numeric_text_tokens(fragment: str | None) -> list[str]:
    cleaned = clean_text(fragment)
    if not cleaned:
        return []

    cleaned = re.sub(r"^[#\s,;:]+", "", cleaned)
    if not cleaned:
        return []

    tokens: list[str] = []
    for part in re.split(r"[;,]", cleaned):
        candidate = part.strip().rstrip(",;")
        if not candidate:
            continue
        if any(ch.isdigit() for ch in candidate):
            tokens.append(candidate)
    return tokens


def find_references_td(soup: BeautifulSoup) -> Tag | None:
    section = soup.find("section", id="fiche_caracteristiques")
    search_root: Tag | BeautifulSoup = section if section is not None else soup

    for row in search_root.find_all("tr"):
        header = row.find("th")
        if header is None:
            continue
        if clean_text(header.get_text(" ", strip=True)).casefold() == "references":
            return row.find("td")

    return None


def extract_catalog_number_after_link(link: Tag) -> str | None:
    started = False
    collected: list[str] = []

    for sibling in link.next_siblings:
        if isinstance(sibling, NavigableString):
            raw = str(sibling)
            if not raw.strip():
                continue
            text = clean_text(raw)
            if not text:
                continue

            if not started:
                if "#" not in text:
                    continue
                started = True
                after_hash = text.split("#", 1)[1]
                collected.extend(_extract_numeric_text_tokens(after_hash))
                continue

            collected.extend(_extract_numeric_text_tokens(text))
            continue

        if not isinstance(sibling, Tag):
            continue

        classes = sibling.get("class") or []
        if sibling.name == "div" and "catalogue_tooltip" in classes:
            break
        if sibling.name == "a" and "fiche_catalogue" in classes:
            break

        sibling_text = clean_text(sibling.get_text(" ", strip=True))
        if not sibling_text:
            continue

        if not started:
            if "#" not in sibling_text:
                continue
            started = True
            after_hash = sibling_text.split("#", 1)[1]
            collected.extend(_extract_numeric_text_tokens(after_hash))
            continue

        if sibling.name == "a":
            cleaned_anchor = normalize_catalog_number(f"#{sibling_text}")
            if cleaned_anchor:
                collected.append(cleaned_anchor)
        else:
            collected.extend(_extract_numeric_text_tokens(sibling_text))

    deduped: list[str] = []
    seen: set[str] = set()
    for token in collected:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)

    if not deduped:
        return None
    return ", ".join(deduped)


def chunked(values: list[int], size: int) -> Iterable[list[int]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def resolve_coin_html_paths_from_db(
    connection: sqlite3.Connection, html_root: str, coin_type_ids: list[int]
) -> dict[int, str]:
    if not coin_type_ids:
        return {}

    resolved_paths: dict[int, str] = {}
    cursor = connection.cursor()

    for id_chunk in chunked(coin_type_ids, MAX_SQLITE_PARAMS):
        placeholders = ",".join(["?"] * len(id_chunk))
        query = f"""
            SELECT
                ct.id,
                ct.coin_type_slug,
                i.numista_url_slug
            FROM coin_types AS ct
            LEFT JOIN issuers AS i ON i.id = ct.issuer_id
            WHERE ct.id IN ({placeholders})
        """
        rows = cursor.execute(query, id_chunk).fetchall()

        for row in rows:
            coin_type_id = int(row[0])
            coin_type_slug = clean_text(row[1] if row[1] is not None else "")
            issuer_slug = clean_text(row[2] if row[2] is not None else "")

            if not coin_type_slug or not issuer_slug:
                continue

            candidate_path = os.path.join(
                html_root, issuer_slug, f"{coin_type_slug}_{coin_type_id}", "coin_type.html"
            )
            if os.path.isfile(candidate_path):
                resolved_paths[coin_type_id] = candidate_path

    return resolved_paths


def scan_coin_html_paths_by_id(html_root: str, target_ids: set[int]) -> dict[int, str]:
    if not target_ids:
        return {}
    if not os.path.isdir(html_root):
        return {}

    resolved: dict[int, str] = {}

    for issuer_folder in os.listdir(html_root):
        issuer_path = os.path.join(html_root, issuer_folder)
        if not os.path.isdir(issuer_path):
            continue

        for coin_folder in os.listdir(issuer_path):
            folder_path = os.path.join(issuer_path, coin_folder)
            if not os.path.isdir(folder_path):
                continue

            parts = coin_folder.rsplit("_", 1)
            if len(parts) != 2:
                continue
            try:
                coin_type_id = int(parts[1])
            except ValueError:
                continue

            if coin_type_id not in target_ids:
                continue

            html_path = os.path.join(folder_path, "coin_type.html")
            if os.path.isfile(html_path):
                resolved[coin_type_id] = html_path

    return resolved


def ensure_catalog_exceptions_table(connection: sqlite3.Connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS _catalog_exceptions (
            issuer_id INTEGER,
            coin_type_id INTEGER NOT NULL,
            catalog_id INTEGER NOT NULL,
            success INTEGER DEFAULT 0
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_catalog_exceptions_coin_catalog
        ON _catalog_exceptions (coin_type_id, catalog_id)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_catalog_exceptions_coin_catalog
        ON _catalog_exceptions (coin_type_id, catalog_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_catalog_exceptions_success
        ON _catalog_exceptions (success)
        """
    )


def upsert_catalog_exception(
    cursor: sqlite3.Cursor,
    issuer_id: int | None,
    coin_type_id: int,
    catalog_id: int,
    success: int,
):
    cursor.execute(
        """
        INSERT INTO _catalog_exceptions (issuer_id, coin_type_id, catalog_id, success)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(coin_type_id, catalog_id) DO UPDATE SET
            issuer_id = excluded.issuer_id,
            success = excluded.success
        """,
        (issuer_id, coin_type_id, catalog_id, success),
    )


def mark_catalog_exception_success(cursor: sqlite3.Cursor, coin_type_id: int, catalog_id: int) -> int:
    cursor.execute(
        """
        UPDATE _catalog_exceptions
        SET success = 1
        WHERE coin_type_id = ? AND catalog_id = ?
        """,
        (coin_type_id, catalog_id),
    )
    return int(cursor.rowcount or 0)


def load_coin_type_ids_from_exceptions(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        """
        SELECT DISTINCT coin_type_id
        FROM _catalog_exceptions
        WHERE COALESCE(success, 0) = 0
        ORDER BY coin_type_id
        """
    ).fetchall()
    return [int(row[0]) for row in rows if row and row[0] is not None]


def main():
    arg_parser = argparse.ArgumentParser(
        description=(
            "Parse catalog references from coin_type.html into coin_types_catalogs_rel "
            "and track failures in _catalog_exceptions."
        )
    )
    arg_parser.add_argument("--coin-type-id", type=int, default=None)
    arg_parser.add_argument("--coin-html-path", default=None)
    arg_parser.add_argument(
        "--from-exceptions",
        "--from_exceptions",
        action="store_true",
        help="Process only coin_type entries listed in _catalog_exceptions with success=0.",
    )
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

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    ensure_catalog_exceptions_table(conn)

    existing_catalog_ids = {
        int(row[0])
        for row in cursor.execute("SELECT id FROM catalogs WHERE id IS NOT NULL").fetchall()
    }
    coin_type_issuer_map = {
        int(row[0]): int(row[1]) if row[1] is not None else None
        for row in cursor.execute("SELECT id, issuer_id FROM coin_types").fetchall()
    }

    processed = 0
    upserted_relations = 0
    missing_catalog_rows = 0
    exceptions_written = 0
    exceptions_resolved = 0

    targets: list[tuple[int, str]] = []
    if args.from_exceptions:
        exception_coin_type_ids = load_coin_type_ids_from_exceptions(conn)
        if not exception_coin_type_ids:
            print("No unresolved rows in _catalog_exceptions. Nothing to process.")
            conn.close()
            return

        print(f"Loaded {len(exception_coin_type_ids)} coin_type_id entries from _catalog_exceptions.")

        resolved_from_db = resolve_coin_html_paths_from_db(conn, html_root, exception_coin_type_ids)
        unresolved_ids = sorted(set(exception_coin_type_ids) - set(resolved_from_db.keys()))
        if unresolved_ids:
            resolved_from_scan = scan_coin_html_paths_by_id(html_root, set(unresolved_ids))
            resolved_from_db.update(resolved_from_scan)
            unresolved_ids = sorted(set(exception_coin_type_ids) - set(resolved_from_db.keys()))

        if unresolved_ids:
            print(
                f"[WARN] Could not resolve coin_type.html for {len(unresolved_ids)} exception coin_type_id values."
            )

        targets = sorted(resolved_from_db.items(), key=lambda item: item[0])
    else:
        targets = list(iter_coin_html_targets(html_root, args.coin_type_id, args.coin_html_path))

    for coin_type_id, coin_html_path in targets:
        processed += 1
        if processed % 1000 == 0:
            print(f"Processed {processed} coin types...")
            conn.commit()

        try:
            with open(coin_html_path, "r", encoding="utf-8") as file:
                html_content = file.read()
        except Exception as ex:
            print(f"Error reading {coin_html_path}: {ex}")
            continue

        soup = BeautifulSoup(html_content, "html.parser")
        references_td = find_references_td(soup)
        if references_td is None:
            continue

        relations_to_upsert: list[tuple[int, int, str]] = []
        seen_pairs: set[tuple[int, int]] = set()
        issuer_id = coin_type_issuer_map.get(coin_type_id)

        for link in references_td.find_all("a", class_="fiche_catalogue", href=True):
            catalog_id = extract_catalog_id_from_href(link.get("href"))
            if catalog_id is None:
                continue

            if catalog_id not in existing_catalog_ids:
                missing_catalog_rows += 1
                upsert_catalog_exception(cursor, issuer_id, coin_type_id, catalog_id, success=0)
                exceptions_written += 1
                continue

            catalog_number = extract_catalog_number_after_link(link)
            if catalog_number is None:
                upsert_catalog_exception(cursor, issuer_id, coin_type_id, catalog_id, success=0)
                exceptions_written += 1
                continue

            pair_key = (coin_type_id, catalog_id)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            relations_to_upsert.append((coin_type_id, catalog_id, catalog_number))
            exceptions_resolved += mark_catalog_exception_success(cursor, coin_type_id, catalog_id)

        if relations_to_upsert:
            cursor.executemany(
                """
                INSERT INTO coin_types_catalogs_rel (coin_type_id, catalog_id, catalog_number)
                VALUES (?, ?, ?)
                ON CONFLICT(coin_type_id, catalog_id) DO UPDATE SET
                    catalog_number = excluded.catalog_number
                """,
                relations_to_upsert,
            )
            upserted_relations += len(relations_to_upsert)

    unresolved_after = cursor.execute(
        "SELECT COUNT(*) FROM _catalog_exceptions WHERE COALESCE(success, 0) = 0"
    ).fetchone()
    unresolved_count = int(unresolved_after[0]) if unresolved_after and unresolved_after[0] is not None else 0

    conn.commit()
    conn.close()

    print(f"Finished processing {processed} coin types.")
    print(f"Catalog relations upserted: {upserted_relations}")
    print(f"References skipped because catalog_id is not in catalogs table: {missing_catalog_rows}")
    print(f"Exceptions written/updated with success=0: {exceptions_written}")
    print(f"Exceptions marked success=1: {exceptions_resolved}")
    print(f"Unresolved exceptions remaining in _catalog_exceptions: {unresolved_count}")


if __name__ == "__main__":
    main()
