import sqlite3
import logging

class DatabaseManager:
    def __init__(self, database_path):
        self.database_path = database_path

    def generate_default_database(self):
        conn = sqlite3.connect(self.database_path)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                name TEXT NOT NULL,
                code TEXT UNIQUE PRIMARY KEY,
                fingerprint TEXT,
                role TEXT,
                notes TEXT
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS clock_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_code TEXT NOT NULL,
                clock_in_time TEXT,
                clock_out_time TEXT,
                notes TEXT,
                break_time TEXT,
                FOREIGN KEY(staff_code) REFERENCES staff(code)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS archive_records (
                staff_name TEXT,
                staff_code TEXT,
                clock_in TEXT,
                clock_out TEXT,
                notes TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logging.info(f"Default database created at {self.database_path}") 