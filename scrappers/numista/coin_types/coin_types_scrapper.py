import os, sys
from curl_cffi import requests as creq
from bs4 import BeautifulSoup, Tag, NavigableString
import re
from urllib.parse import urljoin, urlparse, parse_qs, parse_qsl, urlunparse
import logging
import shutil
# Add parent directory to path to import helpers
# Add parent directory to path to import helpers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "issuers"))

from coin_types_db_functions import *
from issuers_db_functions import *
from helper_functions import *
from basic_functions import *

class CoinTypesScraper:
    def __init__(self):
        self.basic_helper = BasicHelper()

        ALNUM_REGEX = re.compile(r"[A-Za-z0-9]")

        self.base_url = "https://en.numista.com/"
        self.base_refernce_image_url = self.base_url + "catalogue/photos/"
        self.base_examples_image_url = self.base_url + "catalogue/examples/pictures/"
        self.base_sales_image_url = self.base_url + "sales_archive/pictures/"
        
        self.tid_regex = re.compile(r"[?&]tid=(\d+)\b")   
        self.log_file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages.log')

        self.db_helper = CoinTypesDbHelper()
        self.issuers_db_helper = IssuersDbHelper()
        self.basic_helper = BasicHelper()

        logging.basicConfig(
            filename = self.log_file_name,       # Log file name
            level = logging.INFO,       # Log level
            format = '%(message)s'  # Log format
        )
        
        self.should_cleanup = True

    def _parse_edge(self, out, descriptions_section):
        h3 = _find_description_h3(descriptions_section, "edge")
        if not h3:
            return {}

        found_filename = None

        for sib in _section_siblings(h3):
            image_url = None

            # Check if sib itself is the <a> tag
            if sib.name == "a" and sib.has_attr("href") and sib.find("img"):
                image_url = sib["href"].strip()
            else:
                # Fallback to img
                if sib.name == "img" and sib.has_attr("src"):
                    image_url = sib["src"].strip()

            if image_url is not None:
                found_filename = extract_filename_from_url(image_url, strip_original=True)
                if found_filename:
                    break                      

        out["edge_image"] = found_filename

    def _parse_example_images(self, out, soup):
        # Find all example divs
        examples_div = soup.find("div", id="examples_list")
        if not examples_div:
            return

        for example_image_div in examples_div.find_all("div", class_="example_image"):
            # Each should have 2 links (obverse/reverse)
            links = [a for a in example_image_div.find_all("a", href=True) if a.find("img")]
            if len(links) >= 2:
                # Obverse is usually first, Reverse second
                obverse_link = links[0]
                reverse_link = links[1]
                
                obverse_url = obverse_link["href"]
                reverse_url = reverse_link["href"]
                
                obverse_image = extract_filename_from_url(obverse_url)
                reverse_image = extract_filename_from_url(reverse_url)

                out["sample_images"].append({
                    "obverse_image": obverse_image,
                    "reverse_image": reverse_image,
                    "image_type": 2
                })
            elif len(links) == 1:
                # User requested: if only one image, use it for both
                link = links[0]
                url = link["href"]
                image = extract_filename_from_url(url)
                
                out["sample_images"].append({
                    "obverse_image": image,
                    "reverse_image": image,
                    "image_type": 2
                })

    def _parse_sales_images(self, out, soup):
        sales_table = soup.find("table", id="sales_list")
        if not sales_table:
            return

        # Iterate over all rows that look like sales rows
        for picture_td in sales_table.find_all("td", class_="sale_pictures"):
            links = [a for a in picture_td.find_all("a", href=True) if a.find("img")]
            if not links:
                continue

            obverse_image = None
            reverse_image = None
            
            if len(links) >= 1:
                link1 = links[0]
                img1 = extract_filename_from_url(link1["href"])
                
                if len(links) >= 2:
                    link2 = links[1]
                    img2 = extract_filename_from_url(link2["href"])
                    
                    obverse_image = img1
                    reverse_image = img2
                else:
                    obverse_image = img1
                    reverse_image = img1
            
            if obverse_image and reverse_image:
                out["sample_images"].append({
                    "obverse_image": obverse_image,
                    "reverse_image": reverse_image,
                    "image_type": 3
                })

    def _parse_comment_images(self, out, soup):
        comments_div = soup.find("div", id="fiche_comments")
        if not comments_div:
            return

        out["comment_images"] = []
        for a in comments_div.find_all("a", href=True):
             if not a.find("img"):
                 continue
             
             href = a["href"]
             image_name = extract_filename_from_url(href)
             
             if image_name:
                 # Determine source type
                 source_type = 1 # Default: Catalogue
                 if "/forum/images/" in href:
                     source_type = 2
                 
                 out["comment_images"].append({
                     "image": image_name,
                     "source_type": source_type
                 })

    def _parse_rarity_index(self, out, soup):
        val = _strong_value_pair(soup, "Numista Rarity index")
        if val:
             try:
                 out["rarity_index"] = int(val)
             except ValueError:
                 out["rarity_index"] = None

    def _parse_reference_images(self, out, coin_type_image_links):
        main_image_entry = {
            "obverse_image": None,
            "reverse_image": None,
            "image_type": 1
        }

        valid_links = []
        for a in coin_type_image_links:
            img = a.find("img")
            if not img:
                continue

            src = img.get("src", "")
            if "no-obverse" in src or "no-reverse" in src:
                continue
            valid_links.append(a)

        if len(valid_links) == 2:
            obverse_a = valid_links[0]
            reverse_a = valid_links[1]

            obv_name = extract_filename_from_url(obverse_a["href"], strip_original=True) if obverse_a.has_attr("href") else None
            rev_name = extract_filename_from_url(reverse_a["href"], strip_original=True) if reverse_a.has_attr("href") else None
            
            main_image_entry["obverse_image"] = obv_name
            main_image_entry["reverse_image"] = rev_name
        else:
            for idx, a in enumerate(valid_links):
                img = a.find("img")
                # img is guaranteed to exist because of valid_links filter

                # Decide kind
                kind = None
                alt_lc = (img.get("alt") or "").lower()

                if alt_lc.endswith("obverse"):
                    kind = "obverse"
                elif alt_lc.endswith("reverse"):
                    kind = "reverse"
                else:
                    # fallback by order: 1st -> obverse, 2nd -> reverse
                    kind = "obverse" if idx == 0 else ("reverse" if idx == 1 else None)

                image_name = extract_filename_from_url(a["href"], strip_original=True) if a.has_attr("href") else None

                # Assign to the right field
                if kind == "obverse":
                    main_image_entry["obverse_image"] = image_name
                elif kind == "reverse":
                    main_image_entry["reverse_image"] = image_name

        out["sample_images"].append(main_image_entry)       

    def _parse_title(self, out, title_h1):
        # Special-case <h1> with an inline <span> subtitle
        if getattr(title_h1, "name", None) == "h1":
            # subtitle = text inside the first <span> (if any)
            span = title_h1.find("span")
            subtitle = self.basic_helper.clean_text(span.get_text(" ", strip=True)) if span else None

            # title = text up to (but not including) that <span>, preserving punctuation/spaces
            title_chunks = []
            for child in title_h1.children:
                if isinstance(child, NavigableString):
                    title_chunks.append(str(child))
                elif isinstance(child, Tag):
                    if child.name == "span":
                        break  # stop at subtitle
                    title_chunks.append(child.get_text(" ", strip=True))
            title = self.basic_helper.clean_text("".join(title_chunks)) if title_chunks else None

            out["title"] = title
            out["subtitle"] = subtitle

    def clean_html(self, html_content, out=None, url_slug=None):
        soup = BeautifulSoup(html_content, "html.parser")

        # Replace image links if metadata is provided
        if out:
            images_dir = "images" # Relative path
            
            # Helper to create matcher for cleaned filenames
            def create_matcher(img_name):
                # Match if href contains img_name OR if it contains the original version (stem-original.ext)
                if not img_name: return lambda h: False
                name, ext = os.path.splitext(img_name)
                # We assume if it was stripped, it was like name-original.ext
                # But it could also just be name.ext (if no original suffix existed, but we prioritize matching)
                return lambda h: h and (img_name in h or f"{name}-original{ext}" in h)

            # Edge image
            edge_img = out.get("edge_image")
            if edge_img:
                subfolder = "edge_image"
                link = soup.find("a", href=create_matcher(edge_img))
                if link:
                    img = link.find("img")
                    if img:
                        local_path = f"{subfolder}/{edge_img}"
                        img["src"] = local_path
                        if "srcset" in img.attrs: del img["srcset"]
                        if "sizes" in img.attrs: del img["sizes"]
                        link["href"] = local_path
            
            # Sample images
            if out.get("sample_images"):
                for entry in out["sample_images"]:
                    img_type = entry.get("image_type")
                    
                    for face in ["obverse", "reverse"]:
                        img_name = entry.get(f"{face}_image")
                        if img_name:
                            matcher = create_matcher(img_name)
                            link = soup.find("a", href=matcher)
                            if link:
                                img = link.find("img")
                                if img:
                                    local_path = f"{images_dir}/{img_name}"
                                    img["src"] = local_path
                                    if "srcset" in img.attrs: del img["srcset"]
                                    if "sizes" in img.attrs: del img["sizes"]
                                    link["href"] = local_path

        # Clear <head> content as requested
        if soup.head:
            soup.head.clear()

        global_container = soup.find(id="global_container")
        if global_container:
            # Remove global_header as requested
            global_header = global_container.find(id="global_header")
            if global_header:
                global_header.decompose()

            # Remove all next siblings of global_container (e.g. scripts, bottom debug)
            for sibling in global_container.find_next_siblings():
                sibling.decompose()
                
            main_container = global_container.find(id="main_container")
            if main_container:
                # Remove all next siblings of main_container inside global_container (e.g. footer)
                for sibling in main_container.find_next_siblings():
                    sibling.decompose()
                    
                middle_element = main_container.find(id="middle_element")
                if middle_element:
                    main_tag = middle_element.find("main", id="main")
                    if main_tag:
                        # Clear middle_element content and only keep the main tag
                        # We extract main_tag first to ensure it's safe from clear
                        main_tag.extract()
                        middle_element.clear()
                        middle_element.append(main_tag)

        # Remove design images
        for img in soup.find_all("img", src=True):
            if img.parent and img["src"].startswith("https://en.numista.com/design/"):
                img.decompose()
        
        # Remove translated info spans
        for span in soup.find_all("span", class_="translated_info"):
            span.decompose()
        
        # Remove sale_offers
        sale_offers = soup.find(id="sale_offers")
        if sale_offers:
            sale_offers.decompose()

        # Remove fiche_echanges
        fiche_echanges = soup.find(id="fiche_echanges")
        if fiche_echanges:
            fiche_echanges.decompose()

        # Replace comment images
        if out.get("comment_images"):
             comments_div = soup.find("div", id="fiche_comments")
             if comments_div:
                 comment_images_dir = "comment_images"
                 # img_entry is now a dict {"image": "...", "source_type": X}
                 for img_entry in out["comment_images"]:
                     img_name = img_entry["image"]
                     # Match potential links
                     link = comments_div.find("a", href=lambda h: h and img_name in h)
                     if link:
                         img = link.find("img")
                         if img:
                             local_path = f"{comment_images_dir}/{img_name}"
                             img["src"] = local_path
                             if "srcset" in img.attrs: del img["srcset"]
                             if "sizes" in img.attrs: del img["sizes"]
                             link["href"] = local_path

        return str(soup)

    def _download_image(self, url, save_path):
        content = self.basic_helper.fetch(url, is_image=True)
        with open(save_path, "wb") as f:
            f.write(content)

    def download_coin_type_images(self, out, url_slug, coin_type_dir):
        # Edge image
        edge_img = out.get("edge_image")
        if edge_img:
            subfolder = "edge_image"
            target_dir = os.path.join(coin_type_dir, subfolder)
            os.makedirs(target_dir, exist_ok=True)
            
            # Reconstruct -original URL for edge images
            name, ext = os.path.splitext(edge_img)
            image_url = f"{self.base_refernce_image_url}{url_slug}/{name}-original{ext}"
            
            save_path = os.path.join(target_dir, edge_img)
            self._download_image(image_url, save_path)

        # Sample images
        if out.get("sample_images"):
            images_dir = os.path.join(coin_type_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            for entry in out["sample_images"]:
                img_type = entry.get("image_type")
                
                for face in ["obverse", "reverse"]:
                    img_name = entry.get(f"{face}_image")
                    if img_name:
                        if img_type == 1:
                             # Type 1: Reference images - need -original reconstruction
                             name, ext = os.path.splitext(img_name)
                             image_url = f"{self.base_refernce_image_url}{url_slug}/{name}-original{ext}"
                        elif img_type == 2:
                             # Type 2: Example images
                             image_url = f"{self.base_examples_image_url}{img_name}"
                        else:
                             # Type 3: Sales images
                             image_url = f"{self.base_sales_image_url}{img_name}"
                        
                        save_path = os.path.join(images_dir, img_name)
                        self._download_image(image_url, save_path)
        
        # Comment images
        if out.get("comment_images"):
             comment_images_dir = os.path.join(coin_type_dir, "comment_images")
             os.makedirs(comment_images_dir, exist_ok=True)
             
             for img_entry in out["comment_images"]:
                 img_name = img_entry["image"]
                 source_type = img_entry.get("source_type", 1)
                 
                 if source_type == 2:
                     # Forum image
                     # Example: https://en.numista.com/forum/images/68d6a5a20851e.jpg
                     image_url = f"{self.base_url}forum/images/{img_name}"
                 else:
                     # Catalogue image (default)
                     # Example: https://en.numista.com/catalogue/images/{filename}
                     image_url = f"{self.base_url}catalogue/images/{img_name}"
                     
                 save_path = os.path.join(comment_images_dir, img_name)
                 self._download_image(image_url, save_path)

    def parse_coin_type_page(self, out, coin_type_page):
        soup = BeautifulSoup(coin_type_page, "html.parser")

        # Title and subtitle
        self._parse_title(out, soup.select_one("#main_title h1"))

        self._parse_reference_images(out, soup.select("#fiche_photo a.coin_pic"))

        descriptions_section = soup.find("section", id="fiche_descriptions")
        self._parse_edge(out, descriptions_section)

        self._parse_example_images(out, soup)

        self._parse_sales_images(out, soup)

        self._parse_comment_images(out, soup)

        self._parse_rarity_index(out, soup)
  
    def parse_country_page(self, country_page_soup):
        root = country_page_soup.select_one("div.catalogue_search_results")
        if not root:
            return []

        periods = []
        current = None

        for node in root.children:
            if not isinstance(node, Tag):
                continue

            # 1) Start a new period at each <header>
            if node.name == "header":
                h2 = node.find("h2")
                p  = node.find("p")
                current = {
                    "period_text": h2.get_text(strip=True) if h2 else None,
                    "unit_relation_text": p.get_text(" ", strip=True) if p else None,
                    "links": []
                }
                periods.append(current)
                continue

            # 2) Collect links from each .resultat_recherche that follows
            if node.name == "div" and "resultat_recherche" in (node.get("class") or []):
                if current is None:
                    # if results appear before any header, you can choose to skip
                    # or create an anonymous period; here we skip
                    continue

                # strong > a inside .description_piece
                for a in node.select("div.description_piece strong a[href]"):
                    #href = a["href"]
                    current["links"].append(a)
        return periods

    def _get_next_page_number(self, soup):
        # <a rel="next" href="index.php?e=...&p=2">Next</a>
        next_a = soup.find("a", rel="next")
        if not next_a:
            return None
        
        href = next_a.get("href")
        parsed = urlparse(href)
        
        # 1. Try query parameter 'p'
        query = parse_qs(parsed.query)
        if 'p' in query:
            return int(query['p'][0])
            
        return None

    def get_coin_type_dir(self, coin_type_link, issuer_record, id):
        link_text = coin_type_link.get_text(separator=" ", strip=True)
        file_name_prefix = self.basic_helper.slugify(link_text)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(script_dir, "html", issuer_record['numista_url_slug'])
        coin_type_dir = os.path.join(html_dir, f"{file_name_prefix}_{id}")
        return file_name_prefix, coin_type_dir

    def check_if_exists(self, issuer_url_slug, coin_type_db_info):
        if not coin_type_db_info:
            return False

        # Reconstruct directory path using DB info
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(script_dir, "html", issuer_url_slug)
        coin_type_dir = os.path.join(html_dir, f"{coin_type_db_info['coin_type_slug']}_{coin_type_db_info["id"]}")
        file_name_prefix = coin_type_db_info['coin_type_slug']

        if os.path.exists(coin_type_dir):
            # Validate contents
            html_path = os.path.join(coin_type_dir, "coin_type.html")
            html_exists = os.path.exists(html_path)
            
            # Check samples from DB
            stored_samples = coin_type_db_info['sample_images']
            images_dir = os.path.join(coin_type_dir, "images")
            
            samples_exist = True
            if stored_samples:
                for sample_name in stored_samples:
                    img_path = os.path.join(images_dir, sample_name)
                    if not os.path.exists(img_path):
                        samples_exist = False
                        break

            # Check edge image
            edge_image = coin_type_db_info['edge_image']
            edge_image_exist = True
            if edge_image:
                edge_img_path = os.path.join(coin_type_dir, "edge_image", edge_image)
                if not os.path.exists(edge_img_path):
                    edge_image_exist = False

            # Check comment images
            comment_images = coin_type_db_info['comment_images']
            comment_images_exist = True
            if comment_images:
                comment_images_dir = os.path.join(coin_type_dir, "comment_images")
                for img_entry in comment_images:
                    # img_entry is a dict from db helper now
                    img_name = img_entry["image"]
                    img_path = os.path.join(comment_images_dir, img_name)
                    if not os.path.exists(img_path):
                        comment_images_exist = False
                        break
            
            if html_exists and samples_exist and edge_image_exist and comment_images_exist:
                print(f"Skipping existing and valid coin type {coin_type_db_info["id"]}: {file_name_prefix}")
                return True
            else:
                 print(f"Redownloading invalid coin type {coin_type_db_info["id"]}: {file_name_prefix} (HTML: {html_exists}, Samples OK: {samples_exist}, Edge OK: {edge_image_exist}, Comments OK: {comment_images_exist})")
        
        return False

    def log_processed_page(self, issuer_slug, page):
        with open(self.log_file_name, "a", encoding="utf-8") as f:
            f.write(f"{issuer_slug},{page or 1}\n")

    def cleanup_last_run(self):
         print("Checking for last inserted coin type to cleanup...")
         last_coin = self.db_helper.get_last_inserted_coin_type_with_issuer()
         if last_coin:
             id = last_coin["id"]
             slug = last_coin["coin_type_slug"]
             i_slug = last_coin["issuer_url_slug"]
             
             print(f"Found last inserted coin: {slug}_{id} (Issuer: {i_slug})")
             
             # Construct folder path
             script_dir = os.path.dirname(os.path.abspath(__file__))
             html_dir = os.path.join(script_dir, "html", i_slug)
             coin_type_dir = os.path.join(html_dir, f"{slug}_{id}")
             
             if os.path.exists(coin_type_dir):
                 try:
                     shutil.rmtree(coin_type_dir)
                     print(f"Deleted folder: {coin_type_dir}")
                 except Exception as e:
                     print(f"Error deleting folder {coin_type_dir}: {e}")
             else:
                 print(f"Folder not found: {coin_type_dir}")
                 
             # Delete from DB
             self.db_helper.delete_coin_type(id)
             print(f"Deleted coin type {id} from database.")
         else:
             print("No last inserted coin type found.")

    def process(self, issuer_url_slug=None, page=None, coin_type_id=None):
        is_restart = issuer_url_slug is None and page is None and coin_type_id is None
        
        if is_restart:
            issuer_url_slug, page = _read_last_log_entry(self.log_file_name)

        if is_restart and self.should_cleanup:
            self.cleanup_last_run()

        page = 1 if page is None else page
        
        # If we have a target issuer (resume), we skip until we find it
        seeking_resume = issuer_url_slug is not None

        issuer_records = self.issuers_db_helper.get_issuers()

        for issuer_record in issuer_records:
            if seeking_resume:
                if issuer_record["numista_url_slug"] != issuer_url_slug:
                    continue
                # Found the resume point. 
                # Stop seeking so subsequent issuers are processed normally.
                seeking_resume = False
            else:
                # Normal processing starts at page 1 for new issuers
                page = 1

            while True:
                url = urljoin(self.base_url, f"/catalogue/index.php?e={issuer_record['numista_url_slug']}&r=&st=1&cat=y&im1=&im2=&ru=&ie=&ca=3&no=&v=&a=&dg=&i=&b=&m=&f=&t=&t2=&w=&mt=&u=&g=&q=200")
                url += f"&p={page}"

                print(f"Processing {issuer_record['numista_url_slug']} page {page}...")
                
                # Log progress immediately at start
                self.log_processed_page(issuer_record["numista_url_slug"], page)
                
                country_page_text = self.basic_helper.fetch(url)
                country_page_soup = BeautifulSoup(country_page_text, "html.parser")
                
                periods = self.parse_country_page(country_page_soup)

                for period in periods:
                    for coin_type_link in period["links"]:
                        coin_type_url = coin_type_link["href"]

                        id = self.basic_helper.id_from_url_path(coin_type_url)
                        if coin_type_id is not None and id != coin_type_id:
                            continue

                        # Check if we should force reprocess this specific coin
                        force_reprocess = coin_type_id is not None and id == coin_type_id
                        
                        coin_type_db_info = self.db_helper.get_coin_type_full_info(id)

                        if force_reprocess:
                             print(f"Force reprocessing coin type {id}, deleting existing data...")
                             
                             # Delete DB record
                             self.db_helper.delete_coin_type(id)
                             
                             # Calculate folder path to delete it
                             # We need to calculate dir path now to delete it. The existing code calculates it later.
                             # We can call get_coin_type_dir now.
                             _, temp_coin_type_dir = self.get_coin_type_dir(coin_type_link, issuer_record, id)
                             if os.path.exists(temp_coin_type_dir):
                                 shutil.rmtree(temp_coin_type_dir)
                                 print(f"Deleted folder {temp_coin_type_dir}")
                             
                             # Force info to None so check_if_exists returns False (or just skip check)
                             coin_type_db_info = None

                        if self.check_if_exists(issuer_record["numista_url_slug"], coin_type_db_info):
                            continue

                        # Need file_name_prefix for out dict
                        file_name_prefix, coin_type_dir = self.get_coin_type_dir(coin_type_link, issuer_record, id)

                        coin_type_page = self.basic_helper.fetch(urljoin(self.base_url, coin_type_url))

                        if id is None:
                            raise ValueError(f"Cannot extract coin type ID from URL: {coin_type_url}")

                        out = {
                            "id": id,
                            "issuer_id": issuer_record["id"],
                            "title": None,
                            "subtitle": None,
                            "edge_image": None,
                            "period": period["period_text"],
                            "file_name_prefix": file_name_prefix,
                            "sample_images": [],
                            "comment_images": [],
                            "rarity_index": None,
                        } 
                        
                        self.parse_coin_type_page(out, coin_type_page)

                        if not coin_type_db_info:
                            # Save coin type fully
                            self.db_helper.save_coin_type_full(out)

                        # Create dir if not exists (it shouldn't, unless created partially during this run? No, we checked exists above)
                        os.makedirs(coin_type_dir, exist_ok=True)

                        cleaned_page = self.clean_html(coin_type_page, out, issuer_record['numista_url_slug'])

                        file_path = os.path.join(coin_type_dir, "coin_type.html")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(cleaned_page)

                        self.download_coin_type_images(out, issuer_record['numista_url_slug'], coin_type_dir)

                        if coin_type_id is not None and id == coin_type_id:
                             print(f"Finished processing targeted coin type {id}. Exiting.")
                             return
                
                # Pagination
                next_page = self._get_next_page_number(country_page_soup)
                if next_page:
                    page = next_page
                else:
                    break


def main():
    scraper = CoinTypesScraper()
    scraper.should_cleanup = True
    scraper.process()

if __name__ == '__main__':
    raise SystemExit(main())