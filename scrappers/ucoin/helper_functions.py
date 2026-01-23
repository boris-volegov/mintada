from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path

def _scrub_headers(hdrs):
    # Remove headers that requests sets automatically or that are browser-only
    to_remove = {
        "Host", "Content-Length", "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-Dest",
        "Sec-Fetch-User", "Upgrade-Insecure-Requests", "Accept-Encoding", "Connection",
        "Pragma", "Cache-Control"
    }
    # Remove client hints and colon-prefixed pseudo headers
    to_remove |= {k for k in hdrs if k.lower().startswith("sec-ch-")}
    to_remove |= {k for k in hdrs if k.startswith(":")}
    return {k: v for k, v in hdrs.items() if k not in to_remove}

def _clean_text(s: str) -> str:
    # normalize whitespace & &nbsp;
    return " ".join(s.replace("\xa0", " ").split())

def _label_span(table, label_regex):
    # Find a <span> whose text matches the label (ignore classes)
    pat = re.compile(label_regex, re.I)
    return table.find(lambda tag: tag.name == "span" and pat.search(tag.get_text(" ", strip=True)))        

def _find_section_table(soup: BeautifulSoup, label: str):
    # match: "Obverse" / "Obverse:" (case-insensitive; trims spaces)
    h3 = soup.find("h3", string=re.compile(rf"^\s*{re.escape(label)}\s*:?\s*$", re.I))
    if not h3:
        return None
    return h3.find_next("table", class_="tbl coin-desc")     

def _text_after_label(span):
    frag = _fragment_after_label(span)
    if frag is None:
        return None
    tmp = BeautifulSoup(frag, "html.parser")
    return _clean_text(tmp.get_text(" ", strip=True))  

def _fragment_after_label(span):
    # HTML fragment consisting of everything after the label <span> inside its parent <p>
    if not span:
        return None
    html = "".join(str(sib) for sib in span.next_siblings)  # includes <br>, <a>, etc.
    return html

def _first_link_theme_key(p_tag):
    if not p_tag:
        return None
    a = p_tag.find("a", href=True)
    if not a:
        return None
    qs = parse_qs(urlparse(a["href"]).query)
    vals = qs.get("theme")
    return vals[0] if vals else None

def _list_after_label(span):
    # Return list of items split by <br> (using newline separator)
    frag = _fragment_after_label(span)
    if frag is None:
        return []
    tmp = BeautifulSoup(frag, "html.parser")
    items = [ _clean_text(x) for x in tmp.get_text("\n", strip=True).split("\n") ]
    return [x for x in items if x]

def _to_int_or_none(s: str) -> int | None:
    if s is None:
        return None
    s = s.strip()
    if s in ("", "-", "–"):
        return None
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None
    
def _ensure_coin_image_folder(issue_type, country_url_slug, coin_type_page_link):
    base_coin_images_dir = Path.cwd()

    coin_type_slug = coin_type_page_link["url"].split("/")[2]

    folder = base_coin_images_dir / "coin_images" / str(issue_type) / country_url_slug / f"{coin_type_slug}-{coin_type_page_link["tid"]}"

    folder.mkdir(parents=True, exist_ok=True)

    return folder
    
def _build_coin_image_paths(base_image_url, coin_image, is_obverse):
    face_type = 1 if is_obverse else 2

    image_url = urljoin(base_image_url, coin_image.get("url_prefix", "") + "/")
    image_url = urljoin(image_url, f"{coin_image['coin_instance_id']}-{face_type}/")
    image_url = urljoin(image_url, coin_image.get("file_name", ""))

    coin_image_file_name = f"{coin_image.get("year") or "XXXX"}-{coin_image["coin_instance_id"]}-{face_type}.jpg"

    return image_url, coin_image_file_name

def _read_cookie_file():
    return (Path.cwd() / "cookie").read_text(encoding="utf-8")

def _extract_data_from_coin_image_link(url):
    if url is None:
        return None, None, None, None
    
    base = "https://i.ucoin.net/coin/"

    if not url.startswith(base):
        raise ValueError("URL does not start with expected prefix")

        # strip the known base off
    tail = url[len(base):]
    # tail: '22/810/22810822-1/usa-1-cent-1962.jpg'

    # Parse path parts
    parts = tail.split("/")

    url_prefix = "/".join(parts[:-2])  # '22/810'
    coin_piece = parts[-2]         # '22810822-1'
    file_name  = parts[-1]           # 'usa-1-cent-1974.jpg'
    coin_instance_id, side = coin_piece.split("-")[:2]

    return coin_instance_id, file_name, side, url_prefix

def _read_last_log_entry(log_file_path):
    with open(log_file_path, 'rb') as f:
        content = f.read().decode("utf-8").strip()
        if not content:
            return None, None

        f.seek(0, 2)  # Move to end of file
        filesize = f.tell()

        # Read backward to find the last newline
        buffer = bytearray()
        for i in range(filesize - 1, -1, -1):
            f.seek(i)
            byte = f.read(1)
            if byte == b'\n' and buffer:
                break
            buffer.extend(byte)

            if not buffer:
                return None, None

        # Reverse to get correct line
        last_line = buffer[::-1].decode().strip()

    # Parse the comma-delimited values
    try:
        country_url_slug, start_page_str = last_line.split(",", 1)
        country_url_slug = country_url_slug.strip()
        start_page = int(start_page_str.strip())
        return country_url_slug, start_page
    except ValueError:
        raise ValueError(f"Failed to parse last log line: {last_line}")