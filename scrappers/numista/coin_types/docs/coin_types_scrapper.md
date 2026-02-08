# Coin Types Scrapper

This document describes the purpose and high-level behavior of `scrappers/numista/coin_types/coin_types_scrapper.py`.

## Purpose

`coin_types_scrapper.py` is the main Numista coin-type ingestion pipeline.  
It crawls issuer catalogue pages, fetches coin-type detail pages, stores normalized records into DB, writes cleaned HTML files, downloads images, and updates ruler relationships.

## Main functionality summary

1. Load issuers from DB (`issuers` table) and iterate issuer by issuer.
2. Ingest ruler filter options (`ru`) for the issuer and populate/update issuer ruler relations.
3. Walk issuer catalogue pagination and parse coin links by period.
4. For each coin type:
   - fetch details page
   - parse core fields into an `out` structure
   - save/update DB records
   - persist cleaned `coin_type.html` under issuer/coin folder
   - download sample/comment/reference images
   - process ruler links from coin HTML and fill relation tables

## Resume and targeted modes

- Resume mode:
  - Reads last processed issuer/page from `pages.log`.
  - Can clean up last inserted coin on restart (`cleanup_last_run`).
- Targeted coin mode:
  - `process(..., coin_type_id=<id>)` can force reprocess a specific coin:
    - deletes existing DB row and local folder for that coin
    - re-scrapes and exits after that coin is processed
  - If `coin_type_id` is provided without `issuer_url_slug`, the scraper resolves issuer slug automatically by:
    - fetching `https://en.numista.com/{coin_type_id}`
    - reading `section#fiche_caracteristiques` -> `Issuer` row
    - extracting issuer link (e.g. `/catalogue/royaume-uni-1.html`)
    - converting to `issuers.numista_url_slug` (`royaume-uni`)

## Period handling

- Period headers parsed on catalogue pages now feed `periods` and `coin_types.period_id`:
  - for each encountered period, scraper finds existing `periods` row by `(issuer_id, period name)` or inserts a new row with `unit_relation_text`
  - coin type save keeps legacy `coin_types.period` text and also sets `coin_types.period_id`
- This ensures reruns can preserve normalized period linkage while keeping source text.

## Parser invocation (end of scrape flow)

After each coin page is fetched and cleaned HTML is written, the scraper calls:

- `self.coin_type_parser.run_post_parsers_for_coin(id, file_path)`

This delegates to `coin_types_parser.py` / `parsers/parse_all.py`, so all post-HTML parsers run on the newly scraped coin (or a requested subset when used through parser entry points).

This is the key integration point where scraped raw fields are transformed into derived structured fields (years, shapes, denomination fields, dimensions, size, composition, calendar).

## Key outputs

- DB writes:
  - `coin_types` core + parsed fields
  - `issuers_rulers_rel`
  - `coin_types_rulers_rel`
- Filesystem writes:
  - per-coin cleaned `coin_type.html`
  - downloaded images
- Progress tracking:
  - `pages.log`
