import os
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

# Add parent directory to path to import helpers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from basic_functions import BasicHelper


class IssuerCoinTypesScrapper:
    def __init__(self):
        self.base_url = "https://en.numista.com/"
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.html_root = os.path.join(self.script_dir, "html")
        self.log_file_path = os.path.join(self.script_dir, "pages.log")
        self.db_path = r"D:\projects\mintada\data\numista\coins.db"
        self.basic_helper = BasicHelper()

        self.db_connection = sqlite3.connect(self.db_path)
        self.db_connection.row_factory = sqlite3.Row
        self.db_connection.execute("PRAGMA foreign_keys = ON")

    def close(self):
        self.db_connection.close()

    @staticmethod
    def _normalize_name_for_match(text: str) -> str:
        cleaned = BasicHelper.clean_text(text or "")
        if "›" in cleaned:
            # Ignore higher-level hierarchy prefix, keep only the ruler-side text.
            cleaned = cleaned.rsplit("›", 1)[-1]
        return re.sub(r"\s+", "", cleaned)

    def _build_ruler_match_candidates(self, ruler_name: str) -> list[str]:
        cleaned = BasicHelper.clean_text(ruler_name or "")
        if not cleaned:
            return []

        candidates: list[str] = []
        seen = set()

        def add_candidate(raw_text: str):
            normalized = self._normalize_name_for_match(raw_text)
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

        year_suffix = ""
        year_parenthetical = None
        parenthetical_parts = re.findall(r"\(([^)]*)\)", cleaned)
        if parenthetical_parts:
            last_part = BasicHelper.clean_text(parenthetical_parts[-1])
            if last_part and last_part[0].isdigit():
                year_parenthetical = last_part
                year_suffix = f"({last_part})"

        # 1) Prefer main name with only the date part preserved (if present).
        main_without_parentheses = re.sub(r"\s*\([^)]*\)", "", cleaned)
        add_candidate(f"{main_without_parentheses}{year_suffix}")

        # 2) Fallback to first non-date alias parenthetical with the same date suffix.
        for part in parenthetical_parts:
            alias = BasicHelper.clean_text(part)
            if not alias:
                continue
            if year_parenthetical and alias == year_parenthetical:
                continue
            add_candidate(f"{alias}{year_suffix}")
            break

        # Final fallback to full cleaned text.
        add_candidate(cleaned)

        return candidates

    def _build_issuer_coin_types_url(self, issuer_slug: str) -> str:
        return urljoin(
            self.base_url,
            f"/catalogue/index.php?e={issuer_slug}&r=&st=1&cat=y&im1=&im2=&ru=&ie=&ca=3&no=&v=&a=&dg=&i=&b=&m=&f=&t=&t2=&w=&mt=&u=&g=&q=200",
        )

    def _read_last_log_entry(self):
        if not os.path.exists(self.log_file_path):
            return None, None

        with open(self.log_file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            return None, None

        last_line = lines[-1]
        parts = [p.strip() for p in last_line.split(",")]
        if len(parts) < 2:
            raise RuntimeError(
                f"Malformed pages.log last line (expected 'issuer_id,page'): '{last_line}'"
            )

        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            raise RuntimeError(
                f"Invalid pages.log values (expected integers): '{last_line}'"
            )

    def _log_processed_page(self, issuer_id: int, page: int):
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(f"{issuer_id},{page}\n")

    def get_issuers(self):
        cur = self.db_connection.execute(
            """
            SELECT DISTINCT i.id, i.numista_url_slug
            FROM issuers AS i
            JOIN coin_types AS ct ON ct.issuer_id = i.id
            WHERE i.numista_url_slug IS NOT NULL
            ORDER BY i.id
            """
        )
        return cur.fetchall()

    def _upsert_issuer_ruler_relation_group(self, group_id: int, name: str):
        cur = self.db_connection.execute(
            """
            SELECT rowid, id, name
            FROM issuers_rulers_rel_groups
            WHERE id = ?
            """,
            (group_id,),
        )
        rows = cur.fetchall()

        if len(rows) > 1:
            raise RuntimeError(f"Duplicate rows in issuers_rulers_rel_groups for id={group_id}")

        if not rows:
            self.db_connection.execute(
                """
                INSERT INTO issuers_rulers_rel_groups (id, name)
                VALUES (?, ?)
                """,
                (group_id, name),
            )
            return

        row = rows[0]
        if row["name"] != name:
            self.db_connection.execute(
                """
                UPDATE issuers_rulers_rel_groups
                SET name = ?
                WHERE rowid = ?
                """,
                (name, row["rowid"]),
            )

    def _set_issuer_ruler_relation_group(
        self, issuer_id: int, rel_id: int, name: str, group_id: int | None
    ):
        cur = self.db_connection.execute(
            """
            SELECT rowid, id, issuer_id, ruler_id, name, group_id
            FROM issuers_rulers_rel
            WHERE issuer_id = ? AND id = ?
            """,
            (issuer_id, rel_id),
        )
        rows = cur.fetchall()

        if len(rows) > 1:
            raise RuntimeError(
                f"Duplicate rows in issuers_rulers_rel for issuer_id={issuer_id}, id={rel_id}"
            )

        if not rows:
            self.db_connection.execute(
                """
                INSERT INTO issuers_rulers_rel (id, issuer_id, ruler_id, name, group_id)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (rel_id, issuer_id, name, group_id),
            )
            return

        row = rows[0]
        if row["name"] != name or row["group_id"] != group_id:
            self.db_connection.execute(
                """
                UPDATE issuers_rulers_rel
                SET name = ?, group_id = ?
                WHERE rowid = ?
                """,
                (name, group_id, row["rowid"]),
            )

    def _ingest_ru_options(self, issuer_id: int, issuer_slug: str) -> int:
        # Numista populates #ru dynamically; ingest from the dedicated endpoint directly.
        endpoint_url = urljoin(
            self.base_url,
            f"/catalogue/get_rulers.php?country={issuer_slug}&prefill=",
        )
        response_text = self.basic_helper.fetch(endpoint_url)
        response_trimmed = response_text.strip()
        if not response_trimmed or response_trimmed.startswith("ERR"):
            print(
                f"[WARN] {issuer_slug}: get_rulers.php returned no usable data: "
                f"{response_trimmed[:200]!r}. Continuing with existing DB rows."
            )
            return 0

        fragment_soup = BeautifulSoup(f"<select>{response_text}</select>", "html.parser")
        fragment_select = fragment_soup.find("select")
        options_to_use = []
        groups_to_use = {}
        current_group_id = None
        if fragment_select is not None:
            for option in fragment_select.find_all("option"):
                value = (option.get("value") or "").strip()
                if not value:
                    continue

                raw_option_text = option.get_text(separator="", strip=False)
                raw_option_text_no_newline = raw_option_text.lstrip("\r\n\t ")
                is_indented = bool(raw_option_text_no_newline) and raw_option_text_no_newline[0].isspace()

                option_text = BasicHelper.clean_text(option.get_text(" ", strip=True))
                if not option_text:
                    continue

                group_match = re.match(r"^g(\d+)$", value, flags=re.IGNORECASE)
                if group_match:
                    current_group_id = int(group_match.group(1))
                    groups_to_use[current_group_id] = option_text
                    continue

                if not value.isdigit():
                    continue

                rel_id = int(value)
                group_id = current_group_id if is_indented else None
                options_to_use.append((rel_id, option_text, group_id))

        if not options_to_use:
            print(
                f"[WARN] {issuer_slug}: get_rulers.php response had no valid ruler options. "
                "Continuing with existing DB rows."
            )
            return 0

        print(
            f"[INFO] {issuer_slug}: loaded {len(options_to_use)} ru options via get_rulers.php "
            f"({len(groups_to_use)} groups)."
        )

        for group_id, group_name in groups_to_use.items():
            self._upsert_issuer_ruler_relation_group(group_id, group_name)

        for rel_id, option_text, group_id in options_to_use:
            self._set_issuer_ruler_relation_group(issuer_id, rel_id, option_text, group_id)

        self.db_connection.commit()
        return len(options_to_use)

    def _load_issuer_relations_by_normalized_name(self, issuer_id: int):
        cur = self.db_connection.execute(
            """
            SELECT rowid, id, issuer_id, ruler_id, name
            FROM issuers_rulers_rel
            WHERE issuer_id = ?
            """,
            (issuer_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]

        by_name = {}
        for row in rows:
            normalized_name = self._normalize_name_for_match(row["name"] or "")
            if not normalized_name:
                raise RuntimeError(
                    "Empty/invalid issuer ruler name in issuers_rulers_rel for "
                    f"issuer_id={issuer_id}, id={row['id']}, name={row['name']!r}"
                )
            by_name.setdefault(normalized_name, []).append(row)

        return by_name

    @staticmethod
    def _get_next_page_number(soup: BeautifulSoup):
        next_a = soup.find("a", rel="next")
        if not next_a:
            return None

        href = next_a.get("href") or ""
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        if "p" in query and query["p"]:
            try:
                return int(query["p"][0])
            except ValueError:
                return None
        return None

    def _extract_coin_type_ids_from_page_soup(self, soup: BeautifulSoup):
        coin_type_ids = []
        for a in soup.select("div.resultat_recherche div.description_piece strong a[href]"):
            coin_type_url = a.get("href") or ""
            coin_type_id = self.basic_helper.id_from_url_path(coin_type_url)
            if coin_type_id is not None:
                coin_type_ids.append(coin_type_id)
        return coin_type_ids

    def _collect_coin_type_ids_for_issuer(self, issuer_slug: str, first_page_html: str):
        seen = set()
        ordered_ids = []

        page = 1
        page_html = first_page_html

        while True:
            soup = BeautifulSoup(page_html, "html.parser")
            page_ids = self._extract_coin_type_ids_from_page_soup(soup)

            for coin_type_id in page_ids:
                if coin_type_id not in seen:
                    seen.add(coin_type_id)
                    ordered_ids.append(coin_type_id)

            next_page = self._get_next_page_number(soup)
            if not next_page:
                break

            page = next_page
            next_url = self._build_issuer_coin_types_url(issuer_slug) + f"&p={page}"
            print(f"Fetching {issuer_slug} page {page} for coin-type list coverage...")
            page_html = self.basic_helper.fetch(next_url)

        return ordered_ids

    def _iter_coin_type_html_files(self, issuer_slug: str):
        issuer_dir = os.path.join(self.html_root, issuer_slug)
        if not os.path.isdir(issuer_dir):
            return

        for folder_name in sorted(os.listdir(issuer_dir)):
            folder_path = os.path.join(issuer_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            coin_type_id = self.basic_helper.id_from_folder_name(folder_name)
            if coin_type_id is None:
                continue

            coin_type_html_path = os.path.join(folder_path, "coin_type.html")
            if not os.path.isfile(coin_type_html_path):
                continue

            yield coin_type_id, folder_name, coin_type_html_path

    def _build_coin_type_html_index(self, issuer_slug: str):
        index = {}
        for coin_type_id, folder_name, coin_type_html_path in self._iter_coin_type_html_files(issuer_slug):
            if coin_type_id in index:
                raise RuntimeError(
                    f"Duplicate local folder mapping for issuer={issuer_slug}, coin_type_id={coin_type_id}"
                )
            index[coin_type_id] = (folder_name, coin_type_html_path)
        return index

    def _extract_ruler_links(self, coin_type_html: str):
        soup = BeautifulSoup(coin_type_html, "html.parser")
        section = soup.find("section", id="fiche_caracteristiques")
        scope = section if section is not None else soup

        rulers = []
        seen = set()

        for tr in scope.find_all("tr"):
            links = tr.select('a[href*="/catalogue/ruler.php?id="]')
            for link in links:
                href = link.get("href") or ""
                match = re.search(r"[?&]id=(\d+)\b", href)
                if not match:
                    print(f"[WARN] Malformed ruler link href (cannot parse id): {href!r}. Skipping link.")
                    continue

                ruler_id = int(match.group(1))
                ruler_name = BasicHelper.clean_text(link.get_text(" ", strip=True))
                if not ruler_name:
                    print(
                        f"[WARN] Empty ruler name for ruler_id={ruler_id} in coin_type.html. Skipping link."
                    )
                    continue

                key = (ruler_id, ruler_name)
                if key in seen:
                    continue
                seen.add(key)

                rulers.append(
                    {
                        "ruler_id": ruler_id,
                        "ruler_name": ruler_name,
                        "normalized_names": self._build_ruler_match_candidates(ruler_name),
                    }
                )

        return rulers

    def _has_ruler_tr(self, coin_type_html: str) -> bool:
        soup = BeautifulSoup(coin_type_html, "html.parser")
        section = soup.find("section", id="fiche_caracteristiques")
        scope = section if section is not None else soup

        for tr in scope.find_all("tr"):
            if tr.select_one('a[href*="/catalogue/ruler.php?id="]'):
                return True

            header_cell = tr.find("th")
            if header_cell is None:
                continue

            header_text = BasicHelper.clean_text(header_cell.get_text(" ", strip=True)).lower()
            normalized_header = re.sub(r"[^a-z]", "", header_text)
            if normalized_header in {"ruler", "rulers"}:
                return True

        return False

    def _apply_ruler_match(self, issuer_id: int, rel_row: dict, ruler_id: int):
        existing_ruler_id = rel_row["ruler_id"]

        if existing_ruler_id is None:
            self.db_connection.execute(
                """
                UPDATE issuers_rulers_rel
                SET ruler_id = ?
                WHERE rowid = ?
                """,
                (ruler_id, rel_row["rowid"]),
            )
            rel_row["ruler_id"] = ruler_id
            return "updated"

        if int(existing_ruler_id) == int(ruler_id):
            return "same"

        raise RuntimeError(
            "Ruler conflict for issuer_id={issuer_id}, rel_id={rel_id}, name='{name}': "
            "existing ruler_id={existing}, found ruler_id={found}".format(
                issuer_id=issuer_id,
                rel_id=rel_row["id"],
                name=rel_row["name"],
                existing=existing_ruler_id,
                found=ruler_id,
            )
        )

    def _ensure_coin_type_ruler_relation(self, coin_type_id: int, ruler_id: int):
        cur = self.db_connection.execute(
            """
            SELECT 1
            FROM coin_types_rulers_rel
            WHERE coin_type_id = ? AND ruler_id = ?
            LIMIT 1
            """,
            (coin_type_id, ruler_id),
        )
        if cur.fetchone() is None:
            try:
                self.db_connection.execute(
                    """
                    INSERT INTO coin_types_rulers_rel (coin_type_id, ruler_id)
                    VALUES (?, ?)
                    """,
                    (coin_type_id, ruler_id),
                )
                return "inserted"
            except sqlite3.IntegrityError as ex:
                # Missing FK rows (most commonly ruler_id not in rulers) should not stop the run.
                if "foreign key constraint failed" in str(ex).lower():
                    inserted = self._save_coin_type_exception(coin_type_id, ruler_id)
                    print(
                        f"[WARN] FK insert failure for coin_types_rulers_rel "
                        f"(coin_type_id={coin_type_id}, ruler_id={ruler_id}). "
                        f"{'Saved' if inserted else 'Already present in'} _coin_type_exceptions."
                    )
                    return "exception_saved"
                raise
        return "exists"

    def _get_coin_type_db_info(self, coin_type_id: int):
        cur = self.db_connection.execute(
            """
            SELECT id, issuer_id, reviewed
            FROM coin_types
            WHERE id = ?
            """,
            (coin_type_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _set_coin_type_reviewed(self, coin_type_id: int, reviewed_value: int):
        self.db_connection.execute(
            """
            UPDATE coin_types
            SET reviewed = ?
            WHERE id = ?
            """,
            (reviewed_value, coin_type_id),
        )

    def _save_coin_type_exception(
        self,
        coin_type_id: int,
        ruler_id: int | None = None,
        no_match: int | None = None,
    ) -> bool:
        if ruler_id is None and no_match is None:
            cur = self.db_connection.execute(
                """
                SELECT 1
                FROM _coin_type_exceptions
                WHERE coin_type_id = ? AND ruler_id IS NULL AND no_match IS NULL
                LIMIT 1
                """,
                (coin_type_id,),
            )
        elif ruler_id is not None and no_match is None:
            cur = self.db_connection.execute(
                """
                SELECT 1
                FROM _coin_type_exceptions
                WHERE coin_type_id = ? AND ruler_id = ? AND no_match IS NULL
                LIMIT 1
                """,
                (coin_type_id, ruler_id),
            )
        elif ruler_id is None and no_match is not None:
            cur = self.db_connection.execute(
                """
                SELECT 1
                FROM _coin_type_exceptions
                WHERE coin_type_id = ? AND ruler_id IS NULL AND no_match = ?
                LIMIT 1
                """,
                (coin_type_id, no_match),
            )
        else:
            cur = self.db_connection.execute(
                """
                SELECT 1
                FROM _coin_type_exceptions
                WHERE coin_type_id = ? AND ruler_id = ? AND no_match = ?
                LIMIT 1
                """,
                (coin_type_id, ruler_id, no_match),
            )
        if cur.fetchone() is not None:
            return False

        if ruler_id is None and no_match is None:
            self.db_connection.execute(
                """
                INSERT INTO _coin_type_exceptions (coin_type_id)
                VALUES (?)
                """,
                (coin_type_id,),
            )
        elif ruler_id is not None and no_match is None:
            self.db_connection.execute(
                """
                INSERT INTO _coin_type_exceptions (coin_type_id, ruler_id)
                VALUES (?, ?)
                """,
                (coin_type_id, ruler_id),
            )
        elif ruler_id is None and no_match is not None:
            self.db_connection.execute(
                """
                INSERT INTO _coin_type_exceptions (coin_type_id, no_match)
                VALUES (?, ?)
                """,
                (coin_type_id, no_match),
            )
        else:
            self.db_connection.execute(
                """
                INSERT INTO _coin_type_exceptions (coin_type_id, ruler_id, no_match)
                VALUES (?, ?, ?)
                """,
                (coin_type_id, ruler_id, no_match),
            )
        return True

    def _process_coin_type_ids(self, issuer_id: int, issuer_slug: str, coin_type_ids: list[int]):
        relations_by_name = self._load_issuer_relations_by_normalized_name(issuer_id)
        no_relations_available = not relations_by_name
        if no_relations_available:
            print(
                f"[WARN] {issuer_slug}: no rows in issuers_rulers_rel available after ru ingest. "
                "Will proceed only if no coin_type.html contains a ruler <tr>."
            )

        coin_type_html_index = self._build_coin_type_html_index(issuer_slug)

        updated_count = 0
        coin_type_ruler_rel_inserted_count = 0
        checked_links = 0
        missing_local_html_count = 0

        for coin_type_id in coin_type_ids:
            coin_type_db_info = self._get_coin_type_db_info(coin_type_id)
            local_entry = coin_type_html_index.get(coin_type_id)
            if not local_entry:
                missing_local_html_count += 1
                if coin_type_db_info is None:
                    inserted = self._save_coin_type_exception(coin_type_id)
                    print(
                        f"[WARN] {issuer_slug}: missing local coin_type.html and coin_type_id={coin_type_id} "
                        f"is not present in coin_types. "
                        f"{'Saved' if inserted else 'Already present in'} _coin_type_exceptions. Skipping."
                    )
                    continue

                db_issuer_id = int(coin_type_db_info["issuer_id"])
                if db_issuer_id != issuer_id:
                    self._set_coin_type_reviewed(coin_type_id, issuer_id)
                    print(
                        f"[WARN] {issuer_slug}: missing local coin_type.html for coin_type_id={coin_type_id}; "
                        f"DB issuer_id={db_issuer_id}, Numista issuer_id={issuer_id}. "
                        f"Set coin_types.reviewed={issuer_id}."
                    )
                    # Reassigned coin types should not influence ruler-absence validation.
                    continue

                if no_relations_available:
                    raise RuntimeError(
                        f"{issuer_slug}: no rows in issuers_rulers_rel and missing local coin_type.html "
                        f"for coin_type_id={coin_type_id}; cannot confirm absence of ruler <tr>."
                    )

                self._set_coin_type_reviewed(coin_type_id, 0)
                print(
                    f"[WARN] {issuer_slug}: missing local coin_type.html for coin_type_id={coin_type_id}; "
                    "issuer unchanged. Set coin_types.reviewed=0."
                )
                continue

            folder_name, coin_type_html_path = local_entry
            with open(coin_type_html_path, "r", encoding="utf-8") as f:
                coin_type_html = f.read()

            if no_relations_available:
                ruler_links = self._extract_ruler_links(coin_type_html)
                if ruler_links:
                    inserted = self._save_coin_type_exception(coin_type_id)
                    if coin_type_db_info is not None:
                        self._set_coin_type_reviewed(coin_type_id, 0)
                    print(
                        f"[WARN] {issuer_slug}: ru options are empty but coin_type_id={coin_type_id} "
                        f"(folder='{folder_name}') has {len(ruler_links)} ruler link(s). "
                        f"{'Saved' if inserted else 'Already present in'} _coin_type_exceptions."
                    )
                    continue

                if self._has_ruler_tr(coin_type_html):
                    raise RuntimeError(
                        f"{issuer_slug}: no rows in issuers_rulers_rel, but coin_type_id={coin_type_id} "
                        f"(folder='{folder_name}') contains a ruler <tr>."
                    )
                if coin_type_db_info is not None:
                    self._set_coin_type_reviewed(coin_type_id, 1)
                continue

            ruler_links = self._extract_ruler_links(coin_type_html)
            if not ruler_links:
                print(
                    f"[WARN] {issuer_slug}: no ruler links found in coin_type.html for "
                    f"coin_type_id={coin_type_id}. Skipping coin type."
                )
                if coin_type_db_info is not None:
                    self._set_coin_type_reviewed(coin_type_id, 1)
                continue

            for ruler_link in ruler_links:
                checked_links += 1
                matched_rows = []
                matched_normalized_name = None
                for candidate_name in ruler_link["normalized_names"]:
                    candidate_rows = relations_by_name.get(candidate_name, [])
                    if len(candidate_rows) > 1:
                        # Fallback: disambiguate by the ruler_id found in coin_type.html link.
                        ruler_id_matches = [
                            row
                            for row in candidate_rows
                            if row.get("id") is not None
                            and int(row["id"]) == int(ruler_link["ruler_id"])
                        ]
                        if len(ruler_id_matches) > 1:
                            raise RuntimeError(
                                "Ambiguous match for issuer='{issuer_slug}', coin_type_id={coin_type_id}, "
                                "candidate_name='{candidate_name}' ({count} rows), "
                                "fallback ruler_id={ruler_id} also matched multiple rows ({fallback_count}).".format(
                                    issuer_slug=issuer_slug,
                                    coin_type_id=coin_type_id,
                                    candidate_name=candidate_name,
                                    count=len(candidate_rows),
                                    ruler_id=ruler_link["ruler_id"],
                                    fallback_count=len(ruler_id_matches),
                                )
                            )
                        if len(ruler_id_matches) == 1:
                            matched_rows = ruler_id_matches
                            matched_normalized_name = candidate_name
                            break
                        # No ruler_id fallback hit for this candidate: try next candidate;
                        # if no candidate resolves, we will fail below.
                        continue
                    if len(candidate_rows) == 1:
                        matched_rows = candidate_rows
                        matched_normalized_name = candidate_name
                        break

                if not matched_rows:
                    inserted = self._save_coin_type_exception(
                        coin_type_id=coin_type_id,
                        ruler_id=ruler_link["ruler_id"],
                        no_match=1,
                    )
                    print(
                        "[WARN] Match not found for issuer='{issuer_slug}', coin_type_id={coin_type_id}, "
                        "folder='{folder_name}', ruler_name='{ruler_name}', ruler_id={ruler_id}, "
                        "tried_candidates={candidates}. "
                        "{saved_msg} _coin_type_exceptions with no_match=1. Continuing.".format(
                            issuer_slug=issuer_slug,
                            coin_type_id=coin_type_id,
                            folder_name=folder_name,
                            ruler_name=ruler_link["ruler_name"],
                            ruler_id=ruler_link["ruler_id"],
                            candidates=ruler_link["normalized_names"],
                            saved_msg="Saved to" if inserted else "Already present in",
                        )
                    )
                    continue

                if len(matched_rows) > 1:
                    raise RuntimeError(
                        "Ambiguous match for issuer='{issuer_slug}', coin_type_id={coin_type_id}, "
                        "normalized_name='{normalized_name}' ({count} rows)".format(
                            issuer_slug=issuer_slug,
                            coin_type_id=coin_type_id,
                            normalized_name=matched_normalized_name,
                            count=len(matched_rows),
                        )
                    )

                action = self._apply_ruler_match(issuer_id, matched_rows[0], ruler_link["ruler_id"])
                if action == "updated":
                    updated_count += 1

                rel_action = self._ensure_coin_type_ruler_relation(
                    coin_type_id=coin_type_id,
                    ruler_id=ruler_link["ruler_id"],
                )
                if rel_action == "inserted":
                    coin_type_ruler_rel_inserted_count += 1

            if coin_type_db_info is not None:
                self._set_coin_type_reviewed(coin_type_id, 1)

        self.db_connection.commit()
        return checked_links, updated_count, coin_type_ruler_rel_inserted_count, missing_local_html_count

    def process(self):
        issuers = self.get_issuers()
        print(f"Found {len(issuers)} issuers to process.")

        resume_issuer_id, resume_page = self._read_last_log_entry()
        if resume_issuer_id is not None and resume_page is not None:
            print(f"Resuming from pages.log: issuer_id={resume_issuer_id}, page={resume_page}")

        seeking_resume = resume_issuer_id is not None and resume_page is not None

        for issuer in issuers:
            issuer_id = int(issuer["id"])
            issuer_slug = issuer["numista_url_slug"]
            if not issuer_slug:
                raise RuntimeError(f"Missing issuer slug for issuer_id={issuer_id}")

            if seeking_resume:
                if issuer_id < resume_issuer_id:
                    continue
                if issuer_id == resume_issuer_id:
                    start_page = resume_page
                    seeking_resume = False
                else:
                    start_page = 1
                    seeking_resume = False
            else:
                start_page = 1

            print(f"\nProcessing issuer {issuer_slug} (id={issuer_id})")

            ru_count = self._ingest_ru_options(issuer_id, issuer_slug)
            print(f"Parsed {ru_count} ru options.")

            total_checked_links = 0
            total_updated_count = 0
            total_coin_type_ruler_rel_inserted_count = 0
            total_missing_local_html_count = 0
            total_discovered_coin_type_ids = 0

            page = start_page
            while True:
                self._log_processed_page(issuer_id, page)

                page_url = self._build_issuer_coin_types_url(issuer_slug) + f"&p={page}"
                print(f"Fetching {issuer_slug} page {page}...")
                page_html = self.basic_helper.fetch(page_url)
                page_soup = BeautifulSoup(page_html, "html.parser")

                page_coin_type_ids = self._extract_coin_type_ids_from_page_soup(page_soup)
                if not page_coin_type_ids:
                    print(
                        f"[WARN] {issuer_slug}: no coin types found on page {page} (URL: {page_url}). "
                        "Continuing."
                    )
                    next_page = self._get_next_page_number(page_soup)
                    if not next_page:
                        break
                    page = next_page
                    continue
                total_discovered_coin_type_ids += len(page_coin_type_ids)

                (
                    checked_links,
                    updated_count,
                    coin_type_ruler_rel_inserted_count,
                    missing_local_html_count,
                ) = self._process_coin_type_ids(
                    issuer_id, issuer_slug, page_coin_type_ids
                )

                total_checked_links += checked_links
                total_updated_count += updated_count
                total_coin_type_ruler_rel_inserted_count += coin_type_ruler_rel_inserted_count
                total_missing_local_html_count += missing_local_html_count

                next_page = self._get_next_page_number(page_soup)
                if not next_page:
                    break
                page = next_page

            print(f"Discovered {total_discovered_coin_type_ids} coin types across processed pages.")
            print(
                f"Checked {total_checked_links} ruler links. Updated {total_updated_count} ruler_id values."
                f" Inserted {total_coin_type_ruler_rel_inserted_count} rows into coin_types_rulers_rel."
                f" Missing local coin_type.html for {total_missing_local_html_count} coin types."
            )


def main():
    scraper = IssuerCoinTypesScrapper()
    try:
        scraper.process()
    finally:
        scraper.close()


if __name__ == "__main__":
    raise SystemExit(main())
