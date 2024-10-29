import tkinter as tk
from tkinter import messagebox
import sqlite3
import datetime

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
        c.execute('SELECT id, clock_in_time FROM clock_records WHERE staff_code = ? AND clock_out_time IS NULL', (staff_code,))
        clock_record = c.fetchone()
        if not clock_record:
            conn.close()
            messagebox.showerror('Error', 'No clock-in record found')
            return

        c.execute('UPDATE clock_records SET clock_out_time = ? WHERE id = ?', (clock_out_time, clock_record[0]))
        conn.commit()
        conn.close()
        time_out = datetime.datetime.fromisoformat(clock_out_time).strftime('%H:%M')
        messagebox.showinfo('Success', f'Clock-out recorded successfully at {time_out}')

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
    messagebox.showinfo('Total Hours', f'Total hours worked: {total_hours:.2f}')

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
        else:
            greeting_label.config(text='Unknown')

# GUI Setup
def main():
    root = tk.Tk()
    global staff_code_entry, greeting_label
    root.title('Staff Clock In/Out System')

    tk.Label(root, text='Staff Code:').grid(row=0, column=0, padx=10, pady=10)
    staff_code_entry = tk.Entry(root)
    staff_code_entry.grid(row=0, column=1, padx=10, pady=10)
    staff_code_entry.bind('<KeyRelease>', on_staff_code_change)

    greeting_label = tk.Label(root, text='', font=('Helvetica', 12, 'bold'))
    greeting_label.grid(row=1, column=0, columnspan=2, pady=10)

    clock_in_button = tk.Button(root, text='Clock In', command=lambda: clock_action('in', staff_code_entry.get()))
    clock_in_button.grid(row=2, column=0, padx=10, pady=10)

    clock_out_button = tk.Button(root, text='Clock Out', command=lambda: clock_action('out', staff_code_entry.get()))
    clock_out_button.grid(row=2, column=1, padx=10, pady=10)

    get_hours_button = tk.Button(root, text='Get Hours', command=lambda: get_hours(staff_code_entry.get()))
    get_hours_button.grid(row=3, column=0, columnspan=2, pady=10)

    root.mainloop()

if __name__ == '__main__':
    main()
