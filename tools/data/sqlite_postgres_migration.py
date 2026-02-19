#!/usr/bin/env python3
"""
Migrate data from SQLite to Postgres outside EF migrations.

Current scope:
- lookup table: shapes
- lookup table: issuer_types
- lookup table: issue_types
- lookup table: calendar_systems
- lookup table: rulers
- relation table: issuer_alt_names
- relation table: issuer_issue_types_rel (sqlite) -> issuers_issue_types_rel (postgres)
- table: issuers_rulers_rel_groups
- table: issuers_rulers_rel
- table: coin_types
- table: coin_type_samples
- table: coin_types_issuers_rulers_rel
- table mapping: periods (sqlite) -> coinage_periods (postgres)
- hierarchical table: issuers

Safety by default:
- if target Postgres table already has rows, script skips and does not modify it.
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate selected tables from SQLite to Postgres."
    )
    parser.add_argument(
        "--sqlite-path",
        default="data/numista/coins.db",
        help="Path to source SQLite DB (default: data/numista/coins.db).",
    )
    parser.add_argument(
        "--pg-container",
        default="mintada-db",
        help="Docker container name running Postgres (default: mintada-db).",
    )
    parser.add_argument(
        "--pg-db",
        default="mintada_db",
        help="Postgres database name (default: mintada_db).",
    )
    parser.add_argument(
        "--pg-user",
        default="admin",
        help="Postgres user (default: admin).",
    )
    parser.add_argument(
        "--pg-password",
        default="mintada",
        help="Postgres password (default: mintada).",
    )
    parser.add_argument(
        "--table",
        choices=[
            "shapes",
            "issuer_types",
            "issue_types",
            "calendar_systems",
            "rulers",
            "issuer_alt_names",
            "issuers_issue_types_rel",
            "issuers_rulers_rel_groups",
            "issuers_rulers_rel",
            "coin_types",
            "coin_type_samples",
            "coin_types_issuers_rulers_rel",
            "coinage_periods",
            "issuers",
        ],
        default="shapes",
        help=(
            "Table to migrate "
            "(currently: shapes, issuer_types, issue_types, "
            "calendar_systems, rulers, issuer_alt_names, "
            "issuers_issue_types_rel, issuers_rulers_rel_groups, issuers_rulers_rel, "
            "coin_types, coin_type_samples, coin_types_issuers_rulers_rel, "
            "coinage_periods, issuers)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Allow migration even when target Postgres table is non-empty. "
            "When enabled, insert uses ON CONFLICT DO NOTHING."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing to Postgres.",
    )
    return parser


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def resolve_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def to_sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def run_psql_query(
    *,
    container: str,
    db: str,
    user: str,
    password: str,
    query: str,
    use_stdin: bool = False,
) -> str:
    cmd = [
        "docker",
        "exec",
    ]
    if use_stdin:
        cmd.append("-i")

    cmd.extend(
        [
            "-e",
            f"PGPASSWORD={password}",
            container,
            "psql",
            "-h",
            "localhost",
            "-U",
            user,
            "-d",
            db,
            "-X",
            "-A",
            "-t",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
        ]
    )

    stdin_payload: bytes | None = None
    if use_stdin:
        cmd.extend(["-f", "-"])
        stdin_payload = query.encode("utf-8")
    else:
        cmd.extend(["-c", query])

    result = subprocess.run(
        cmd,
        input=stdin_payload,
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(
            "psql query failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )
    return stdout


def parse_single_int(output: str) -> int:
    for line in output.splitlines():
        text = line.strip()
        if text:
            return int(text)
    raise RuntimeError("Failed to parse integer from psql output.")


def parse_int_set(output: str) -> set[int]:
    values: set[int] = set()
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        values.add(int(text))
    return values


def parse_int_pair_set(output: str) -> set[tuple[int, int]]:
    values: set[tuple[int, int]] = set()
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        parts = text.split("|")
        if len(parts) != 2:
            raise RuntimeError(f"Failed to parse pair row: {text!r}")
        values.add((int(parts[0]), int(parts[1])))
    return values


def sqlite_to_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    text = str(value).strip().lower()
    if text in {"1", "t", "true", "yes", "y"}:
        return True
    if text in {"0", "f", "false", "no", "n", ""}:
        return False
    raise RuntimeError(f"Cannot convert value to bool: {value!r}")


def sqlite_to_nullable_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    text = str(value).strip().lower()
    if text == "":
        return None
    if text in {"1", "t", "true", "yes", "y"}:
        return True
    if text in {"0", "f", "false", "no", "n"}:
        return False
    raise RuntimeError(f"Cannot convert value to nullable bool: {value!r}")


def sqlite_to_nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def sqlite_to_required_text(value: Any, *, field: str, row_id: int) -> str:
    text = sqlite_to_nullable_text(value)
    if text is None:
        raise RuntimeError(f"Found coin_types row with empty {field} for id={row_id}.")
    return text


def sqlite_to_nullable_int(value: Any, *, field: str, row_id: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise RuntimeError(
            f"Found non-integer numeric {field}={value!r} for coin_types id={row_id}."
        )

    text = str(value).strip()
    if not text:
        return None
    try:
        numeric = Decimal(text)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Failed to parse integer field {field}={value!r} "
            f"for coin_types id={row_id}."
        ) from exc

    if numeric != numeric.to_integral_value():
        raise RuntimeError(
            f"Found non-integer numeric {field}={value!r} for coin_types id={row_id}."
        )
    return int(numeric)


def sqlite_to_required_int(value: Any, *, field: str, row_id: int) -> int:
    parsed = sqlite_to_nullable_int(value, field=field, row_id=row_id)
    if parsed is None:
        raise RuntimeError(f"Found coin_types row with NULL {field} for id={row_id}.")
    return parsed


def sqlite_to_nullable_decimal(
    value: Any, *, field: str, row_id: int
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise RuntimeError(
            f"Failed to parse numeric field {field}={value!r} "
            f"for coin_types id={row_id}."
        ) from exc


def sqlite_datetime_to_local_iso(value: Any, *, row_id: int) -> str:
    text = sqlite_to_required_text(value, field="date_time_inserted", row_id=row_id)

    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text[:-1]).replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to parse date_time_inserted={value!r} for coin_types id={row_id}."
        ) from exc

    if dt.tzinfo is None:
        dt = dt.astimezone()
    else:
        dt = dt.astimezone()
    return dt.isoformat(timespec="seconds")


def iter_chunks(rows: list[Any], chunk_size: int):
    for i in range(0, len(rows), chunk_size):
        yield rows[i : i + chunk_size]


def load_sqlite_shapes(sqlite_path: Path) -> list[tuple[int, str, int]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, seq_number FROM shapes ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    shapes: list[tuple[int, str, int]] = []
    for row in rows:
        shape_id = row["id"]
        name = row["name"]
        seq_number = row["seq_number"]
        if shape_id is None:
            raise RuntimeError("Found shapes row with NULL id in SQLite.")
        if name is None:
            raise RuntimeError(f"Found shapes row with NULL name for id={shape_id}.")
        if seq_number is None:
            raise RuntimeError(
                f"Found shapes row with NULL seq_number for id={shape_id}."
            )

        shapes.append((int(shape_id), str(name), int(seq_number)))

    return shapes


def load_sqlite_issuer_types(sqlite_path: Path) -> list[tuple[int, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, description FROM issuer_types ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    issuer_types: list[tuple[int, str]] = []
    for row in rows:
        issuer_type_id = row["id"]
        name = row["description"]
        if issuer_type_id is None:
            raise RuntimeError("Found issuer_types row with NULL id in SQLite.")
        if name is None:
            raise RuntimeError(
                f"Found issuer_types row with NULL description for id={issuer_type_id}."
            )
        issuer_types.append((int(issuer_type_id), str(name)))

    return issuer_types


def load_sqlite_issue_types(sqlite_path: Path) -> list[tuple[int, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, description FROM issue_types ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    issue_types: list[tuple[int, str]] = []
    for row in rows:
        issue_type_id = row["id"]
        name = row["description"]
        if issue_type_id is None:
            raise RuntimeError("Found issue_types row with NULL id in SQLite.")
        if name is None:
            raise RuntimeError(
                f"Found issue_types row with NULL description for id={issue_type_id}."
            )
        issue_types.append((int(issue_type_id), str(name)))

    return issue_types


def load_sqlite_calendar_systems(sqlite_path: Path) -> list[tuple[int, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name FROM calendar_systems ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    calendar_systems: list[tuple[int, str]] = []
    for row in rows:
        calendar_system_id = row["id"]
        name = row["name"]
        if calendar_system_id is None:
            raise RuntimeError("Found calendar_systems row with NULL id in SQLite.")
        if name is None:
            raise RuntimeError(
                "Found calendar_systems row with NULL name "
                f"for id={calendar_system_id}."
            )
        calendar_systems.append((int(calendar_system_id), str(name)))

    return calendar_systems


def load_sqlite_rulers(
    sqlite_path: Path,
) -> tuple[list[tuple[int, str, str | None, str | None]], int]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, name, title, dynasty, portrait_url, info FROM rulers ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    rulers: list[tuple[int, str, str | None, str | None]] = []
    fallback_name_count = 0
    for row in rows:
        ruler_id = row["id"]
        name_raw = row["name"]
        title_raw = row["title"]
        dynasty_raw = row["dynasty"]
        portrait_url_raw = row["portrait_url"]
        info_raw = row["info"]

        if ruler_id is None:
            raise RuntimeError("Found rulers row with NULL id in SQLite.")

        candidates = [name_raw, title_raw, dynasty_raw]
        resolved_name = ""
        for item in candidates:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                resolved_name = text
                break

        if not resolved_name:
            fallback_name_count += 1
            resolved_name = f"unnamed_ruler_{int(ruler_id)}"

        portrait_url = None
        if portrait_url_raw is not None:
            portrait_text = str(portrait_url_raw).strip()
            if portrait_text:
                portrait_url = portrait_text

        info = None
        if info_raw is not None:
            info_text = str(info_raw).strip()
            if info_text:
                info = info_text

        rulers.append((int(ruler_id), resolved_name, portrait_url, info))

    return rulers, fallback_name_count


def load_sqlite_issuer_alt_names(sqlite_path: Path) -> list[tuple[int, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT issuer_id, alt_name FROM issuers_alt_names "
            "ORDER BY issuer_id, alt_name"
        ).fetchall()
    finally:
        conn.close()

    alt_names: list[tuple[int, str]] = []
    for row in rows:
        issuer_id = row["issuer_id"]
        alt_name_raw = row["alt_name"]
        if issuer_id is None:
            raise RuntimeError("Found issuers_alt_names row with NULL issuer_id.")
        if alt_name_raw is None:
            raise RuntimeError(
                f"Found issuers_alt_names row with NULL alt_name for issuer_id={issuer_id}."
            )

        alt_name = str(alt_name_raw).strip()
        if not alt_name:
            raise RuntimeError(
                f"Found issuers_alt_names row with empty alt_name for issuer_id={issuer_id}."
            )

        alt_names.append((int(issuer_id), alt_name))

    return alt_names


def load_sqlite_issuer_issue_types_rel(sqlite_path: Path) -> list[tuple[int, int]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT issuer_id, issue_type_id FROM issuer_issue_types_rel "
            "ORDER BY issuer_id, issue_type_id"
        ).fetchall()
    finally:
        conn.close()

    rel_rows: list[tuple[int, int]] = []
    for row in rows:
        issuer_id = row["issuer_id"]
        issue_type_id = row["issue_type_id"]

        if issuer_id is None:
            raise RuntimeError(
                "Found issuer_issue_types_rel row with NULL issuer_id."
            )
        if issue_type_id is None:
            raise RuntimeError(
                "Found issuer_issue_types_rel row with NULL issue_type_id "
                f"for issuer_id={issuer_id}."
            )

        rel_rows.append((int(issuer_id), int(issue_type_id)))

    return rel_rows


def load_sqlite_issuers_rulers_rel_groups(
    sqlite_path: Path,
) -> list[tuple[int, int, str]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, issuer_id, name FROM issuers_rulers_rel_groups ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    group_rows: list[tuple[int, int, str]] = []
    for row in rows:
        group_id = row["id"]
        issuer_id = row["issuer_id"]
        name_raw = row["name"]

        if group_id is None:
            raise RuntimeError(
                "Found issuers_rulers_rel_groups row with NULL id in SQLite."
            )
        if issuer_id is None:
            raise RuntimeError(
                "Found issuers_rulers_rel_groups row with NULL issuer_id "
                f"for id={group_id}."
            )
        if name_raw is None:
            raise RuntimeError(
                "Found issuers_rulers_rel_groups row with NULL name "
                f"for id={group_id}."
            )

        name = str(name_raw).strip()
        if not name:
            raise RuntimeError(
                "Found issuers_rulers_rel_groups row with empty name "
                f"for id={group_id}."
            )

        group_rows.append((int(group_id), int(issuer_id), name))

    return group_rows


def load_sqlite_issuers_rulers_rel(
    sqlite_path: Path,
) -> tuple[
    list[tuple[int, int, int | None, int, str | None, str | None]],
    int,
    list[int],
]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                issuer_id,
                group_id,
                ruler_id,
                name,
                rule_type
            FROM issuers_rulers_rel
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    rel_rows: list[tuple[int, int, int | None, int, str | None, str | None]] = []
    skipped_missing_required_fk_count = 0
    skipped_missing_required_fk_sample_ids: list[int] = []
    for row in rows:
        rel_id = row["id"]
        issuer_id = row["issuer_id"]
        group_id_raw = row["group_id"]
        ruler_id = row["ruler_id"]
        name_raw = row["name"]
        rule_type_raw = row["rule_type"]

        if rel_id is None:
            raise RuntimeError("Found issuers_rulers_rel row with NULL id in SQLite.")
        if issuer_id is None or ruler_id is None:
            skipped_missing_required_fk_count += 1
            if len(skipped_missing_required_fk_sample_ids) < 20:
                skipped_missing_required_fk_sample_ids.append(int(rel_id))
            continue

        group_id = None if group_id_raw is None else int(group_id_raw)

        name = None
        if name_raw is not None:
            text = str(name_raw).strip()
            if text:
                name = text

        rule_type = None
        if rule_type_raw is not None:
            text = str(rule_type_raw).strip()
            if text:
                rule_type = text

        rel_rows.append(
            (int(rel_id), int(issuer_id), group_id, int(ruler_id), name, rule_type)
        )

    return rel_rows, skipped_missing_required_fk_count, skipped_missing_required_fk_sample_ids


def load_sqlite_periods(
    sqlite_path: Path,
) -> list[tuple[int, int, str | None, str | None]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, issuer_id, name, unit_relation_text FROM periods ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    periods: list[tuple[int, int, str | None, str | None]] = []
    for row in rows:
        period_id = row["id"]
        issuer_id = row["issuer_id"]
        name_raw = row["name"]
        unit_relation_raw = row["unit_relation_text"]

        if period_id is None:
            raise RuntimeError("Found periods row with NULL id in SQLite.")
        if issuer_id is None:
            raise RuntimeError(f"Found periods row with NULL issuer_id for id={period_id}.")

        name = None
        if name_raw is not None:
            trimmed = str(name_raw).strip()
            if trimmed:
                name = trimmed

        unit_relation_text = None
        if unit_relation_raw is not None:
            text = str(unit_relation_raw).strip()
            if text:
                unit_relation_text = text

        periods.append((int(period_id), int(issuer_id), name, unit_relation_text))

    return periods


def load_sqlite_issuers(
    sqlite_path: Path,
) -> list[tuple[int, int | None, int, str | None, str | None, str | None, bool, bool]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                parent_id,
                name,
                url_slug,
                territory_type,
                is_historical_period,
                is_section
            FROM issuers
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    # User-selected default for missing source issuer type.
    default_issuer_type_id = 1

    issuers: list[tuple[int, int | None, int, str | None, str | None, str | None, bool, bool]] = []
    for row in rows:
        issuer_id = row["id"]
        parent_id_raw = row["parent_id"]
        if issuer_id is None:
            raise RuntimeError("Found issuers row with NULL id in SQLite.")

        parent_id = None if parent_id_raw is None else int(parent_id_raw)
        name = None if row["name"] is None else str(row["name"])
        url_slug = None if row["url_slug"] is None else str(row["url_slug"])
        territory_type = (
            None if row["territory_type"] is None else str(row["territory_type"])
        )
        is_historical_period = sqlite_to_bool(row["is_historical_period"])
        is_section = sqlite_to_bool(row["is_section"])

        issuers.append(
            (
                int(issuer_id),
                parent_id,
                default_issuer_type_id,
                name,
                url_slug,
                territory_type,
                is_historical_period,
                is_section,
            )
        )

    return issuers


def load_sqlite_coin_types(
    sqlite_path: Path,
) -> list[
    tuple[
        int,
        int,
        str,
        str | None,
        str | None,
        int | None,
        int | None,
        int | None,
        str,
        str,
        int,
        int | None,
        Decimal | None,
        Decimal | None,
        Decimal | None,
        str | None,
        str | None,
        str | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
    ]
]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                issuer_id,
                title,
                subtitle,
                edge_image,
                shape_id,
                period_id,
                rarity_index,
                coin_type_slug,
                date_time_inserted,
                issue_type_id,
                calendar_system_id,
                weight,
                diameter,
                thickness,
                size,
                denomination_text,
                denomination_unit,
                start_date,
                end_date,
                start_native_date,
                end_native_date,
                start_mint_date,
                end_mint_date,
                restrike_start_mint_date,
                restrike_end_mint_date
            FROM coin_types
            ORDER BY id
            """
        ).fetchall()
    finally:
        conn.close()

    coin_types: list[
        tuple[
            int,
            int,
            str,
            str | None,
            str | None,
            int | None,
            int | None,
            int | None,
            str,
            str,
            int,
            int | None,
            Decimal | None,
            Decimal | None,
            Decimal | None,
            str | None,
            str | None,
            str | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
        ]
    ] = []

    for row in rows:
        coin_type_id = sqlite_to_required_int(row["id"], field="id", row_id=-1)
        issuer_id = sqlite_to_required_int(
            row["issuer_id"], field="issuer_id", row_id=coin_type_id
        )
        title = sqlite_to_required_text(row["title"], field="title", row_id=coin_type_id)
        subtitle = sqlite_to_nullable_text(row["subtitle"])
        edge_image = sqlite_to_nullable_text(row["edge_image"])
        shape_id = sqlite_to_nullable_int(
            row["shape_id"], field="shape_id", row_id=coin_type_id
        )
        coinage_period_id = sqlite_to_nullable_int(
            row["period_id"], field="period_id", row_id=coin_type_id
        )
        rarity_index = sqlite_to_nullable_int(
            row["rarity_index"], field="rarity_index", row_id=coin_type_id
        )
        url_slug = sqlite_to_required_text(
            row["coin_type_slug"], field="coin_type_slug", row_id=coin_type_id
        )
        date_time_inserted = sqlite_datetime_to_local_iso(
            row["date_time_inserted"], row_id=coin_type_id
        )
        issue_type_id = sqlite_to_required_int(
            row["issue_type_id"], field="issue_type_id", row_id=coin_type_id
        )
        calendar_system_id = sqlite_to_nullable_int(
            row["calendar_system_id"],
            field="calendar_system_id",
            row_id=coin_type_id,
        )
        weight = sqlite_to_nullable_decimal(
            row["weight"], field="weight", row_id=coin_type_id
        )
        diameter = sqlite_to_nullable_decimal(
            row["diameter"], field="diameter", row_id=coin_type_id
        )
        thickness = sqlite_to_nullable_decimal(
            row["thickness"], field="thickness", row_id=coin_type_id
        )
        size = sqlite_to_nullable_text(row["size"])
        denomination_text = sqlite_to_nullable_text(row["denomination_text"])
        denomination_unit = sqlite_to_nullable_text(row["denomination_unit"])
        start_date = sqlite_to_nullable_int(
            row["start_date"], field="start_date", row_id=coin_type_id
        )
        end_date = sqlite_to_nullable_int(
            row["end_date"], field="end_date", row_id=coin_type_id
        )
        start_native_date = sqlite_to_nullable_int(
            row["start_native_date"], field="start_native_date", row_id=coin_type_id
        )
        end_native_date = sqlite_to_nullable_int(
            row["end_native_date"], field="end_native_date", row_id=coin_type_id
        )
        start_mint_date = sqlite_to_nullable_int(
            row["start_mint_date"], field="start_mint_date", row_id=coin_type_id
        )
        end_mint_date = sqlite_to_nullable_int(
            row["end_mint_date"], field="end_mint_date", row_id=coin_type_id
        )
        restrike_start_mint_date = sqlite_to_nullable_int(
            row["restrike_start_mint_date"],
            field="restrike_start_mint_date",
            row_id=coin_type_id,
        )
        restrike_end_mint_date = sqlite_to_nullable_int(
            row["restrike_end_mint_date"],
            field="restrike_end_mint_date",
            row_id=coin_type_id,
        )

        coin_types.append(
            (
                coin_type_id,
                issuer_id,
                title,
                subtitle,
                edge_image,
                shape_id,
                coinage_period_id,
                rarity_index,
                url_slug,
                date_time_inserted,
                issue_type_id,
                calendar_system_id,
                weight,
                diameter,
                thickness,
                size,
                denomination_text,
                denomination_unit,
                start_date,
                end_date,
                start_native_date,
                end_native_date,
                start_mint_date,
                end_mint_date,
                restrike_start_mint_date,
                restrike_end_mint_date,
            )
        )

    return coin_types


