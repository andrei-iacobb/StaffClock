import tkinter as tk
from tkinter import messagebox
import sqlite3
import datetime
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import fitz
import io
from PIL import ImageTk, Image


# Function to handle clock in and out actions
def clock_action(action, staff_code):
    conn = sqlite3.connect('staff_hours.db')
    c = conn.cursor()

    # Check if the staff member exists
    c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
    staff = c.fetchone()
    if not staff:
        conn.close()
        messagebox.showerror('Error', 'Invalid staff code')
        return

    if action == 'in':
        clock_in_time = datetime.datetime.now().isoformat()
        c.execute('INSERT INTO clock_records (staff_code, clock_in_time) VALUES (?, ?)', (staff_code, clock_in_time))
        conn.commit()
        conn.close()
        time_in = datetime.datetime.fromisoformat(clock_in_time).strftime('%H:%M')
        messagebox.showinfo('Success', f'Clock-in recorded successfully at {time_in}')
    elif action == 'out':
        clock_out_time = datetime.datetime.now().isoformat()
        c.execute('SELECT id, clock_in_time FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL',
                  (staff_code,))
        clock_record = c.fetchone()
        if not clock_record:
            conn.close()
            messagebox.showerror('Error', 'No clock-in record found')
            return

        c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
        conn.commit()
        conn.close()
        time_out = datetime.datetime.fromisoformat(clock_out_time).strftime('%H:%M')
        messagebox.showinfo('Success', f'Clock-out recorded successfully at {time_out}.\n'
                                       f'Today you have worked {get_hours(staff_code)}')
    else:
        conn.close()
        messagebox.showerror('Error', 'Invalid action')


# Function to get total hours
def get_hours(staff_code):
    conn = sqlite3.connect('staff_hours.db')
    c = conn.cursor()
    c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,))
    staff = c.fetchone()
    if not staff:
        conn.close()
        messagebox.showerror('Error', 'Invalid staff code')
        return

    c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
    records = c.fetchall()
    total_hours = 0.0
    for record in records:
        if record[1]:
            clock_in = datetime.datetime.fromisoformat(record[0])
            clock_out = datetime.datetime.fromisoformat(record[1])
            total_hours += (clock_out - clock_in).total_seconds() / 3600

    conn.close()
    return f'{total_hours:.2f} hours'


# Function to handle live updates based on staff code entry
def on_staff_code_change(event):
    staff_code = staff_code_entry.get()
    if len(staff_code) == 4 and staff_code.isdigit():
        # Fetch staff name and display greeting
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        c.execute('SELECT name FROM staff WHERE code = ?', (staff_code,))
        staff = c.fetchone()
        conn.close()
        if staff:
            greeting_label.config(text=f'Hello, {staff[0]}!')
    elif staff_code == '123456':
        admin_button.grid(row=5, column=0, columnspan=2, pady=10)
        greeting_label.config(text="Admin")
    elif staff_code == '654321':
        exit_button.grid(row=4, column=0, columnspan=2, pady=20)
        greeting_label.config(text="Exit")
    elif len(staff_code) < 6:
        greeting_label.config(text='')
    else:
        greeting_label.config(text=f'Unknown code')


def add_staff():
    staff_name = name_entry.get()

    # Check if staff_name is a valid string and not empty
    if isinstance(staff_name, str) and staff_name.strip():
        staff_code = random.randint(1000, 9999)
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()

        # Generate a unique code
        while c.execute('SELECT * FROM staff WHERE code = ?', (staff_code,)).fetchone():
            staff_code = random.randint(1000, 9999)

        try:
            # Insert the new staff member
            c.execute('INSERT INTO staff (name, code) VALUES (?, ?)', (staff_name, staff_code))
            conn.commit()
            messagebox.showinfo('Success', f'Staff member {staff_name} added with code {staff_code}')
        except sqlite3.Error as e:
            messagebox.showerror('Database Error', f'An error occurred: {e}')
        finally:
            conn.close()
    else:
        messagebox.showerror('Invalid Input', 'Please enter a valid staff name')

