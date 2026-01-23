import sqlite3

class TechniquesDbHelper:
    def __init__(self):
        self.db_path = "db/coins.db"
        self.db_connection =sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON") 

    def populate_techniques(self, techniques):
        sql = """
        INSERT INTO techniques (id, name, img_url)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            img_url=excluded.img_url;
        """
        
        # Prepare data for bulk insert
        data = [
            (technique['id'], technique['name'], technique['img_url'])
            for technique in techniques
            if technique['id'] is not None  # Ensure we only include valid records
        ]

        # Execute the bulk insert
        if data:
            self.db_connection.executemany(sql, data)
            self.db_connection.commit()  # Commit the transaction after all inserts
    
    def commit(self):
        self.db_connection.commit()