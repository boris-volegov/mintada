import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from basic_functions import *
from tags_db_functions import *
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from bs4 import BeautifulSoup

class TagsCoinScraper:
    def __init__(self):
        self.tags_url = "https://en.numista.com/catalogue/tags.php"
        self.db_helper = TagsDbHelper()
        self.basic_helper = BasicHelper()

    def _parse_tag(self, li):
         # --- 1) img_name: everything after 'catalogue/photos/' in the img src ---
        img = li.find("img")
        img_name = None
        if img and img.has_attr("src"):
            src = img["src"]
            marker = "catalogue/photos/"
            if marker in src:
                img_name = src.split(marker, 1)[1]

        # --- 2) id and name from <strong><a href="...">Name</a></strong> ---
        a = li.find("strong")
        if a:
            a = a.find("a")
        tag_id = None
        tag_name = None
        if a:
            # Name
            tag_name = a.get_text(strip=True) or None

            # ID from href ?k[]=34 (encoded as k%5B%5D=34)
            href = a.get("href", "")
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)  # automatically decodes k%5B%5D -> k[]
            raw_id = qs.get("k[]", [None])[0]
            try:
                tag_id = int(raw_id) if raw_id is not None else None
            except ValueError:
                tag_id = None

        # --- 3) additional_info from <p>...</p> or None if empty/missing ---
        p = li.find("p")
        if p:
            text = p.get_text(strip=True)
            additional_info = text if text else None
        else:
            additional_info = None

        return {
            "id": tag_id,
            "name": tag_name,
            "additional_info": additional_info,
            "img_name": img_name
        }

    def _parse_tags(self, tags_page):
        soup = BeautifulSoup(tags_page, "html.parser")

        # Find the <ul> inside <div id="main">
        main_div = soup.find("main", id="main")
        ul = main_div.find("ul") if main_div else None

        tags = []

        # Iterate through all <li> elements within it
        for li in ul.find_all("li", recursive=False):
           tags.append(self._parse_tag(li))

        return tags       

    def process(self):
        tags_page = self.basic_helper.fetch(self.tags_url)

        tags = self._parse_tags(tags_page)
        self.db_helper.populate_tags(tags)   

def main():
    scraper = TagsCoinScraper()
    scraper.process()

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    raise SystemExit(main())        