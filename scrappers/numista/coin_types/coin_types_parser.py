import argparse
import os
import sqlite3
import subprocess
import sys


class CoinTypesParser:
    def __init__(self, db_connection: sqlite3.Connection | None = None):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = r"D:\projects\mintada\data\numista\coins.db"
        self.parse_all_script_path = os.path.join(self.script_dir, "parsers", "parse_all.py")

        self._owns_connection = db_connection is None
        self.db_connection = db_connection or sqlite3.connect(self.db_path)
        self.db_connection.row_factory = sqlite3.Row

    def close(self):
        if self._owns_connection and self.db_connection:
            self.db_connection.close()

    def _get_coin_type_context(self, coin_type_id: int):
        cur = self.db_connection.execute(
            """
            SELECT ct.id, ct.coin_type_slug, ct.issuer_id, i.numista_url_slug
            FROM coin_types AS ct
            LEFT JOIN issuers AS i ON i.id = ct.issuer_id
            WHERE ct.id = ?
            """,
            (coin_type_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _find_coin_html_path(self, coin_type_id: int, coin_type_slug: str | None, issuer_slug: str):
        issuer_html_dir = os.path.join(self.script_dir, "html", issuer_slug)
        candidate_dirs = []

        if coin_type_slug:
            candidate_dirs.append(os.path.join(issuer_html_dir, f"{coin_type_slug}_{coin_type_id}"))

        if os.path.isdir(issuer_html_dir):
            suffix = f"_{coin_type_id}"
            for entry in os.listdir(issuer_html_dir):
                full_path = os.path.join(issuer_html_dir, entry)
                if os.path.isdir(full_path) and entry.endswith(suffix):
                    if full_path not in candidate_dirs:
                        candidate_dirs.append(full_path)

        for coin_type_dir in candidate_dirs:
            html_path = os.path.join(coin_type_dir, "coin_type.html")
            if os.path.isfile(html_path):
                return html_path

        raise RuntimeError(
            "coin_type.html not found for coin_type_id={coin_type_id} under issuer='{issuer_slug}'. "
            "Expected one of: {paths}".format(
                coin_type_id=coin_type_id,
                issuer_slug=issuer_slug,
                paths=", ".join([os.path.join(d, "coin_type.html") for d in candidate_dirs])
                or "<no candidate folders found>",
            )
        )

    def run_post_parsers_for_coin(
        self,
        coin_type_id: int,
        coin_html_path: str,
        parsers: list[str] | None = None,
        include_dependencies: bool = True,
    ):
        if not os.path.isfile(self.parse_all_script_path):
            raise RuntimeError(f"Missing parser runner script: {self.parse_all_script_path}")

        cmd = [
            sys.executable,
            self.parse_all_script_path,
            "--coin-type-id",
            str(coin_type_id),
            "--coin-html-path",
            coin_html_path,
        ]

        if parsers:
            cmd.append("--parsers")
            cmd.extend(parsers)
            if not include_dependencies:
                cmd.append("--no-auto-deps")

        print(f"Running post-parsers for coin type {coin_type_id}...", flush=True)
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"parse_all.py failed for coin_type_id={coin_type_id} with exit code {result.returncode}"
            )

    def parse_only(
        self,
        coin_type_id: int,
        parsers: list[str] | None = None,
    ):
        context = self._get_coin_type_context(coin_type_id)
        if not context:
            raise RuntimeError(f"coin_type_id={coin_type_id} not found in coin_types.")

        issuer_slug = context.get("numista_url_slug")
        if not issuer_slug:
            raise RuntimeError(
                f"coin_type_id={coin_type_id} has no issuer slug (issuers.numista_url_slug)."
            )

        coin_html_path = self._find_coin_html_path(
            coin_type_id=coin_type_id,
            coin_type_slug=context.get("coin_type_slug"),
            issuer_slug=issuer_slug,
        )

        self.run_post_parsers_for_coin(
            coin_type_id=coin_type_id,
            coin_html_path=coin_html_path,
            parsers=parsers,
            include_dependencies=parsers is None,
        )
        print(
            f"Finished parse_only for coin_type_id={coin_type_id} using "
            f"{coin_html_path}."
        )


def main():
    arg_parser = argparse.ArgumentParser(
        description=(
            "Parse already-scraped coin_type.html into DB fields for a specific coin type. "
            "By default runs all parsers; optionally pass a subset (e.g. composition, shape). "
            "When --parsers is provided, only that explicit subset is run."
        )
    )
    arg_parser.add_argument("coin_type_id", type=int, help="Coin type ID to parse.")
    arg_parser.add_argument(
        "--parsers",
        nargs="*",
        default=None,
        help=(
            "Optional parser subset names; accepts aliases like composition/shape. "
            "Runs exactly the provided subset."
        ),
    )
    args = arg_parser.parse_args()

    parser = CoinTypesParser()
    try:
        parser.parse_only(args.coin_type_id, args.parsers)
    finally:
        parser.close()


if __name__ == "__main__":
    raise SystemExit(main())
