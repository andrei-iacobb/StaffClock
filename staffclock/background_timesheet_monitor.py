#!/usr/bin/env python3
"""
Background Timesheet Monitor Service
===================================

This service runs continuously in the background to monitor workers with active shifts
and automatically generates their timesheets when they clock out.

Features:
- Persistent background monitoring
- Real-time clock-out detection
- Automatic timesheet generation
- Database connection management
- Error handling and logging
- Service start/stop controls

Author: StaffClock Progressive System
Date: December 2024
"""

import sqlite3
import datetime
import time
import logging
import threading
import os
from typing import Dict, List, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class BackgroundTimesheetMonitor(QObject):
    """
    Background service that monitors workers with active shifts and generates
    timesheets automatically when they clock out.
    """
    
    # Signals for status updates (can be connected to UI or logging)
    worker_clocked_out = pyqtSignal(str, str, dict)  # staff_code, name, timesheet_info
    timesheet_generated = pyqtSignal(str, str, bool)  # staff_code, name, success
    monitoring_status = pyqtSignal(str)  # status message
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    
    def __init__(self, database_path: str, check_interval: int = 30):
        super().__init__()
        self.database_path = database_path
        self.check_interval = check_interval  # Check every 30 seconds by default
        self.monitoring_active = False
        self.pending_workers = set()
        self.worker_last_status = {}
        self.total_timesheets_generated = 0
        
        # Timer for periodic checks
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.check_pending_workers)
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup dedicated logging for the background monitor."""
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        
        # Setup file handler for background monitor
        file_handler = logging.FileHandler("logs/background_timesheet_monitor.log")
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] BackgroundMonitor - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Create logger
        self.logger = logging.getLogger('background_timesheet_monitor')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        
        # Also log to main system
        main_logger = logging.getLogger('main')
        if main_logger:
            self.logger.addHandler(main_logger.handlers[0] if main_logger.handlers else logging.StreamHandler())
    
    def start_monitoring(self, initial_pending_workers: Set[str] = None):
        """
        Start the background monitoring service.
        
        Args:
            initial_pending_workers: Set of staff codes to monitor initially
        """
        if self.monitoring_active:
            self.logger.warning("🔄 Background monitoring already active")
            return
        
        self.monitoring_active = True
        
        # Initialize pending workers
        if initial_pending_workers:
            self.pending_workers = initial_pending_workers.copy()
        else:
            self.discover_pending_workers()
        
        self.logger.info(f"🚀 BACKGROUND TIMESHEET MONITORING STARTED")
        self.logger.info(f"   • Monitoring {len(self.pending_workers)} workers with active shifts")
        self.logger.info(f"   • Check interval: {self.check_interval} seconds")
        
        # Start the timer
        self.monitor_timer.start(self.check_interval * 1000)  # Convert to milliseconds
        
        self.monitoring_status.emit(f"🔄 Background monitoring active for {len(self.pending_workers)} workers")
        
    def stop_monitoring(self):
        """Stop the background monitoring service."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.monitor_timer.stop()
        
        self.logger.info(f"🛑 BACKGROUND TIMESHEET MONITORING STOPPED")
        self.logger.info(f"   • Total timesheets generated during session: {self.total_timesheets_generated}")
        
        self.monitoring_status.emit("🛑 Background monitoring stopped")
    
    def discover_pending_workers(self):
        """Discover workers with active shifts by checking the database."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            
            # Find workers with incomplete shifts (clocked in but not out)
            c.execute("""
                SELECT DISTINCT cr.staff_code, s.name, s.role
                FROM clock_records cr
                JOIN staff s ON cr.staff_code = s.code
                WHERE cr.clock_out_time IS NULL
                ORDER BY s.name
            """)
            
            active_workers = c.fetchall()
            conn.close()
            
            self.pending_workers = {staff_code for staff_code, _, _ in active_workers}
            
            # Initialize status tracking
            for staff_code, name, role in active_workers:
                self.worker_last_status[staff_code] = {
                    'name': name,
                    'role': role,
                    'last_check': datetime.datetime.now(),
                    'shift_start': None
                }
            
            self.logger.info(f"🔍 Discovered {len(active_workers)} workers with active shifts:")
            for staff_code, name, role in active_workers:
                self.logger.info(f"   • {name} ({staff_code}) - {role}")
                
        except Exception as e:
            self.logger.error(f"❌ Error discovering pending workers: {e}")
            self.error_occurred.emit("discovery_error", str(e))
    
    def check_pending_workers(self):
        """
        Check all pending workers to see if any have clocked out.
        This is called periodically by the timer.
        """
        if not self.monitoring_active or not self.pending_workers:
            return
        
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            
            newly_completed = []
            
            for staff_code in list(self.pending_workers):
                worker_info = self.worker_last_status.get(staff_code, {})
                name = worker_info.get('name', 'Unknown')
                
                # Check if worker has completed their shift
                if self.check_worker_completed(c, staff_code):
                    self.logger.info(f"🎉 {name} ({staff_code}) has clocked out!")
                    
                    # Generate timesheet immediately
                    success = self.generate_timesheet_for_worker(c, staff_code, worker_info)
                    
                    if success:
                        self.logger.info(f"✅ Timesheet automatically generated for {name}")
                        self.total_timesheets_generated += 1
                        self.timesheet_generated.emit(staff_code, name, True)
                    else:
                        self.logger.error(f"❌ Failed to generate timesheet for {name}")
                        self.timesheet_generated.emit(staff_code, name, False)
                    
                    # Remove from pending list
                    newly_completed.append((staff_code, name))
                    self.pending_workers.remove(staff_code)
                    
                    # Emit signal for UI updates
                    timesheet_info = {
                        'completion_time': datetime.datetime.now().isoformat(),
                        'timesheet_generated': success
                    }
                    self.worker_clocked_out.emit(staff_code, name, timesheet_info)
                
                else:
                    # Still active - update status
                    hours_worked = self.calculate_hours_worked_so_far(c, staff_code)
                    if hours_worked > 0:
                        self.logger.debug(f"⏳ {name} still working - {hours_worked:.1f}h so far")
            
            conn.close()
            
            if newly_completed:
                completed_names = [name for _, name in newly_completed]
                self.logger.info(f"🎊 {len(newly_completed)} workers completed: {', '.join(completed_names)}")
                self.monitoring_status.emit(f"🎉 Generated timesheets for {len(newly_completed)} workers")
            
            # Check if we should continue monitoring
            if not self.pending_workers:
                self.logger.info("✅ All workers have completed their shifts - stopping background monitoring")
                self.stop_monitoring()
                self.monitoring_status.emit("✅ All workers completed - monitoring stopped")
            else:
                active_count = len(self.pending_workers)
                self.monitoring_status.emit(f"🔄 Monitoring {active_count} active workers")
                
        except Exception as e:
            self.logger.error(f"❌ Error checking pending workers: {e}")
            self.error_occurred.emit("monitoring_error", str(e))
    
    def check_worker_completed(self, cursor, staff_code: str) -> bool:
        """Check if a worker has completed their current shift."""
        try:
            # Look for incomplete records for this worker (any age)
            cursor.execute("""
                SELECT COUNT(*)
                FROM clock_records
                WHERE staff_code = ? 
                AND clock_out_time IS NULL
            """, (staff_code,))
            
            incomplete_count = cursor.fetchone()[0]
            return incomplete_count == 0  # True if no incomplete records
            
        except Exception as e:
            self.logger.error(f"Error checking completion status for {staff_code}: {e}")
            return False
    
    def calculate_hours_worked_so_far(self, cursor, staff_code: str) -> float:
        """Calculate hours worked so far for active workers."""
        try:
            cursor.execute("""
                SELECT clock_in_time
                FROM clock_records
                WHERE staff_code = ? 
                AND clock_out_time IS NULL
                ORDER BY clock_in_time DESC
                LIMIT 1
            """, (staff_code,))
            
            result = cursor.fetchone()
            if result:
                clock_in_time = datetime.datetime.fromisoformat(result[0])
                hours_so_far = (datetime.datetime.now() - clock_in_time).total_seconds() / 3600
                return max(0, hours_so_far)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error calculating hours for {staff_code}: {e}")
            return 0
    
    def generate_timesheet_for_worker(self, cursor, staff_code: str, worker_info: Dict) -> bool:
        """Generate timesheet for a worker who just completed their shift."""
        try:
            from progressive_timesheet_generator import ProgressiveTimesheetGenerator
            
            # Calculate timesheet date range
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)  # Last 30 days
            
            # Create a temporary generator instance for timesheet creation
            temp_generator = ProgressiveTimesheetGenerator(self.database_path, start_date, end_date)
            
            # Get worker status
            worker_status = temp_generator.check_worker_completion_status(
                cursor, staff_code, worker_info.get('name', 'Unknown'), worker_info.get('role', 'Unknown')
            )
            
            # Generate the timesheet
            success = temp_generator.generate_single_timesheet(staff_code, worker_status)
            
            if success:
                self.logger.info(f"📄 Timesheet generated for {worker_info.get('name')} - {worker_status.get('total_hours', 0):.2f}h")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Error generating timesheet for {staff_code}: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status."""
        return {
            'active': self.monitoring_active,
            'pending_workers': len(self.pending_workers),
            'total_generated': self.total_timesheets_generated,
            'check_interval': self.check_interval,
            'worker_list': list(self.pending_workers)
        }