def load_sqlite_coin_type_samples(
    sqlite_path: Path,
) -> list[
    tuple[
        int,
        int,
        str | None,
        str | None,
        int,
        bool | None,
        bool | None,
        bool | None,
        bool | None,
        bool | None,
    ]
]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                rowid,
                coin_type_id,
                obverse_image,
                reverse_image,
                sample_type,
                is_holder,
                is_counterstamped,
                is_roll,
                contains_holder,
                is_multi_coin
            FROM coin_type_samples
            WHERE removed IS NULL OR removed = 0
            ORDER BY rowid
            """
        ).fetchall()
    finally:
        conn.close()

    samples: list[
        tuple[
            int,
            int,
            str | None,
            str | None,
            int,
            bool | None,
            bool | None,
            bool | None,
            bool | None,
            bool | None,
        ]
    ] = []

    for generated_id, row in enumerate(rows, start=1):
        row_id = row["rowid"]
        if row_id is None:
            raise RuntimeError("Found coin_type_samples row with NULL rowid in SQLite.")

        coin_type_id = sqlite_to_required_int(
            row["coin_type_id"], field="coin_type_id", row_id=generated_id
        )
        sample_type = sqlite_to_required_int(
            row["sample_type"], field="sample_type", row_id=generated_id
        )

        obverse_image = sqlite_to_nullable_text(row["obverse_image"])
        reverse_image = sqlite_to_nullable_text(row["reverse_image"])
        is_holder = sqlite_to_nullable_bool(row["is_holder"])
        is_counterstamped = sqlite_to_nullable_bool(row["is_counterstamped"])
        is_roll = sqlite_to_nullable_bool(row["is_roll"])
        contains_holder = sqlite_to_nullable_bool(row["contains_holder"])
        is_multi_coin = sqlite_to_nullable_bool(row["is_multi_coin"])

        samples.append(
            (
                generated_id,
                coin_type_id,
                obverse_image,
                reverse_image,
                sample_type,
                is_holder,
                is_counterstamped,
                is_roll,
                contains_holder,
                is_multi_coin,
            )
        )

    return samples


def load_sqlite_coin_types_issuers_rulers_rel(
    sqlite_path: Path,
) -> list[tuple[int, int]]:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT coin_type_id, issuer_ruler_rel_id
            FROM coin_types_issuers_rulers_rel
            ORDER BY coin_type_id, issuer_ruler_rel_id
            """
        ).fetchall()
    finally:
        conn.close()

    rel_rows: list[tuple[int, int]] = []
    for row in rows:
        coin_type_id = row["coin_type_id"]
        issuer_ruler_rel_id = row["issuer_ruler_rel_id"]

        if coin_type_id is None:
            raise RuntimeError(
                "Found coin_types_issuers_rulers_rel row with NULL coin_type_id."
            )
        if issuer_ruler_rel_id is None:
            raise RuntimeError(
                "Found coin_types_issuers_rulers_rel row with NULL issuer_ruler_rel_id."
            )

        rel_rows.append((int(coin_type_id), int(issuer_ruler_rel_id)))

    return rel_rows


