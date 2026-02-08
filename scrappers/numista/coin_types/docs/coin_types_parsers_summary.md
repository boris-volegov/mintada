# Coin Types Parsers Summary

This document summarizes the current parser pipeline behavior for Numista coin types.

## Entry points

- `scrappers/numista/coin_types/coin_types_parser.py`
  - `parse_only(coin_type_id, parsers=None)` resolves `coin_type.html` from DB context and runs parser scripts.
  - If `parsers` is omitted, all parsers run in canonical order.
  - If `parsers` is provided, only the explicit subset is run.

- `scrappers/numista/coin_types/parsers/parse_all.py`
  - Canonical parser order:
    1. `parse_years`
    2. `parse_shapes`
    3. `parse_denomination`
    4. `parse_denomination_unit`
    5. `parse_dimensions`
    6. `parse_size`
    7. `parse_composition`
    8. `parse_calendar`
  - Supports aliases (for example: `shape`, `composition`, `denomination_unit`).
  - Supports targeted mode via `--coin-type-id` and `--coin-html-path`.
  - Dependency behavior:
    - default: dependencies are injected (for example `parse_denomination` before `parse_denomination_unit`)
    - `--no-auto-deps`: run only explicitly requested parsers

## Denomination parsing split

- `scrappers/numista/coin_types/parsers/parse_denomination.py`
  - Responsibility: populate only `coin_types.denomination_text` from HTML.
  - Extracts from the `Value` row in `coin_type.html`.
  - Normalizes fraction characters and spacing.
  - Does not populate `value_amount` or `denomination_unit`.

- `scrappers/numista/coin_types/parsers/parse_denomination_unit.py`
  - Responsibility: transform `denomination_text` into derived fields.
  - Populates:
    - `coin_types.value_amount`
    - `coin_types.denomination_unit`
  - Numeric parsing supports:
    - integer/decimal numbers
    - simple fractions (for example `1/2`)
    - mixed fractions (for example `10 1/2`)

## Majority-based denomination_unit normalization

When `parse_denomination_unit.py` derives a raw unit from `denomination_text`, it performs a majority lookup:

1. Use the raw parsed unit as search token.
2. Query `coin_types` rows where `denomination_text LIKE '%<raw unit>%'`.
3. Group matches by existing `denomination_unit` and count rows.
4. Use the unit from the largest group as default for the current row.
5. If no grouped matches exist, fallback to the raw parsed unit.

Example:

- `denomination_text = "960 Réis"` can normalize to `denomination_unit = "Real"` if `Real` is the dominant grouped value among matching rows.
