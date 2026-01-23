import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from basic_functions import *
from mints_db_functions import *
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from bs4 import BeautifulSoup

class MintsCoinScraper:
    def __init__(self):
        self.mints_url = "https://en.numista.com/catalogue/mints.php"
        self.db_helper = MintsDbHelper()
        self.basic_helper = BasicHelper()

    def _parse_mint(self, li):
        # find the anchor that points to mint.php
        mint_a = li.find("a", href=re.compile(r"mint\.php"))
        if not mint_a or not mint_a.has_attr("href"):
            return None

        # id
        qs = parse_qs(urlparse(mint_a["href"]).query)
        mint_id = self.basic_helper.int_or_none(qs.get("id", [""])[0])

        # name from <strong>
        strong = mint_a.find("strong")
        name = None
        if strong:
            name = strong.get_text(strip=True)

        # remaining text inside the <a> after removing <strong>
        clone = BeautifulSoup(str(mint_a), "html.parser").a
        for s in clone.find_all("strong"):
            s.decompose()
        remaining = self.basic_helper.clean_text(clone.get_text(" ", strip=True) or "")

        if remaining is not None:
            # remove leading comma produced after removing <strong>
            remaining = re.sub(r'^\s*,\s*', '', remaining)

        # extract trailing parenthesis (period) only if it is at the end
        period = None
        m = re.search(r'\(([^)]+)\)\s*$', remaining)
        if m:
            period = m.group(1).strip()
            remaining = remaining[:m.start()].strip()

        additional_location_info = remaining or None

        # find onclick map.flyTo and extract lat/lon
        lat = lon = None
        a_map = li.find("a", onclick=re.compile(r"map\.flyTo"))
        if a_map and a_map.has_attr("onclick"):
            m2 = re.search(r"map\.flyTo\(\s*\[\s*([0-9.+\-]+)\s*,\s*([0-9.+\-]+)\s*\]", a_map["onclick"])
            if m2:
                try:
                    lat = float(m2.group(1))
                    lon = float(m2.group(2))
                except ValueError:
                    lat = lon = None

        return {
            "id": mint_id,
            "name": name,
            "additional_location_info": additional_location_info,
            "latitude": lat,
            "longitude": lon,
            "period": period,
        }

    def _parse_mints(self, mints_page):
        soup = BeautifulSoup(mints_page, "html.parser")

        # Find the <ul> inside <div id="main">
        main_div = soup.find("main", id="main")
        ul = main_div.find("ul") if main_div else None

        mints = []

        # Iterate through all <li> elements within it
        for li in ul.find_all("li", recursive=False):
           mints.append(self._parse_mint(li))

        return mints       

    def process(self):
        mints_page = self.basic_helper.fetch(self.mints_url)

        mints = self._parse_mints(mints_page)
        self.db_helper.populate_mints(mints)   

def main():
    scraper = MintsCoinScraper()
    scraper.process()

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    raise SystemExit(main())        