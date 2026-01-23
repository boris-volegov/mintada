import sqlite3

class MintsDbHelper:
    def __init__(self):
        self.db_path = "db/coins.db"
        self.db_connection =sqlite3.connect(self.db_path)  

        self.db_connection.execute("PRAGMA foreign_keys = ON") 

    def populate_mints(self, mints):
        sql = """
        INSERT INTO mints (id, name, additional_location_info, latitude, longitude, period)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            additional_location_info=excluded.additional_location_info,
            latitude=excluded.latitude,
            longitude=excluded.longitude,
            period=excluded.period;
        """
        
        # Prepare data for bulk insert
        data = [
            (mint['id'], mint['name'], mint['additional_location_info'], mint['latitude'], mint['longitude'], mint['period'])
            for mint in mints
            if mint['id'] is not None  # Ensure we only include valid records
        ]

        # Execute the bulk insert
        if data:
            self.db_connection.executemany(sql, data)
            self.db_connection.commit()  # Commit the transaction after all inserts
    
    def commit(self):
        self.db_connection.commit()