def get_postgres_shapes_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."shapes";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuer_types_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuer_types";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issue_types_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issue_types";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_calendar_systems_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."calendar_systems";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_rulers_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."rulers";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuer_alt_names_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuer_alt_names";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_coinage_periods_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."coinage_periods";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_coin_types_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."coin_types";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_coin_type_samples_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."coin_type_samples";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_coin_types_issuers_rulers_rel_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."coin_types_issuers_rulers_rel";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuers_issue_types_rel_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuers_issue_types_rel";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuers_rulers_rel_groups_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuers_rulers_rel_groups";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuers_rulers_rel_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuers_rulers_rel";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuers_count(args: argparse.Namespace) -> int:
    query = 'SELECT COUNT(*) FROM public."issuers";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output)


def get_postgres_issuer_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."issuers";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_coin_type_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."coin_types";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_issuer_ruler_rel_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."issuers_rulers_rel";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_issue_type_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."issue_types";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_shape_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."shapes";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_coinage_period_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."coinage_periods";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_calendar_system_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."calendar_systems";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_ruler_ids(args: argparse.Namespace) -> set[int]:
    query = 'SELECT "Id" FROM public."rulers";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_set(output)


def get_postgres_issuer_group_pairs(args: argparse.Namespace) -> set[tuple[int, int]]:
    query = 'SELECT "Id", "IssuerId" FROM public."issuers_rulers_rel_groups";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_pair_set(output)


