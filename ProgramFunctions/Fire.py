from datetime import datetime
import sqlite3

class Fire:
    def fire(self):
        time_now = datetime.datetime.now().strftime('%Y-%m-%d')  # Today's date
        print(f"Today's date: {time_now}")  # Debugging: print the date being queried

        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()

        # Test query to debug
        c.execute('SELECT clock_in_time FROM clock_records')
        all_records = c.fetchall()
        print("All clock_in_time values in the database:")
        for record in all_records:
            print(record)

        # Now attempt the original query
        c.execute('SELECT staff_code, clock_in_time FROM clock_records WHERE DATE(clock_in_time) = ?', (time_now,))
        records = c.fetchall()

        if not records:
            print("No records found for today's date.")
        else:
            print("Records for today:")
            for record in records:
                print(f"Staff Code: {record[0]}, Clock In Time: {record[1]}")

        conn.close()
