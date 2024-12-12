from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout
import os

class PDF():
    def create_table_pdf(self, staff_name, records):
        file_path = f"Timesheets/{staff_name}.pdf"
        table_data = [["Clock In Date", "Clock In Time", "Clock Out Date", "Clock Out Time"]]
        for record in records:
            clock_in = datetime.datetime.fromisoformat(record[0]) if record[0] else None
            clock_out = datetime.datetime.fromisoformat(record[1]) if record[1] else None
            table_data.append([
                clock_in.strftime('%d-%m-%Y') if clock_in else '',
                clock_in.strftime('%H:%M:%S') if clock_in else '',
                clock_out.strftime('%d-%m-%Y') if clock_out else '',
                clock_out.strftime('%H:%M:%S') if clock_out else '',
            ])

        pdf = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title_paragraph = Paragraph(f"Records for {staff_name}", title_style)
        spacer = Spacer(1, 20)
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        pdf.build([title_paragraph, spacer, table])

    def show_pdf(self, staff_name):
        file_path = f"Timesheets/{staff_name}_records.pdf"
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            QMessageBox.critical(self, "Error", "The file is empty or does not exist.")
            return

        document = QPdfDocument(self)
        if document.load(file_path) != QPdfDocument.Status.Ready:
            QMessageBox.critical(self, "Error", "Failed to load the PDF document.")
            return

        view_dialog = QDialog(self)
        view_dialog.setWindowTitle(f"{staff_name} - Records")
        view_dialog.setGeometry(100, 100, 600, 800)

        pdf_view = QPdfView(view_dialog)
        pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        pdf_view.setDocument(document)

        layout = QVBoxLayout(view_dialog)
        layout.addWidget(pdf_view)
        view_dialog.exec()