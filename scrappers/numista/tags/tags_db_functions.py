import sqlite3

class TagsDbHelper:
    def __init__(self):
        self.db_path = "db/coins.db"
        self.db_connection =sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON") 

    def populate_tags(self, tags):
        sql = """
        INSERT INTO tags (id, name, additional_info, img_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            additional_info=excluded.additional_info,
            img_name=excluded.img_name
        """
        
        # Prepare data for bulk insert
        data = [
            (tag['id'], tag['name'], tag['additional_info'], tag['img_name'])
            for tag in tags
            if tag['id'] is not None  # Ensure we only include valid records
        ]

        # Execute the bulk insert
        if data:
            self.db_connection.executemany(sql, data)
            self.db_connection.commit()  # Commit the transaction after all inserts
    
    def commit(self):
        self.db_connection.commit()