def delete_staff():
    staff_name = name_entry.get()

    if isinstance(staff_name, str) and staff_name.strip():
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        if c.execute('SELECT * FROM staff WHERE name = ?', (staff_name,)).fetchone():
            c.execute('DELETE FROM staff WHERE name = ?', (staff_name,))
            conn.commit()
            messagebox.showinfo('Success', f'Staff member {staff_name} deleted')
            conn.close()

def show_record():
    staff_name = name_entry.get()
    if isinstance(staff_name, str) and staff_name.strip():
        conn = sqlite3.connect('staff_hours.db')
        c = conn.cursor()
        c.execute('SELECT code FROM staff WHERE name = ?', (staff_name,))
        staff = c.fetchone()
        if staff:
            staff_code = staff[0]
            c.execute('SELECT clock_in_time, clock_out_time FROM clock_records WHERE staff_code = ?', (staff_code,))
            records = c.fetchall()
            conn.close()

            # Process the data to make it more readable
            headers = ['Clock In Date', 'Clock In Time', 'Clock Out Date', 'Clock Out Time']
            data = [headers]
            for record in records:
                clock_in_time = datetime.datetime.fromisoformat(record[0]) if record[0] else None
                clock_out_time = datetime.datetime.fromisoformat(record[1]) if record[1] else None
                clock_in_date_str = clock_in_time.strftime('%Y-%m-%d') if clock_in_time else ''
                clock_in_time_str = clock_in_time.strftime('%H:%M:%S') if clock_in_time else ''
                clock_out_date_str = clock_out_time.strftime('%Y-%m-%d') if clock_out_time else ''
                clock_out_time_str = clock_out_time.strftime('%H:%M:%S') if clock_out_time else ''
                data.append([clock_in_date_str, clock_in_time_str, clock_out_date_str, clock_out_time_str])
            pdfFileName = f"{staff_name}_hours.pdf"
            pdf = SimpleDocTemplate(pdfFileName, pagesize=A4)
            elements = []

            # Add title to the PDF
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(name='Title', fontSize=18, leading=22, alignment=1, spaceAfter=20)
            elements.append(Paragraph(f'Staff Clock Records for {staff_name}', title_style))

            # Add a spacer
            elements.append(Spacer(1, 0.2 * inch))

            # Create and style the table
            table = Table(data, hAlign='CENTER', colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')),  # Header background color
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align all cells
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font bold
                ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Header padding
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#D9E1F2')),  # Background for data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Data row font
                ('FONTSIZE', (0, 1), (-1, -1), 10),  # Data row font size
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)  # Grid for all cells
            ])
            table.setStyle(style)
            elements.append(table)

            # Add a footer paragraph
            elements.append(Spacer(1, 0.5 * inch))
            footer_style = ParagraphStyle(name='Footer', fontSize=10, leading=12, alignment=1)
            elements.append(Paragraph('Generated by Staff Clock In/Out System', footer_style))

            pdf.build(elements)

            # Display the generated PDF using PyMuPDF
            record_tab = tk.Toplevel()
            record_tab.title('Staff Clock Records')
            record_tab.geometry("1240x1754")
            label = tk.Label(record_tab)
            label.pack()

            # Open the PDF using PyMuPDF
            doc = fitz.open(pdfFileName)
            page = doc.load_page(0)  # Load the first page
            pix = page.get_pixmap()  # Convert the page to a pixmap

            # Convert pixmap to image and display
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            a4_dimensions = (1240, 1754)
            img.thumbnail(a4_dimensions, Image.ANTIALIAS)
            pdf_image = ImageTk.PhotoImage(img)

            label.config(image=pdf_image)
            label.image = pdf_image

        else:
            conn.close()
            messagebox.showerror('Error', 'Staff member not found')
    else:
        messagebox.showerror('Invalid Input', 'Please enter a valid staff name')



