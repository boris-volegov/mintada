import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from basic_functions import *
from techniques_db_functions import *
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from bs4 import BeautifulSoup

class MintsCoinScraper:
    def __init__(self):
        self.techniques_url = "https://en.numista.com/catalogue/techniques.php"
        self.db_helper = TechniquesDbHelper()
        self.basic_helper = BasicHelper()

    def _parse_technique(self, li):
        # find the anchor that points to mint.php
        technique_a = li.find("a", href=re.compile(r"technique\.php"))
        if not technique_a or not technique_a.has_attr("href"):
            return None

        # id
        qs = parse_qs(urlparse(technique_a["href"]).query)
        technique_id = self.basic_helper.int_or_none(qs.get("id", [""])[0])

        img = li.find("img", src=True)
        if img:
            src = img["src"]
            path = urlparse(src).path  # e.g. "/catalogue/photos/ancient-china/5eaa04bb1fe675.68042440-360.jpg"
            idx = path.find("/photos/")
            if idx != -1:
                img_url = path[idx + len("/photos"):]  # yields "/ancient-china/5eaa04bb1fe675.68042440-360.jpg"

        return {
            "id": technique_id,
            "name": self.basic_helper.text_or_none(technique_a),
            "img_url": img_url,
        }

    def _parse_techniques(self, mints_page):
        soup = BeautifulSoup(mints_page, "html.parser")

        # Find the <ul>
        ul = soup.find("ul", id="technique_list")

        techniques = []

        # Iterate through all <li> elements within it
        for li in ul.find_all("li", recursive=False):
           techniques.append(self._parse_technique(li))

        return techniques       

    def process(self):
        techniques_page = self.basic_helper.fetch(self.techniques_url)

        techniques = self._parse_techniques(techniques_page)
        self.db_helper.populate_techniques(techniques)   

def main():
    scraper = MintsCoinScraper()
    scraper.process()

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    raise SystemExit(main())        