from pathlib import Path
from curl_cffi import requests as creq
import re
import time
from urllib.parse import parse_qs, urlparse

class BasicHelper:
    def __init__(self):
        cookie = BasicHelper._read_cookie_file()

        self.headers = {
            "accept": r"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": r"gzip, deflate, br, zstd",
            "accept-language": r"en-US,en;q=0.9",
            "cache-control": r"max-age=0",
            "priority": r"u=0, i",
            #"Referer": r"https://en.numista.com/catalogue/pays.php",
            "Referer": r"https://en.numista.com/catalogue/royaume-uni-1.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not.A/Brand";v="99", "Chromium";v="136"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Cookie": cookie
        }

    def fetch(self, url: str, is_image:bool=False) -> str | bytes:
        delay = 1
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                r = creq.get(url, headers=self.headers, impersonate="chrome136", timeout=30)
                
                # Check for HTTP errors that warrant a retry
                if r.status_code in [429, 500, 502, 503, 504]:
                     # Raise to trigger exception handling block below which handles retries
                     r.raise_for_status()

                if is_image:
                    return r.content
                else:
                    text = r.text
                    # Check for Cloudflare challenge page
                    if "Checking connection" in text and ("Numista" in text or "Enable JavaScript and cookies to continue" in text):
                        raise Exception("Cloudflare challenge page detected")
                    return text
            except Exception as e:
                msg = str(e)
                is_retryable_http = False
                
                # Check if it's an HTTP error with a retryable status code
                # curl_cffi might wrap it, or we can check the response object if attached to exception
                # but we manualy triggered raise_for_status above. 
                # Let's rely on string matching or attributes if available, but simple logic:
                # If we raised above, it goes here.
                # However, raise_for_status() raises RequestsError/HTTPError. 
                # Let's check if the exception has a 'response' attribute with status code.
                if hasattr(e, 'response') and e.response is not None:
                     if e.response.status_code in [429, 500, 502, 503, 504]:
                         is_retryable_http = True

                # Retry on TLS errors (35), Timeouts (28/Operation timed out), DNS errors (6), or Server Errors
                if is_retryable_http or "TLS connect error" in msg or "curl: (35)" in msg or "curl: (28)" in msg or "Operation timed out" in msg or "curl: (6)" in msg or "Could not resolve host" in msg:
                    if attempt == max_retries:
                        raise
                    
                    # If 429, maybe respect Retry-After header? For now, exponential backoff.
                    print(f"Fetch warning ({msg}), retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # exponential backoff
                else:
                    # some other error: raise immediately
                    raise
        
    @staticmethod     
    def text_or_none(el, sep=" ", strip=True):
        return BasicHelper.clean_text(el.get_text(separator=sep)) if el else None
    
    @staticmethod   
    def int_or_none(s):
        m = re.sub(r"[^\d]", "", s or "")
        return int(m) if m else None
    
    @staticmethod
    def id_from_querystring(url: str):
        qs = parse_qs(urlparse(url).query)
        ruler_id = BasicHelper.int_or_none(qs.get("id", [""])[0])
        return ruler_id

    
    @staticmethod
    def id_from_url_path(url: str):
        # take last path segment, e.g. "/2345" -> "2345", "/path/2345?x=1" -> "2345"
        seg = urlparse(url).path.rsplit("/", 1)[-1]
        return BasicHelper.int_or_none(seg)

    @staticmethod
    def id_from_folder_name(folder_name: str) -> int | None:
        """
        Extracts ID from folder name format: {slug}_{id}
        """
        if not folder_name:
            return None
        return BasicHelper.int_or_none(folder_name.rsplit("_", 1)[-1])

    @staticmethod 
    def clean_text(s: str) -> str:
        """
        Normalize whitespace and common HTML/unicode artifacts:
        - Unescape HTML entities
        - Replace various non-breaking/narrow spaces with regular space
        - Replace fraction-slash (⁄) with normal slash
        - Collapse all whitespace runs to a single space and strip
        """
        if not s:
            return ""
        import html as _html
        s = _html.unescape(s)
        # common non-breaking / narrow spaces and invisible separators
        for ch in ("\u00A0", "\u202F", "\u2009", "\u2007", "\u2060", "\uFEFF"):
            s = s.replace(ch, " ")
        # normalize fraction slash to plain slash (e.g. 1⁄480 -> 1/480)
        s = s.replace("\u2044", "/")
        # Collapse all whitespace to single spaces
        return " ".join(s.split())

    @staticmethod
    def slugify(s: str) -> str:
        """
        Convert string to a slug: lowercase, replace non-alphanumeric with _, strip _.
        Handles unicode fractions (½ -> 1_2) and accents (é -> e).
        """
        if not s:
            return ""
        import unicodedata
        
        # Normalize unicode characters
        s = unicodedata.normalize('NFKD', s)
        
        # Replace fraction slash with underscore
        s = s.replace('\u2044', '_')
        
        # Remove accents and other non-ascii chars
        s = s.encode('ascii', 'ignore').decode('ascii')
        
        # Lowercase and replace non-alphanumeric chars with underscore
        s = re.sub(r'[^a-z0-9]+', '_', s.lower())
        
        return s.strip('_')

    @staticmethod
    def _read_cookie_file():
        return (Path(__file__).parent / "cookie").read_text(encoding="utf-8")

