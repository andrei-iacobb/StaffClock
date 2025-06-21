import sqlite3
import os
import shutil
from datetime import datetime
import logging
from typing import List, Dict, Optional, Tuple


class ArchiveManager:
    """Manages database archiving operations."""
    
    def __init__(self, database_path: str, archive_folder: str):
        self.database_path = database_path
        self.archive_folder = archive_folder
        os.makedirs(archive_folder, exist_ok=True)
    
    def create_archive(self, manual: bool = False) -> Tuple[bool, str]:
        """Create an archive of the current database."""
        try:
            # Create archive filename with current date
            archive_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            prefix = "manual_archive_" if manual else "database_archive_"
            archive_filename = f"{prefix}{archive_date}.db"
            archive_path = os.path.join(self.archive_folder, archive_filename)
            
            logging.info(f"Starting database archival process for {archive_date}")
            
            # Copy current database to archive
            shutil.copy2(self.database_path, archive_path)
            logging.info(f"Database copied to archive: {archive_path}")
            
            return True, f"Archive created successfully: {archive_filename}"
            
        except Exception as e:
            logging.error(f"Failed to create archive: {e}")
            return False, f"Error creating archive: {str(e)}"
    
    def get_archive_list(self) -> List[Dict]:
        """Get a list of all archive databases with their metadata."""
        try:
            archive_files = []
            if os.path.exists(self.archive_folder):
                for filename in os.listdir(self.archive_folder):
                    if filename.endswith(".db") and ("archive" in filename.lower()):
                        file_path = os.path.join(self.archive_folder, filename)
                        
                        # Handle different archive naming patterns
                        date_part = None
                        if filename.startswith("database_archive_"):
                            date_part = filename.replace("database_archive_", "").replace(".db", "")
                        elif filename.startswith("manual_archive_"):
                            date_part = filename.replace("manual_archive_", "").replace(".db", "")
                        
                        if date_part:
                            try:
                                archive_date = datetime.strptime(date_part, "%Y-%m-%d_%H-%M-%S")
                                archive_files.append({
                                    'filename': filename,
                                    'path': file_path,
                                    'date': archive_date,
                                    'size': os.path.getsize(file_path),
                                    'type': 'Manual' if filename.startswith("manual_") else 'Automatic'
                                })
                            except ValueError:
                                # Try alternative date formats or use file modification time
                                try:
                                    file_stat = os.path.getmtime(file_path)
                                    archive_date = datetime.fromtimestamp(file_stat)
                                    archive_files.append({
                                        'filename': filename,
                                        'path': file_path,
                                        'date': archive_date,
                                        'size': os.path.getsize(file_path),
                                        'type': 'Unknown'
                                    })
                                except:
                                    continue
            
            # Sort by date (newest first)
            archive_files.sort(key=lambda x: x['date'], reverse=True)
            return archive_files
            
        except Exception as e:
            logging.error(f"Failed to get archive databases: {e}")
            return []
    
    def delete_archive(self, archive_path: str) -> Tuple[bool, str]:
        """Delete an archive database."""
        try:
            if os.path.exists(archive_path):
                os.remove(archive_path)
                filename = os.path.basename(archive_path)
                logging.info(f"Deleted archive database: {filename}")
                return True, f"Archive '{filename}' deleted successfully."
            else:
                return False, "Archive file not found."
        except Exception as e:
            logging.error(f"Error deleting archive {archive_path}: {e}")
            return False, f"Error deleting archive: {str(e)}"
    
    def get_archive_info(self, archive_path: str) -> Dict:
        """Get detailed information about an archive database."""
        try:
            conn = sqlite3.connect(archive_path)
            cursor = conn.cursor()
            
            info = {
                'staff_count': 0,
                'records_count': 0,
                'visitors_count': 0,
                'visitors_table_exists': False,
                'tables': []
            }
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            info['tables'] = [table[0] for table in tables]
            
            # Get counts for each table
            if 'staff' in info['tables']:
                cursor.execute("SELECT COUNT(*) FROM staff")
                info['staff_count'] = cursor.fetchone()[0]
            
            if 'clock_records' in info['tables']:
                cursor.execute("SELECT COUNT(*) FROM clock_records")
                info['records_count'] = cursor.fetchone()[0]
            
            if 'visitors' in info['tables']:
                info['visitors_table_exists'] = True
                cursor.execute("SELECT COUNT(*) FROM visitors")
                info['visitors_count'] = cursor.fetchone()[0]
            
            conn.close()
            return info
            
        except Exception as e:
            logging.error(f"Error getting archive info for {archive_path}: {e}")
            return {}


