---
name: nmbkp
description: Create Numista backup archives by running tools/commands/backup_data.ps1. Use when the user asks to backup, snapshot, or archive the Numista data (coins.db, and optionally coin_types/html). Supports optional suffix and optional db-only toggle.
---

# Numista Backup

Run the project backup command and choose parameters from the user request.

## Inputs

Supported options in user text:

- `suffix=<text>`: optional explicit suffix to use
- `dbonly=true|false|1|0`: optional toggle
- `background=true|false|1|0`: optional toggle
- Default `dbonly=true` if not specified

If `dbonly=false`, include both DB and HTML in the archive.
If `dbonly=true`, include DB only.

Background default:

- `dbonly=false` -> default `background=true` (avoid blocking on large HTML backups)
- `dbonly=true` -> default `background=false`

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
powershell -ExecutionPolicy Bypass -File tools/commands/backup_data.ps1 -suffix "<suffix>" -dbonly <true_or_false_or_1_or_0> -background <true_or_false_or_1_or_0>
```

After running, read:

`D:\bkp\numista_bkp\logs\last_backup.json`

Use this file as source of truth for status, archive path, PID, and log paths.

Then report:

- resolved suffix
- `dbonly` value used
- `background` value used
- resulting archive path
- if background was used: PID and log file paths

