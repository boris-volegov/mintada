import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from basic_functions import *
from issuers_db_functions import *
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from bs4 import BeautifulSoup

import csv

class IssuersCoinScraper:
    def __init__(self):
        self.tags_url = "https://en.numista.com/catalogue/pays.php"
        self.db_helper = IssuersDbHelper()
        self.basic_helper = BasicHelper()

    def _find_safe(self, parent, tag_name):
        """
        Finds direct children with tag_name.
        Workaround for html.parser bug where some elements (like details or ul) might be nested inside <img> tags.
        """
        # standard check
        found = list(parent.find_all(tag_name, recursive=False))
        
        # workaround check inside direct img children
        imgs = parent.find_all("img", recursive=False)
        for img in imgs:
            found.extend(img.find_all(tag_name, recursive=False))
            
        return found

    def _parse_issuer(self, issuer_li, parent_slug=None, parent_numista_slug=None):
        """Recursively parse <li> elements and return structured records"""
        records = []

        # find <a>
        issuer_a = issuer_li.find("a", class_="name")

        # Check for historical_period class
        classes = issuer_a.get("class", [])
        is_historical_period = "historical_period" in classes

        href = issuer_a.get("href") if issuer_a else None
        
        url_slug = None
        numista_url_slug = None

        if href:
            # e.g. /catalogue/algiers_regency-1.html -> algiers_regency-1
            m = re.search(r'/catalogue/([^/]+)\.html', href)
            if m:
                raw_slug = m.group(1)
                numista_url_slug = raw_slug
                # e.g. algiers_regency-1 -> algiers_regency
                url_slug = re.sub(r'-\d+$', '', raw_slug)

        # get text inside <a>
        territory_type = None
        numista_territory_type = None
        issuer_text = None
        numista_name = None
        
        if issuer_a:
            # clone to avoid mutating original tree
            clone = BeautifulSoup(str(issuer_a), "html.parser").a
            em_tag = clone.find("em")
            if em_tag:
                raw_territory_type = em_tag.get_text(" ", strip=True)
                territory_type = raw_territory_type
                numista_territory_type = raw_territory_type
                em_tag.decompose()
            
            raw_text = clone.get_text(" ", strip=True)
            numista_name = raw_text
            issuer_text = raw_text.rstrip(",").strip()
        
        # get alt_names (if exist)
        alt_span = issuer_li.find("span", class_="alt_names", recursive=False)
        # could contain multiple names separated by spaces
        alt_names_text = alt_span.get_text(" ", strip=True) if alt_span else None

        # get tag classes (all classes of <li> that start with "tag_")
        tags = [cls for cls in issuer_li.get("class", []) if cls.startswith("tag_")]

        record = {
            "href": href,
            "url_slug": url_slug,
            "issuer_text": issuer_text,
            "territory_type": territory_type,
            "alt_names": alt_names_text,
            "tags": tags,
            "parent_url_slug": parent_slug,
            "is_historical_period": is_historical_period,
            # Numista specific fields (raw)
            "numista_url_slug": numista_url_slug,
            "numista_name": numista_name, 
            "numista_territory_type": numista_territory_type,
            "numista_parent_url_slug": parent_numista_slug
        }

        records.append(record)

        # now recurse into children <ul> (may appear under <details> or directly)
        for child_ul in self._find_safe(issuer_li, "ul"):
            for child_li in child_ul.find_all("li", recursive=False):
                records.extend(self._parse_issuer(child_li, parent_slug=url_slug, parent_numista_slug=numista_url_slug))

        # also handle <details> that wrap <ul>
        for details in self._find_safe(issuer_li, "details"):
            for child_ul in self._find_safe(details, "ul"):
                for child_li in child_ul.find_all("li", recursive=False):
                    records.extend(self._parse_issuer(child_li, parent_slug=url_slug, parent_numista_slug=numista_url_slug))

        return records

    def _parse_issuers(self, issuers_page):
        soup = BeautifulSoup(issuers_page, "html.parser")

        # Find the <ul> with the specific class
        #ul = soup.find("ul", class_="liste_pays")

        uls = soup.find_all("ul", class_="liste_pays")
        ul = uls[0] if len(uls) > 1 else None

        issuers = []

        # Iterate through all <li> elements within it
        li_list = ul.find_all("li", recursive=False)

        for li in li_list:   
            issuers.extend(self._parse_issuer(li))

        return issuers     

    def process(self):
        issuers_page = self.basic_helper.fetch(self.tags_url)

        issuers = self._parse_issuers(issuers_page)
        self.db_helper.populate_issuers(issuers) 
        
    def check_missing_issuers(self):
        print("Fetching existing Numista slugs from DB...")
        existing_slugs = self.db_helper.get_all_numista_slugs()
        print(f"Found {len(existing_slugs)} existing slugs.")
        
        print("Fetching issuers page...")
        issuers_page = self.basic_helper.fetch(self.tags_url)
        print("Parsing issuers...")
        all_issuers = self._parse_issuers(issuers_page)
        print(f"Scraped {len(all_issuers)} total issuers.")
        
        missing_issuers = []
        for issuer in all_issuers:
            # DB numista_url_slugs are found to be "cleaned" (no -id suffix)
            # So we must compare our cleaned 'url_slug' against them.
            cleaned_slug = issuer.get("url_slug")
            
            # If cleaned_slug is None, skip
            # If cleaned_slug implies it's already in DB (as numista_url_slug), skip
            if cleaned_slug and cleaned_slug not in existing_slugs:
                missing_issuers.append(issuer)
        
        print(f"Identified {len(missing_issuers)} missing issuers.")
        
        if not missing_issuers:
            print("No missing issuers found.")
            return

        csv_filename = "missing_issuers.csv"
        print(f"Writing to {csv_filename}...")
        
        fieldnames = [
            "numista_url_slug", "numista_name", "numista_parent_url_slug", "numista_territory_type",
            "url_slug", "issuer_text", "parent_url_slug", "territory_type", 
            "alt_names", "is_historical_period", "tags"
        ]
        
        with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for issuer in missing_issuers:
                # tags is a list, join it
                row = issuer.copy()
                if row.get("tags"):
                    row["tags"] = ",".join(row["tags"])
                writer.writerow(row)
                
        print("Done.")

def main():
    scraper = IssuersCoinScraper()
    #scraper.process()
    scraper.check_missing_issuers()
if __name__ == "__main__":
    main()

if __name__ == '__main__':
    raise SystemExit(main())        