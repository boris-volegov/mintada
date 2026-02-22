import argparse
import subprocess
import sys
import time
from pathlib import Path


PARSER_ORDER = [
    "parse_years",
    "parse_shapes",
    "parse_denomination",
    "parse_denomination_unit",
    "parse_dimensions",
    "parse_size",
    "parse_composition",
    "parse_calendar",
    "parse_catalog_references",
]

DEPENDENCIES = {
    "parse_denomination_unit": ["parse_denomination"],
}

PARSER_ALIASES = {
    "year": "parse_years",
    "years": "parse_years",
    "shape": "parse_shapes",
    "shapes": "parse_shapes",
    "denomination": "parse_denomination",
    "denomination_unit": "parse_denomination_unit",
    "unit": "parse_denomination_unit",
    "dimensions": "parse_dimensions",
    "dimension": "parse_dimensions",
    "size": "parse_size",
    "composition": "parse_composition",
    "calendar": "parse_calendar",
    "catalog_references": "parse_catalog_references",
    "catalog_reference": "parse_catalog_references",
    "catalog": "parse_catalog_references",
    "catalogs": "parse_catalog_references",
}


def _normalize_parser_name(raw_name: str) -> str:
    name = raw_name.strip().lower()
    if name.endswith(".py"):
        name = name[:-3]
    if name in PARSER_ALIASES:
        return PARSER_ALIASES[name]
    if name.startswith("parse_"):
        return name
    mapped = f"parse_{name}"
    if mapped in PARSER_ORDER:
        return mapped
    return name


def _resolve_requested_order(
    requested: list[str],
    include_dependencies: bool = True,
) -> list[str]:
    if not requested:
        return PARSER_ORDER[:]

    requested_names = [_normalize_parser_name(name) for name in requested]
    unknown = [name for name in requested_names if name not in PARSER_ORDER]
    if unknown:
        raise ValueError(
            "Unknown parser(s): {unknown}. Available: {available}".format(
                unknown=", ".join(unknown),
                available=", ".join(PARSER_ORDER),
            )
        )

    selected = []
    selected_set = set()

    def add_with_dependencies(name: str):
        for dep in DEPENDENCIES.get(name, []):
            if dep not in selected_set:
                add_with_dependencies(dep)
        if name not in selected_set:
            selected.append(name)
            selected_set.add(name)

    for name in requested_names:
        if include_dependencies:
            add_with_dependencies(name)
        elif name not in selected_set:
            selected.append(name)
            selected_set.add(name)

    # Keep global canonical order.
    return [name for name in PARSER_ORDER if name in selected_set]


def run_parsers(
    requested: list[str],
    continue_on_error: bool,
    coin_type_id: int | None = None,
    coin_html_path: str | None = None,
    include_dependencies: bool = True,
) -> int:
    script_dir = Path(__file__).resolve().parent
    execution_order = _resolve_requested_order(
        requested=requested,
        include_dependencies=include_dependencies,
    )

    print("Parser execution order:")
    for parser_name in execution_order:
        print(f"- {parser_name}.py")
    print("")

    failures = []

    for parser_name in execution_order:
        script_path = script_dir / f"{parser_name}.py"
        if not script_path.exists():
            message = f"Missing parser file: {script_path}"
            print(f"[ERROR] {message}")
            failures.append((parser_name, 127, 0.0))
            if not continue_on_error:
                break
            continue

        print(f"[START] {parser_name}.py")
        start = time.monotonic()
        cmd = [sys.executable, str(script_path)]
        if coin_type_id is not None:
            cmd.extend(["--coin-type-id", str(coin_type_id)])
        if coin_html_path:
            cmd.extend(["--coin-html-path", coin_html_path])
        result = subprocess.run(cmd, check=False)
        elapsed = time.monotonic() - start

        if result.returncode == 0:
            print(f"[OK] {parser_name}.py ({elapsed:.1f}s)")
        else:
            print(f"[FAIL] {parser_name}.py exited with code {result.returncode} ({elapsed:.1f}s)")
            failures.append((parser_name, result.returncode, elapsed))
            if not continue_on_error:
                break

        print("")

    if failures:
        print("Failed parsers:")
        for parser_name, code, elapsed in failures:
            print(f"- {parser_name}.py (exit={code}, duration={elapsed:.1f}s)")
        return 1

    print("All parsers completed successfully.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Numista coin-type parsers in the correct order. "
            "Dependency rule: parse_denomination runs before parse_denomination_unit "
            "(unless --no-auto-deps is used)."
        )
    )
    parser.add_argument(
        "--parsers",
        nargs="*",
        default=[],
        help=(
            "Optional subset of parser names (with or without .py). "
            "If omitted, runs all parsers."
        ),
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running remaining parsers even if one fails.",
    )
    parser.add_argument(
        "--coin-type-id",
        type=int,
        default=None,
        help="Optional single coin_type_id target; parsers run in targeted mode when supported.",
    )
    parser.add_argument(
        "--coin-html-path",
        default=None,
        help="Optional coin_type.html path for targeted mode.",
    )
    parser.add_argument(
        "--no-auto-deps",
        action="store_true",
        help=(
            "Run only explicitly requested parsers without injecting dependency parsers. "
            "Ignored when --parsers is omitted."
        ),
    )
    args = parser.parse_args()

    try:
        return run_parsers(
            requested=args.parsers,
            continue_on_error=args.continue_on_error,
            coin_type_id=args.coin_type_id,
            coin_html_path=args.coin_html_path,
            include_dependencies=not args.no_auto_deps,
        )
    except ValueError as ex:
        print(f"[ERROR] {ex}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
