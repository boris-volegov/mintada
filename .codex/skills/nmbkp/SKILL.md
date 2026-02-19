---
name: nmbkp
description: Create Numista backups by running tools/commands/backup_data.ps1. Supports SQLite archive backups and Postgres dump backups with optional suffix, db-only toggle, background toggle, and db type selection.
---

# Numista Backup

Run the project backup command and choose parameters from the user request.

## Inputs

Supported options in user text:

- `suffix=<text>`: optional explicit suffix to use
- `dbtype=s|p|sqlite|postgres`: required DB type selector
- `dbonly=true|false|1|0`: optional toggle
- `background=true|false|1|0`: optional toggle
- Default `dbonly=true` if not specified.

If `dbtype` is missing:
- Ask a short clarifying question before running anything:
  - "Choose backup type: `s` (SQLite archive) or `p` (Postgres dump)?"
- Do not assume a default.

Mode behavior:

- `dbtype=s` (SQLite):
  - if `dbonly=false`, include both DB and HTML in the `.7z` archive
  - if `dbonly=true`, include DB only
- `dbtype=p` (Postgres):
  - create a Postgres `.dump` backup via `pg_dump`
  - `dbonly` is ignored (Postgres backup is DB-only)

Background default:

- `dbtype=s`:
  - `dbonly=false` -> default `background=true` (avoid blocking on large HTML backups)
  - `dbonly=true` -> default `background=false`
- `dbtype=p`:
  - default `background=false`
  - if user sets `background=true`, script runs foreground and reports that background is unsupported for dump mode

If user sets `background`, use the explicit value.

## Suffix Rules

1. If user provides `suffix=...`, use it directly.
2. Otherwise auto-generate a short suffix from recent work:
- Inspect `git status --porcelain` and recent commit subjects (`git log -n 5 --pretty=%s`).
- Extract 1-3 topical tokens from changed paths/messages.
- Keep lowercase snake_case and short (prefer <= 24 chars).
- Good examples: `mcp_http`, `backup_tools`, `coin_types_parser`, `issuer_fix`.
- Fallback: `work`.

## Execute

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/commands/backup_data.ps1 -suffix "<suffix>" -dbtype <s_or_p> -dbonly <true_or_false_or_1_or_0> -background <true_or_false_or_1_or_0>
```

After running, read:

- if `dbtype=s`: `D:\bkp\numista_bkp\logs\last_backup.json`
- if `dbtype=p`: `D:\numista_bkp\logs\last_backup.json`

Use this file as source of truth for status, archive path, PID, and log paths.

Then report:

- resolved suffix
- `dbtype` value used
- `dbonly` value used
- `background` value used
- resulting archive path
- if background was used: PID and log file paths

