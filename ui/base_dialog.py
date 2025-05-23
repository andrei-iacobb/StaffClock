from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class BaseDialog(QDialog):
    def __init__(self, parent=None, title: str = "", width: int = 400, height: int = 300):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(width, height)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

        # Define color scheme
        self.COLORS = {
            'primary': '#1a73e8',      # Blue
            'success': '#34a853',      # Green
            'danger': '#ea4335',       # Red
            'warning': '#fbbc05',      # Yellow
            'dark': '#202124',         # Dark gray
            'light': '#ffffff',        # White
            'gray': '#5f6368',         # Medium gray
            'purple': '#9334e8',       # Purple for visitor
            'brown': '#795548',        # Brown for admin
        }

        # Set base style
        self.setStyleSheet(f"""
            QDialog {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 2px solid {self.COLORS['primary']};
                border-radius: 10px;
            }}
            QLabel {{
                color: {self.COLORS['light']};
                font-family: Inter;
            }}
            QLineEdit {{
                background: {self.COLORS['dark']};
                color: {self.COLORS['light']};
                border: 1px solid {self.COLORS['gray']};
                border-radius: 5px;
                padding: 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.COLORS['primary']};
            }}
            QPushButton {{
                background: {self.COLORS['primary']};
                color: {self.COLORS['light']};
                border: none;
                border-radius: 5px;
                padding: 10px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: {self.COLORS['primary']}dd;
            }}
        """)

        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(20, 20, 20, 20)

    def create_button(self, text: str, color: str, callback, min_width: int = 100) -> QPushButton:
        """Create a styled button."""
        button = QPushButton(text)
        button.setFont(QFont("Inter", 12))
        button.setMinimumWidth(min_width)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS[color]};
                color: {self.COLORS['light']};
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS[color]}dd;
            }}
        """)
        button.clicked.connect(callback)
        return button

    def create_label(self, text: str, font_size: int = 12, bold: bool = False) -> QLabel:
        """Create a styled label."""
        label = QLabel(text)
        font = QFont("Inter", font_size)
        if bold:
            font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {self.COLORS['light']};")
        return label

    def create_button_layout(self, *buttons: QPushButton) -> QHBoxLayout:
        """Create a horizontal layout for buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        for button in buttons:
            button_layout.addWidget(button)
        return button_layout

    def center_on_screen(self):
        """Center the dialog on the screen."""
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        ) 