def open_admin_tab():
    admin_tab = tk.Toplevel()
    admin_tab.title('Admin Page')
    admin_tab.geometry('400x400')
    admin_tab.config(bg=bg_color)
    global name_entry

    tk.Label(admin_tab, text='Enter Name:', bg=bg_color, fg=fg_color, font=font_medium).grid(
        row=1, column=0, padx=20, pady=10, sticky='e'
    )

    name_entry = tk.Entry(admin_tab, font=font_medium)
    name_entry.grid(row=1, column=1, padx=20, pady=10)

    # Admin buttons with consistent style
    admin_button_style = {"bg": button_bg, "fg": button_fg, "font": font_medium, "width": 15, "height": 2}

    add_staff_button = tk.Button(admin_tab, text='Add Staff', **admin_button_style, command= lambda: add_staff())
    add_staff_button.grid(row=2, column=0, columnspan=2, pady=10)

    remove_staff_button = tk.Button(admin_tab, text='Remove Staff', **admin_button_style, command= lambda: delete_staff())
    remove_staff_button.grid(row=3, column=0, columnspan=2, pady=10)

    view_records_button = tk.Button(admin_tab, text='View Records', **admin_button_style, command=lambda: show_record())
    view_records_button.grid(row=4, column=0, columnspan=2, pady=10)

    hide_admin_button =tk.Button(admin_tab, text='Hide Admin', **admin_button_style, command= lambda: admin_button.grid_forget())
    hide_admin_button.grid(row=5, column=0, columnspan=2, pady=10)

    hide_exit_button = tk.Button(admin_tab, text='Hide Exit', **admin_button_style, command = lambda: exit_button.grid_forget())
    hide_exit_button.grid(row=6, column=0, columnspan=2, pady=10)

# GUI Setup
def main():
    root = tk.Tk()
    root.title('Staff Clock In/Out System')
    root.overrideredirect(True)  # Fullscreen without borders
    root.resizable(False, False)

    # Fullscreen settings
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}")

    # Colors and font
    global bg_color, fg_color, button_bg, button_fg, font_large, font_medium
    bg_color = "#2C3E50"
    fg_color = "#ECF0F1"
    button_bg = "#3498DB"
    button_fg = "#ECF0F1"
    font_large = ('Helvetica', 16, 'bold')
    font_medium = ('Helvetica', 12)

    root.config(bg=bg_color)

    global staff_code_entry, greeting_label
    global admin_button
    global exit_button


    # Center Frame to hold all widgets
    center_frame = tk.Frame(root, bg=bg_color)
    center_frame.place(relx=0.5, rely=0.5, anchor="center")

    # Staff Code Label
    tk.Label(center_frame, text='Enter Staff Code:', bg=bg_color, fg=fg_color, font=font_medium).grid(
        row=0, column=0, padx=20, pady=10, sticky="e"
    )
    staff_code_entry = tk.Entry(center_frame, font=font_medium)
    staff_code_entry.grid(row=0, column=1, padx=20, pady=10)
    staff_code_entry.bind('<KeyRelease>', on_staff_code_change)

    # Greeting Label
    greeting_label = tk.Label(center_frame, text='', bg=bg_color, fg=fg_color, font=font_large)
    greeting_label.grid(row=1, column=0, columnspan=2, pady=20)

    # Buttons with consistent style
    button_style = {"bg": button_bg, "fg": button_fg, "font": font_medium, "width": 15, "height": 2}

    clock_in_button = tk.Button(center_frame, text='Clock In',
                                command=lambda: clock_action('in', staff_code_entry.get()), **button_style)
    clock_in_button.grid(row=2, column=0, padx=10, pady=5)

    clock_out_button = tk.Button(center_frame, text='Clock Out',
                                 command=lambda: clock_action('out', staff_code_entry.get()), **button_style)
    clock_out_button.grid(row=2, column=1, padx=10, pady=5)

    exit_button = tk.Button(center_frame, text='Exit', command=root.destroy, **button_style)
    exit_button.grid(row=4, column=0, columnspan=2, pady=20)

    admin_button = tk.Button(center_frame, text='Admin', command=open_admin_tab, **button_style)
    admin_button.grid(row=5, column=0, columnspan=2, pady=10)

    root.mainloop()


if __name__ == '__main__':
    main()
