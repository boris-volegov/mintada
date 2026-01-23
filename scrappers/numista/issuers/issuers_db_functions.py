import sqlite3
import os

class IssuersDbHelper:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "coins.db")
        self.db_connection =sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON") 

    def _upsert_issuer(self, issuer_record):
        """
        rec = {url_slug, issuer_text, alt_names, parent_url_slug, is_historical_period}
        Returns issuer_id.
        """
        sql = """
        INSERT INTO issuers (url_slug, name, alt_names, parent_url_slug, territory_type, is_historical_period)
        VALUES (:url_slug, :issuer_text, :alt_names, :parent_url_slug, :territory_type, :is_historical_period)
        ON CONFLICT(url_slug) DO UPDATE SET
        name=excluded.name,
        alt_names=excluded.alt_names,
        parent_url_slug=excluded.parent_url_slug,
        territory_type=excluded.territory_type,
        is_historical_period=excluded.is_historical_period
        RETURNING id;
        """
        cur = self.db_connection.execute(sql, issuer_record)
        return cur.fetchone()[0]

    def _upsert_issuer_tag(self, text):
        """
        Insert a tag text if missing; return its id (works on conflict too).
        """
        cur = self.db_connection.execute(
            """
            INSERT INTO issuer_tags(text) VALUES (?)
            ON CONFLICT(text) DO UPDATE SET text=excluded.text
            RETURNING id;
            """,
            (text,)
        )
        return cur.fetchone()[0]

    def _upsert_issuer_tags(self, tags):
        """
        Upsert a list[str] of tags; return list[int] of tag_ids in same order, deduped.
        """
        seen, ids = set(), []
        for t in tags or []:
            if t in seen:  # avoid duplicate inserts in the same batch
                continue
            seen.add(t)
            ids.append(self._upsert_issuer_tag(t))
        return ids

    def _insert_issuers_tags_rels(self, issuer_id, tag_ids):
        """
        Insert multiple (issuer_id, tag_id) pairs into country_tags.
        Deduplicates via PRIMARY KEY constraint.
        """
        if not tag_ids:
            return

        data = [(issuer_id, tag_id) for tag_id in tag_ids]

        sql = "INSERT OR IGNORE INTO issuers_tags_rel (issuer_id, tag_id) VALUES (?, ?)"
        self.db_connection.executemany(sql, data)

    def populate_issuers(self, issuer_records):
        # One transaction for the whole batch
        with self.db_connection:
            for issuer_record in issuer_records:
                issuer_id = self._upsert_issuer(issuer_record)
                if "tags" in issuer_record and issuer_record["tags"] is not None:
                    tag_ids = self._upsert_issuer_tags(issuer_record["tags"])

                    self._insert_issuers_tags_rels(issuer_id, tag_ids)

    def get_issuers(self, issue_type=1):
        self.db_connection.row_factory = sqlite3.Row
        cur = self.db_connection.cursor()
        cur.execute("""
            SELECT p.*
            FROM issuers AS p JOIN issuer_issue_types_rel ON p.id = issuer_issue_types_rel.issuer_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM issuers AS c
                WHERE c.parent_id = p.id
            )
            ORDER BY p.id;
        """)
        return cur.fetchall()

    def get_all_numista_slugs(self):
        """
        Returns a set of all numista_url_slug present in the issuers table.
        Used to identify missing issuers without re-querying everything.
        """
        cur = self.db_connection.execute("SELECT numista_url_slug FROM issuers WHERE numista_url_slug IS NOT NULL")
        return {row[0] for row in cur.fetchall()}