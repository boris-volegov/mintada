# Issuer Coin Types Scrapper Context

## Purpose
This scraper (`issuer_coin_types_scrapper.py`) links Numista ruler data to local coin type HTML files and updates `issuers_rulers_rel.ruler_id`.

Main goal:
- Populate `issuers_rulers_rel` from Numista "ruling authority" options.
- For each coin type, parse ruler link(s) from `coin_type.html`.
- Match ruler name -> `issuers_rulers_rel.name` (space-insensitive).
- Fill `ruler_id` when missing, and enforce strict consistency checks.
- Update `coin_types.reviewed` with review status.

## Numista Navigation Path
High-level website flow used by the scraper:

1. Open issuer coin types list:
   - `https://en.numista.com/catalogue/index.php?e={issuer_slug}&r=&st=1&cat=y&im1=&im2=&ru=&ie=&ca=3&no=&v=&a=&dg=&i=&b=&m=&f=&t=&t2=&w=&mt=&u=&g=&q=200`
2. From page 1, capture ruling authorities:
   - Use endpoint (always): `https://en.numista.com/catalogue/get_rulers.php?country={issuer_slug}&prefill=`
   - Parse returned `<option ...>` values.
   - Group options (`value="g{integer}"`) are stored in `issuers_rulers_rel_groups`:
     - `id = parsed integer part`
     - `name = option text`
   - For regular ruler options (`value="{integer}"`):
     - if option text is visually indented, assign current `group_id`
     - if option is not indented, keep `group_id = NULL`
   - When a new group option appears, it becomes the current group.
3. Collect coin type IDs from all paginated issuer list pages:
   - Parse links from `div.resultat_recherche div.description_piece strong a[href]`
   - Follow pagination via `<a rel="next" ...>`.
4. For each discovered coin type ID:
   - Find local folder under `coin_types/html/{issuer_slug}/{slug}_{coin_type_id}/coin_type.html`
   - Parse ruler links from rows containing `a[href*="/catalogue/ruler.php?id="]`.

## Data Sources
- Remote:
  - Numista list pages (`index.php?...`).
  - Numista rulers endpoint (`get_rulers.php`).
- Local filesystem:
  - `scrappers/numista/coin_types/html/{issuer_slug}/.../coin_type.html`
- Database:
  - `D:\projects\mintada\data\numista\coins.db`
  - Tables used:
    - `coin_types` (drives issuer list; only issuers that already have coin types are processed)
    - `issuers_rulers_rel (id, issuer_id, ruler_id, name, group_id)`
    - `issuers_rulers_rel_groups (id, name)`
    - `coin_types_rulers_rel (coin_type_id, ruler_id)`
    - `_coin_type_exceptions (coin_type_id, ruler_id, no_match)`

## Matching/Update Rules
For each ruler link found in `coin_type.html`:

1. Extract:
   - `ruler_id` from `/catalogue/ruler.php?id={ruler_id}`
   - `ruler_name` from link text
2. Normalize for comparison:
   - Clean text
   - Remove all whitespace
3. Match normalized link text to normalized `issuers_rulers_rel.name` for same `issuer_id`.
4. Apply strict behavior:
   - If no match: raise exception and stop.
   - If multiple matches: raise exception and stop.
   - If match and DB `ruler_id` is NULL: update it.
   - If match and DB `ruler_id` equals parsed value: ignore.
   - If match and DB `ruler_id` differs: raise exception and stop.
5. On each successful match, ensure relation exists in `coin_types_rulers_rel`:
   - Insert `(coin_type_id, ruler_id)` if missing.
6. Update `coin_types.reviewed`:
   - `1` when coin type was successfully reviewed locally.
   - `0` when local `coin_type.html` is missing and DB issuer matches current Numista issuer.
   - `{issuer_id}` (current Numista issuer id) when local `coin_type.html` is missing and DB issuer differs.

## Issuer Selection
- Issuers are loaded from `issuers JOIN coin_types` (distinct), so only issuers with coin-type records are processed.

## Expected Runtime Logs
Typical progress messages:
- Number of issuers loaded
- Resume point from `pages.log` (if present)
- Current issuer slug/id
- Number of `ru` options loaded from `get_rulers.php`
- Pagination fetch progress (`rel="next"` pages)
- Number of coin type IDs discovered
- Missing local `coin_type.html` warnings
- Final counts: checked links, updated `ruler_id` rows

## Resume Behavior (`pages.log`)
- Log file path: `scrappers/numista/coin_types/pages.log`
- Format per line: `issuer_id,page_number`
- The scraper appends one line before each page fetch.
- On restart, it reads the last line and resumes from that issuer/page.
- This is intended to avoid restarting from scratch after an exception.

## Fail-Fast Behavior
- The scraper is configured to stop immediately on irregularities (raises exception),
  with two explicit warning-and-continue exceptions listed below.
- Examples:
  - malformed `pages.log` last line
  - missing/ambiguous ruler name match or conflicting `ruler_id`
- Warning-and-continue exceptions:
  - `get_rulers.php` returns unusable/empty/no-valid options (continue with existing DB rows)
  - issuer page has no coin types (continue to next page/issuer)
  - local `coin_type.html` missing (set `coin_types.reviewed` as described above and continue)
  - missing/malformed/empty ruler link entries inside `coin_type.html` (skip those links/coin type)

## Recent Changes (2026-02)
Short summary of behavior updates applied during current iteration:

- Ruler extraction processes all `<tr>` rows and all ruler links (`a[href*="/catalogue/ruler.php?id="]`)
  found in a coin type page, not just a single ruler row/link.
  Duplicate `(ruler_id, ruler_name)` pairs are deduplicated before matching.
- Name normalization now ignores hierarchy prefix before the last hierarchy separator (U+203A) character.
  Example: `Northern Song dynasty [U+203A] Taizong (...)` is matched as `Taizong (...)`.
- Ruler matching now uses ordered candidates from link text:
  - base name + date suffix (if last parenthetical starts with a digit)
  - first alias parenthetical + same date suffix
  - full original text
- When candidate name matching is ambiguous (`>1` rows), scraper now tries fallback by relation id:
  `issuers_rulers_rel.id == ruler_id` parsed from ruler link.
  - if fallback resolves to exactly one row: continue
  - if still ambiguous: raise exception
  - if no fallback match: continue candidate attempts, then unresolved no-match path applies
- If no candidate matches:
  - do not raise
  - insert into `_coin_type_exceptions` with `(coin_type_id, ruler_id, no_match=1)`
  - continue processing
- If `coin_types_rulers_rel` insert fails on FK constraint (typically missing `rulers.id`):
  - do not raise
  - insert `(coin_type_id, ruler_id)` into `_coin_type_exceptions`
  - continue processing
- If RU options are empty for an issuer (`issuers_rulers_rel` has no rows):
  - if local `coin_type.html` has ruler links, insert coin type into `_coin_type_exceptions` and continue
  - if local html is missing and coin type is absent in DB, insert coin type into `_coin_type_exceptions` and continue
  - if local html is missing but DB issuer differs from current issuer, set `coin_types.reviewed={issuer_id}` and continue

## How To Run
From repository root:

```powershell
.\.venv\Scripts\python.exe scrappers\numista\coin_types\issuer_coin_types_scrapper.py
```

## Notes
- `#ru` on list page is JS-populated on Numista; direct HTML often has only one empty option.
- That is why this scraper always calls `get_rulers.php` directly for ruler options.

