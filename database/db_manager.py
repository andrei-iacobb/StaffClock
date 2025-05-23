import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from utils.logging_manager import LoggingManager

class DatabaseManager:
    def __init__(self, database_path: str, logger: LoggingManager):
        self.database_path = database_path
        self.logger = logger
        self.initialize_database()

    def initialize_database(self):
        """Initialize the database with required tables."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()

            # Create staff table
            c.execute('''
                CREATE TABLE IF NOT EXISTS staff (
                    name TEXT NOT NULL,
                    code TEXT UNIQUE PRIMARY KEY,
                    fingerprint TEXT,
                    role TEXT,
                    notes TEXT
                )
            ''')

            # Create clock records table
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

            # Create archive records table
            c.execute('''
                CREATE TABLE IF NOT EXISTS archive_records (
                    staff_name TEXT,
                    staff_code TEXT,
                    clock_in TEXT,
                    clock_out TEXT,
                    notes TEXT
                )
            ''')

            # Create visitors table
            c.execute('''
                CREATE TABLE IF NOT EXISTS visitors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    car_reg TEXT,
                    purpose TEXT,
                    time_in TEXT,
                    time_out TEXT
                )
            ''')

            conn.commit()
            self.logger.log_database_operation("Initialize", "Database tables created/verified", True)
        except sqlite3.Error as e:
            self.logger.log_error(e, "Database initialization")
        finally:
            conn.close()

    def get_staff_by_code(self, staff_code: str) -> Optional[Dict[str, Any]]:
        """Get staff details by their code."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            c.execute('SELECT name, code, role FROM staff WHERE code = ?', (staff_code,))
            result = c.fetchone()
            if result:
                self.logger.log_database_operation("Query", f"Retrieved staff details for code {staff_code}", True)
                return {"name": result[0], "code": result[1], "role": result[2]}
            self.logger.log_database_operation("Query", f"No staff found for code {staff_code}", False)
            return None
        except sqlite3.Error as e:
            self.logger.log_error(e, "get_staff_by_code")
            return None
        finally:
            conn.close()

    def add_staff(self, name: str, code: str, role: str = "") -> bool:
        """Add a new staff member."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            c.execute('INSERT INTO staff (name, code, role) VALUES (?, ?, ?)', 
                     (name, code, role))
            conn.commit()
            self.logger.log_database_operation("Insert", f"Added staff member: {name} with code {code}", True)
            return True
        except sqlite3.Error as e:
            self.logger.log_error(e, "add_staff")
            return False
        finally:
            conn.close()

    def remove_staff(self, staff_code: str) -> bool:
        """Remove a staff member and archive their records."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()

            # Get staff details
            c.execute('SELECT name FROM staff WHERE code = ?', (staff_code,))
            staff = c.fetchone()
            if not staff:
                self.logger.log_database_operation("Delete", f"Staff not found: {staff_code}", False)
                return False

            # Archive records
            c.execute('''
                INSERT INTO archive_records 
                SELECT s.name, c.staff_code, c.clock_in_time, c.clock_out_time, c.notes
                FROM clock_records c
                JOIN staff s ON c.staff_code = s.code
                WHERE s.code = ?
            ''', (staff_code,))

            # Delete records
            c.execute('DELETE FROM clock_records WHERE staff_code = ?', (staff_code,))
            c.execute('DELETE FROM staff WHERE code = ?', (staff_code,))
            
            conn.commit()
            self.logger.log_database_operation("Delete", f"Removed staff member: {staff[0]} ({staff_code})", True)
            return True
        except sqlite3.Error as e:
            self.logger.log_error(e, "remove_staff")
            return False
        finally:
            conn.close()

    def clock_action(self, staff_code: str, action: str, break_time: str = None) -> Tuple[bool, str]:
        """Handle clock in/out actions."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            current_time = datetime.now().isoformat()

            if action == 'in':
                c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)',
                         (staff_code, current_time))
                message = "Clock-in recorded successfully"
                self.logger.log_database_operation("Clock In", f"Staff {staff_code} clocked in at {current_time}", True)
            elif action == 'out':
                c.execute('''
                    UPDATE clock_records 
                    SET clock_out_time = ?, break_time = ?
                    WHERE staff_code = ? AND clock_out_time IS NULL
                ''', (current_time, break_time, staff_code))
                message = "Clock-out recorded successfully"
                self.logger.log_database_operation("Clock Out", f"Staff {staff_code} clocked out at {current_time}", True)

            conn.commit()
            return True, message
        except sqlite3.Error as e:
            self.logger.log_error(e, "clock_action")
            return False, str(e)
        finally:
            conn.close()

    def get_clock_records(self, staff_code: str, start_date: str = None, end_date: str = None) -> List[Tuple]:
        """Get clock records for a staff member within a date range."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            
            query = 'SELECT * FROM clock_records WHERE staff_code = ?'
            params = [staff_code]
            
            if start_date and end_date:
                query += ' AND DATE(clock_in_time) BETWEEN ? AND ?'
                params.extend([start_date, end_date])
                
            c.execute(query, params)
            records = c.fetchall()
            self.logger.log_database_operation("Query", f"Retrieved {len(records)} clock records for staff {staff_code}", True)
            return records
        except sqlite3.Error as e:
            self.logger.log_error(e, "get_clock_records")
            return []
        finally:
            conn.close()

    def handle_visitor(self, name: str, car_reg: str, purpose: str, action: str) -> Tuple[bool, str]:
        """Handle visitor check-in/out."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            current_time = datetime.now().isoformat()

            if action == "in":
                c.execute('''
                    INSERT INTO visitors (name, car_reg, purpose, time_in) 
                    VALUES (?, ?, ?, ?)
                ''', (name, car_reg, purpose, current_time))
                message = "Visitor checked in successfully"
                self.logger.log_database_operation("Visitor Check In", 
                    f"Visitor {name} ({car_reg}) checked in at {current_time}", True)
            elif action == "out":
                c.execute('''
                    UPDATE visitors 
                    SET time_out = ? 
                    WHERE name = ? AND car_reg = ? AND time_out IS NULL
                ''', (current_time, name, car_reg))
                message = "Visitor checked out successfully"
                self.logger.log_database_operation("Visitor Check Out", 
                    f"Visitor {name} ({car_reg}) checked out at {current_time}", True)

            conn.commit()
            return True, message
        except sqlite3.Error as e:
            self.logger.log_error(e, "handle_visitor")
            return False, str(e)
        finally:
            conn.close()

    def get_current_visitors(self) -> List[Tuple]:
        """Get list of current visitors (checked in but not out)."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            c.execute('''
                SELECT name, car_reg, purpose, time_in 
                FROM visitors 
                WHERE time_out IS NULL
            ''')
            visitors = c.fetchall()
            self.logger.log_database_operation("Query", f"Retrieved {len(visitors)} current visitors", True)
            return visitors
        except sqlite3.Error as e:
            self.logger.log_error(e, "get_current_visitors")
            return []
        finally:
            conn.close()

    def update_visitor_record(self, visitor_id: int, name: str, car_reg: str, purpose: str) -> bool:
        """Update a visitor record."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            c.execute('''
                UPDATE visitors 
                SET name = ?, car_reg = ?, purpose = ?
                WHERE id = ?
            ''', (name, car_reg, purpose, visitor_id))
            conn.commit()
            self.logger.log_database_operation("Update", f"Updated visitor record for ID {visitor_id}", True)
            return True
        except sqlite3.Error as e:
            self.logger.log_error(e, "update_visitor_record")
            return False
        finally:
            conn.close() 