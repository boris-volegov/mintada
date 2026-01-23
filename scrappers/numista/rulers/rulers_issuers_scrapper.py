import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from basic_functions import *
from rulers_db_functions import *
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
from bs4 import BeautifulSoup

class RulersIssuersScraper:
    def __init__(self):
        self.rulers_url = "https://en.numista.com/catalogue/rulers.php"
        self.ruler_url = "https://en.numista.com/catalogue/ruler.php"
        self.db_helper = RulersDbHelper()
        self.basic_helper = BasicHelper()

    def _issuer_name_from_h2(self, h2_text: str) -> str:
        parts = [p.strip() for p in re.split(r'[›»]', h2_text) if p.strip()]
        return parts[-1] if parts else h2_text.strip()
    
    def _parse_ruler_a(self, a):
        if not a or not a.has_attr("href"):
            return None
        href = a["href"]
        qs = parse_qs(urlparse(href).query)
        ruler_id = self.basic_helper.id_from_querystring(href)

        em = a.find("em")
        years = em.get_text(strip=True) if em else None

        full_text = a.get_text(" ", strip=True)
        if years:
            name = re.sub(r'\s*\(\s*' + re.escape(years) + r'\s*\)\s*$', "", full_text).strip()
        else:
            # remove any trailing parenthesis content if present
            name = re.sub(r'\s*\([^)]*\)\s*$', "", full_text).strip()

        return {"ruler_id": ruler_id, "ruler_name": name, "years": years}

    def _parse_rulers(self, rulers_page):
        soup = BeautifulSoup(rulers_page, "html.parser")

        # Find the <ul> inside <div id="main">
        main_div = soup.find("main", id="main")
        details_list = main_div.find_all("details", recursive=True)
        
        rulers = []

        for detail in details_list:
            h2 = detail.find("h2")
            issuer_text = h2.get_text(" ", strip=True) if h2 else ""
            issuer_name = self._issuer_name_from_h2(issuer_text)

            if not issuer_name:
                continue

            outer_ul = detail.find("ul")
            if not outer_ul:
                continue

            period_order = 0
            for li in outer_ul.find_all("li", recursive=False):
                inner_ul = li.find("ul")

                period_order += 1
                if inner_ul:
                    period_em = li.find("em")
                    period = period_em.get_text(strip=True) if period_em else None
                    subperiod_order = 0
                    for inner_li in inner_ul.find_all("li", recursive=False):
                        a = inner_li.find("a", href=re.compile(r"ruler\.php"))
                        parsed = self._parse_ruler_a(a)
                        if parsed:
                            subperiod_order += 1
                            rulers.append({
                                "ruler_id": parsed["ruler_id"],
                                "name": parsed["ruler_name"],
                                "issuer_name": issuer_name,
                                "period": period,
                                "years_text": parsed["years"],
                                "period_order": period_order,
                                "subperiod_order": subperiod_order,
                            })           
                else:
                    a = li.find("a", href=re.compile(r"ruler\.php"))
                    parsed = self._parse_ruler_a(a)
                    if parsed:
                        rulers.append({
                            "ruler_id": parsed["ruler_id"],
                            "name": parsed["ruler_name"],
                            "issuer_name": issuer_name,
                            "period": None,
                            "years_text": parsed["years"],
                            "period_order": period_order,
                            "subperiod_order": None,
                        })

        return rulers    

    def _parse_ruler(self, ruler_page, ruler_id, ruler_name):
        soup = BeautifulSoup(ruler_page, "html.parser")

        main_title = soup.find("header", id="main_title")
        name = None
        dynasty = None
        
        if main_title:
            h1 = main_title.find("h1")
            if h1:
                name = h1.get_text(strip=True)
            
            p = main_title.find("p")
            if p:
                dynasty = p.get_text(strip=True)
        
        # Portrait extraction
        portrait_div = soup.find("div", class_="ruler_portrait")
        portrait_url = None
        portrait_src = None
        
        if portrait_div:
            img = portrait_div.find("img")
            if img:
                portrait_src = img.get("src")
                if img.get("srcset"):
                    # Format is usually "url 2x", take first part
                    portrait_url = img["srcset"].split(" ")[0]
                else:
                    # Fallback if no srcset
                    portrait_url = portrait_src

        # Info extraction (between portrait and "See ... coins" link)
        # If portrait exists, start after it. Otherwise start after main_title.
        start_element = portrait_div if portrait_div else main_title
        info_html = ""
        
        if start_element:
            siblings = start_element.find_next_siblings()
            fragments = []
            for sibling in siblings:
                # User requested to stop at a div containing <a> starting with "See"
                is_stop = False
                if hasattr(sibling, "find"): # Is a Tag
                    # Check if the tag itself is the link
                    if sibling.name == 'a' and sibling.get_text(strip=True).startswith("See"):
                        is_stop = True
                    # Check if it contains the link
                    elif sibling.find("a", string=re.compile(r"^\s*See\b")):
                        is_stop = True
                
                if is_stop:
                    break
                
                fragments.append(str(sibling))
            
            info_html = "".join(fragments).strip()

        # Title extraction from ruler_examples
        title = None
        ruler_examples_div = soup.find("div", class_="ruler_examples")
        if ruler_examples_div:
            h2 = ruler_examples_div.find("h2")
            if h2:
                # Text format is expected to be "{Location}: {Name with Title}..."
                # e.g. "Niue: Queen Elizabeth II (1952-2022)"
                # We need the part between ":" and "Elizabeth II"
                text = h2.get_text(" ", strip=True)
                if ":" in text:
                    # Split by first colon
                    second_part = text.split(":", 1)[1]
                    # Find ruler_name in second_part
                    # User requested to use only the first word of ruler_name
                    if ruler_name:
                        # User requested to use only the first word of ruler_name, stripping punctuation
                        # Use regex to find the first word (alphanumeric sequence)
                        match = re.search(r'\w+', ruler_name)
                        if match:
                            first_word = match.group()
                            if first_word in second_part:
                                # Extract text before ruler_name
                                title_candidate = second_part.split(first_word, 1)[0]
                                title = title_candidate.strip()
        
        # Fallbacks if title is still empty
        if not title:
            known_titles = [
                "Emperor", "King", "Regent", "Queen", "Archbishop", "Grand duke", 
                "Empress", "Bishop", "Duke", "Administrator", "Prince-archbishop", 
                "Prince", "Emir", "Count", "Margrave", "Governor", "Prince-bishop", 
                "Sultan", "Shah", "Lord", "Landgrave", "Duchess", "Co-prince", 
                "Ban", "Prince-abbot", "Prince elector", "Countess", "Prime minister", 
                "Lady", "Abbess", "Princess", "Vizier", "Abbot"
            ]
            
            # Fallback 1: Check name
            if name:
                for known_title in known_titles:
                    # Check for "{title} of" in name
                    target_phrase = f"{known_title} of"
                    if target_phrase in name:
                        title = known_title
                        break
                    
                    if not known_title.istitle():
                        target_phrase_title = f"{known_title.title()} of"
                        if target_phrase_title in name:
                            title = known_title.title()
                            break

            # Fallback 2: Check info_html
            if not title and info_html:
                soup_info = BeautifulSoup(info_html, "html.parser")
                first_p = soup_info.find("p")
                if first_p:
                    p_text = first_p.get_text(strip=True)
                    for known_title in known_titles:
                        target_phrase = f"{known_title} of"
                        if p_text.startswith(target_phrase):
                            title = known_title
                            break
                        
                        if not known_title.istitle():
                            target_phrase_title = f"{known_title.title()} of"
                            if p_text.startswith(target_phrase_title):
                                title = known_title.title()
                                break
                
        ruler = {
            "id": ruler_id,
            "name": name,
            "dynasty": dynasty,
            "portrait_url": portrait_url,
            "portrait_src": portrait_src,
            "info": info_html,
            "title": title
        }

        return ruler

    def process_issuers_rulers(self):
        rulers_page = self.basic_helper.fetch(self.rulers_url)

        rulers = self._parse_rulers(rulers_page)   

        self.db_helper.populate_rulers(rulers)   


    def process_rulers(self, ruler_name=None):
        rulers_page = self.basic_helper.fetch(self.rulers_url)

        rulers = self._parse_rulers(rulers_page)
        
        # Sort rulers by ID to ensure sequential processing
        rulers.sort(key=lambda x: x["id"] if x["id"] is not None else -1)
        
        if ruler_name:
            rulers = [r for r in rulers if r["name"].startswith(ruler_name)]

        # Checkpointing logic
        log_file = os.path.join(os.path.dirname(__file__), "last_ruler_id.log")
        last_processed_id = -1
        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        last_processed_id = int(content)
            except Exception as e:
                print(f"Error reading log file: {e}")

        for ruler_issuer in rulers:
            current_id = ruler_issuer["id"]
            if current_id is None:
                continue

            # Skip if already processed (checkpointing)
            if not ruler_name and current_id <= last_processed_id:
                continue

            if self.db_helper.ruler_exists(current_id):
                # Update log even if exists in DB to move forward, 
                # but maybe we want to re-process if DB has it but log was behind?
                # User said: "ignore rulers prior to this id"
                # So we simply ensure we move the checkpoint forward.
                # However, if it exists in DB, we skip processing, but we should probably 
                # still update the log if we are strictly following "process sequentially".
                # But safer to just let the logic flow. 
                # If we skip DB check, we re-scrape. 
                # Let's keep existing logic: if db exists, continue. But we might not write to log?
                # The user requirement is: "recording the last successfully processed id ... in the end of each iteration"
                # If we skip because of DB, it counts as "processed" or "skipped"? 
                # Let's assume we only update log if we actually attempt to process or confirm it's done.
                pass
            
            # If we skip due to DB existence, we should still potentialy update log if we are confident?
            # Actually, if we skip because it's in DB, we effectively "processed" it in the past. 
            # So we should probably update the log file to current_id to ensure next run picks up from here?
            # But simpler is: loop runs, if we do work or skip, we are 'done' with this ID.
            
            # BUT: The existing code does `continue` if `ruler_exists`. 
            # We should probably update the log there too? 
            # Or just update the log at the very end of the loop iteration regardless.

            if self.db_helper.ruler_exists(current_id):
                # Update log file
                if not ruler_name:
                     with open(log_file, "w") as f:
                        f.write(str(current_id))
                continue

            ruler_page = self.basic_helper.fetch(f'{self.ruler_url}?id={current_id}')
            ruler = self._parse_ruler(ruler_page, current_id, ruler_issuer["name"])
            
            if ruler:
                self.db_helper.populate_ruler([ruler])
                
            # Update log file after successful processing
            if not ruler_name:
                with open(log_file, "w") as f:
                    f.write(str(current_id))

def main():
    scraper = RulersIssuersScraper()
    scraper.process_issuers_rulers()

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    raise SystemExit(main())        