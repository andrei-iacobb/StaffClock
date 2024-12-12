from datetime import datetime, timedelta
from PyQt6.QtWidgets import QMessageBox
import os
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

class TimeSheetGenerator:
    def get_date_range_for_timesheet(self, day_selected):
        today = datetime.now()
        if today.day < day_selected:
            end_date = today.replace(day=day_selected) - timedelta(days=30)
        else:
            end_date = today.replace(day=day_selected)

        start_date = end_date.replace(day=21) - timedelta(days=30)
        return start_date, end_date

    def fetch_timesheet_records(self, conn, start_date, end_date):
        c = conn.cursor()
        c.execute("""
            SELECT s.name, s.role, c.clock_in_time, c.clock_out_time
            FROM staff s
            LEFT JOIN clock_records c ON s.code = c.staff_code
            WHERE DATE(c.clock_in_time) BETWEEN ? AND ?
            ORDER BY s.role, s.name, c.clock_in_time
        """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        records = c.fetchall()
        return records

    def generate_all_timesheets(self, day_selected):
        # Get date range
        start_date, end_date = self.get_date_range_for_timesheet(day_selected)

        # Fetch records
        conn = sqlite3.connect('staff_hours.db')
        records = self.fetch_timesheet_records(conn, start_date, end_date)
        conn.close()

        if not records:
            QMessageBox.information(self, "Info", "No records found for the selected period.")
            return

        # Organize records by staff
        staff_data = {}
        for name, role, clock_in, clock_out in records:
            if name not in staff_data:
                staff_data[name] = {"role": role, "records": []}
            staff_data[name]["records"].append((clock_in, clock_out))

        # Generate timesheets for all staff
        for staff_name, details in staff_data.items():
            self.generate_timesheet(staff_name, details["role"], start_date, end_date, details["records"])

        QMessageBox.information(
            self,
            "Success",
            f"Timesheets generated for the period {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"
        )

    def generate_timesheet(self, employee_name, role, start_date, end_date, records):
        # Create the PDF file path
        os.makedirs("Timesheets", exist_ok=True)
        output_file = f"Timesheets/{employee_name.replace(' ', '_')}_timesheet.pdf"

        # Create the PDF document
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

        # Table header
        data = [
            ["Date", "Day", "Clock In", "Clock Out", "Hours Worked", "Notes"]
        ]

        # Add rows for each day
        for record in records:
            clock_in = datetime.fromisoformat(record[0]) if record[0] else None
            clock_out = datetime.fromisoformat(record[1]) if record[1] else None
            hours_worked = (
                (clock_out - clock_in).total_seconds() / 3600 if clock_in and clock_out else ""
            )
            data.append([
                clock_in.strftime('%d-%m-%Y') if clock_in else '',
                clock_in.strftime('%A') if clock_in else '',
                clock_in.strftime('%H:%M') if clock_in else '',
                clock_out.strftime('%H:%M') if clock_out else '',
                f"{hours_worked:.2f}" if hours_worked else '',
                ""
            ])

        # Add totals row
        data.append(["Totals"] + [""] * 5)

        # Create the table
        table = Table(data, colWidths=[70, 70, 70, 70, 70, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        # Footer
        footer_lines = [
            "Checked by Administrator: ……………………………………………………….. Signed         ………………………………….. Date",
            "Checked by Manager:           ……………………………………………………….. Signed       ……………………………………. Date"
        ]
        elements.append(Spacer(1, 40))
        for line in footer_lines:
            elements.append(Paragraph(line, getSampleStyleSheet()['Normal']))

        # Build the PDF
        doc.build(elements)
