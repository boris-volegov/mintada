# Add Coin Type: Issuer Context + Cookie Flow

## Scope Implemented

This note captures the work completed in `Mintada.Navigator` for adding coin types from Numista without rewriting Python scrapers.

1. Added issuer-scoped **Add** action in the left issuer hierarchy via right-click context menu.
2. Added modal dialog (`OK` / `Cancel`) with:
   - `coin_type_id` input,
   - large multiline cookie textbox.
3. Integrated Navigator with existing Python scraper in targeted mode:
   - `--issuer-url-slug {issuer_slug}`
   - `--page 1`
   - `--coin-type-id {coin_type_id}`
4. Added cookie override path from app to scraper via environment variable:
   - `NUMISTA_COOKIE`.
5. Added successful-run cookie persistence:
   - after scraper succeeds, dialog cookie is written to `scrappers/numista/cookie`.
6. Removed fragile XAML command/data bindings for context menu and switched to runtime context-menu creation in code-behind (fix for startup/XAML parse cycle issues).
7. Restricted targeted scraper behavior:
   - when both `issuer_url_slug` and `coin_type_id` are provided, scraper exits after that issuer (does not continue scanning other issuers).

## Files Changed

- `src/Tools/Mintada.Navigator/Views/MainWindow.xaml`
  - removed top-row Add button approach
  - added `TreeViewItem` context-menu opening event hook

- `src/Tools/Mintada.Navigator/Views/MainWindow.xaml.cs`
  - added runtime context menu creation for issuer items
  - added `Add...` click handler that calls ViewModel command

- `src/Tools/Mintada.Navigator/Views/AddCoinTypeDialog.xaml`
  - new dialog UI with issuer display, coin id textbox, multiline cookie textbox

- `src/Tools/Mintada.Navigator/Views/AddCoinTypeDialog.xaml.cs`
  - dialog data wiring, validation, `OK` / `Cancel` behavior

- `src/Tools/Mintada.Navigator/ViewModels/MainViewModel.cs`
  - added `AddCoinTypeForIssuer` flow
  - invokes scraper service in issuer-targeted mode
  - on success: persists cookie file, refreshes data, selects the new coin

- `src/Tools/Mintada.Navigator/Services/CoinTypesScraperService.cs`
  - new subprocess service for scraper invocation
  - supports optional cookie injection via `NUMISTA_COOKIE`

- `scrappers/numista/basic_functions.py`
  - `_read_cookie_file()` now checks `NUMISTA_COOKIE` first, then falls back to local cookie file

- `scrappers/numista/coin_types/coin_types_scrapper.py`
  - added CLI arguments (`--issuer-url-slug`, `--page`, `--coin-type-id`, `--no-cleanup`)
  - added issuer-bounded exit for targeted issuer+coin runs

## Runtime Flow (Current)

1. User right-clicks an issuer in the left tree and selects **Add...**.
2. Dialog opens with issuer context, coin id input, and cookie textbox.
3. User clicks `OK`.
4. App runs Python scraper with issuer-targeted arguments and cookie override env var.
5. If scraper succeeds:
   - cookie is saved to `scrappers/numista/cookie`,
   - DB is reloaded,
   - app navigates/selects the added coin.
6. If scraper fails:
   - status shows tail of error text,
   - no cookie file overwrite occurs.

## Notes

- Cookie normalization currently flattens line breaks to spaces and trims whitespace; cookie semantics (`;`, `=`, order) are preserved.
- Publish validation was run after Navigator changes:
  - `dotnet publish src/Tools/Mintada.Navigator/Mintada.Navigator.csproj -c Release -o src/Tools/Mintada.Navigator/publish`
