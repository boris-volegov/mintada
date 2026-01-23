#!/usr/bin/env python3
"""
Validate the coin_images directory structure.

Hierarchy:
Level 1 (root): coin_images/
  - Only country folders allowed.

Level 2 (inside each country folder):
  - Only coin_type folders allowed.
  - Each coin_type folder name must start with the *country folder name* + "-".
    e.g., country="albania" -> "albania-1-2-lek-1930-1931-62230"

Level 3 (inside each coin_type folder):
  - Must not be empty.
  - Must not contain subfolders.
  - Must contain only JPG/JPEG files that form pairs of the same base name,
    differing only by the "-1" or "-2" suffix.
    e.g., "1930-8161157-1.jpg" and "1930-8161157-2.jpg"

All deviations are written to a log file (coin_structure_issues.log).
"""

import argparse
import os
import re
from datetime import datetime

PAIR_RE = re.compile(r'^(?P<base>.+)-(?P<side>[12])\.(?P<ext>jpe?g)$', re.IGNORECASE)

def log_issue(fp, issue_type, path, detail=""):
    fp.write(f"{issue_type}\t{path}\t{detail}\n")

def is_hidden(name: str) -> bool:
    return name.startswith('.') or name.startswith('_')

def validate(root_dir: str, log_path: str) -> int:
    issues = 0
    with open(log_path, 'w', encoding='utf-8') as fp:
        fp.write(f"# Coin images structure validation\n")
        fp.write(f"# Root: {root_dir}\n")
        fp.write(f"# When: {datetime.now().isoformat(sep=' ', timespec='seconds')}\n")
        fp.write("# Format: ISSUE_TYPE\\tPATH\\tDETAILS\n\n")

        if not os.path.isdir(root_dir):
            log_issue(fp, "ERROR_ROOT_MISSING", root_dir, "Root directory does not exist or is not a directory")
            return 1

        # Level 1: root should only contain country folders
        for entry in sorted(os.listdir(root_dir)):
            entry_path = os.path.join(root_dir, entry)

            # ignore hidden metadata like .DS_Store, thumbs.db, etc.
            if is_hidden(entry):
                continue

            if not os.path.isdir(entry_path):
                issues += 1
                log_issue(fp, "NON_FOLDER_IN_ROOT", entry_path, "Only country folders are allowed at root")
                continue

            country = entry
            # Level 2: coin_type folders inside each country
            for sub in sorted(os.listdir(entry_path)):
                sub_path = os.path.join(entry_path, sub)

                if is_hidden(sub):
                    continue

                if not os.path.isdir(sub_path):
                    issues += 1
                    log_issue(fp, "NON_FOLDER_IN_COUNTRY", sub_path, "Only coin_type folders are allowed inside a country folder")
                    continue

                # coin_type folder name must start with '{country}-'
                if not sub.lower().startswith(country.lower() + "-"):
                    issues += 1
                    log_issue(fp, "BAD_COIN_TYPE_NAME", sub_path, f"Coin-type folder must start with '{country}-'")
                    # keep validating its contents anyway

                # Level 3: check contents of coin_type folder
                items = [f for f in os.listdir(sub_path) if not is_hidden(f)]
                if not items:
                    issues += 1
                    log_issue(fp, "EMPTY_COIN_TYPE_FOLDER", sub_path, "Folder is empty")
                    continue

                # No subfolders allowed at level 3
                subfolders = [f for f in items if os.path.isdir(os.path.join(sub_path, f))]
                if subfolders:
                    issues += 1
                    log_issue(fp, "UNEXPECTED_SUBFOLDERS", sub_path, f"Contains subfolders: {', '.join(sorted(subfolders))}")

                # Only JPG/JPEG files are allowed
                files = [f for f in items if os.path.isfile(os.path.join(sub_path, f))]
                non_jpgs = [f for f in files if not f.lower().endswith((".jpg", ".jpeg"))]
                if non_jpgs:
                    issues += 1
                    log_issue(fp, "NON_JPG_FILES", sub_path, f"Only JPG/JPEG allowed. Found: {', '.join(sorted(non_jpgs))}")

                # Validate pairs (-1 / -2)
                base_to_sides = {}
                for fname in files:
                    m = PAIR_RE.match(fname)
                    if not m:
                        # Skip non-jpgs already reported. If JPG but doesn't match naming, report.
                        if fname.lower().endswith((".jpg", ".jpeg")):
                            issues += 1
                            log_issue(fp, "BAD_IMAGE_NAME", os.path.join(sub_path, fname),
                                      "Expected '<base>-1.jpg' or '<base>-2.jpg'")
                        continue
                    base = m.group("base")
                    side = m.group("side")
                    base_to_sides.setdefault(base, set()).add(side)

                # Check each base has both sides
                for base, sides in sorted(base_to_sides.items()):
                    missing = {"1", "2"} - sides
                    if missing:
                        issues += 1
                        log_issue(fp, "INCOMPLETE_PAIR", os.path.join(sub_path, base),
                                  f"Missing side(s): {', '.join(sorted(missing))}")

    return issues

def main():
    parser = argparse.ArgumentParser(description="Validate coin_images folder structure and log deviations.")
    parser.add_argument("issue_type", nargs="?", default="5",
                    help="Subfolder for issue type (default: ./coin_images/1)")
    parser.add_argument("root", nargs="?", default="coin_images",
                        help="Path to the coin_images root folder (default: ./coin_images)")
    parser.add_argument("--log", default="coin_structure_issues.log",
                        help="Path to output log file (default: coin_structure_issues.log)")
    args = parser.parse_args()

    issues = validate(os.path.join(args.root, args.issue_type), args.log)
    print(f"Validation complete. Issues found: {issues}")
    print(f"Log written to: {os.path.abspath(args.log)}")

if __name__ == "__main__":
    main()