def get_postgres_issuer_issue_type_pairs(args: argparse.Namespace) -> set[tuple[int, int]]:
    query = 'SELECT "IssuerId", "IssueTypeId" FROM public."issuers_issue_types_rel";'
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_int_pair_set(output)


def postgres_issuer_type_exists(args: argparse.Namespace, issuer_type_id: int) -> bool:
    query = (
        'SELECT COUNT(*) FROM public."issuer_types" '
        f'WHERE "Id" = {to_sql_literal(issuer_type_id)};'
    )
    output = run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=query,
    )
    return parse_single_int(output) > 0


def build_shapes_insert_sql(
    rows: list[tuple[int, str, int]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for shape_id, name, seq_number in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(shape_id),
                    to_sql_literal(name),
                    to_sql_literal(seq_number),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."shapes" ("Id", "Name", "SeqNumber") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_issuer_types_insert_sql(
    rows: list[tuple[int, str]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for issuer_type_id, name in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(issuer_type_id),
                    to_sql_literal(name),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuer_types" ("Id", "Name") VALUES\n' + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_issue_types_insert_sql(
    rows: list[tuple[int, str]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for issue_type_id, name in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(issue_type_id),
                    to_sql_literal(name),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issue_types" ("Id", "Name") VALUES\n' + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_calendar_systems_insert_sql(
    rows: list[tuple[int, str]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for calendar_system_id, name in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(calendar_system_id),
                    to_sql_literal(name),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."calendar_systems" ("Id", "Name") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_rulers_insert_sql(
    rows: list[tuple[int, str, str | None, str | None]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for ruler_id, name, portrait_url, info in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(ruler_id),
                    to_sql_literal(name),
                    to_sql_literal(portrait_url),
                    to_sql_literal(info),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."rulers" ("Id", "Name", "PortraitUrl", "Info") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_issuer_alt_names_insert_sql(
    rows: list[tuple[int, str]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for issuer_id, alt_name in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(issuer_id),
                    to_sql_literal(alt_name),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuer_alt_names" ("IssuerId", "AltName") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("IssuerId", "AltName") DO NOTHING'
    return sql


def build_issuers_issue_types_rel_insert_sql(
    rows: list[tuple[int, int]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for issuer_id, issue_type_id in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(issuer_id),
                    to_sql_literal(issue_type_id),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuers_issue_types_rel" ("IssuerId", "IssueTypeId") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("IssuerId", "IssueTypeId") DO NOTHING'
    return sql


def build_issuers_rulers_rel_groups_insert_sql(
    rows: list[tuple[int, int, str]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for group_id, issuer_id, name in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(group_id),
                    to_sql_literal(issuer_id),
                    to_sql_literal(name),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuers_rulers_rel_groups" ("Id", "IssuerId", "Name") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_issuers_rulers_rel_insert_sql(
    rows: list[tuple[int, int, int | None, int, str | None, str | None]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for rel_id, issuer_id, group_id, ruler_id, name, rule_type in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(rel_id),
                    to_sql_literal(issuer_id),
                    to_sql_literal(group_id),
                    to_sql_literal(ruler_id),
                    to_sql_literal(name),
                    to_sql_literal(rule_type),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuers_rulers_rel" '
        '("Id", "IssuerId", "GroupId", "RulerId", "Name", "RuleType") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_coin_types_insert_sql(
    rows: list[
        tuple[
            int,
            int,
            str,
            str | None,
            str | None,
            int | None,
            int | None,
            int | None,
            str,
            str,
            int,
            int | None,
            Decimal | None,
            Decimal | None,
            Decimal | None,
            str | None,
            str | None,
            str | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
            int | None,
        ]
    ],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for (
        coin_type_id,
        issuer_id,
        title,
        subtitle,
        edge_image,
        shape_id,
        coinage_period_id,
        rarity_index,
        url_slug,
        date_time_inserted,
        issue_type_id,
        calendar_system_id,
        weight,
        diameter,
        thickness,
        size,
        denomination_text,
        denomination_unit,
        start_date,
        end_date,
        start_native_date,
        end_native_date,
        start_mint_date,
        end_mint_date,
        restrike_start_mint_date,
        restrike_end_mint_date,
    ) in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(coin_type_id),
                    to_sql_literal(issuer_id),
                    to_sql_literal(title),
                    to_sql_literal(subtitle),
                    to_sql_literal(edge_image),
                    to_sql_literal(shape_id),
                    to_sql_literal(coinage_period_id),
                    to_sql_literal(rarity_index),
                    to_sql_literal(url_slug),
                    to_sql_literal(date_time_inserted),
                    to_sql_literal(issue_type_id),
                    to_sql_literal(calendar_system_id),
                    to_sql_literal(weight),
                    to_sql_literal(diameter),
                    to_sql_literal(thickness),
                    to_sql_literal(size),
                    to_sql_literal(denomination_text),
                    to_sql_literal(denomination_unit),
                    to_sql_literal(start_date),
                    to_sql_literal(end_date),
                    to_sql_literal(start_native_date),
                    to_sql_literal(end_native_date),
                    to_sql_literal(start_mint_date),
                    to_sql_literal(end_mint_date),
                    to_sql_literal(restrike_start_mint_date),
                    to_sql_literal(restrike_end_mint_date),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."coin_types" '
        '("Id", "IssuerId", "Title", "Subtitle", "EdgeImage", "ShapeId", '
        '"CoinagePeriodId", "RarityIndex", "UrlSlug", "DateTimeInserted", '
        '"IssueTypeId", "CalendarSystemId", "Weight", "Diameter", "Thickness", '
        '"Size", "DenominationText", "DenominationUnit", "StartDate", '
        '"EndDate", "StartNativeDate", "EndNativeDate", "StartMintDate", '
        '"EndMintDate", "RestrikeStartMintDate", "RestrikeEndMintDate") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_coin_type_samples_insert_sql(
    rows: list[
        tuple[
            int,
            int,
            str | None,
            str | None,
            int,
            bool | None,
            bool | None,
            bool | None,
            bool | None,
            bool | None,
        ]
    ],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for (
        sample_id,
        coin_type_id,
        obverse_image,
        reverse_image,
        sample_type,
        is_holder,
        is_counterstamped,
        is_roll,
        contains_holder,
        is_multi_coin,
    ) in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(sample_id),
                    to_sql_literal(coin_type_id),
                    to_sql_literal(obverse_image),
                    to_sql_literal(reverse_image),
                    to_sql_literal(sample_type),
                    to_sql_literal(contains_holder),
                    to_sql_literal(is_counterstamped),
                    to_sql_literal(is_holder),
                    to_sql_literal(is_multi_coin),
                    to_sql_literal(is_roll),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."coin_type_samples" '
        '("Id", "CoinTypeId", "ObverseImage", "ReverseImage", "SampleType", '
        '"ContainsHolder", "IsCounterstamped", "IsHolder", "IsMultiCoin", "IsRoll") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_coin_types_issuers_rulers_rel_insert_sql(
    rows: list[tuple[int, int]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for coin_type_id, issuer_ruler_rel_id in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(coin_type_id),
                    to_sql_literal(issuer_ruler_rel_id),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."coin_types_issuers_rulers_rel" '
        '("CoinTypeId", "IssuerRulerRelId") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("CoinTypeId", "IssuerRulerRelId") DO NOTHING'
    return sql


def build_coinage_periods_insert_sql(
    rows: list[tuple[int, int, str | None, str | None]],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for period_id, issuer_id, name, unit_relation_text in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(period_id),
                    to_sql_literal(issuer_id),
                    to_sql_literal(name),
                    to_sql_literal(unit_relation_text),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."coinage_periods" '
        '("Id", "IssuerId", "Name", "UnitRelationText") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def build_issuers_insert_sql(
    rows: list[
        tuple[int, int | None, int, str | None, str | None, str | None, bool, bool]
    ],
    *,
    on_conflict_do_nothing: bool,
) -> str:
    if not rows:
        return ""

    values = []
    for (
        issuer_id,
        parent_id,
        issuer_type_id,
        name,
        url_slug,
        territory_type,
        is_historical_period,
        is_section,
    ) in rows:
        values.append(
            "("
            + ", ".join(
                [
                    to_sql_literal(issuer_id),
                    to_sql_literal(parent_id),
                    to_sql_literal(issuer_type_id),
                    to_sql_literal(name),
                    to_sql_literal(url_slug),
                    to_sql_literal(territory_type),
                    to_sql_literal(is_historical_period),
                    to_sql_literal(is_section),
                ]
            )
            + ")"
        )

    sql = (
        'INSERT INTO public."issuers" '
        '("Id", "ParentId", "IssuerTypeId", "Name", "UrlSlug", '
        '"TerritoryType", "IsHistoricalPeriod", "IsSection") VALUES\n'
        + ",\n".join(values)
    )
    if on_conflict_do_nothing:
        sql += '\nON CONFLICT ("Id") DO NOTHING'
    return sql


def migrate_shapes(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_shapes(sqlite_path)
    target_count = get_postgres_shapes_count(args)

    print("Shapes migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."shapes": {target_count}')

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."shapes" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite shapes table is empty.")
        return 0

    insert_sql = build_shapes_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.shapes', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"shapes\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
    )

    final_count = get_postgres_shapes_count(args)
    print(f'- Postgres rows in public."shapes" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_issuer_types(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_issuer_types(sqlite_path)
    target_count = get_postgres_issuer_types_count(args)

    print("Issuer types migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."issuer_types": {target_count}')

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuer_types" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuer_types table is empty.")
        return 0

    insert_sql = build_issuer_types_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.issuer_types', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"issuer_types\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
    )

    final_count = get_postgres_issuer_types_count(args)
    print(f'- Postgres rows in public."issuer_types" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_issue_types(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_issue_types(sqlite_path)
    target_count = get_postgres_issue_types_count(args)

    print("Issue types migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."issue_types": {target_count}')

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issue_types" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issue_types table is empty.")
        return 0

    insert_sql = build_issue_types_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.issue_types', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"issue_types\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
    )

    final_count = get_postgres_issue_types_count(args)
    print(f'- Postgres rows in public."issue_types" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_calendar_systems(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_calendar_systems(sqlite_path)
    target_count = get_postgres_calendar_systems_count(args)

    print("Calendar systems migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."calendar_systems": {target_count}')

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."calendar_systems" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite calendar_systems table is empty.")
        return 0

    insert_sql = build_calendar_systems_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.calendar_systems', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"calendar_systems\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
    )

    final_count = get_postgres_calendar_systems_count(args)
    print(f'- Postgres rows in public."calendar_systems" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_rulers(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows, fallback_name_count = load_sqlite_rulers(sqlite_path)
    target_count = get_postgres_rulers_count(args)

    print("Rulers migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."rulers": {target_count}')
    print(
        "- Mapping: SQLite(id,name,portrait_url,info) -> "
        'Postgres("Id","Name","PortraitUrl","Info")'
    )
    print("- Ignored SQLite-only columns: dynasty, portrait_src, title")
    if fallback_name_count > 0:
        print(
            f"- Name fallback applied for {fallback_name_count} rows "
            "(empty name/title/dynasty)."
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."rulers" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite rulers table is empty.")
        return 0

    insert_sql = build_rulers_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.rulers', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"rulers\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_rulers_count(args)
    print(f'- Postgres rows in public."rulers" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_issuer_alt_names(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_issuer_alt_names(sqlite_path)
    target_count = get_postgres_issuer_alt_names_count(args)

    source_issuer_ids = {issuer_id for issuer_id, _ in source_rows}
    target_issuer_ids = get_postgres_issuer_ids(args)
    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)

    print("Issuer alt names migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(f'- Postgres current rows in public."issuer_alt_names": {target_count}')

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuer_alt_names because some issuer ids do not exist "
            "in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuer_alt_names" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuers_alt_names table is empty.")
        return 0

    insert_sql = build_issuer_alt_names_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_issuer_alt_names_count(args)
    print(f'- Postgres rows in public."issuer_alt_names" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_issuers_issue_types_rel(
    args: argparse.Namespace, sqlite_path: Path
) -> int:
    source_rows = load_sqlite_issuer_issue_types_rel(sqlite_path)
    target_count = get_postgres_issuers_issue_types_rel_count(args)

    source_issuer_ids = {issuer_id for issuer_id, _ in source_rows}
    source_issue_type_ids = {issue_type_id for _, issue_type_id in source_rows}
    target_issuer_ids = get_postgres_issuer_ids(args)
    target_issue_type_ids = get_postgres_issue_type_ids(args)

    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)
    missing_issue_type_ids = sorted(source_issue_type_ids - target_issue_type_ids)

    print("Issuer issue types relation migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(f"- Distinct issue_type references in source: {len(source_issue_type_ids)}")
    print(
        f'- Postgres current rows in public."issuers_issue_types_rel": {target_count}'
    )
    print(
        "- Mapping: SQLite issuer_issue_types_rel(issuer_id,issue_type_id) -> "
        'Postgres issuers_issue_types_rel("IssuerId","IssueTypeId")'
    )

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuers_issue_types_rel because some issuer ids do not "
            "exist in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if missing_issue_type_ids:
        sample = missing_issue_type_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuers_issue_types_rel because some issue_type ids do not "
            "exist in Postgres issue_types table. Populate issue_types first. "
            f"Missing count={len(missing_issue_type_ids)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuers_issue_types_rel" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuer_issue_types_rel table is empty.")
        return 0

    insert_sql = build_issuers_issue_types_rel_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_issuers_issue_types_rel_count(args)
    print(
        '- Postgres rows in public."issuers_issue_types_rel" '
        f"after migration: {final_count}"
    )
    print("- Completed.")
    return 0


def migrate_issuers_rulers_rel_groups(
    args: argparse.Namespace, sqlite_path: Path
) -> int:
    source_rows = load_sqlite_issuers_rulers_rel_groups(sqlite_path)
    target_count = get_postgres_issuers_rulers_rel_groups_count(args)

    source_issuer_ids = {issuer_id for _, issuer_id, _ in source_rows}
    target_issuer_ids = get_postgres_issuer_ids(args)
    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)

    print("Issuers rulers relation groups migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(
        f'- Postgres current rows in public."issuers_rulers_rel_groups": {target_count}'
    )
    print(
        "- Mapping: SQLite issuers_rulers_rel_groups(id,issuer_id,name) -> "
        'Postgres issuers_rulers_rel_groups("Id","IssuerId","Name")'
    )

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuers_rulers_rel_groups because some issuer ids do not "
            "exist in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuers_rulers_rel_groups" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuers_rulers_rel_groups table is empty.")
        return 0

    insert_sql = build_issuers_rulers_rel_groups_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.issuers_rulers_rel_groups', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"issuers_rulers_rel_groups\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_issuers_rulers_rel_groups_count(args)
    print(
        '- Postgres rows in public."issuers_rulers_rel_groups" '
        f"after migration: {final_count}"
    )
    print("- Completed.")
    return 0


def migrate_issuers_rulers_rel(args: argparse.Namespace, sqlite_path: Path) -> int:
    (
        source_rows,
        skipped_missing_required_fk_count,
        skipped_missing_required_fk_sample_ids,
    ) = load_sqlite_issuers_rulers_rel(sqlite_path)
    target_count = get_postgres_issuers_rulers_rel_count(args)
    total_source_rows = len(source_rows) + skipped_missing_required_fk_count

    source_issuer_ids = {issuer_id for _, issuer_id, _, _, _, _ in source_rows}
    source_ruler_ids = {ruler_id for _, _, _, ruler_id, _, _ in source_rows}
    source_group_pairs = {
        (group_id, issuer_id)
        for _, issuer_id, group_id, _, _, _ in source_rows
        if group_id is not None
    }

    target_issuer_ids = get_postgres_issuer_ids(args)
    target_ruler_ids = get_postgres_ruler_ids(args)
    target_group_pairs = get_postgres_issuer_group_pairs(args)

    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)
    missing_ruler_ids = sorted(source_ruler_ids - target_ruler_ids)
    missing_group_pairs = sorted(source_group_pairs - target_group_pairs)

    print("Issuers rulers relation migration")
    print(f"- SQLite source rows (total): {total_source_rows}")
    print(f"- SQLite source rows (eligible for insert): {len(source_rows)}")
    if skipped_missing_required_fk_count > 0:
        print(
            "- Skipped source rows with NULL required FK "
            f"(issuer_id or ruler_id): {skipped_missing_required_fk_count} "
            f"sample ids={skipped_missing_required_fk_sample_ids}"
        )
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(f"- Distinct ruler references in source: {len(source_ruler_ids)}")
    print(
        f"- Distinct non-null (group_id, issuer_id) references in source: {len(source_group_pairs)}"
    )
    print(f'- Postgres current rows in public."issuers_rulers_rel": {target_count}')
    print(
        "- Mapping: SQLite issuers_rulers_rel(id,issuer_id,group_id,ruler_id,name,rule_type) -> "
        'Postgres issuers_rulers_rel("Id","IssuerId","GroupId","RulerId","Name","RuleType")'
    )

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuers_rulers_rel because some issuer ids do not "
            "exist in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if missing_ruler_ids:
        sample = missing_ruler_ids[:20]
        raise RuntimeError(
            "Cannot migrate issuers_rulers_rel because some ruler ids do not "
            "exist in Postgres rulers table. Populate rulers first. "
            f"Missing count={len(missing_ruler_ids)} sample={sample}"
        )

    if missing_group_pairs:
        sample = missing_group_pairs[:20]
        raise RuntimeError(
            "Cannot migrate issuers_rulers_rel because some (group_id, issuer_id) "
            "pairs do not exist in Postgres issuers_rulers_rel_groups table. "
            "Populate issuers_rulers_rel_groups first. "
            f"Missing count={len(missing_group_pairs)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuers_rulers_rel" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuers_rulers_rel table is empty.")
        return 0

    insert_sql = build_issuers_rulers_rel_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.issuers_rulers_rel', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"issuers_rulers_rel\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_issuers_rulers_rel_count(args)
    print(f'- Postgres rows in public."issuers_rulers_rel" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_coin_types(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_coin_types(sqlite_path)
    target_count = get_postgres_coin_types_count(args)

    source_issuer_ids = {row[1] for row in source_rows}
    source_issue_type_ids = {row[10] for row in source_rows}
    source_shape_ids = {row[5] for row in source_rows if row[5] is not None}
    source_period_ids = {row[6] for row in source_rows if row[6] is not None}
    source_calendar_system_ids = {row[11] for row in source_rows if row[11] is not None}
    source_issuer_issue_type_pairs = {(row[1], row[10]) for row in source_rows}

    target_issuer_ids = get_postgres_issuer_ids(args)
    target_issue_type_ids = get_postgres_issue_type_ids(args)
    target_shape_ids = get_postgres_shape_ids(args)
    target_coinage_period_ids = get_postgres_coinage_period_ids(args)
    target_calendar_system_ids = get_postgres_calendar_system_ids(args)
    target_issuer_issue_type_pairs = get_postgres_issuer_issue_type_pairs(args)

    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)
    missing_issue_type_ids = sorted(source_issue_type_ids - target_issue_type_ids)
    missing_shape_ids = sorted(source_shape_ids - target_shape_ids)
    missing_period_ids = sorted(source_period_ids - target_coinage_period_ids)
    missing_calendar_system_ids = sorted(
        source_calendar_system_ids - target_calendar_system_ids
    )
    missing_issuer_issue_type_pairs = sorted(
        source_issuer_issue_type_pairs - target_issuer_issue_type_pairs
    )

    print("Coin types migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(f"- Distinct issue_type references in source: {len(source_issue_type_ids)}")
    print(f"- Distinct shape references in source (non-null): {len(source_shape_ids)}")
    print(f"- Distinct period references in source (non-null): {len(source_period_ids)}")
    print(
        "- Distinct calendar_system references in source (non-null): "
        f"{len(source_calendar_system_ids)}"
    )
    print(
        f"- Distinct (issuer_id, issue_type_id) references in source: "
        f"{len(source_issuer_issue_type_pairs)}"
    )
    print(f'- Postgres current rows in public."coin_types": {target_count}')
    print("- Mapping policy: all overlapping Postgres coin_types columns")
    print("- DateTimeInserted: SQLite text treated as local time and stored with offset")

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some issuer ids do not exist "
            "in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if missing_issue_type_ids:
        sample = missing_issue_type_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some issue_type ids do not exist "
            "in Postgres issue_types table. Populate issue_types first. "
            f"Missing count={len(missing_issue_type_ids)} sample={sample}"
        )

    if missing_shape_ids:
        sample = missing_shape_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some shape ids do not exist "
            "in Postgres shapes table. Populate shapes first. "
            f"Missing count={len(missing_shape_ids)} sample={sample}"
        )

    if missing_period_ids:
        sample = missing_period_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some period ids do not exist "
            "in Postgres coinage_periods table. Populate coinage_periods first. "
            f"Missing count={len(missing_period_ids)} sample={sample}"
        )

    if missing_calendar_system_ids:
        sample = missing_calendar_system_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some calendar_system ids do not exist "
            "in Postgres calendar_systems table. Populate calendar_systems first. "
            f"Missing count={len(missing_calendar_system_ids)} sample={sample}"
        )

    if missing_issuer_issue_type_pairs:
        sample = missing_issuer_issue_type_pairs[:20]
        raise RuntimeError(
            "Cannot migrate coin_types because some (issuer_id, issue_type_id) pairs "
            "do not exist in Postgres issuers_issue_types_rel table. "
            "Populate issuers_issue_types_rel first. "
            f"Missing count={len(missing_issuer_issue_type_pairs)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."coin_types" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite coin_types table is empty.")
        return 0

    batch_size = 2000
    total_batches = (len(source_rows) + batch_size - 1) // batch_size

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        print(f"- Batch size: {batch_size}; total batches: {total_batches}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    for batch_index, batch_rows in enumerate(iter_chunks(source_rows, batch_size), start=1):
        insert_sql = build_coin_types_insert_sql(
            batch_rows,
            on_conflict_do_nothing=args.force,
        )
        if not insert_sql:
            continue

        migration_sql = "\n".join(
            [
                "BEGIN;",
                insert_sql + ";",
                "COMMIT;",
            ]
        )

        run_psql_query(
            container=args.pg_container,
            db=args.pg_db,
            user=args.pg_user,
            password=args.pg_password,
            query=migration_sql,
            use_stdin=True,
        )

        if batch_index == 1 or batch_index % 10 == 0 or batch_index == total_batches:
            print(f"- Inserted batch {batch_index}/{total_batches}")

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.coin_types', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"coin_types\"), 0) + 1, "
        "false"
        ");"
    )

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=sequence_sql,
    )

    final_count = get_postgres_coin_types_count(args)
    print(f'- Postgres rows in public."coin_types" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_coin_type_samples(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_coin_type_samples(sqlite_path)
    target_count = get_postgres_coin_type_samples_count(args)

    source_coin_type_ids = {row[1] for row in source_rows}
    target_coin_type_ids = get_postgres_coin_type_ids(args)
    missing_coin_type_ids = sorted(source_coin_type_ids - target_coin_type_ids)

    print("Coin type samples migration")
    print(f"- SQLite active source rows: {len(source_rows)}")
    print(f"- Distinct coin_type references in source: {len(source_coin_type_ids)}")
    print(f'- Postgres current rows in public."coin_type_samples": {target_count}')
    print("- Source filter: removed IS NULL OR removed = 0")
    print(
        "- Mapping: SQLite coin_type_samples -> Postgres coin_type_samples "
        '(with generated "Id" based on SQLite row order)'
    )

    if missing_coin_type_ids:
        sample = missing_coin_type_ids[:20]
        raise RuntimeError(
            "Cannot migrate coin_type_samples because some coin_type ids do not "
            "exist in Postgres coin_types table. Populate coin_types first. "
            f"Missing count={len(missing_coin_type_ids)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."coin_type_samples" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite coin_type_samples active set is empty.")
        return 0

    batch_size = 3000
    total_batches = (len(source_rows) + batch_size - 1) // batch_size

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        print(f"- Batch size: {batch_size}; total batches: {total_batches}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    for batch_index, batch_rows in enumerate(iter_chunks(source_rows, batch_size), start=1):
        insert_sql = build_coin_type_samples_insert_sql(
            batch_rows,
            on_conflict_do_nothing=args.force,
        )
        if not insert_sql:
            continue

        migration_sql = "\n".join(
            [
                "BEGIN;",
                insert_sql + ";",
                "COMMIT;",
            ]
        )

        run_psql_query(
            container=args.pg_container,
            db=args.pg_db,
            user=args.pg_user,
            password=args.pg_password,
            query=migration_sql,
            use_stdin=True,
        )

        if batch_index == 1 or batch_index % 10 == 0 or batch_index == total_batches:
            print(f"- Inserted batch {batch_index}/{total_batches}")

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.coin_type_samples', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"coin_type_samples\"), 0) + 1, "
        "false"
        ");"
    )

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=sequence_sql,
    )

    final_count = get_postgres_coin_type_samples_count(args)
    print(f'- Postgres rows in public."coin_type_samples" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_coin_types_issuers_rulers_rel(
    args: argparse.Namespace, sqlite_path: Path
) -> int:
    source_rows = load_sqlite_coin_types_issuers_rulers_rel(sqlite_path)
    target_count = get_postgres_coin_types_issuers_rulers_rel_count(args)

    source_coin_type_ids = {coin_type_id for coin_type_id, _ in source_rows}
    source_issuer_ruler_rel_ids = {rel_id for _, rel_id in source_rows}
    target_coin_type_ids = get_postgres_coin_type_ids(args)
    target_issuer_ruler_rel_ids = get_postgres_issuer_ruler_rel_ids(args)

    missing_coin_type_ids = sorted(source_coin_type_ids - target_coin_type_ids)
    missing_issuer_ruler_rel_ids = sorted(
        source_issuer_ruler_rel_ids - target_issuer_ruler_rel_ids
    )
    valid_rows = [
        row
        for row in source_rows
        if row[0] in target_coin_type_ids and row[1] in target_issuer_ruler_rel_ids
    ]
    skipped_invalid_rows = len(source_rows) - len(valid_rows)

    print("Coin types issuers rulers relation migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- SQLite source rows (valid for insert): {len(valid_rows)}")
    if skipped_invalid_rows > 0:
        print(f"- Skipped invalid source rows: {skipped_invalid_rows}")
    print(f"- Distinct coin_type references in source: {len(source_coin_type_ids)}")
    print(
        "- Distinct issuer_ruler_rel references in source: "
        f"{len(source_issuer_ruler_rel_ids)}"
    )
    print(
        '- Postgres current rows in public."coin_types_issuers_rulers_rel": '
        f"{target_count}"
    )
    print(
        "- Mapping: SQLite coin_types_issuers_rulers_rel(coin_type_id,issuer_ruler_rel_id) -> "
        'Postgres coin_types_issuers_rulers_rel("CoinTypeId","IssuerRulerRelId")'
    )

    if missing_coin_type_ids:
        print(
            "- Missing coin_type ids in Postgres (rows skipped): "
            f"{len(missing_coin_type_ids)} sample={missing_coin_type_ids[:20]}"
        )

    if missing_issuer_ruler_rel_ids:
        print(
            "- Missing issuer_ruler_rel ids in Postgres (rows skipped): "
            f"{len(missing_issuer_ruler_rel_ids)} sample={missing_issuer_ruler_rel_ids[:20]}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."coin_types_issuers_rulers_rel" is not empty. '
            "Use --force to override."
        )
        return 0

    if not valid_rows:
        print(
            "- Nothing to migrate: no valid rows after FK filtering."
        )
        return 0

    batch_size = 5000
    total_batches = (len(valid_rows) + batch_size - 1) // batch_size

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(valid_rows)}")
        print(f"- Batch size: {batch_size}; total batches: {total_batches}")
        if valid_rows:
            print(f"- First row preview: {valid_rows[0]!r}")
        return 0

    for batch_index, batch_rows in enumerate(iter_chunks(valid_rows, batch_size), start=1):
        insert_sql = build_coin_types_issuers_rulers_rel_insert_sql(
            batch_rows,
            on_conflict_do_nothing=args.force,
        )
        if not insert_sql:
            continue

        migration_sql = "\n".join(
            [
                "BEGIN;",
                insert_sql + ";",
                "COMMIT;",
            ]
        )

        run_psql_query(
            container=args.pg_container,
            db=args.pg_db,
            user=args.pg_user,
            password=args.pg_password,
            query=migration_sql,
            use_stdin=True,
        )

        if batch_index == 1 or batch_index % 10 == 0 or batch_index == total_batches:
            print(f"- Inserted batch {batch_index}/{total_batches}")

    final_count = get_postgres_coin_types_issuers_rulers_rel_count(args)
    print(
        '- Postgres rows in public."coin_types_issuers_rulers_rel" '
        f"after migration: {final_count}"
    )
    print("- Completed.")
    return 0


def migrate_coinage_periods(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_periods(sqlite_path)
    target_count = get_postgres_coinage_periods_count(args)

    source_issuer_ids = {issuer_id for _, issuer_id, _, _ in source_rows}
    target_issuer_ids = get_postgres_issuer_ids(args)
    missing_issuer_ids = sorted(source_issuer_ids - target_issuer_ids)

    print("Coinage periods migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f"- Distinct issuer references in source: {len(source_issuer_ids)}")
    print(f'- Postgres current rows in public."coinage_periods": {target_count}')
    print(
        "- Mapping: SQLite periods(id,issuer_id,name,unit_relation_text) -> "
        'Postgres coinage_periods("Id","IssuerId","Name","UnitRelationText")'
    )

    if missing_issuer_ids:
        sample = missing_issuer_ids[:20]
        raise RuntimeError(
            "Cannot migrate coinage_periods because some issuer ids do not exist "
            "in Postgres issuers table. Populate issuers first. "
            f"Missing count={len(missing_issuer_ids)} sample={sample}"
        )

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."coinage_periods" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite periods table is empty.")
        return 0

    insert_sql = build_coinage_periods_insert_sql(
        source_rows,
        on_conflict_do_nothing=args.force,
    )
    if not insert_sql:
        print("- Nothing to insert.")
        return 0

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.coinage_periods', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"coinage_periods\"), 0) + 1, "
        "false"
        ");"
    )

    migration_sql = "\n".join(
        [
            "BEGIN;",
            insert_sql + ";",
            sequence_sql,
            "COMMIT;",
        ]
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Rows prepared for insert: {len(source_rows)}")
        if source_rows:
            print(f"- First row preview: {source_rows[0]!r}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=migration_sql,
        use_stdin=True,
    )

    final_count = get_postgres_coinage_periods_count(args)
    print(f'- Postgres rows in public."coinage_periods" after migration: {final_count}')
    print("- Completed.")
    return 0


def migrate_issuers(args: argparse.Namespace, sqlite_path: Path) -> int:
    source_rows = load_sqlite_issuers(sqlite_path)
    target_count = get_postgres_issuers_count(args)

    default_issuer_type_id = 1
    if not postgres_issuer_type_exists(args, default_issuer_type_id):
        raise RuntimeError(
            "Cannot migrate issuers: default IssuerTypeId=1 does not exist in "
            'public."issuer_types". Populate issuer_types first.'
        )

    print("Issuers migration")
    print(f"- SQLite source rows: {len(source_rows)}")
    print(f'- Postgres current rows in public."issuers": {target_count}')
    print("- Mapping: SQLite issuers -> Postgres issuers (hierarchical parent-first)")
    print("- Default IssuerTypeId applied to all rows: 1")

    if target_count > 0 and not args.force:
        print(
            '- Skip: target table public."issuers" is not empty. '
            "Use --force to override."
        )
        return 0

    if not source_rows:
        print("- Nothing to migrate: SQLite issuers table is empty.")
        return 0

    pending: dict[int, tuple[int, int | None, int, str | None, str | None, str | None, bool, bool]] = {
        row[0]: row for row in source_rows
    }

    # In force mode we may already have partial data in target.
    resolved_ids = get_postgres_issuer_ids(args) if args.force else set()

    pass_count = 0
    processed_count = 0
    while pending:
        ready_ids = [
            issuer_id
            for issuer_id, row in pending.items()
            if row[1] is None or row[1] in resolved_ids
        ]

        if not ready_ids:
            sample = []
            for issuer_id, row in list(pending.items())[:20]:
                sample.append((issuer_id, row[1]))
            raise RuntimeError(
                "Cannot resolve issuer hierarchy. Remaining rows have parents "
                "that are not present in target set. Possible cycle/orphan. "
                f"Remaining={len(pending)} sample(id,parent_id)={sample}"
            )

        ready_rows = [pending[issuer_id] for issuer_id in sorted(ready_ids)]
        insert_sql = build_issuers_insert_sql(
            ready_rows,
            on_conflict_do_nothing=args.force,
        )
        if not insert_sql:
            raise RuntimeError("Unexpected empty insert SQL for issuers ready batch.")

        migration_sql = "\n".join(
            [
                "BEGIN;",
                insert_sql + ";",
                "COMMIT;",
            ]
        )

        if not args.dry_run:
            run_psql_query(
                container=args.pg_container,
                db=args.pg_db,
                user=args.pg_user,
                password=args.pg_password,
                query=migration_sql,
                use_stdin=True,
            )

        for issuer_id in ready_ids:
            resolved_ids.add(issuer_id)
            pending.pop(issuer_id, None)

        pass_count += 1
        processed_count += len(ready_ids)
        print(
            f"- Pass {pass_count}: processed {len(ready_ids)} rows "
            f"(remaining {len(pending)})"
        )

    sequence_sql = (
        "SELECT setval("
        "pg_get_serial_sequence('public.issuers', 'Id'), "
        "COALESCE((SELECT MAX(\"Id\") FROM public.\"issuers\"), 0) + 1, "
        "false"
        ");"
    )

    if args.dry_run:
        print("- Dry run: no data written to Postgres.")
        print(f"- Total rows prepared: {processed_count}")
        print(f"- Hierarchy passes required: {pass_count}")
        return 0

    run_psql_query(
        container=args.pg_container,
        db=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
        query=sequence_sql,
    )

    final_count = get_postgres_issuers_count(args)
    print(f'- Postgres rows in public."issuers" after migration: {final_count}')
    print(f"- Hierarchy passes used: {pass_count}")
    print("- Completed.")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")

    parser = build_parser()
    args = parser.parse_args()

    repo_root = repo_root_from_script()
    sqlite_path = resolve_path(args.sqlite_path, repo_root)

    if args.table == "shapes":
        return migrate_shapes(args, sqlite_path)
    if args.table == "issuer_types":
        return migrate_issuer_types(args, sqlite_path)
    if args.table == "issue_types":
        return migrate_issue_types(args, sqlite_path)
    if args.table == "calendar_systems":
        return migrate_calendar_systems(args, sqlite_path)
    if args.table == "rulers":
        return migrate_rulers(args, sqlite_path)
    if args.table == "issuer_alt_names":
        return migrate_issuer_alt_names(args, sqlite_path)
    if args.table == "issuers_issue_types_rel":
        return migrate_issuers_issue_types_rel(args, sqlite_path)
    if args.table == "issuers_rulers_rel_groups":
        return migrate_issuers_rulers_rel_groups(args, sqlite_path)
    if args.table == "issuers_rulers_rel":
        return migrate_issuers_rulers_rel(args, sqlite_path)
    if args.table == "coin_types":
        return migrate_coin_types(args, sqlite_path)
    if args.table == "coin_type_samples":
        return migrate_coin_type_samples(args, sqlite_path)
    if args.table == "coin_types_issuers_rulers_rel":
        return migrate_coin_types_issuers_rulers_rel(args, sqlite_path)
    if args.table == "coinage_periods":
        return migrate_coinage_periods(args, sqlite_path)
    if args.table == "issuers":
        return migrate_issuers(args, sqlite_path)

    raise RuntimeError(f"Unsupported table: {args.table}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
