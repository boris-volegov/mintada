import os
import sqlite3


class CatalogsDbHelper:
    def __init__(self):
        current_dir = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        self.db_path = os.environ.get(
            "NUMISTA_DB_PATH",
            os.path.join(repo_root, "data", "numista", "coins.db"),
        )
        self.db_connection = sqlite3.connect(self.db_path)
        self.db_connection.execute("PRAGMA foreign_keys = ON")

        self._has_name_column = self._table_has_column("catalogs", "name")

    def _table_has_column(self, table_name: str, column_name: str) -> bool:
        cursor = self.db_connection.execute(f"PRAGMA table_info({table_name})")
        return any(row[1] == column_name for row in cursor.fetchall())

    def populate_catalogs(self, catalogs):
        if not catalogs:
            return

        if self._has_name_column:
            update_sql = "UPDATE catalogs SET name = ?, code = ?, description = ? WHERE id = ?"
            insert_sql = "INSERT INTO catalogs (id, name, code, description) VALUES (?, ?, ?, ?)"
        else:
            update_sql = "UPDATE catalogs SET code = ?, description = ? WHERE id = ?"
            insert_sql = "INSERT INTO catalogs (id, code, description) VALUES (?, ?, ?)"

        cursor = self.db_connection.cursor()

        for catalog in catalogs:
            catalog_id = catalog.get("id")
            if catalog_id is None:
                continue

            code = catalog.get("code")
            description = catalog.get("description")

            if self._has_name_column:
                cursor.execute(update_sql, (code, code, description, catalog_id))
                if cursor.rowcount == 0:
                    cursor.execute(insert_sql, (catalog_id, code, code, description))
            else:
                cursor.execute(update_sql, (code, description, catalog_id))
                if cursor.rowcount == 0:
                    cursor.execute(insert_sql, (catalog_id, code, description))

        self.db_connection.commit()

    def close(self):
        self.db_connection.close()

