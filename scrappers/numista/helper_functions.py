from bs4 import BeautifulSoup, Tag, NavigableString
import re
from urllib.parse import urljoin, urlparse, parse_qs
from pathlib import Path
from curl_cffi import requests as creq
from curl_cffi import requests as creq
from basic_functions import *
import os

ALNUM = re.compile(r"[A-Za-z0-9]")
basic_helper = BasicHelper()

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
        country_url_slug, start_page_str = last_line.split(",", 1)
        country_url_slug = country_url_slug.strip()
        start_page = int(start_page_str.strip())
        return country_url_slug, start_page

# ...existing code...
def _parse_year_range(text: str):
    """
    Parse a year or year-range. Returns:
      - (start, end) for simple values like "1926" or "1925-1928"
      - ((greg_start, greg_end), (native_start, native_end)) when a parenthetical
        range is present, e.g. "1228-1277 (1813-1860)" -> ((1813,1860),(1228,1277))
      - (None, None) or ((None,None),(None,None)) when not found

    Parenthetical part (if present) is treated as the gregorian range and the
    outer part as the native range, per your request.
    """
    if not text:
        return (None, None)

    t = text.strip()

    def parse_single(s: str):
        if not s:
            return (None, None)
        s = s.strip()
        # explicit range first: allow hyphen, en dash, em dash, with optional spaces
        m = re.search(r'(?<!\d)(\d{3,4})\s*[–—-]\s*(\d{3,4})(?!\d)', s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return (a, b) if a <= b else (b, a)
        # single year
        m = re.search(r'(?<!\d)(\d{3,4})(?!\d)', s)
        if m:
            y = int(m.group(1))
            return (y, y)
        return (None, None)

    # If there's a parenthetical at the end, treat it as gregorian and outer as native
    par = re.search(r'\(([^)]+)\)\s*$', t)
    if par:
        greg_text = par.group(1).strip()
        native_text = t[:par.start()].strip()
        greg = parse_single(greg_text)
        native = parse_single(native_text) if native_text else (None, None)
        return (greg, native)

    # no parenthetical: return single tuple as before
    return parse_single(t)

def _text_after_strong(p: Tag) -> str:
    """Return the visible text of a <p> after its leading <strong>…</strong> label."""
    if not p: 
        return ""
    strong = p.find("strong")
    if strong:
        # Collect everything in the <p> after the <strong>
        out = []
        for sib in strong.next_siblings:
            if isinstance(sib, NavigableString):
                out.append(str(sib))
            elif isinstance(sib, Tag):
                out.append(sib.get_text(separator=" ", strip=True))
        return " ".join(" ".join(out).split()).strip(" :")
    # no <strong>: just plain text
    return p.get_text(" ", strip=True)

def _strong_value_pair(container: Tag, key: str) -> str:
    """Find a label text (like 'Rarity index') and return the <strong> value following it."""
    label_node = container.find(string=lambda t: key in t)
    if not label_node:
        return ""
    strong = label_node.find_next("strong")
    return strong.get_text(strip=True) if strong else None

def _collect_face_descriptions(h3: Tag) -> list[str]:
    desc = []
    for sib in h3.next_siblings:
        if isinstance(sib, NavigableString):
            continue
        if isinstance(sib, Tag):
            if sib.name == "p":
                if sib.find("strong"):
                    break  # stop at the first labeled paragraph
                
                # Remove translation indicators and their detail blocks
                for span in sib.find_all("span", class_="translated_info"):
                    tid = span.get("data-details-id")
                    span.decompose()
                    if tid:
                        # try immediate next sibling first, then search the section
                        div = sib.find_next_sibling(id=tid)
                        if not div:
                            sec = h3.parent if h3 else None
                            if sec:
                                div = sec.find(id=tid)
                        if div:
                            div.decompose()
                
                # If the paragraph contains double (or more) <br>, split into separate descriptions.
                html = sib.decode_contents()
                parts = [p.strip() for p in re.split(r'(?:<br\s*/?>\s*){2,}', html, flags=re.I) if p.strip()]
                for part in parts:
                    t = BeautifulSoup(part, "html.parser").get_text(" ", strip=True)
                    if t:
                        desc.append(t)
            elif sib.name == "h3":
                break  # next face section begins
    return desc

def _find_face_paragraph(h3: Tag, label: str) -> Tag | None:
    for sib in h3.next_siblings:
        if isinstance(sib, NavigableString):
            continue
        if isinstance(sib, Tag):
            if sib.name == "h3":  # stop at next face section
                break
            if sib.name == "p":
                strong = sib.find("strong")
                if strong:
                    key = strong.get_text(" ", strip=True).rstrip(":").strip().lower()
                    if key.startswith(label.lower()):
                        return sib
    return None

def _parse_letterings(p: Tag) -> list[str]:
    """
    Parse the lettering block:
    - Prefer inside <span class="lettering">…</span> if present
    - Split on <br> boundaries (using get_text with separator)
    - Strip each line and drop empties
    """
    if not p: 
        return []
    span = p.find("span", class_="lettering")
    node = span if span else p
    raw = node.get_text(separator="\n", strip=True)
    # split on newlines (from <br>) and clean
    lines = [line.strip() for line in raw.split("\n")]
    # If the <p> had a leading label, its text may still leak in; remove if present
    if lines and lines[0].lower().startswith("lettering"):
        lines = lines[1:]
    return [ln for ln in lines if ln]

def _parse_engravers(p: Tag) -> list[str]:
    """
    Extract engraver names from a paragraph like:
      <p><strong>Engravers:</strong> <a>...</a>, Some Name, <a>...</a></p>
    Returns list of objects: {"text": <name>, "href": <link or None>, "artist_id": <int or None>}
    """
    if not p:
        return []

    p_clone = p.__copy__() if hasattr(p, "__copy__") else BeautifulSoup(str(p), "html.parser").p
    strong = p_clone.find("strong")
    if strong:
        strong.decompose()

    results = []
    for node in p_clone.contents:
        if isinstance(node, Tag) and node.name == "a":
            text = node.get_text(strip=True)
            href = node.get("href")
            artist_id = None
            if href and "artist.php" in href:
                qs = parse_qs(urlparse(href).query)
                artist_id = basic_helper.int_or_none(qs.get("id", [""])[0])
            if text:
                results.append({"text": text, "href": href, "artist_id": artist_id})
        elif isinstance(node, NavigableString):
            for part in str(node).split(","):
                t = part.strip()
                if t:
                    results.append({"text": t, "href": None, "artist_id": None})

    return results

def _parse_comments_structured(comments_div):
    """Parse comments into structured segments, splitting on double line breaks."""
    if not comments_div:
        return []
    
    def make_segment(content):
        """Create a structured segment from HTML content."""
        if not content:
            return None
        soup = BeautifulSoup(content, "html.parser")
        text = " ".join(soup.stripped_strings)
        img = soup.find("img")
        a = soup.find("a")
        
        if img:
            return {
                "type": "image_group",
                "text": None,
                "image": {
                    "src": img.get("src"),
                    "href": a.get("href") if a else None,
                    "html": str(content)
                },
                "copyright": None
            }
        elif text.startswith("©"):
            return {"type": "copyright", "copyright": text}
        elif text.strip():
            return {"type": "text", "text": text}
        return None

    # Split on double <br> tags
    content = str(comments_div)
    segments = [s.strip() for s in re.split(r'<br\s*/?\s*><br\s*/?\s*>', content, flags=re.I)]
    
    # Process each segment
    results = []
    for raw_segment in segments:
        if seg := make_segment(raw_segment):
            results.append(seg)
    
    return results
    
def _find_description_h3(section: Tag, paragraph_name: str) -> Tag | None:
    target = paragraph_name.lower()
    if section is None:
        return None
        
    for h in section.find_all("h3"):
        text = h.get_text(strip=True).lower()
        if text.startswith(target):   # matches both 'Mint' and 'Mints'
            return h
    return None   

def _section_siblings(h3):
    """Yield element siblings after h3 until the next <h3>."""
    for sib in h3.next_siblings:
        if isinstance(sib, NavigableString):
            continue
        if getattr(sib, "name", None) == "h3":
            break
        yield sib

def extract_filename_from_url(url: str, strip_original: bool = False) -> str | None:
    """
    Extracts the filename (including extension) from a URL.
    Example: https://.../abc.jpg -> abc.jpg
    If strip_original is True: abc-original.jpg -> abc.jpg
    """
    if not url:
        return None
    
    parsed = urlparse(url)
    path = parsed.path
    if not path:
        return None
        
    filename = os.path.basename(path)
    if not filename:
        return None

    if strip_original:
        name, ext = os.path.splitext(filename)
        if name.endswith("-original"):
            name = name[:-9] # remove -original
            filename = f"{name}{ext}"
            
    return filename

__all__ = [
    "_read_last_log_entry",
    "_parse_year_range",
    "_text_after_strong",
    "_strong_value_pair",
    "_collect_face_descriptions",
    "_find_face_paragraph",
    "_parse_letterings",
    "_parse_engravers",
    "_parse_comments_structured",
    "_find_description_h3",
    "_section_siblings",
    "extract_filename_from_url",
]




