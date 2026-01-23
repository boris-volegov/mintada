import os
import sys
from PIL import Image, UnidentifiedImageError
import csv

def is_broken_image(file_path):
    """
    Checks if an image is broken or truncated.
    Returns True if broken, False otherwise.
    """
    try:
        with Image.open(file_path) as img:
            img.verify()  # Verify integrity
        return False
    except (IOError, SyntaxError, UnidentifiedImageError) as e:
        # print(f"Broken image found: {file_path} - {e}")
        return True
    except Exception as e:
        # print(f"Unexpected error checking {file_path}: {e}")
        return True

def find_broken_images(base_dir, log_file):
    """
    Recursively finds broken images in base_dir and logs them to log_file.
    """
    
    print(f"Scanning for broken images in: {base_dir}")
    print(f"Logging to: {log_file}")
    
    try:
        with open(log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['issuer_slug', 'coin_type_slug', 'image_name', 'error_type'])
            
            # Walk through the directory structure
            # Structure: base_dir / issuer_slug / coin_type_folder / images / image.ext
            
            # Since base_dir is .../coin_types/html usually
            # we expect immediate children to be issuer_slugs (directories)
            
            if not os.path.isdir(base_dir):
                print(f"Error: {base_dir} is not a directory.")
                return

            issuers = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
            total_issuers = len(issuers)
            
            for i, issuer_slug in enumerate(issuers):
                issuer_path = os.path.join(base_dir, issuer_slug)
                print(f"[{i+1}/{total_issuers}] Processing issuer: {issuer_slug}")
                
                # Inside issuer_slug, there are coin type folders
                # Naming convention: {coin_type_slug}_{id}
                
                coin_type_folders = [d for d in os.listdir(issuer_path) if os.path.isdir(os.path.join(issuer_path, d))]
                
                for coin_folder_name in coin_type_folders:
                    coin_folder_path = os.path.join(issuer_path, coin_folder_name)
                    
                    # Parse coin_type_slug from folder name
                    # format: prefix_id, but slug might contain underscores. id is integer at the end.
                    # safer: rsplit by last underscore
                    if '_' in coin_folder_name:
                        parts = coin_folder_name.rsplit('_', 1)
                        if len(parts) == 2 and parts[1].isdigit():
                             coin_type_slug = parts[0]
                        else:
                             coin_type_slug = coin_folder_name # Fallback
                    else:
                        coin_type_slug = coin_folder_name

                    # Directories to check for images
                    subdirs_to_check = ['images', 'edge_image', 'comment_images']
                    
                    for subdir in subdirs_to_check:
                        target_dir = os.path.join(coin_folder_path, subdir)
                        if os.path.isdir(target_dir):
                            for filename in os.listdir(target_dir):
                                file_path = os.path.join(target_dir, filename)
                                
                                # Check extension
                                lower_name = filename.lower()
                                if lower_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff')):
                                    if is_broken_image(file_path):
                                        print(f"!!! Broken Image: {issuer_slug} / {coin_type_slug} / {subdir} / {filename}")
                                        writer.writerow([issuer_slug, coin_type_slug, filename, 'Broken/Truncated'])

    except Exception as e:
        print(f"An error occurred during execution: {e}")

if __name__ == "__main__":
    # Determine base directory: typically directory_of_script/html
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_dir = os.path.join(script_dir, "html")
    
    # Allow overriding via command line arg for testing, but default to relative 'html'
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        html_dir = sys.argv[1]
        
    log_file_path = os.path.join(script_dir, "broken_images.log")
    
    if os.path.exists(html_dir):
        find_broken_images(html_dir, log_file_path)
        print("Done.")
    else:
        print(f"Directory not found: {html_dir}")
