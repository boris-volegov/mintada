import os
import re
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from basic_functions import BasicHelper
from catalogs_db_functions import CatalogsDbHelper


class CatalogsScrapper:
    def __init__(self):
        self.catalogs_url = "https://en.numista.com/literature/catalogues.php"
        self.db_helper = CatalogsDbHelper()
        self.basic_helper = BasicHelper()

    @staticmethod
    def _extract_catalog_id(href: str | None) -> int | None:
        if not href:
            return None

        path_segment = urlparse(href).path.rstrip("/").split("/")[-1]
        # Expected format: L101607 -> keep numeric part as default ID.
        match = re.match(r"^[A-Za-z](\d+)$", path_segment)
        if not match:
            return None

        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _parse_catalog_pair(self, dt_tag: Tag, dd_tag: Tag):
        link = dt_tag.find("a", href=True)
        if not link:
            return None

        catalog_id = self._extract_catalog_id(link.get("href"))
        if catalog_id is None:
            return None

        code = self.basic_helper.clean_text(link.get_text(" ", strip=True))
        code = code if code else None

        description = self.basic_helper.clean_text(dd_tag.get_text(" ", strip=True))
        description = description if description else None

        return {
            "id": catalog_id,
            "code": code,
            "description": description,
        }

    def _parse_catalogs(self, html_page: str):
        soup = BeautifulSoup(html_page, "html.parser")
        dl = soup.find("dl", id="catalogues_list")
        if dl is None:
            return []

        catalogs = []
        pending_dt = None

        for child in dl.children:
            if not isinstance(child, Tag):
                continue

            if child.name == "dt":
                pending_dt = child
                continue

            if child.name == "dd" and pending_dt is not None:
                parsed = self._parse_catalog_pair(pending_dt, child)
                if parsed is not None:
                    catalogs.append(parsed)
                pending_dt = None

        return catalogs

    def process(self):
        catalogs_page = self.basic_helper.fetch(self.catalogs_url)
        catalogs = self._parse_catalogs(catalogs_page)
        self.db_helper.populate_catalogs(catalogs)
        print(f"Catalogs processed: {len(catalogs)}")

    def close(self):
        self.db_helper.close()


def main():
    scrapper = CatalogsScrapper()
    try:
        scrapper.process()
    finally:
        scrapper.close()


if __name__ == "__main__":
    raise SystemExit(main())