class DatabaseCleaner:
    """Handles database cleanup and maintenance operations."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
    
    def reset_database(self, keep_staff: bool = True) -> Tuple[bool, str]:
        """Reset the database by clearing records but optionally keeping staff."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Count records before deletion for logging
            cursor.execute('SELECT COUNT(*) FROM clock_records')
            clock_records_count = cursor.fetchone()[0]
            
            # Check if visitors table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='visitors'")
            visitors_table_exists = cursor.fetchone() is not None
            visitors_count = 0
            
            if visitors_table_exists:
                cursor.execute('SELECT COUNT(*) FROM visitors')
                visitors_count = cursor.fetchone()[0]
            
            logging.info(f"About to reset database: {clock_records_count} clock records, {visitors_count} visitor records")
            
            # Clear clock records
            cursor.execute('DELETE FROM clock_records')
            
            # Clear visitor records if table exists
            if visitors_table_exists:
                cursor.execute('DELETE FROM visitors')
            
            # Clear archive records if any exist
            cursor.execute('DELETE FROM archive_records WHERE 1=1')
            
            # Optionally clear staff (for complete reset)
            if not keep_staff:
                cursor.execute('DELETE FROM staff')
            
            conn.commit()
            conn.close()
            
            message = f"Database reset successfully - cleared {clock_records_count} clock records"
            if visitors_count > 0:
                message += f", {visitors_count} visitor records"
            if not keep_staff:
                message += ", and all staff records"
            
            logging.info(message)
            return True, message
            
        except Exception as e:
            logging.error(f"Failed to reset database: {e}")
            return False, f"Error resetting database: {str(e)}"
    
    def vacuum_database(self) -> Tuple[bool, str]:
        """Vacuum the database to reclaim unused space."""
        try:
            conn = sqlite3.connect(self.database_path)
            conn.execute('VACUUM')
            conn.close()
            
            logging.info("Database vacuumed successfully")
            return True, "Database optimized successfully"
            
        except Exception as e:
            logging.error(f"Failed to vacuum database: {e}")
            return False, f"Error optimizing database: {str(e)}"
    
    def check_database_integrity(self) -> Tuple[bool, str]:
        """Check database integrity."""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('PRAGMA integrity_check')
            result = cursor.fetchone()[0]
            conn.close()
            
            if result == 'ok':
                logging.info("Database integrity check passed")
                return True, "Database integrity check passed"
            else:
                logging.warning(f"Database integrity check failed: {result}")
                return False, f"Database integrity issues found: {result}"
                
        except Exception as e:
            logging.error(f"Failed to check database integrity: {e}")
            return False, f"Error checking database integrity: {str(e)}"


class DatabaseValidator:
    """Validates database structure and data consistency."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
    
    def validate_tables(self) -> Tuple[bool, List[str]]:
        """Validate that all required tables exist with correct structure."""
        issues = []
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check required tables
            required_tables = {
                'staff': ['name', 'code', 'fingerprint', 'role', 'notes'],
                'clock_records': ['id', 'staff_code', 'clock_in_time', 'clock_out_time', 'notes', 'break_time'],
                'archive_records': ['staff_name', 'staff_code', 'clock_in', 'clock_out', 'notes']
            }
            
            for table_name, required_columns in required_tables.items():
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                if not cursor.fetchone():
                    issues.append(f"Missing required table: {table_name}")
                    continue
                
                # Check table structure
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [column[1] for column in cursor.fetchall()]
                
                for required_column in required_columns:
                    if required_column not in columns:
                        issues.append(f"Missing column '{required_column}' in table '{table_name}'")
            
            conn.close()
            
            if not issues:
                logging.info("Database structure validation passed")
                return True, []
            else:
                logging.warning(f"Database structure validation failed: {issues}")
                return False, issues
                
        except Exception as e:
            logging.error(f"Failed to validate database structure: {e}")
            return False, [f"Error validating database structure: {str(e)}"]
    
    def validate_data_consistency(self) -> Tuple[bool, List[str]]:
        """Validate data consistency across tables."""
        issues = []
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check for orphaned clock records (staff_code not in staff table)
            cursor.execute("""
                SELECT DISTINCT c.staff_code 
                FROM clock_records c 
                LEFT JOIN staff s ON c.staff_code = s.code 
                WHERE s.code IS NULL
            """)
            orphaned_codes = cursor.fetchall()
            
            if orphaned_codes:
                codes = [code[0] for code in orphaned_codes]
                issues.append(f"Orphaned clock records for non-existent staff codes: {codes}")
            
            # Check for duplicate staff codes
            cursor.execute("""
                SELECT code, COUNT(*) as count 
                FROM staff 
                GROUP BY code 
                HAVING count > 1
            """)
            duplicate_codes = cursor.fetchall()
            
            if duplicate_codes:
                codes = [f"{code[0]} ({code[1]} times)" for code in duplicate_codes]
                issues.append(f"Duplicate staff codes found: {codes}")
            
            # Check for invalid date formats in clock records
            cursor.execute("""
                SELECT id, clock_in_time, clock_out_time 
                FROM clock_records 
                WHERE clock_in_time IS NOT NULL 
                AND clock_in_time != ''
            """)
            
            invalid_dates = []
            for record in cursor.fetchall():
                try:
                    datetime.fromisoformat(record[1])
                    if record[2]:
                        datetime.fromisoformat(record[2])
                except ValueError:
                    invalid_dates.append(record[0])
            
            if invalid_dates:
                issues.append(f"Invalid date formats in clock records: {invalid_dates}")
            
            conn.close()
            
            if not issues:
                logging.info("Database data consistency validation passed")
                return True, []
            else:
                logging.warning(f"Database data consistency validation failed: {issues}")
                return False, issues
                
        except Exception as e:
            logging.error(f"Failed to validate data consistency: {e}")
            return False, [f"Error validating data consistency: {str(e)}"] 