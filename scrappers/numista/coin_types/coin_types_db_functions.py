import sqlite3
import os

class CoinTypesDbHelper:
    def __init__(self):
        # Database is in the parent directory's db folder
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "coins.db")
        self.db_connection = sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON")


    def save_coin_type_samples_adj(self, coin_type_id, images):
        # images: list of filename strings
        if not images:
            return

        # Delete existing for this coin type (clean slate for this scraper run)
        self.db_connection.execute("DELETE FROM coin_type_samples_adj WHERE coin_type_id = ?", (coin_type_id,))

        sql = "INSERT INTO coin_type_samples_adj (coin_type_id, image) VALUES (?, ?)"
        data = [(coin_type_id, img) for img in images]
        self.db_connection.executemany(sql, data)
        self.db_connection.commit()

    def save_coin_type(self, out):
        if not out.get("title"):
            print(f"Skipping coin type {out.get('id')} - No title found.")
            return

        data = {
            "id": out["id"],
            "issuer_id": out["issuer_id"],
            "title": out["title"],
            "subtitle": out["subtitle"],
            "edge_image": out["edge_image"],
            "period": out["period"],
            "coin_type_slug": out["file_name_prefix"],
            "rarity_index": out.get("rarity_index"),
        }
        
        sql = """
        INSERT INTO coin_types (
            id, issuer_id, title, subtitle, 
            edge_image, period, coin_type_slug, rarity_index, issue_type_id
        ) VALUES (
            :id, :issuer_id, :title, :subtitle,
            :edge_image, :period, :coin_type_slug, :rarity_index, 1
        )
        ON CONFLICT(id) DO UPDATE SET
            issuer_id=excluded.issuer_id,
            title=excluded.title,
            subtitle=excluded.subtitle,
            edge_image=excluded.edge_image,
            period=excluded.period,
            coin_type_slug=excluded.coin_type_slug,
            rarity_index=excluded.rarity_index,
            issue_type_id=excluded.issue_type_id
        """
        self.db_connection.execute(sql, data)
        self.db_connection.commit()


    def save_coin_type_samples(self, coin_type_id, samples):
        # First, delete existing samples for this coin type to ensure clean state
        delete_sql = "DELETE FROM coin_type_samples WHERE coin_type_id = ?"
        self.db_connection.execute(delete_sql, (coin_type_id,))

        # Insert new samples
        insert_sql = """
        INSERT INTO coin_type_samples (
            coin_type_id, obverse_image, reverse_image, sample_type
        ) VALUES (
            :coin_type_id, :obverse_image, :reverse_image, :sample_type
        )
        """
        
        for sample in samples:
            # Skip if missing required images (some samples might be partial? Logic says we have both usually)
            if not sample.get("obverse_image") or not sample.get("reverse_image"):
                 continue

            data = {
                "coin_type_id": coin_type_id,
                "obverse_image": sample["obverse_image"],
                "reverse_image": sample["reverse_image"],
                "sample_type": sample["image_type"]
            }
            
            self.db_connection.execute(insert_sql, data)

        self.db_connection.commit()

    def get_coin_type_samples(self, coin_type_id):
        sql = "SELECT obverse_image, reverse_image FROM coin_type_samples WHERE coin_type_id = ?"
        cursor = self.db_connection.execute(sql, (coin_type_id,))
        images = set()
        for row in cursor:
            if row[0]: images.add(str(row[0]))
            if row[1]: images.add(str(row[1]))
        return list(images)

    def get_coin_type_edge_image(self, coin_type_id):
        sql = "SELECT edge_image FROM coin_types WHERE id = ?"
        cursor = self.db_connection.execute(sql, (coin_type_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return str(row[0])
        return None

    def save_coin_type_comment_images(self, coin_type_id, comment_images):
        """
        comment_images: list of dicts {"image": filename, "source_type": int}
        """
        # First, delete existing comment images for this coin type
        delete_sql = "DELETE FROM coin_type_comment_images WHERE coin_type_id = ?"
        self.db_connection.execute(delete_sql, (coin_type_id,))

        if not comment_images:
            return

        # Insert new
        insert_sql = "INSERT INTO coin_type_comment_images (coin_type_id, image, source_type) VALUES (?, ?, ?)"
        data = [(coin_type_id, img["image"], img.get("source_type", 1)) for img in comment_images]
    
        self.db_connection.executemany(insert_sql, data)
        self.db_connection.commit()

    def save_coin_type_full(self, out):
        self.save_coin_type(out)
        
        if out.get("sample_images"):
            self.save_coin_type_samples(out["id"], out["sample_images"])

        if out.get("comment_images"):
            self.save_coin_type_comment_images(out["id"], out["comment_images"])

    def get_coin_type_comment_images(self, coin_type_id):
        sql = "SELECT image, source_type FROM coin_type_comment_images WHERE coin_type_id = ?"
        cursor = self.db_connection.execute(sql, (coin_type_id,))
        # Return list of dicts to match new structure
        return [{"image": str(row[0]), "source_type": row[1]} for row in cursor if row[0]]

    def get_coin_type_full_info(self, coin_type_id):
        # Fetch base info
        sql = "SELECT id, coin_type_slug, edge_image FROM coin_types WHERE id = ?"
        cursor = self.db_connection.execute(sql, (coin_type_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        info = {
            "id": row[0],
            "coin_type_slug": row[1],
            "edge_image": str(row[2]) if row[2] else None,
            "sample_images": self.get_coin_type_samples(coin_type_id),
            "comment_images": self.get_coin_type_comment_images(coin_type_id)
        }
        return info




    def check_reference_image_exists(self, coin_type_id):
        # sample_type=1 is Reference image
        sql = "SELECT 1 FROM coin_type_samples WHERE coin_type_id = ? AND sample_type = 1 LIMIT 1"
        cursor = self.db_connection.execute(sql, (coin_type_id,))
        return cursor.fetchone() is not None

    def insert_missing_reference_image(self, coin_type_id, obverse_image, reverse_image):
        # Insert with is_fix=1
        # Note: If 'is_fix' column is missing from table schema, this will fail.
        # User requested: "is_fix (new field) = 1"
        sql = """
        INSERT INTO coin_type_samples (
            coin_type_id, obverse_image, reverse_image, sample_type, is_fix
        ) VALUES (
            ?, ?, ?, 1, 1
        )
        """
        self.db_connection.execute(sql, (coin_type_id, obverse_image, reverse_image))
        self.db_connection.commit()

    def delete_coin_type(self, coin_type_id):
        self.db_connection.execute("DELETE FROM coin_types WHERE id = ?", (coin_type_id,))
        self.db_connection.commit()

    def get_last_inserted_coin_type_with_issuer(self):
        sql = """
            SELECT ct.id, ct.coin_type_slug, i.numista_url_slug
            FROM coin_types ct
            JOIN issuers i ON ct.issuer_id = i.id
            ORDER BY ct.date_time_inserted DESC
            LIMIT 1
        """
        cursor = self.db_connection.execute(sql)
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "coin_type_slug": row[1],
                "issuer_url_slug": row[2] # This key name is expected by the caller
            }
        return None
