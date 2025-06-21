import os
import logging
from datetime import datetime
from typing import List, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

class PDFGenerator:
    def __init__(self, temp_path: str, permanent_path: str):
        self.temp_path = temp_path
        self.permanent_path = permanent_path
        self.styles = getSampleStyleSheet()

    def generate_timesheet(self, employee_name: str, role: str, start_date: datetime, 
                         end_date: datetime, records: List[Tuple]) -> str:
        """Generate a timesheet PDF for an employee."""
        output_file = os.path.join(self.permanent_path, f"{employee_name}_timesheet.pdf")
        doc = SimpleDocTemplate(output_file, pagesize=A4)
        elements = []

        # Add header
        title = f"The Partnership in Care\nMONTHLY TIMESHEET"
        elements.extend([
            Spacer(1, 20),
            Paragraph(title, self.styles['Title']),
            Spacer(1, 20),
            Paragraph(f"NAME: {employee_name}", self.styles['Normal']),
            Paragraph(f"ROLE: {role}", self.styles['Normal']),
            Paragraph(f"DATE: {start_date.strftime('%d %B')} to {end_date.strftime('%d %B %Y')}", 
                     self.styles['Normal']),
            Spacer(1, 40),
            Paragraph("SIGNED: ……………………………………………………….", self.styles['Normal']),
            Spacer(1, 20)
        ])

        # Create table
        data = [["Date", "Day", "Clock In", "Clock Out", "Hours Worked", "Notes"]]
        
        for record in records:
            clock_in = datetime.fromisoformat(record[0]) if record[0] else None
            clock_out = datetime.fromisoformat(record[1]) if record[1] else None
            
            hours_worked = ""
            if clock_in and clock_out:
                hours_worked = f"{(clock_out - clock_in).total_seconds() / 3600:.2f}"

            data.append([
                clock_in.strftime('%d-%m-%Y') if clock_in else '',
                clock_in.strftime('%A') if clock_in else '',
                clock_in.strftime('%H:%M') if clock_in else '',
                clock_out.strftime('%H:%M') if clock_out else '',
                hours_worked,
                ""
            ])

        # Add totals row
        data.append(["Totals"] + [""] * 5)

        # Create and style the table
        table = Table(data, colWidths=[70, 70, 70, 70, 70, 100])
        table.setStyle(self._get_table_style())
        elements.append(table)

        # Add footer
        elements.extend([
            Spacer(1, 40),
            Paragraph("Checked by Administrator: ……………………………………………………….. Signed         ………………………………….. Date",
                     self.styles['Normal']),
            Paragraph("           ", self.styles['Normal']),
            Paragraph("Checked by Manager:           ……………………………………………………….. Signed       ……………………………………. Date",
                     self.styles['Normal'])
        ])

        # Build the PDF
        doc.build(elements)
        logging.info(f"Generated timesheet for {employee_name}")
        return output_file

    def generate_visitor_list(self, records: List[Tuple]) -> str:
        """Generate a PDF of visitor records."""
        output_file = os.path.join(self.temp_path, "visitors_temp.pdf")
        doc = SimpleDocTemplate(output_file, pagesize=A4)
        elements = []

        # Add title
        elements.extend([
            Paragraph("Visitor Records", self.styles['Title']),
            Spacer(1, 20)
        ])

        # Create table data
        data = [["Name", "Car Registration", "Purpose", "Time In", "Time Out"]]
        for record in records:
            name, car_reg, purpose = record[0], record[1], record[2]
            time_in = datetime.fromisoformat(record[3]).strftime('%H:%M %d/%m/%y') if record[3] else "N/A"
            time_out = datetime.fromisoformat(record[4]).strftime('%H:%M %d/%m/%y') if record[4] else "N/A"
            data.append([name, car_reg, purpose, time_in, time_out])

        # Create and style the table
        table = Table(data)
        table.setStyle(self._get_table_style())
        elements.append(table)

        # Add timestamp
        elements.extend([
            Spacer(1, 20),
            Paragraph(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                     self.styles['Normal'])
        ])

        # Build the PDF
        doc.build(elements)
        logging.info("Generated visitor list PDF")
        return output_file

    def generate_fire_list(self, staff_records: List[Tuple], visitor_records: List[Tuple]) -> str:
        """Generate a fire evacuation list PDF."""
        output_file = os.path.join(self.temp_path, "fire.pdf")
        doc = SimpleDocTemplate(output_file, pagesize=A4)
        elements = []

        # Add title and timestamp
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.extend([
            Paragraph("FIRE EVACUATION LIST", self.styles['Title']),
            Paragraph(f"Generated at: {current_time}", self.styles['Normal']),
            Spacer(1, 20)
        ])

        # Add staff section if there are staff records
        if staff_records:
            elements.extend([
                Paragraph("Staff Currently In Building:", self.styles['Heading2']),
                Spacer(1, 12)
            ])

            staff_data = [["Name", "Clock In Time"]]
            for name, clock_in in staff_records:
                readable_time = datetime.fromisoformat(clock_in).strftime('%H:%M') if clock_in else "N/A"
                staff_data.append([name, readable_time])

            staff_table = Table(staff_data, colWidths=[300, 100])
            staff_table.setStyle(self._get_table_style())
            elements.extend([staff_table, Spacer(1, 20)])

        # Add visitors section if there are visitor records
        if visitor_records:
            elements.extend([
                Paragraph("Visitors Currently In Building:", self.styles['Heading2']),
                Spacer(1, 12)
            ])

            visitor_data = [["Name", "Car Registration", "Purpose", "Time In"]]
            for visitor in visitor_records:
                name, car_reg, purpose, time_in = visitor
                time_in_formatted = datetime.fromisoformat(time_in).strftime('%H:%M') if time_in else "N/A"
                visitor_data.append([name, car_reg, purpose, time_in_formatted])

            visitor_table = Table(visitor_data, colWidths=[150, 100, 150, 100])
            visitor_table.setStyle(self._get_table_style())
            elements.append(visitor_table)

        # Add signature lines
        elements.extend([
            Spacer(1, 30),
            Paragraph("Fire Marshal Signature: _______________________", self.styles['Normal']),
            Spacer(1, 20),
            Paragraph("Time Completed: _______________________", self.styles['Normal'])
        ])

        # Build the PDF
        doc.build(elements)
        logging.info("Generated fire evacuation list")
        return output_file

    @staticmethod
    def _get_table_style() -> TableStyle:
        """Return the standard table style used across all PDFs."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]) 