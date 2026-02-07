# Change Attributes: Periods & Rulers Context

## Scope Implemented

This note captures the work completed in `Mintada.Navigator` for the **Change Attributes** dialog:

1. Renamed section title from `Periods` to `Periods &Rulers`.
2. Added three ruler dropdowns (`Ruler 1`, `Ruler 2`, `Ruler 3`) on the same row as `Period`.
3. Parsed ruler links from `coin_type.html` (`/catalogue/ruler.php?id=...`) to extract:
   - `ruler_id` (from link querystring),
   - display text (cleaned of tags/entities and extra spaces, without name normalization).
4. Populated ruler dropdowns from parsed rulers:
   - value = parsed `ruler_id`,
   - text = parsed ruler link text,
   - defaults = first/second/third parsed rulers.
5. On `OK`, inserted missing relations only:
   - `issuers_rulers_rel` if `(issuer_id, ruler_id)` does not exist,
   - `coin_types_rulers_rel` if `(coin_type_id, ruler_id)` does not exist.
6. Generated `issuers_rulers_rel.id` from Unix milliseconds (collision-safe by incrementing if needed).

## Files Changed

- `src/Tools/Mintada.Navigator/Views/ChangeCoinAttributesDialog.xaml`
  - section title changed to `Periods &Rulers`
  - added `Ruler1ComboBox`, `Ruler2ComboBox`, `Ruler3ComboBox`

- `src/Tools/Mintada.Navigator/Views/ChangeCoinAttributesDialog.xaml.cs`
  - added selected ruler properties:
    - `SelectedRuler1`, `SelectedRuler2`, `SelectedRuler3`
    - `SelectedRulers` (deduped by `Id`)
  - extended `SetData(...)` to accept `List<RulerOption>`
  - default selection logic for first 3 parsed rulers

- `src/Tools/Mintada.Navigator/Models/RulerOption.cs`
  - new model: `Id`, `Name`

- `src/Tools/Mintada.Navigator/Services/CoinParserService.cs`
  - added `ExtractRulers(string htmlContent): List<RulerOption>`
  - added text cleanup helper used for ruler link text extraction

- `src/Tools/Mintada.Navigator/ViewModels/MainViewModel.cs`
  - in `ChangeCoinAttributesAsync()`:
    - loads current coin `coin_type.html`
    - parses rulers via `_coinParserService.ExtractRulers(...)`
    - passes ruler options into dialog
    - on save, calls DB relation upsert helper with `dialog.SelectedRulers`

- `src/Tools/Mintada.Navigator/Services/DatabaseService.cs`
  - added `EnsureRulerRelationsForCoinTypeAsync(...)`
  - added `GetNextIssuerRulerRelationIdAsync(...)`
  - relation insert behavior:
    - checks existence first,
    - inserts only missing rows,
    - keeps save flow resilient on FK issues for `coin_types_rulers_rel`

## Runtime Flow (Current)

1. User opens **Change Attributes**.
2. ViewModel reads local `coin_type.html` for selected coin.
3. Ruler links are parsed into `RulerOption` list.
4. Dialog shows `Period` + `Ruler 1/2/3` dropdowns.
5. User clicks `OK`.
6. App:
   - ensures ruler relations exist in DB (insert-if-missing),
   - updates coin attributes as before.

## Notes / Follow-ups

- Current implementation stores ruler ID in dropdown selected item (`RulerOption`), which is preferable to plain textbox for reliable ID-text association.
- If we later need explicit user feedback (e.g., how many ruler relations were inserted), expose `relationInsertions` in status/UI.
- If preferred, ruler parsing can be moved from `CoinParserService` into a dedicated `RulerParserService` to separate concerns.
