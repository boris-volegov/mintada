import sqlite3
import os

class RulersDbHelper:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "coins.db")
        self.db_connection = sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON") 

    def populate_rulers(self, rulers):
        sql = """
        INSERT INTO issuers_rulers_rel (ruler_id, name, issuer_name, period, years_text, period_order, subperiod_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        # Prepare data for bulk insert
        data = [
            (ruler['ruler_id'], ruler['name'], ruler['issuer_name'], ruler['period'], ruler['years_text'], ruler['period_order'], ruler['subperiod_order'])
            for ruler in rulers
            if ruler['ruler_id'] is not None  # Ensure we only include valid records
        ]

        # Execute the bulk insert
        if data:
            self.db_connection.executemany(sql, data)
            self.db_connection.commit()  # Commit the transaction after all inserts

    def populate_ruler(self, rulers):
        sql = """
        INSERT OR REPLACE INTO rulers (id, name, dynasty, portrait_url, portrait_src, info, title)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                ruler['id'], 
                ruler.get('name'), 
                ruler.get('dynasty'), 
                ruler.get('portrait_url'), 
                ruler.get('portrait_src'), 
                ruler.get('info'),
                ruler.get('title')
            )
            for ruler in rulers
            if ruler.get('id') is not None
        ]

        if data:
            self.db_connection.executemany(sql, data)
            self.db_connection.commit()

    def ruler_exists(self, ruler_id):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT 1 FROM rulers WHERE id = ?", (ruler_id,))
        return cursor.fetchone() is not None
    
    def commit(self):
        self.db_connection.commit()