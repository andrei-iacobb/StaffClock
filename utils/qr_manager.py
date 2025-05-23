import os
import logging
import qrcode
import cv2
from typing import Optional, Tuple
from threading import Thread, Event
from PyQt6.QtCore import QObject, pyqtSignal

class QRManager(QObject):
    qr_code_detected = pyqtSignal(str)  # Signal emitted when QR code is detected

    def __init__(self, qr_code_folder: str):
        super().__init__()
        self.qr_code_folder = qr_code_folder
        self.scanner_active = False
        self.stop_event = Event()
        self.cap = None

    def generate_qr_code(self, staff_code: str) -> Optional[str]:
        """Generate a QR code for the given staff code."""
        try:
            os.makedirs(self.qr_code_folder, exist_ok=True)
            qr_code_file = os.path.join(self.qr_code_folder, f"{staff_code}.png")

            # Generate QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(staff_code)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            img.save(qr_code_file)

            logging.info(f"Generated QR code for staff code {staff_code}")
            return qr_code_file
        except Exception as e:
            logging.error(f"Error generating QR code: {e}")
            return None

    def start_scanner(self) -> bool:
        """Start the QR code scanner."""
        if self.scanner_active:
            return False

        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Failed to open camera")

            self.scanner_active = True
            self.stop_event.clear()
            Thread(target=self._scan_loop, daemon=True).start()
            logging.info("QR scanner started")
            return True
        except Exception as e:
            logging.error(f"Error starting QR scanner: {e}")
            self.stop_scanner()
            return False

    def stop_scanner(self):
        """Stop the QR code scanner."""
        self.scanner_active = False
        self.stop_event.set()
        if self.cap:
            self.cap.release()
            self.cap = None
        logging.info("QR scanner stopped")

    def _scan_loop(self):
        """Main scanning loop."""
        detector = cv2.QRCodeDetector()

        while self.scanner_active and not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                continue

            try:
                data, bbox, _ = detector.detectAndDecode(frame)
                if data:
                    self.qr_code_detected.emit(data)
                    logging.info(f"QR Code detected: {data}")
                    break
            except Exception as e:
                logging.error(f"Error in QR scanning loop: {e}")
                continue

        self.stop_scanner()

    def get_frame_dimensions(self) -> Tuple[int, int]:
        """Get the dimensions of the camera frame."""
        if not self.cap:
            return 0, 0
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height 