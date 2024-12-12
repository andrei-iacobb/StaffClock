import socket

class Print():
    def preparePrint(self):
        staff_name = self.name_entry.text().strip()
        if staff_name:
            file_path = f"Timesheets/{staff_name}_records.pdf"
            self.print_via_jetdirect(file_path)

    def print_via_jetdirect(self, file_path):
        printer_ip = "192.168.1.250"
        printer_port = 9100
        try:
            with open(file_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as printer_socket:
                printer_socket.connect((printer_ip, printer_port))
                printer_socket.sendall(pdf_data)
            print("PDF sent to printer successfully!")
        except Exception as e:
            print(f"Failed to print PDF: {e}")