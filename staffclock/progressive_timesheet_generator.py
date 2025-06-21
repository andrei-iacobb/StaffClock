#!/usr/bin/env python3
"""
Progressive Timesheet Generation System
======================================

Smart timesheet generation that processes completed workers immediately,
monitors active workers, and generates their timesheets as they complete shifts.

Features:
- Real-time progress tracking with cool loading animations
- Individual worker status monitoring
- Safe handling of incomplete shifts
- Automatic completion as workers clock out
- Visual feedback in admin interface

Author: StaffClock Progressive System
Date: December 2024
"""

import sqlite3
import datetime
import time
import threading
import json
import logging
from typing import List, Dict, Tuple, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QMutex
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QProgressBar, QListWidget, 
                            QListWidgetItem, QWidget, QTextEdit, QScrollArea)
from PyQt6.QtGui import QFont, QMovie, QPalette, QColor
from PyQt6.QtCore import Qt
import os

class ProgressiveTimesheetGenerator(QThread):
    # Signals for UI updates
    worker_completed = pyqtSignal(str, str, dict)  # worker_name, status, details
    worker_pending = pyqtSignal(str, str, dict)    # worker_name, status, details
    generation_progress = pyqtSignal(int, int)     # completed, total
    all_completed = pyqtSignal(dict)               # final summary
    status_update = pyqtSignal(str)                # general status messages
    
    def __init__(self, database_path: str, start_date: datetime.datetime, end_date: datetime.datetime):
        super().__init__()
        self.database_path = database_path
        self.start_date = start_date
        self.end_date = end_date
        self.running = True
        self.completed_workers = set()
        self.pending_workers = set()
        self.worker_status = {}
        self.generation_stats = {
            'total_workers': 0,
            'completed': 0,
            'pending': 0,
            'hours_generated': 0,
            'start_time': datetime.datetime.now()
        }
        
    def run(self):
        """Main generation loop with real-time monitoring."""
        try:
            self.status_update.emit("🚀 Starting Progressive Timesheet Generation...")
            
            # Phase 1: Analyze all workers and their status
            self.analyze_all_workers()
            
            # Phase 2: Generate timesheets for completed workers
            self.generate_completed_timesheets()
            
            # Phase 3: Monitor and generate for pending workers
            self.monitor_pending_workers()
            
        except Exception as e:
            self.status_update.emit(f"❌ Error in generation: {e}")
            logging.error(f"Progressive timesheet generation error: {e}")
    
    def analyze_all_workers(self):
        """Analyze all workers and categorize by completion status."""
        try:
            conn = sqlite3.connect(self.database_path)
            c = conn.cursor()
            
            # Get all staff members
            c.execute("SELECT code, name, role FROM staff ORDER BY name")
            all_staff = c.fetchall()
            self.generation_stats['total_workers'] = len(all_staff)
            
            self.status_update.emit(f"📊 Analyzing {len(all_staff)} workers...")
            logging.info(f"🔍 WORKER ANALYSIS STARTED")
            logging.info(f"   • Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
            logging.info(f"   • Total staff to analyze: {len(all_staff)}")
            
            analysis_counters = {
                'workers_with_records': 0,
                'workers_without_records': 0,
                'completed_workers': 0,
                'pending_workers': 0,
                'workers_with_errors': 0,
                'total_hours_found': 0
            }
            
            for code, name, role in all_staff:
                try:
                    status = self.check_worker_completion_status(c, code, name, role)
                    self.worker_status[code] = status
                    
                    # Log detailed analysis for each worker
                    if 'error' in status:
                        analysis_counters['workers_with_errors'] += 1
                        logging.error(f"❌ {name} ({code}): Analysis error - {status['error']}")
                        self.worker_completed.emit(name, "❌ Analysis Error", status)
                        continue
                    
                    records_count = status.get('total_records', 0)
                    hours = status.get('total_hours', 0)
                    analysis_counters['total_hours_found'] += hours
                    
                    if records_count == 0:
                        analysis_counters['workers_without_records'] += 1
                        logging.info(f"📭 {name} ({code}): No records in timesheet period")
                        self.completed_workers.add(code)  # No records = ready for empty timesheet
                        self.worker_completed.emit(name, "📭 No Records", status)
                    elif status['completed']:
                        analysis_counters['workers_with_records'] += 1
                        analysis_counters['completed_workers'] += 1
                        self.completed_workers.add(code)
                        logging.info(f"✅ {name} ({code}): Ready - {status['completed_records']} complete shifts, {hours:.2f}h total")
                        self.worker_completed.emit(name, "✅ Ready for generation", status)
                    else:
                        analysis_counters['workers_with_records'] += 1
                        analysis_counters['pending_workers'] += 1
                        self.pending_workers.add(code)
                        active_shifts = status.get('active_incomplete', 0)
                        incomplete_shifts = status.get('incomplete_records', 0)
                        logging.info(f"⏳ {name} ({code}): Pending - {active_shifts} active shifts, {incomplete_shifts} total incomplete")
                        self.worker_pending.emit(name, f"⏳ {incomplete_shifts} incomplete shifts", status)
                        
                except Exception as worker_error:
                    analysis_counters['workers_with_errors'] += 1
                    logging.error(f"❌ {name} ({code}): Worker analysis failed - {worker_error}")
                    error_status = {'name': name, 'role': role, 'staff_code': code, 'error': str(worker_error)}
                    self.worker_status[code] = error_status
                    self.worker_completed.emit(name, "❌ Analysis Failed", error_status)
            
            conn.close()
            
            # Log comprehensive analysis summary
            logging.info(f"📊 WORKER ANALYSIS COMPLETE:")
            logging.info(f"   • Total workers: {len(all_staff)}")
            logging.info(f"   • Workers with records: {analysis_counters['workers_with_records']}")
            logging.info(f"   • Workers without records: {analysis_counters['workers_without_records']}")
            logging.info(f"   • Ready for generation: {analysis_counters['completed_workers']}")
            logging.info(f"   • Pending (active shifts): {analysis_counters['pending_workers']}")
            logging.info(f"   • Analysis errors: {analysis_counters['workers_with_errors']}")
            logging.info(f"   • Total hours found: {analysis_counters['total_hours_found']:.2f}")
            
            self.generation_stats['completed'] = len(self.completed_workers)
            self.generation_stats['pending'] = len(self.pending_workers)
            
            self.generation_progress.emit(0, self.generation_stats['total_workers'])
            self.status_update.emit(f"📋 Analysis complete: {len(self.completed_workers)} ready, {len(self.pending_workers)} pending")
            
        except Exception as e:
            logging.error(f"❌ WORKER ANALYSIS FAILED: {e}")
            self.status_update.emit(f"❌ Analysis failed: {e}")
            raise e
    
    def check_worker_completion_status(self, cursor, staff_code: str, name: str, role: str) -> Dict:
        """Check if a worker has completed all their shifts for the timesheet period."""
        try:
            # Get all clock records for this worker in the period
            cursor.execute("""
                SELECT id, clock_in_time, clock_out_time, break_time, notes
                FROM clock_records
                WHERE staff_code = ? AND DATE(clock_in_time) BETWEEN ? AND ?
                ORDER BY clock_in_time
            """, (staff_code, self.start_date.strftime('%Y-%m-%d'), self.end_date.strftime('%Y-%m-%d')))
            
            records = cursor.fetchall()
            
            if not records:
                return {
                    'completed': True,
                    'name': name,
                    'role': role,
                    'staff_code': staff_code,
                    'total_records': 0,
                    'incomplete_records': 0,
                    'total_hours': 0,
                    'status_reason': 'No records in period'
                }
            
            # Analyze completion status
            incomplete_records = []
            completed_records = []
            total_hours = 0
            
            for record_id, clock_in, clock_out, break_time, notes in records:
                if clock_in and not clock_out:
                    # Check if this is a current active shift
                    clock_in_dt = datetime.datetime.fromisoformat(clock_in)
                    hours_so_far = (datetime.datetime.now() - clock_in_dt).total_seconds() / 3600
                    
                    incomplete_records.append({
                        'record_id': record_id,
                        'clock_in': clock_in,
                        'hours_so_far': hours_so_far,
                        'is_current': True  # If clock_out is NULL, this is ALWAYS an active shift regardless of age
                    })
                elif clock_in and clock_out:
                    # Complete record
                    clock_in_dt = datetime.datetime.fromisoformat(clock_in)
                    clock_out_dt = datetime.datetime.fromisoformat(clock_out)
                    hours = (clock_out_dt - clock_in_dt).total_seconds() / 3600
                    total_hours += hours
                    completed_records.append({
                        'record_id': record_id,
                        'clock_in': clock_in,
                        'clock_out': clock_out,
                        'hours': hours
                    })
            
            # Determine if worker is completed (no active incomplete shifts)
            active_incomplete = [r for r in incomplete_records if r['is_current']]
            
            return {
                'completed': len(active_incomplete) == 0,
                'name': name,
                'role': role,
                'staff_code': staff_code,
                'total_records': len(records),
                'incomplete_records': len(incomplete_records),
                'active_incomplete': len(active_incomplete),
                'completed_records': len(completed_records),
                'total_hours': total_hours,
                'status_reason': 'All shifts complete' if len(active_incomplete) == 0 else f'{len(active_incomplete)} active shifts',
                'incomplete_details': incomplete_records,
                'completed_details': completed_records
            }
            
        except Exception as e:
            return {
                'completed': False,
                'name': name,
                'role': role,
                'staff_code': staff_code,
                'error': str(e)
            }
    
    def generate_completed_timesheets(self):
        """Generate timesheets for all completed workers."""
        if not self.completed_workers:
            self.status_update.emit("ℹ️ No completed workers to process")
            logging.info("ℹ️ No completed workers found for timesheet generation")
            return
        
        self.status_update.emit(f"🏗️ Generating timesheets for {len(self.completed_workers)} completed workers...")
        logging.info(f"🏗️ TIMESHEET GENERATION STARTED for {len(self.completed_workers)} workers")
        
        generation_counters = {
            'successful': 0,
            'failed_no_records': 0,
            'failed_pdf_error': 0,
            'failed_database_error': 0,
            'failed_other': 0
        }
        
        for staff_code in self.completed_workers:
            if not self.running:
                logging.info("🛑 Generation stopped by user")
                break
                
            try:
                status = self.worker_status[staff_code]
                name = status.get('name', 'Unknown')
                
                # Detailed generation attempt
                success, failure_reason = self.generate_single_timesheet_with_diagnostics(staff_code, status)
                
                if success:
                    generation_counters['successful'] += 1
                    hours = status.get('total_hours', 0)
                    records = status.get('completed_records', 0)
                    logging.info(f"✅ {name} ({staff_code}): Timesheet generated successfully - {records} records, {hours:.2f}h")
                    
                    self.worker_completed.emit(
                        name, 
                        "✅ Timesheet Generated", 
                        {**status, 'generated': True, 'generation_time': datetime.datetime.now().isoformat()}
                    )
                    self.generation_stats['hours_generated'] += hours
                else:
                    # Categorize failure type
                    if 'no records' in failure_reason.lower():
                        generation_counters['failed_no_records'] += 1
                    elif 'pdf' in failure_reason.lower():
                        generation_counters['failed_pdf_error'] += 1
                    elif 'database' in failure_reason.lower():
                        generation_counters['failed_database_error'] += 1
                    else:
                        generation_counters['failed_other'] += 1
                    
                    logging.error(f"❌ {name} ({staff_code}): Generation failed - {failure_reason}")
                    self.worker_completed.emit(
                        name, 
                        f"❌ Failed: {failure_reason}", 
                        {**status, 'generated': False, 'failure_reason': failure_reason}
                    )
                
                self.generation_progress.emit(generation_counters['successful'], len(self.completed_workers))
                time.sleep(0.1)  # Small delay for smooth UI updates
                
            except Exception as e:
                generation_counters['failed_other'] += 1
                name = self.worker_status.get(staff_code, {}).get('name', 'Unknown')
                logging.error(f"❌ {name} ({staff_code}): Unexpected generation error - {e}")
                self.status_update.emit(f"❌ Failed to generate for {staff_code}: {e}")
        
        # Log generation summary
        total_processed = sum(generation_counters.values())
        logging.info(f"🏁 TIMESHEET GENERATION COMPLETE:")
        logging.info(f"   • Total processed: {total_processed}")
        logging.info(f"   • Successful: {generation_counters['successful']}")
        logging.info(f"   • Failed (no records): {generation_counters['failed_no_records']}")
        logging.info(f"   • Failed (PDF error): {generation_counters['failed_pdf_error']}")
        logging.info(f"   • Failed (database error): {generation_counters['failed_database_error']}")
        logging.info(f"   • Failed (other): {generation_counters['failed_other']}")
        logging.info(f"   • Success rate: {(generation_counters['successful']/total_processed*100):.1f}%" if total_processed > 0 else "   • Success rate: N/A")
        
        self.status_update.emit(f"✅ Generated {generation_counters['successful']} timesheets for completed workers")
    
    def generate_single_timesheet_with_diagnostics(self, staff_code: str, worker_status: Dict) -> tuple[bool, str]:
        """Generate timesheet for a single worker with detailed failure diagnostics."""
        try:
            name = worker_status.get('name', 'Unknown')
            
            # Check if worker has any error from analysis
            if 'error' in worker_status:
                return False, f"Worker analysis error: {worker_status['error']}"
            
            # Check for minimum requirements
            total_records = worker_status.get('total_records', 0)
            if total_records == 0:
                # For workers with no records, we can still generate an empty timesheet
                try:
                    self.generate_pdf_timesheet(
                        name, 
                        worker_status.get('role', 'Unknown'), 
                        self.start_date, 
                        self.end_date, 
                        []  # Empty records
                    )
                    return True, "Empty timesheet generated successfully"
                except Exception as pdf_error:
                    return False, f"PDF generation failed for empty timesheet: {pdf_error}"
            
            # Get timesheet records from database
            try:
                conn = sqlite3.connect(self.database_path)
                c = conn.cursor()
                
                c.execute("""
                    SELECT clock_in_time, clock_out_time
                    FROM clock_records
                    WHERE staff_code = ? AND clock_out_time IS NOT NULL 
                    AND DATE(clock_in_time) BETWEEN ? AND ?
                    ORDER BY clock_in_time
                """, (staff_code, self.start_date.strftime('%Y-%m-%d'), self.end_date.strftime('%Y-%m-%d')))
                
                records = c.fetchall()
                conn.close()
                
                if not records:
                    return False, f"No complete records found in database for date range {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                
                # Generate PDF timesheet
                try:
                    self.generate_pdf_timesheet(
                        name, 
                        worker_status.get('role', 'Unknown'), 
                        self.start_date, 
                        self.end_date, 
                        records
                    )
                    
                    hours = worker_status.get('total_hours', 0)
                    return True, f"Timesheet generated: {len(records)} records, {hours:.2f} hours"
                    
                except Exception as pdf_error:
                    return False, f"PDF generation failed: {str(pdf_error)}"
                
            except Exception as db_error:
                return False, f"Database error: {str(db_error)}"
            
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def generate_single_timesheet(self, staff_code: str, worker_status: Dict) -> bool:
        """Generate timesheet for a single worker (legacy method for compatibility)."""
        success, _ = self.generate_single_timesheet_with_diagnostics(staff_code, worker_status)
        return success

    def generate_pdf_timesheet(self, employee_name: str, role: str, start_date: datetime.datetime, 
                              end_date: datetime.datetime, records: List):
        """Generate PDF timesheet using the production logic."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from datetime import datetime as dt
            
            # Create output directory
            timesheets_dir = "Timesheets"
            os.makedirs(timesheets_dir, exist_ok=True)
            
            # Clean filename for cross-platform compatibility
            safe_name = "".join(c for c in employee_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_file = os.path.join(timesheets_dir, f"{safe_name}_timesheet.pdf")
            
            logging.info(f"📄 Generating PDF timesheet for {employee_name} ({len(records)} records)")
            
            # Create PDF document
            doc = SimpleDocTemplate(output_file, pagesize=A4)
            elements = []
            
            # Header
            title = f"The Partnership in Care\nMONTHLY TIMESHEET"
            name_line = f"NAME: {employee_name}"
            role_line = f"ROLE: {role}"
            date_line = f"DATE: {start_date.strftime('%d %B')} to {end_date.strftime('%d %B')} {end_date.year}"
            signed_line = "SIGNED: ……………………………………………………….."
            
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(title, getSampleStyleSheet()['Title']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(name_line, getSampleStyleSheet()['Normal']))
            elements.append(Paragraph(role_line, getSampleStyleSheet()['Normal']))
            elements.append(Paragraph(date_line, getSampleStyleSheet()['Normal']))
            elements.append(Spacer(1, 40))
            elements.append(Paragraph(signed_line, getSampleStyleSheet()['Normal']))
            elements.append(Spacer(1, 20))
            
            # Table data
            data = [["Date", "Day", "Clock In", "Clock Out", "Hours Worked", "Notes"]]
            total_hours = 0
            
            if not records:
                # Empty timesheet
                data.append(["No records found", "in period", "", "", "0.00", ""])
                logging.info(f"📋 Empty timesheet generated for {employee_name}")
            else:
                # Process records
                for clock_in_str, clock_out_str in records:
                    try:
                        clock_in = dt.fromisoformat(clock_in_str)
                        clock_out = dt.fromisoformat(clock_out_str)
                        
                        # Calculate hours worked
                        duration = clock_out - clock_in
                        hours_worked = duration.total_seconds() / 3600
                        total_hours += hours_worked
                        
                        # Format data
                        date_str = clock_in.strftime('%d/%m/%Y')
                        day_str = clock_in.strftime('%A')
                        in_str = clock_in.strftime('%H:%M')
                        out_str = clock_out.strftime('%H:%M')
                        hours_str = f"{hours_worked:.2f}"
                        
                        data.append([date_str, day_str, in_str, out_str, hours_str, ""])
                        
                    except Exception as record_error:
                        logging.error(f"⚠️ Error processing record for {employee_name}: {record_error}")
                        data.append(["Error", "processing", "record", "", "0.00", str(record_error)[:20]])
            
            # Add total row
            data.append(["", "", "", "TOTAL HOURS:", f"{total_hours:.2f}", ""])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 40))
            
            # Build PDF
            doc.build(elements)
            
            # Verify file was created
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                logging.info(f"✅ PDF timesheet saved: {output_file} ({file_size} bytes)")
            else:
                raise Exception("PDF file was not created successfully")
                
        except ImportError as import_error:
            raise Exception(f"Missing required library for PDF generation: {import_error}")
        except Exception as pdf_error:
            logging.error(f"❌ PDF generation error for {employee_name}: {pdf_error}")
            raise Exception(f"PDF generation failed: {pdf_error}")
    
    def monitor_pending_workers(self):
        """Continuously monitor pending workers and generate timesheets as they complete."""
        if not self.pending_workers:
            self.all_completed.emit(self.generation_stats)
            return
        
        self.status_update.emit(f"👀 Monitoring {len(self.pending_workers)} workers with active shifts...")
        logging.info(f"👀 MONITORING PHASE STARTED for {len(self.pending_workers)} workers with active shifts")
        
        check_interval = 30  # Check every 30 seconds
        while self.running and self.pending_workers:
            time.sleep(check_interval)
            
            if not self.running:
                break
            
            # Re-check status of pending workers
            newly_completed = []
            
            try:
                conn = sqlite3.connect(self.database_path)
                c = conn.cursor()
                
                for staff_code in list(self.pending_workers):
                    current_status = self.worker_status[staff_code]
                    updated_status = self.check_worker_completion_status(
                        c, staff_code, current_status['name'], current_status['role']
                    )
                    
                    if updated_status['completed'] and not current_status['completed']:
                        # Worker just completed their shift!
                        newly_completed.append(staff_code)
                        self.worker_status[staff_code] = updated_status
                        
                        # Generate their timesheet immediately
                        success = self.generate_single_timesheet(staff_code, updated_status)
                        
                        if success:
                            self.worker_completed.emit(
                                updated_status['name'],
                                "🎉 Just completed & generated!",
                                {**updated_status, 'generated': True, 'completion_time': datetime.datetime.now().isoformat()}
                            )
                            self.generation_stats['hours_generated'] += updated_status.get('total_hours', 0)
                        else:
                            self.worker_completed.emit(
                                updated_status['name'],
                                "⚠️ Completed but generation failed",
                                {**updated_status, 'generated': False}
                            )
                        
                        self.pending_workers.remove(staff_code)
                        self.completed_workers.add(staff_code)
                        
                        current_completed = len(self.completed_workers)
                        self.generation_progress.emit(current_completed, self.generation_stats['total_workers'])
                    
                    elif not updated_status['completed']:
                        # Update pending status
                        self.worker_status[staff_code] = updated_status
                        hours_in_progress = sum(r['hours_so_far'] for r in updated_status.get('incomplete_details', []) if r['is_current'])
                        self.worker_pending.emit(
                            updated_status['name'],
                            f"⏳ {hours_in_progress:.1f}h in progress",
                            updated_status
                        )
                
                conn.close()
                
                if newly_completed:
                    self.status_update.emit(f"🎉 {len(newly_completed)} workers just completed their shifts!")
                
            except Exception as e:
                self.status_update.emit(f"❌ Error monitoring workers: {e}")
        
        # All workers completed
        self.generation_stats['completion_time'] = datetime.datetime.now()
        self.generation_stats['total_duration'] = (
            self.generation_stats['completion_time'] - self.generation_stats['start_time']
        ).total_seconds()
        
        # Start background monitoring for pending workers if any
        if self.pending_workers:
            logging.info(f"🔄 Starting background monitoring for {len(self.pending_workers)} pending workers")
            try:
                from .background_timesheet_monitor import start_background_monitoring
                
                # Start background monitoring for remaining workers
                background_monitor = start_background_monitoring(
                    self.database_path, 
                    self.pending_workers, 
                    check_interval=30
                )
                
                if background_monitor:
                    logging.info(f"✅ Background monitoring started for pending workers")
                    self.status_update.emit(f"🔄 Background monitoring started for {len(self.pending_workers)} workers")
                else:
                    logging.error("❌ Failed to start background monitoring")
                    
            except Exception as bg_error:
                logging.error(f"❌ Error starting background monitoring: {bg_error}")
        
        # Final comprehensive logging summary
        logging.info(f"🎊 PROGRESSIVE TIMESHEET GENERATION COMPLETE!")
        logging.info(f"📊 FINAL SUMMARY:")
        logging.info(f"   • Total workers processed: {self.generation_stats.get('total_workers', 0)}")
        logging.info(f"   • Initially completed: {self.generation_stats.get('completed', 0)}")
        logging.info(f"   • Initially pending: {self.generation_stats.get('pending', 0)}")
        logging.info(f"   • Total hours processed: {self.generation_stats.get('hours_generated', 0):.2f}")
        logging.info(f"   • Total duration: {self.generation_stats['total_duration']:.1f} seconds")
        logging.info(f"   • Average time per worker: {self.generation_stats['total_duration']/max(1, self.generation_stats.get('total_workers', 1)):.2f} seconds")
        
        # Check timesheets directory
        try:
            if os.path.exists("Timesheets"):
                pdf_files = [f for f in os.listdir("Timesheets") if f.endswith('.pdf')]
                logging.info(f"📁 Timesheets folder contains {len(pdf_files)} PDF files")
            else:
                logging.warning("📁 Timesheets folder not found")
        except Exception as dir_error:
            logging.error(f"📁 Error checking Timesheets directory: {dir_error}")
        
        self.all_completed.emit(self.generation_stats)
        
        if self.pending_workers:
            self.status_update.emit(f"✅ Immediate timesheets complete! 🔄 Background monitoring {len(self.pending_workers)} workers")
        else:
            self.status_update.emit("🎊 All timesheets generated successfully!")
    
    def stop(self):
        """Stop the monitoring process."""
        self.running = False


class ProgressiveTimesheetDialog(QDialog):
    """Cool UI dialog for progressive timesheet generation."""
    
    def __init__(self, database_path: str, start_date: datetime.datetime, end_date: datetime.datetime, parent=None):
        super().__init__(parent)
        self.database_path = database_path
        self.start_date = start_date
        self.end_date = end_date
        self.generator_thread = None
        
        self.setWindowTitle("🚀 Progressive Timesheet Generation")
        self.setFixedSize(800, 600)
        self.setup_ui()
        self.start_generation()
    
    def setup_ui(self):
        """Create the cool loading UI."""
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("🚀 Progressive Timesheet Generation")
        header_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(header_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: #ecf0f1;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Inter", 11))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; margin: 5px;")
        layout.addWidget(self.status_label)
        
        # Worker status area
        status_layout = QHBoxLayout()
        
        # Completed workers
        completed_widget = QWidget()
        completed_layout = QVBoxLayout(completed_widget)
        completed_title = QLabel("✅ Completed Workers")
        completed_title.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        completed_title.setStyleSheet("color: #27ae60;")
        completed_layout.addWidget(completed_title)
        
        self.completed_list = QListWidget()
        self.completed_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ecf0f1;
            }
        """)
        completed_layout.addWidget(self.completed_list)
        status_layout.addWidget(completed_widget)
        
        # Pending workers
        pending_widget = QWidget()
        pending_layout = QVBoxLayout(pending_widget)
        pending_title = QLabel("⏳ Workers in Progress")
        pending_title.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        pending_title.setStyleSheet("color: #f39c12;")
        pending_layout.addWidget(pending_title)
        
        self.pending_list = QListWidget()
        self.pending_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #fff3cd;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ffeaa7;
            }
        """)
        pending_layout.addWidget(self.pending_list)
        status_layout.addWidget(pending_widget)
        
        layout.addLayout(status_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("⏸️ Pause Monitoring")
        self.pause_button.setFont(QFont("Inter", 10))
        self.pause_button.clicked.connect(self.toggle_monitoring)
        button_layout.addWidget(self.pause_button)
        
        self.close_button = QPushButton("❌ Close")
        self.close_button.setFont(QFont("Inter", 10))
        self.close_button.clicked.connect(self.close_generation)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Detailed log area
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }
        """)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
    
    def start_generation(self):
        """Start the progressive generation process."""
        self.generator_thread = ProgressiveTimesheetGenerator(
            self.database_path, self.start_date, self.end_date
        )
        
        # Connect signals
        self.generator_thread.worker_completed.connect(self.on_worker_completed)
        self.generator_thread.worker_pending.connect(self.on_worker_pending)
        self.generator_thread.generation_progress.connect(self.on_progress_update)
        self.generator_thread.all_completed.connect(self.on_all_completed)
        self.generator_thread.status_update.connect(self.on_status_update)
        
        self.generator_thread.start()
    
    def on_worker_completed(self, name: str, status: str, details: Dict):
        """Handle worker completion update."""
        item_text = f"{name} - {status}"
        if 'total_hours' in details:
            item_text += f" ({details['total_hours']:.1f}h)"
        
        item = QListWidgetItem(item_text)
        if "Generated" in status:
            item.setBackground(QColor("#d5f4e6"))
        elif "Failed" in status:
            item.setBackground(QColor("#f8d7da"))
        
        self.completed_list.addItem(item)
        self.log_area.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {name}: {status}")
    
    def on_worker_pending(self, name: str, status: str, details: Dict):
        """Handle worker pending update."""
        item_text = f"{name} - {status}"
        if 'incomplete_details' in details:
            active_shifts = len([r for r in details['incomplete_details'] if r['is_current']])
            if active_shifts > 0:
                item_text += f" ({active_shifts} active shifts)"
        
        # Update or add to pending list
        for i in range(self.pending_list.count()):
            item = self.pending_list.item(i)
            if item.text().startswith(name):
                item.setText(item_text)
                return
        
        item = QListWidgetItem(item_text)
        item.setBackground(QColor("#fff3cd"))
        self.pending_list.addItem(item)
    
    def on_progress_update(self, completed: int, total: int):
        """Update progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(completed)
        self.progress_bar.setFormat(f"{completed}/{total} workers processed ({(completed/total)*100:.1f}%)")
    
    def on_all_completed(self, stats: Dict):
        """Handle completion of all timesheets."""
        self.status_label.setText("🎊 All timesheets generated successfully!")
        self.pause_button.setText("✅ Completed")
        self.pause_button.setEnabled(False)
        
        duration = stats.get('total_duration', 0)
        self.log_area.append(f"\n=== GENERATION COMPLETE ===")
        self.log_area.append(f"Total workers: {stats.get('total_workers', 0)}")
        self.log_area.append(f"Total hours processed: {stats.get('hours_generated', 0):.2f}")
        self.log_area.append(f"Duration: {duration:.1f} seconds")
    
    def on_status_update(self, message: str):
        """Handle general status updates."""
        self.status_label.setText(message)
        self.log_area.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
        self.log_area.ensureCursorVisible()
    
    def toggle_monitoring(self):
        """Toggle monitoring pause/resume."""
        if self.generator_thread and self.generator_thread.running:
            self.generator_thread.stop()
            self.pause_button.setText("▶️ Resume Monitoring")
        else:
            self.start_generation()
            self.pause_button.setText("⏸️ Pause Monitoring")
    
    def close_generation(self):
        """Close the generation dialog."""
        if self.generator_thread:
            self.generator_thread.stop()
            self.generator_thread.wait()
        self.close()


def get_timesheet_date_range(database_path: str) -> tuple[datetime.datetime, datetime.datetime]:
    """
    Calculates the timesheet date range.
    Prioritizes the actual date range of data in the database,
    with a fallback to the traditional monthly calculation.
    """
    try:
        conn = sqlite3.connect(database_path)
        c = conn.cursor()
        
        c.execute("SELECT MIN(DATE(clock_in_time)), MAX(DATE(clock_in_time)) FROM clock_records")
        date_range = c.fetchone()
        conn.close()
        
        if date_range and date_range[0] and date_range[1]:
            start_date = datetime.datetime.strptime(date_range[0], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(date_range[1], '%Y-%m-%d') + datetime.timedelta(days=1)
            return start_date, end_date
    except Exception as e:
        logging.warning(f"Could not determine date range from database, using fallback. Error: {e}")

    # Fallback to traditional calculation
    today = datetime.datetime.now()
    start_day = 21
    
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    
    start_date = datetime.datetime(prev_year, prev_month, start_day)
    end_date = today
    return start_date, end_date


# Integration function for main.py
def start_progressive_timesheet_generation(database_path: str, parent_window=None) -> QDialog:
    """
    Start progressive timesheet generation with cool UI.
    
    Args:
        database_path: Path to the staff database
        parent_window: Parent window for the dialog
    
    Returns:
        QDialog: The progressive generation dialog
    """
    # Calculate timesheet date range
    start_date, end_date = get_timesheet_date_range(database_path)
    
    # Create and show the progressive generation dialog
    dialog = ProgressiveTimesheetDialog(database_path, start_date, end_date, parent_window)
    dialog.show()
    
    return dialog


if __name__ == "__main__":
    """Test the progressive generation system."""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test with the production database
    db_path = os.path.join("ProgramData", "staff_hours.db")
    dialog = start_progressive_timesheet_generation(db_path)
    
    sys.exit(app.exec()) 