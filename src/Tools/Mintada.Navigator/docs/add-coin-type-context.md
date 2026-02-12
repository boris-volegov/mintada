# Add Coin Type: Button + Auto-Issuer Flow

## Scope Implemented

This note captures the work completed in `Mintada.Navigator` for adding coin types from Numista without rewriting Python scrapers.

1. Added persistent **Add...** button in Coin Types tab header row (same row as Coin ID filter, right-aligned).
2. Updated modal dialog (`OK` / `Cancel`) to:
   - keep `coin_type_id` input,
   - remove cookie textbox,
   - show red warning when coin type already exists:
     - "This coin type ID already exists. Clicking OK will reprocess and overwrite its current scraped data."
3. Integrated Navigator with Python scraper targeted mode:
   - always passes `--coin-type-id {coin_type_id}`,
   - passes `--issuer-url-slug {issuer_slug}` only when issuer context is intentionally used for non-reprocess runs.
4. Removed Navigator-side cookie injection and persistence logic:
   - no `NUMISTA_COOKIE` environment override from app,
   - scraper reads cookie from `scrappers/numista/cookie` using its own file logic.
5. Added auto-issuer support end-to-end:
   - Add action can run with no selected issuer,
   - scraper auto-resolves issuer slug from `https://en.numista.com/{coin_type_id}`.
6. Existing coin IDs no longer short-circuit to selection only:
   - clicking `OK` now triggers forced reprocess path.

## Files Changed

- `src/Tools/Mintada.Navigator/Views/MainWindow.xaml`
  - added right-aligned `Add...` button on Coin ID row
  - removed issuer TreeView context-menu hook for Add action

- `src/Tools/Mintada.Navigator/Views/MainWindow.xaml.cs`
  - removed context-menu Add handlers
  - added `AddCoinTypeButton_Click` calling ViewModel command (selected issuer optional)

- `src/Tools/Mintada.Navigator/Views/AddCoinTypeDialog.xaml`
  - dialog UI with issuer display and coin id textbox
  - added red "existing ID will reprocess" warning text block
  - removed cookie textbox section

- `src/Tools/Mintada.Navigator/Views/AddCoinTypeDialog.xaml.cs`
  - added async coin existence check hook for warning visibility
  - removed cookie fields and cookie bindings

- `src/Tools/Mintada.Navigator/ViewModels/MainViewModel.cs`
  - added `AddCoinTypeForIssuer` flow
  - supports null issuer context (auto-detect mode)
  - reprocesses when coin already exists instead of returning early
  - removed cookie read/write and normalization logic
  - refreshes data and selects coin after successful scrape/reprocess

- `src/Tools/Mintada.Navigator/Services/CoinTypesScraperService.cs`
  - new subprocess service for scraper invocation
  - removed cookie parameter and environment override logic

- `scrappers/numista/coin_types/coin_types_scrapper.py`
  - added CLI arguments (`--issuer-url-slug`, `--page`, `--coin-type-id`, `--no-cleanup`)
  - added issuer-bounded exit for targeted issuer+coin runs
  - auto-resolves issuer slug from coin page when only coin id is supplied

## Runtime Flow (Current)

1. User clicks **Add...** in Coin Types tab header (right side of Coin ID row).
2. Dialog opens with issuer display:
   - selected issuer context, or
   - `Auto-detect from Coin ID (Auto)` when none selected.
3. User clicks `OK`.
4. App runs Python scraper in targeted mode (`--coin-type-id`, optional issuer slug).
5. If scraper succeeds:
   - DB is reloaded,
   - app navigates/selects the added coin.
6. If scraper fails:
   - status shows tail of error text.

## Notes

- Cookie input is intentionally removed from Navigator UI to avoid drift; cookie file remains the source of truth.
- Publish validation was run after Navigator changes:
  - `dotnet publish src/Tools/Mintada.Navigator/Mintada.Navigator.csproj -c Release -o src/Tools/Mintada.Navigator/publish`
