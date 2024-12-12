from PyQt6.QtWidgets import QMessageBox
import sqlite3

class Records():
    def open_records_tab(self):
        staff_name = self.name_entry.text().strip()
        if not staff_name:
            QMessageBox.critical(self, "Error", "Please enter a valid staff name.")
            return

        records = self.get_records(staff_name)
        if records:
            self.create_table_pdf(staff_name, records)
            self.show_pdf(staff_name)

    def get_records(self, staff_name):
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, "Error", "Staff member not found")
            return None

        staff_code = staff[0]
        c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
        records = c.fetchall()
        conn.close()
        return records