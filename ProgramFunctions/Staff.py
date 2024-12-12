from PyQt6.QtWidgets import QMessageBox
import datetime
import random
import sqlite3

class Staff:
    def clock_action(self, action, staff_code):
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()

        # Check if the staff member exists
        c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        if not staff:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid staff code')
            return

        if action == 'in':
            clock_in_time = datetime.datetime.now().isoformat()
            c.execute('INSERT   clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                      (staff_code, clock_in_time))
            conn.commit()
            conn.close()
            time_in = datetime.datetime.fromisoformat(clock_in_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-in recorded successfully at {time_in}')
            self.staff_code_entry.clear()
        elif action == 'out':
            clock_out_time = datetime.datetime.now().isoformat()
            c.execute('SELECT id FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL',
                      (staff_code,))
            clock_record = c.fetchone()
            if not clock_record:
                conn.close()
                QMessageBox.critical(self, 'Error', 'No clock-in record found')
                return
            c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
            conn.commit()
            conn.close()
            time_out = datetime.datetime.fromisoformat(clock_out_time).strftime('%H:%M')
            QMessageBox.information(self, 'Success', f'Clock-out recorded successfully at {time_out}')
            self.staff_code_entry.clear()
        else:
            conn.close()
            QMessageBox.critical(self, 'Error', 'Invalid action')

    def add_staff(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            staff_code = random.randint(1000, 9999)
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
                staff_code = random.randint(1000, 9999)
            try:
                c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} added with code {staff_code}')
            except sqlite3.Error as e:
                QMessageBox.critical(self, 'Database Error', f'An error occurred: {e}')
            finally:
                conn.close()

    def remove_staff(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            conn = sqlite3.connect('staff_hours.db')
            c = conn.cursor()
            if c.execute('SELECT * FROM staff WHERE name = ?', (staff_name,)).fetchone():
                c.execute('DELETE FROM staff WHERE name = ?', (staff_name,))
                conn.commit()
                QMessageBox.information(self, 'Success', f'Staff member {staff_name} deleted')
            conn.close()

