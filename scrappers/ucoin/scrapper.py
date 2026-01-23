import os, sys
from curl_cffi import requests as creq
from bs4 import BeautifulSoup
import sqlite3
import re
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from db_functions import *
from helper_functions import _clean_text, _label_span, _find_section_table, _text_after_label, _fragment_after_label, _first_link_theme_key, _list_after_label, _to_int_or_none, _build_coin_image_paths, _ensure_coin_image_folder, _read_cookie_file, _extract_data_from_coin_image_link, _read_last_log_entry
import time
import random
import logging

class CoinScraper:
    def __init__(self, issue_type=1):
        cookie = _read_cookie_file()

        self.issue_type = issue_type
        self.base_url = "https://en.ucoin.net"
        self.base_image_url = "https://i.ucoin.net/coin/"
        self.headers = {
            "accept": r"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": r"gzip, deflate, br, zstd",
            "accept-language": r"en-US,en;q=0.9",
            "cache-control": r"max-age=0",
            "priority": r"u=0, i",
            "User-Agent": r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            #"Referer": r"https://en.ucoin.net/catalog",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Cookie": cookie        
        }
        self.coin_type_info_field_map = {
            "number": "catalog_number",
            "country": "country",
            "period": "period",
            "currency": "currency",
            "coin type": "issue_category",
            "denomination": "denomination",
            "year": "date_range",
            "subject": "subject",
            "composition": "composition",
            "edge type": "edge_type",
            "shape": "shape",
            "alignment": "alignment",
            "weight (g)": "weight",
            "diameter (mm)": "diameter",
            "thickness (mm)": "thickness",
            # fallback variants (if site omits units)
            "weight": "weight",
            "diameter": "diameter",
            "thickness": "thickness",
        }
        self.db_path = "db/coins.db"
        self.db_connection =sqlite3.connect(self.db_path)  
        self.tid_regex = re.compile(r"[?&]tid=(\d+)\b")   

        self.db_connection.execute("PRAGMA foreign_keys = ON") 
        self.db_cursor = self.db_connection.cursor()

        self.log_file_name = 'pages.log'

        logging.basicConfig(
            filename = self.log_file_name,       # Log file name
            level = logging.INFO,       # Log level
            format = '%(message)s'  # Log format
        )

    def fetch(self, url: str, is_image:bool=False) -> str:
        delay = 1
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                r = creq.get(url, headers=self.headers, impersonate="chrome136", timeout=30)

                r.raise_for_status()
                if is_image:
                    return r.content
                else:
                    return r.text
            except Exception as e:
                msg = str(e)
                if "TLS connect error" in msg or "curl: (35)" in msg:
                    if attempt == max_retries:
                        raise
                    time.sleep(delay)
                    delay *= 2  # exponential backoff
                else:
                    # some other error: raise immediately
                    raise

    def map_coin_type_info_field(self, header_text: str) -> str | None:
        h = _clean_text(header_text).lower().rstrip(":")
        if h in self.coin_type_info_field_map:
            return self.coin_type_info_field_map[h]
        # try without units in parentheses, e.g. "weight (g)" -> "weight"
        h_no_units = re.sub(r"\s*\([^)]*\)", "", h).strip()
        return self.coin_type_info_field_map.get(h_no_units)

    def extract_tid(self, href: str) -> int | None:
        # Prefer robust parse_qs; fallback to regex
        try:
            qs = parse_qs(urlparse(href).query)
            if "tid" in qs and qs["tid"]:
                return int(qs["tid"][0])
        except Exception:
            pass
        m = self.tid_regex.search(href)
        return int(m.group(1)) if m else None

    def extract_country_slug_from_country_url(href: str) -> str | None:
        return parse_qs(urlparse(href).query).get("country", [None])[0]

    def extract_country_slug_from_coin_type_url(url: str) -> str | None:
        try:
            seg = urlparse(url).path.split("/coin/", 1)[1].split("/", 1)[0]
            return seg.split("-", 1)[0]  # everything before the first hyphen
        except (IndexError, AttributeError):
            return None

    def has_no_result(html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        return soup.select_one("p.no-result") is not None

    def populate_countries(self, db_connection, db_cursor):
        # 1) get catalog page and first-level links
        countries_page = self.fetch(urljoin(self.base_url, "catalog"))
        country_links = self.parse_country_links(countries_page)

        # 2) save countries
        for cl in country_links:
            url_slug = CoinScraper.extract_country_slug_from_country_url(cl["url"])
            db_upsert_country(db_cursor, cl["name"], url_slug, cl["url"])
            db_connection.commit()    

    def find_mintage_table(html: str):
        """Return the <table> element under the <h3>Mintage, Worth</h3> heading."""
        soup = BeautifulSoup(html, "html.parser")
        h3 = soup.find("h3", string=lambda s: s and re.search(r"mintage", s, re.I))
        if not h3:
            return None
        return h3.find_next("table")

    def parse_mintage_table(html: str):
        """
        Parse the 'Mintage, Worth' table into a list of rows:
        [{'year': int|None, 'mark': str|None, 'unc': int|None, 'bu': int|None, 'proof': int|None}, ...]
        """
        tbl = CoinScraper.find_mintage_table(html)
        if not tbl:
            return []
        
        thead = tbl.find("thead")
        if not thead:
            return []

        rows = thead.find_all("tr")
        if not rows:
            return []
        
        def _norm(s: str) -> str:
            return _clean_text(s).lower()
        
        final_header = []

        if len(rows) == 1:
            for th in rows[0].find_all("th"):
                final_header.append(_norm(th.get_text(" ", strip=True)))
        else:
            tops = rows[0].find_all("th")
            subs = [_norm(th.get_text(" ", strip=True)) for th in rows[1].find_all("th")]

            sub_it = iter(subs)

            for th in tops:
                label = _norm(th.get_text(" ", strip=True))
                colspan = int(th.get("colspan", "1"))

                if re.search(r"\bmintage\b", label) and colspan > 1:
                    for _ in range(colspan):
                        try:
                            final_header.append(next(sub_it))
                        except StopIteration:
                            break
                else:
                    final_header.append(label)

        def _find_idx(word: str):
            for i, h in enumerate(final_header):
                if re.search(rf"\b{word}\b", h):
                    return i
            return None
        
        year_idx  = _find_idx("year")
        mint_idx = _find_idx("mint")
        mark_idx  = _find_idx("mark")
        unc_idx   = _find_idx("unc")
        bu_idx    = _find_idx("bu")
        proof_idx = _find_idx("proof")

        out = []
        for tr in tbl.select("tbody tr"):
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue

            def cell(i):
                if i is None or i >= len(tds):
                    return None
                value = _clean_text(tds[i].get_text(" ", strip=True))
                # If the cleaned value contains "unknown" (case-insensitive), return None
                if "unknown" in value.lower():
                    return None
                return value
            
            row = {
                "year":  _to_int_or_none(cell(year_idx)),
                "mint": cell(mint_idx) or "",
                "mark":  cell(mark_idx) or "",
                "unc":   _to_int_or_none(cell(unc_idx)),
                "bu":    _to_int_or_none(cell(bu_idx)),
                "proof": _to_int_or_none(cell(proof_idx)),
            }

            has_value = any(v not in (None, "") for v in row.values())
            if has_value:
                out.append(row)

        return out

    def find_obverse_reverse_tables(html: str):
        """Return (obverse_table, reverse_table) as BeautifulSoup elements (or None)."""
        soup = BeautifulSoup(html, "html.parser")
        obverse_tbl = _find_section_table(soup, "Obverse")
        reverse_tbl = _find_section_table(soup, "Reverse")
        return obverse_tbl, reverse_tbl    

    def parse_coin_face_table(self, face_tbl) -> dict:
        """
        Parse an 'Obverse' or 'Reverse' table (<table class="tbl coin-desc">).
        Returns keys: themes, description_text, description_key, legend, creators.
        """
        out = {
            "themes": [],
            "description_text": None,
            "description_key": None,
            "legends": [],
            "creators": None,
            "reference_image_url": None
        }

        if not face_tbl:
            return out

        # 1) themes: zero or more <span class="theme">...</span>
        out["themes"] = [_clean_text(s.get_text(" ", strip=True)) for s in face_tbl.select("span.theme")]

        # 2) Description block
        desc_span = _label_span(face_tbl, r"^\s*Description\s*$")
        if desc_span:
            out["description_text"] = _text_after_label(desc_span)
            out["description_key"] = _first_link_theme_key(desc_span.parent)

        # 3) Legend block -> list split on <br>
        legend_span = _label_span(face_tbl, r"^\s*Legend\s*$")
        if legend_span:
            out["legends"] = _list_after_label(legend_span)

        # 4) Creators block -> list split on <br>
        creators_span = _label_span(face_tbl, r"^\s*Creators?:\s*$")
        if creators_span:
            out["creators"] = _text_after_label(creators_span) if creators_span else None

        reference_image = face_tbl.select_one("tr:first-of-type th img")
        reference_image_url = reference_image.get("src")

        if reference_image_url and "noimage" not in reference_image_url.lower():
            out["reference_image_url"] = reference_image_url

        return out    

    def parse_coin_type_info_table(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.tbl.coin-info")
        if not table:
            return {}
        
        out = {}

        for tr in table.select("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if not th or not td:
                continue

            key = self.map_coin_type_info_field(th.get_text(" ", strip=True))
            if not key:
                continue

            value = _clean_text(td.get_text(" ", strip=True))
            if value:
                lv = value.lower()
                if "unknown" in lv and "help us to know" in lv:
                    value = None

            out[key] = value
        return out

    def parse_coin_type_link(self, url):
        tid = self.extract_tid(url)
        country_url_slug = CoinScraper.extract_country_slug_from_coin_type_url(url)

        return {"tid": tid, "country_url_slug": country_url_slug, "url": url}

    def parse_coin_types_tables(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        coin_type_links = []
        for table in soup.select("table.coin"):
            a = table.select_one('td.coin-info a.value[href]')
            if not a:
                continue

            coin_type_link = self.parse_coin_type_link(a["href"])
            if coin_type_link.get("tid") is None or coin_type_link.get("country_url_slug") is None:
                continue

            coin_type_links.append(coin_type_link)

        if len(coin_type_links) == 0 and soup.find(text="Oops!") and "your IP" in soup.text and "blocked" in soup.text:
            raise Exception("Access blocked: Detected IP ban message on the page.")
        
        return coin_type_links

    def parse_country_links(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("li.cntry > a[href]"):
            name_el = a.select_one(".wrap") or a
            name = (name_el.get_text(strip=True) or a.get_text(strip=True))
            href = a.get("href")
            if href and name:
                links.append({"name": name, "url": href})
        return links

    def parse_coin_gallery(html: str):
        soup = BeautifulSoup(html, "html.parser")
        gallery = soup.find("div", class_="gallery")
        if not gallery:
            return []

        # dict keyed by coin_instance_id -> {"obverse_url":..., "reverse_url":...}
        coins = {}

        for img in gallery.select("ul.images img"):
            url = img.get("src")
            if not url or "noimage" in url:
                continue

            coin_instance_id, file_name, side, url_prefix = _extract_data_from_coin_image_link(url)

            # Extract year from filename (last token before .jpg)
            name_no_ext = os.path.splitext(file_name)[0]  # 'usa-1-cent-1974'
            tokens = name_no_ext.split("-")

            year = None
            if tokens:
                maybe_year = tokens[-1]
                if maybe_year.isdigit():
                    try:
                        year = int(maybe_year)
                    except ValueError:
                        year = None

            # Insert or update entry
            entry = coins.setdefault(
                coin_instance_id, {
                    "coin_instance_id": coin_instance_id,
                    "file_name": None,
                    "url_prefix": None,
                    "year": None,   # will update if we find a better one later
                }
            )

            if file_name is not None:
                entry["file_name"] = file_name
            if url_prefix is not None:
                entry["url_prefix"] = url_prefix
            if year is not None:
                entry["year"] = year

        # Return as a list
        return list(coins.values())

    def iter_pages(self, first_url: str, country_url_slug: str, start_page: int | None = None):
        first_html = self.fetch(first_url)
        soup = BeautifulSoup(first_html, "html.parser")

        # default = only one page
        max_page = 1

        pages_div = soup.select_one("div.pages")
        if pages_div:
            last_link = pages_div.select("a[href]")[-1]
            # try text first, else extract from query
            text = last_link.get_text(strip=True)
            max_page = int(text)

        # where to start
        start = start_page or 1

        # build URLs from first_url by replacing page= param
        parsed = urlparse(first_url)
        base_params = dict(parse_qsl(parsed.query))

        for page_num in range(start, max_page + 1):
            if "page=" in first_url:
                new_url = re.sub(r'(page=)\d+', rf'\1{page_num}', first_url)
            else:
                new_url = f"{first_url}&page={page_num}"

            logging.info(f"{country_url_slug}, {page_num}")

            yield self.fetch(new_url)

    def fetch_coin_image(self, coin_image, country_url_slug, coin_type_page_link, is_obverse):
        url, coin_image_file_name = _build_coin_image_paths(self.base_image_url, coin_image, is_obverse)

        folder = _ensure_coin_image_folder(self.issue_type, country_url_slug, coin_type_page_link)
        file_path = folder / coin_image_file_name

        if os.path.exists(file_path):
            return
        
        if "coin/77/283/77283218-" in url or "coin/71/684/71684506-" in url or "coin/66/550/66550079-" in url or "coin/66/550/66550099-" in url:
            return

        image = self.fetch(url, True)

        with open(file_path, "wb") as f:
            f.write(image)

    def process_coin_type(self, coin_type_page_link, country_id, country_url_slug):
        coin_type_page = self.fetch(urljoin(self.base_url, coin_type_page_link["url"]))  

        coin_type_info = self.parse_coin_type_info_table(coin_type_page)

        obv_tbl, rev_tbl = CoinScraper.find_obverse_reverse_tables(coin_type_page)

        obverse_info = self.parse_coin_face_table(obv_tbl)
        reverse_info = self.parse_coin_face_table(rev_tbl)

        mintage_info = CoinScraper.parse_mintage_table(coin_type_page)

        populate_coin_type(self.db_connection, self.db_cursor, coin_type_page_link["tid"], self.issue_type, country_id, coin_type_page_link["url"], coin_type_info, obverse_info, reverse_info, mintage_info)
        
        coin_images = CoinScraper.parse_coin_gallery(coin_type_page)

        populate_coin_images(self.db_connection, self.db_cursor, coin_type_page_link["tid"], coin_images)

    def process_coin_type_link(self, coin_type_page_link, country_id, country_url_slug):
        if coin_type_page_link["country_url_slug"] != country_url_slug:
            if country_url_slug not in ["brandenburg_bayreuth", "saxe_saalfeld"]:
                db_upsert_country_rels(self.db_connection, self.db_cursor, coin_type_page_link["country_url_slug"], country_url_slug)
                return

        if not db_coin_type_exists(self.db_cursor, coin_type_page_link["tid"]):
            self.process_coin_type(coin_type_page_link, country_id, country_url_slug)

        coin_images = db_get_coin_images(self.db_cursor, coin_type_page_link["tid"])
        for coin_image in coin_images:
            self.fetch_coin_image(coin_image, country_url_slug, coin_type_page_link, True)
            self.fetch_coin_image(coin_image, country_url_slug, coin_type_page_link, False)


    def process_page(self, coin_types_page, country_id, country_url_slug):
        coin_types_page_links = self.parse_coin_types_tables(coin_types_page)

        for coin_type_page_link in coin_types_page_links:
            self.process_coin_type_link(coin_type_page_link, country_id, country_url_slug)

    def get_countries(self, start_country):
        self.db_cursor.execute("SELECT id, name, url_slug, url FROM countries ORDER BY id")
        countries = self.db_cursor.fetchall()

        if start_country is not None:
            i = next((k for k, t in enumerate(countries) if t[2] == start_country), None)
            countries = countries[i:] if i is not None else []   # sublist from first match to end

        return countries

    def process_country(self, country_id, country_url_slug, coin_types_url, start_page):
        for coin_types_page in self.iter_pages(urljoin(self.base_url, coin_types_url), country_url_slug, start_page):
            if CoinScraper.has_no_result(coin_types_page):
                continue
            self.process_page(coin_types_page, country_id, country_url_slug)

            time.sleep(2)

    def process_coin_type_ids(self, coin_type_ids):

        for tid in coin_type_ids:
            url = db_get_coin_type_url(self.db_cursor, tid)

            self.process_link(url)

    def process_link(self, url):

        coin_type_page_link = self.parse_coin_type_link(url)

        db_delete_coin_type(self.db_connection, self.db_cursor, coin_type_page_link["tid"])

        country_url_slug = coin_type_page_link["country_url_slug"]

        country_id = db_get_country_id(self.db_cursor, country_url_slug)

        self.process_coin_type_link(coin_type_page_link, country_id, country_url_slug)
      
    def process(self, start_country=None, start_page=None):
        if start_country is None and os.path.exists(self.log_file_name):
            start_country, start_page = _read_last_log_entry(self.log_file_name)

        countries = self.get_countries(start_country)

        for country_id, country_name, country_url_slug, coin_types_url in countries:
            if "?" in coin_types_url:
                coin_types_url += f"&type={self.issue_type}"
            else:
                coin_types_url += f"?type={self.issue_type}"

            self.process_country(country_id, country_url_slug, coin_types_url, start_page)
            start_page = None

    def detect_broken_links(self, start_country=None, start_page=None):
        countries = self.get_countries(None)
        filtered_countries = self.get_countries(start_country)
        for country_id, country_name, country_url_slug, coin_types_url in filtered_countries:
            if not "-" in country_url_slug and not "_" in country_url_slug:
                if "?" in coin_types_url:
                    coin_types_url += f"&type={self.issue_type}"
                else:
                    coin_types_url += f"?type={self.issue_type}"

                self.detect_broken_links_country(country_id, country_url_slug, coin_types_url, start_page, countries)
                start_page = None

    def detect_broken_links_country(self, country_id, country_url_slug, coin_types_url, start_page, countries):
        for coin_types_page in self.iter_pages(urljoin(self.base_url, coin_types_url), country_url_slug, start_page):
            if CoinScraper.has_no_result(coin_types_page):
                continue

            coin_types_page_links = self.parse_coin_types_tables(coin_types_page)

            for coin_type_page_link in coin_types_page_links:
                coin_type_country_url_slug = coin_type_page_link["country_url_slug"] 

                if coin_type_country_url_slug != country_url_slug:

                    exists = any(c[2] == coin_type_country_url_slug for c in countries)

                    if not exists:
                        seg = urlparse(coin_type_page_link["url"]).path.split("/coin/", 1)[1].split("/", 1)[0]
                        seg_adj = re.sub(r'[-_]+', '_', seg)

                        exception_type = 1 if country_url_slug in seg_adj else 2
                        
                        db_upsert_exception(self.db_connection, self.db_cursor, coin_type_country_url_slug, country_url_slug, coin_type_page_link["url"], exception_type)
      
def main():
    scraper = CoinScraper(3)

    #scraper.fetch(r"https://en.ucoin.net/")
    scraper.process("israel")
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import ctypes
        import winsound
        winsound.MessageBeep(winsound.MB_ICONHAND)
        ctypes.windll.user32.MessageBoxW(0, "The script crashed with an exception.", "Execution Error", 0x10)
        raise