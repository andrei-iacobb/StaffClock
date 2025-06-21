#!/usr/bin/env python3
"""
Fingerprint Manager for DigitalPersona U.are.U 4500
Real device integration with biometric enrollment and verification.
"""

import cv2
import numpy as np
import time
import logging
import sqlite3
import os
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# Import our real device drivers
# try:
#     from .digitalpersona_sdk_simple import DigitalPersonaU4500
#     print("Using DigitalPersona SDK Simple implementation")
# except ImportError:
#     from .digitalpersona_simple import DigitalPersonaSimple as DigitalPersonaU4500
#     print("Using simple DigitalPersona implementation")

# from .biometric_enrollment import BiometricProfileEnrollment

# --- Mock/Stub Classes since real drivers are missing ---

class MockDigitalPersona:
    def connect(self):
        logging.warning("MOCK FINGERPRINT: Device connection called, but device is not available.")
        return False
    def disconnect(self):
        pass

class MockBiometricEnrollment:
    def connect_device(self):
        logging.warning("MOCK FINGERPRINT: Enrollment connection called, but device is not available.")
        return False
    def enroll_biometric_profile(self, *args, **kwargs):
        return False, "Fingerprint device not configured.", {}
    def disconnect(self):
        pass

# --- End Mock/Stub Classes ---