# Global monitor instance
_background_monitor = None


def start_background_monitoring(database_path: str, pending_workers: Set[str] = None, check_interval: int = 30):
    """
    Start the global background timesheet monitoring service.
    
    Args:
        database_path: Path to the staff database
        pending_workers: Set of staff codes to monitor initially
        check_interval: Check interval in seconds (default 30)
    """
    global _background_monitor
    
    if _background_monitor and _background_monitor.monitoring_active:
        logging.info("Background monitoring already running")
        return _background_monitor
    
    _background_monitor = BackgroundTimesheetMonitor(database_path, check_interval)
    _background_monitor.start_monitoring(pending_workers)
    
    logging.info(f"🚀 Global background timesheet monitoring started")
    return _background_monitor


def stop_background_monitoring():
    """Stop the global background timesheet monitoring service."""
    global _background_monitor
    
    if _background_monitor:
        _background_monitor.stop_monitoring()
        _background_monitor = None
        logging.info("🛑 Global background timesheet monitoring stopped")


def get_background_monitor():
    """Get the current background monitor instance."""
    return _background_monitor


if __name__ == "__main__":
    """Test the background monitoring service."""
    import sys
    
    app = QApplication(sys.argv)
    
    # Test with the production database
    monitor = start_background_monitoring("ProgramData/staff_hours.db")
    
    if monitor:
        print("🚀 Background monitoring test started")
        print("Monitor will check for worker completions every 30 seconds")
        print("Press Ctrl+C to stop")
        
        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            print("\n🛑 Stopping background monitoring...")
            stop_background_monitoring()
    else:
        print("❌ Failed to start background monitoring") 