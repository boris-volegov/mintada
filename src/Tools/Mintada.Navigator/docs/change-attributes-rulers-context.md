# Change Attributes: Periods & Rulers Context

## Scope Implemented

This note captures the work completed in `Mintada.Navigator` for the **Change Attributes** dialog:

1. Renamed section title from `Periods` to `Periods &Rulers`.
2. Added three ruler dropdowns (`Ruler 1`, `Ruler 2`, `Ruler 3`) on the same row as `Period`.
3. Parsed ruler links from `coin_type.html` (`/catalogue/ruler.php?id=...`) to extract:
   - `ruler_id` (from link querystring),
   - display text (cleaned of tags/entities and extra spaces, without name normalization).
4. Populated ruler dropdowns from a union by `ruler_id`:
   - all DB rulers for issuer from `issuers_rulers_rel` (with name fallback from `rulers`),
   - plus HTML ruler IDs not already present in issuer DB list.
5. Default selected ruler(s):
   - first from `coin_types_rulers_rel` for current coin type,
   - if no DB mapping exists, fallback to first up to 3 parsed HTML rulers,
   - if neither exists, keep dropdowns empty (no forced first-option selection).
6. On `OK`, inserted missing relations only:
   - ensure `issuers_rulers_rel` exists for each selected `(issuer_id, ruler_id)`,
   - then ensure `coin_types_rulers_rel` exists for each selected `(coin_type_id, ruler_id)`.
7. Generated `issuers_rulers_rel.id` from Unix milliseconds (collision-safe by incrementing if needed).

## Files Changed

- `src/Tools/Mintada.Navigator/Views/ChangeCoinAttributesDialog.xaml`
  - section title changed to `Periods &Rulers`
  - added `Ruler1ComboBox`, `Ruler2ComboBox`, `Ruler3ComboBox`

- `src/Tools/Mintada.Navigator/Views/ChangeCoinAttributesDialog.xaml.cs`
  - added selected ruler properties:
    - `SelectedRuler1`, `SelectedRuler2`, `SelectedRuler3`
    - `SelectedRulers` (deduped by `Id`)
  - extended `SetData(...)` to accept `List<RulerOption>` and selected ruler IDs
  - selection defaults now passed as explicit selected ruler IDs

- `src/Tools/Mintada.Navigator/Models/RulerOption.cs`
  - new model: `Id`, `Name`

- `src/Tools/Mintada.Navigator/Services/CoinParserService.cs`
  - added `ExtractRulers(string htmlContent): List<RulerOption>`
  - added text cleanup helper used for ruler link text extraction

- `src/Tools/Mintada.Navigator/ViewModels/MainViewModel.cs`
  - in `ChangeCoinAttributesAsync()`:
    - loads current coin `coin_type.html` and parses rulers via `_coinParserService.ExtractRulers(...)`
    - loads issuer ruler options from DB (`GetRulerOptionsForIssuerAsync`)
    - builds union list by `ruler_id` (DB first, add missing HTML IDs)
    - loads selected ruler IDs from `coin_types_rulers_rel` (`GetRulerIdsForCoinTypeAsync`)
    - falls back to parsed HTML IDs only when DB relation list is empty
    - passes both options and selected IDs into dialog
    - on save, calls DB relation upsert helper with `dialog.SelectedRulers`

- `src/Tools/Mintada.Navigator/Services/DatabaseService.cs`
  - added `GetRulerOptionsForIssuerAsync(...)`
  - added `GetRulerIdsForCoinTypeAsync(...)`
  - added `EnsureRulerRelationsForCoinTypeAsync(...)`
  - added `GetNextIssuerRulerRelationIdAsync(...)`
  - relation insert behavior:
    - checks existence first for both relation tables,
    - inserts only missing rows (no duplicate inserts),
    - keeps save flow resilient on FK issues for `coin_types_rulers_rel`

## Runtime Flow (Current)

1. User opens **Change Attributes**.
2. ViewModel loads issuer ruler options from DB and parses ruler links from local `coin_type.html`.
3. Ruler options are merged by `ruler_id` (DB options + missing HTML options).
4. Dialog shows `Period` + `Ruler 1/2/3` dropdowns.
5. Selection defaults from `coin_types_rulers_rel`; fallback to HTML IDs only if no DB mapping exists; otherwise stay empty.
6. User clicks `OK`.
7. App:
   - ensures ruler relations exist in DB (insert-if-missing),
   - updates coin attributes as before.

## Notes / Follow-ups

- Current implementation stores ruler ID in dropdown selected item (`RulerOption`), which is preferable to plain textbox for reliable ID-text association.
- If we later need explicit user feedback (e.g., how many ruler relations were inserted), expose `relationInsertions` in status/UI.
- If preferred, ruler parsing can be moved from `CoinParserService` into a dedicated `RulerParserService` to separate concerns.