class FingerprintManager(QObject):
    """Manages fingerprint operations using real DigitalPersona device."""
    
    # PyQt signals for GUI updates
    fingerprint_captured = pyqtSignal(str)  # message
    error_occurred = pyqtSignal(str)        # error message
    status_updated = pyqtSignal(str)        # status message
    
    def __init__(self, db_path: str = "staff_timesheet.db"):
        super().__init__()
        self.db_path = db_path
        # self.device = DigitalPersonaU4500()
        # self.enrollment_system = BiometricProfileEnrollment()
        self.device = MockDigitalPersona()
        self.enrollment_system = MockBiometricEnrollment()
        self.is_initialized = False
        
        # Initialize fingerprint tables in main database
        self._init_fingerprint_tables()
        
        logging.info("FingerprintManager initialized with real device support")
    
    def _init_fingerprint_tables(self):
        """Initialize fingerprint-related tables in the main database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create fingerprint_users table for linking employees to biometric profiles
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS fingerprint_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id TEXT UNIQUE NOT NULL,
                        employee_name TEXT NOT NULL,
                        biometric_user_id TEXT UNIQUE NOT NULL,
                        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_verification TIMESTAMP,
                        verification_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'ACTIVE',
                        FOREIGN KEY (employee_id) REFERENCES employees(id)
                    )
                ''')
                
                # Create fingerprint_logs table for tracking fingerprint access
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS fingerprint_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,  -- 'CLOCK_IN', 'CLOCK_OUT', 'ENROLLMENT', 'VERIFICATION'
                        success BOOLEAN NOT NULL,
                        match_score REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (employee_id) REFERENCES employees(id)
                    )
                ''')
                
                conn.commit()
            
            logging.info("Fingerprint tables initialized in main database")
            
        except Exception as e:
            logging.error(f"Error initializing fingerprint tables: {e}")
    
    def initialize_device(self) -> Tuple[bool, str]:
        """Initialize the fingerprint device and enrollment system."""
        try:
            # Connect to the real device
            if self.device.connect():
                logging.info("DigitalPersona device connected successfully")
                
                # Connect enrollment system to same device
                if self.enrollment_system.connect_device():
                    self.is_initialized = True
                    self.status_updated.emit("Fingerprint device ready")
                    return True, "Fingerprint device initialized successfully"
                else:
                    return False, "Failed to initialize enrollment system"
            else:
                error_msg = "Failed to connect to DigitalPersona U.are.U 4500 device"
                logging.error(error_msg)
                return False, error_msg
        
        except Exception as e:
            error_msg = f"Error initializing fingerprint device: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def shutdown_device(self):
        """Shutdown the fingerprint device."""
        try:
            if self.enrollment_system:
                self.enrollment_system.disconnect()
            
            if self.device:
                self.device.disconnect()
            
            self.is_initialized = False
            self.status_updated.emit("Fingerprint device disconnected")
            logging.info("Fingerprint device shutdown")
        
        except Exception as e:
            logging.error(f"Error shutting down fingerprint device: {e}")
    
    def enroll_employee(self, employee_id: str, employee_name: str) -> Tuple[bool, str, Dict]:
        """
        Enroll an employee's fingerprint using multiple samples.
        
        Args:
            employee_id: Employee ID from the main system
            employee_name: Employee name
            
        Returns:
            Tuple of (success, message, stats)
        """
        if not self.is_initialized:
            return False, "Fingerprint device not initialized", {}
        
        try:
            # Check if employee already enrolled
            if self._is_employee_enrolled(employee_id):
                return False, f"Employee {employee_id} already enrolled", {}
            
            # Create unique biometric user ID
            biometric_user_id = f"emp_{employee_id}_{int(time.time())}"
            
            # Perform enrollment using the biometric system
            success, message, stats = self.enrollment_system.enroll_biometric_profile(
                employee_id, employee_name
            )
            
            if success:
                # Link employee to biometric profile in main database
                self._link_employee_to_biometric(employee_id, employee_name, biometric_user_id)
                
                # Log enrollment
                self._log_fingerprint_action(employee_id, 'ENROLLMENT', True, 
                                           stats.get('average_quality', 0), 
                                           f"Enrolled with {stats.get('samples_captured', 0)} samples")
                
                self.fingerprint_captured.emit(f"Employee {employee_name} enrolled successfully")
                
                # Add enrollment stats to message
                stats['biometric_user_id'] = biometric_user_id
                return True, message, stats
            else:
                # Log failed enrollment
                self._log_fingerprint_action(employee_id, 'ENROLLMENT', False, 0, message)
                return False, message, {}
        
        except Exception as e:
            error_msg = f"Error enrolling employee: {str(e)}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False, error_msg, {}
    
    def verify_employee_fingerprint(self, timeout_seconds: int = 30) -> Tuple[bool, Optional[str], str, float]:
        """
        Verify employee fingerprint and return employee ID if successful.
        
        Args:
            timeout_seconds: Maximum time to wait for fingerprint
            
        Returns:
            Tuple of (success, employee_id, message, match_score)
        """
        if not self.is_initialized:
            return False, None, "Fingerprint device not initialized", 0.0
        
        self.status_updated.emit("Place finger on scanner for verification...")
        
        try:
            # Get all enrolled employees
            enrolled_employees = self._get_enrolled_employees()
            
            if not enrolled_employees:
                return False, None, "No employees enrolled for fingerprint verification", 0.0
            
            # Capture fingerprint for verification using real device
            image = self.device.capture_fingerprint()
            
            if image is None:
                return False, None, "No fingerprint detected", 0.0
            
            # Additional validation - check if image has sufficient quality/content
            import numpy as np
            if isinstance(image, np.ndarray):
                # Check if image has sufficient variation (not just noise/empty)
                if np.std(image) < 10:  # Very low variation suggests no finger present
                    return False, None, "No fingerprint detected", 0.0
            
            # Verify against all enrolled employees using the biometric system
            staff_code, match_score, verify_message = self.enrollment_system.verify_biometric(image)
            
            verification_threshold = 0.9  # Require 90% accuracy to prevent false positives
            
            if staff_code and match_score >= verification_threshold:
                # Find the employee data for this staff code
                matched_employee = None
                for emp_data in enrolled_employees:
                    if emp_data['employee_id'] == staff_code:
                        matched_employee = emp_data
                        break
                
                if matched_employee:
                    employee_id = matched_employee['employee_id']
                    employee_name = matched_employee['employee_name']
                
                    # Update verification statistics
                    self._update_employee_verification(employee_id, match_score)
                    
                    # Log successful verification
                    self._log_fingerprint_action(employee_id, 'VERIFICATION', True, match_score,
                                               f"Successful verification")
                    
                    success_message = f"Employee verified: {employee_name} (ID: {employee_id})"
                    self.fingerprint_captured.emit(success_message)
                    
                    return True, employee_id, success_message, match_score
                else:
                    # Staff code found but no matching employee record
                    failure_message = f"Staff code {staff_code} not found in employee records"
                    return False, None, failure_message, match_score
            else:
                # Log failed verification
                self._log_fingerprint_action('UNKNOWN', 'VERIFICATION', False, match_score,
                                           f"No matching employee found")
                
                failure_message = f"Fingerprint verification failed (score: {match_score:.3f})"
                return False, None, failure_message, match_score
        
        except Exception as e:
            error_msg = f"Error during fingerprint verification: {str(e)}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False, None, error_msg, 0.0
    
    def _is_employee_enrolled(self, employee_id: str) -> bool:
        """Check if employee is already enrolled."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM fingerprint_users WHERE employee_id = ? AND status = "ACTIVE"', 
                              (employee_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logging.error(f"Error checking employee enrollment: {e}")
            return False
    
    def _link_employee_to_biometric(self, employee_id: str, employee_name: str, biometric_user_id: str):
        """Link employee to their biometric profile."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO fingerprint_users 
                    (employee_id, employee_name, biometric_user_id, enrollment_date)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (employee_id, employee_name, biometric_user_id))
                conn.commit()
            
            logging.info(f"Linked employee {employee_id} to biometric profile {biometric_user_id}")
        
        except Exception as e:
            logging.error(f"Error linking employee to biometric profile: {e}")
    
    def _get_enrolled_employees(self) -> list:
        """Get list of all enrolled employees."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT employee_id, employee_name, biometric_user_id, enrollment_date,
                           verification_count, last_verification
                    FROM fingerprint_users 
                    WHERE status = "ACTIVE"
                    ORDER BY employee_name
                ''')
                
                employees = []
                for row in cursor.fetchall():
                    employees.append({
                        'employee_id': row[0],
                        'employee_name': row[1],
                        'biometric_user_id': row[2],
                        'enrollment_date': row[3],
                        'verification_count': row[4],
                        'last_verification': row[5]
                    })
                
                return employees
        
        except Exception as e:
            logging.error(f"Error getting enrolled employees: {e}")
            return []
    
    def _update_employee_verification(self, employee_id: str, match_score: float):
        """Update employee verification statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE fingerprint_users 
                    SET verification_count = verification_count + 1,
                        last_verification = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                ''', (employee_id,))
                conn.commit()
        
        except Exception as e:
            logging.error(f"Error updating employee verification: {e}")
    
    def _log_fingerprint_action(self, employee_id: str, action_type: str, success: bool, 
                               match_score: float, notes: str = ""):
        """Log fingerprint actions for audit trail."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO fingerprint_logs 
                    (employee_id, action_type, success, match_score, notes, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (employee_id, action_type, success, match_score, notes))
                conn.commit()
        
        except Exception as e:
            logging.error(f"Error logging fingerprint action: {e}")
    
    def get_enrollment_status(self) -> Dict[str, Any]:
        """Get current enrollment status and statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get enrollment statistics
                cursor.execute('SELECT COUNT(*) FROM fingerprint_users WHERE status = "ACTIVE"')
                enrolled_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM fingerprint_logs WHERE action_type = "VERIFICATION"')
                total_verifications = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM fingerprint_logs WHERE action_type = "VERIFICATION" AND success = 1')
                successful_verifications = cursor.fetchone()[0]
                
                # Calculate success rate
                success_rate = (successful_verifications / total_verifications * 100) if total_verifications > 0 else 0
                
                return {
                    'device_connected': self.is_initialized,
                    'enrolled_employees': enrolled_count,
                    'total_verifications': total_verifications,
                    'successful_verifications': successful_verifications,
                    'success_rate': success_rate,
                    'device_status': self.device.get_device_status() if self.device else None
                }
        
        except Exception as e:
            logging.error(f"Error getting enrollment status: {e}")
            return {
                'device_connected': False,
                'enrolled_employees': 0,
                'total_verifications': 0,
                'successful_verifications': 0,
                'success_rate': 0,
                'device_status': None
            }
    
    def remove_employee_enrollment(self, employee_id: str) -> Tuple[bool, str]:
        """Remove employee's fingerprint enrollment."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get biometric user ID
                cursor.execute('SELECT biometric_user_id FROM fingerprint_users WHERE employee_id = ?', 
                              (employee_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "Employee not enrolled"
                
                biometric_user_id = result[0]
                
                # Remove from biometric enrollment system
                if self.enrollment_system:
                    biometric_removed = self.enrollment_system.remove_profile(employee_id)
                    if biometric_removed:
                        logging.info(f"Removed biometric profile for {employee_id}")
                    else:
                        logging.warning(f"Failed to remove biometric profile for {employee_id}")
                
                # Delete the record completely for clean re-enrollment
                conn.execute('''
                    DELETE FROM fingerprint_users 
                    WHERE employee_id = ?
                ''', (employee_id,))
                
                # Log removal
                self._log_fingerprint_action(employee_id, 'REMOVAL', True, 0, 
                                           "Enrollment removed by administrator")
                
                conn.commit()
            
            return True, "Employee fingerprint enrollment removed"
        
        except Exception as e:
            error_msg = f"Error removing employee enrollment: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def test_device_connection(self) -> Tuple[bool, str]:
        """Test the device connection and functionality."""
        if not self.is_initialized:
            return False, "Device not initialized"
        
        try:
            device_status = self.device.get_device_status()
            
            if device_status['connected'] and device_status['device_ready']:
                return True, "Device is connected and ready"
            else:
                return False, f"Device not ready: {device_status}"
        
        except Exception as e:
            return False, f"Device test failed: {str(e)}"
    
    def is_device_available(self) -> bool:
        """Check if fingerprint device is available and ready."""
        try:
            if not self.is_initialized:
                return False
            
            device_status = self.device.get_device_status()
            return device_status.get('connected', False) and device_status.get('device_ready', False)
        
        except Exception as e:
            logging.error(f"Error checking device availability: {e}")
            return False
    
    def authenticate_fingerprint(self, timeout_seconds: int = 5) -> Tuple[Optional[str], str]:
        """
        Fast authenticate user fingerprint and return staff code if successful.
        This method is called by main.py for compatibility.
        
        Args:
            timeout_seconds: Maximum time to wait for fingerprint (default: 5 seconds)
            
        Returns:
            Tuple of (staff_code, message)
        """
        success, employee_id, message, match_score = self.verify_employee_fingerprint(timeout_seconds)
        
        if success and employee_id:
            return employee_id, f"Welcome {employee_id}!"
        else:
            return None, "Fingerprint not recognized"
    
def detect_digitalPersona_device() -> Tuple[bool, str]:
    """
    Detect DigitalPersona U.are.U 4500 device availability.
    
    Returns:
        Tuple of (detected, message)
    """
    try:
        # Try to create and connect to device
        device = DigitalPersonaU4500()
        
        if device.connect():
            status = device.get_device_status()
            device.disconnect()
            
            if status['connected']:
                return True, f"DigitalPersona U.are.U 4500 detected and ready"
            else:
                return False, "DigitalPersona device found but not ready"
        else:
            return False, "DigitalPersona U.are.U 4500 not detected or failed to connect"
    
    except Exception as e:
        return False, f"Error detecting DigitalPersona device: {str(e)}"

class FingerprintThread(QThread):
    """Thread for handling fingerprint operations without blocking UI."""
    
    finished = pyqtSignal(bool, str, dict)  # success, message, data
    
    def __init__(self, manager: FingerprintManager, operation: str, **kwargs):
        super().__init__()
        self.manager = manager
        self.operation = operation
        self.kwargs = kwargs
    
    def run(self):
        """Run the fingerprint operation in a separate thread."""
        try:
            if self.operation == 'enroll':
                success, message, stats = self.manager.enroll_employee(
                    self.kwargs['employee_id'], self.kwargs['employee_name']
                )
                self.finished.emit(success, message, stats)
            
            elif self.operation == 'verify':
                success, employee_id, message, score = self.manager.verify_employee_fingerprint(
                    self.kwargs.get('timeout', 30)
                )
                data = {'employee_id': employee_id, 'match_score': score}
                self.finished.emit(success, message, data)
                
            elif self.operation == 'authenticate':
                staff_code, message = self.manager.authenticate_fingerprint(
                    self.kwargs.get('timeout', 5)
                )
                success = staff_code is not None
                data = {'employee_id': staff_code, 'message': message}
                self.finished.emit(success, message, data)
            
            else:
                self.finished.emit(False, f"Unknown operation: {self.operation}", {})
        
        except Exception as e:
            self.finished.emit(False, f"Thread error: {str(e)}", {}) 