import json
import logging
from typing import Dict, Any, Optional
from PyQt6.QtCore import QRect

class SettingsManager:
    def __init__(self, settings_file_path: str):
        self.settings_file_path = settings_file_path
        self.default_settings = {
            "start_day": 21,
            "end_day": 20,
            "printer_IP": "10.60.1.146",
            "width": 1920,
            "height": 1080
        }
        self.settings = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create with defaults if not exists."""
        try:
            with open(self.settings_file_path, "r") as file:
                settings = json.load(file)
                # Ensure all default settings exist
                for key, value in self.default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_settings(self.default_settings)
            return self.default_settings.copy()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to file."""
        try:
            with open(self.settings_file_path, "w") as file:
                json.dump(settings, file, indent=4)
            self.settings = settings
            logging.info("Settings saved successfully")
            return True
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return False

    def get_setting(self, key: str) -> Optional[Any]:
        """Get a specific setting value."""
        return self.settings.get(key)

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a specific setting."""
        try:
            self.settings[key] = value
            return self.save_settings(self.settings)
        except Exception as e:
            logging.error(f"Error updating setting {key}: {e}")
            return False

    def update_screen_dimensions(self, rect: QRect) -> bool:
        """Update screen dimensions in settings."""
        try:
            self.settings['width'] = rect.width()
            self.settings['height'] = rect.height()
            return self.save_settings(self.settings)
        except Exception as e:
            logging.error(f"Error updating screen dimensions: {e}")
            return False

    def validate_settings(self) -> bool:
        """Validate current settings."""
        try:
            # Validate day settings
            start_day = self.settings.get('start_day', 0)
            end_day = self.settings.get('end_day', 0)
            if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                return False

            # Validate printer IP
            printer_ip = self.settings.get('printer_IP', '')
            if not printer_ip:
                return False

            # Validate screen dimensions
            width = self.settings.get('width', 0)
            height = self.settings.get('height', 0)
            if width <= 0 or height <= 0:
                return False

            return True
        except Exception as e:
            logging.error(f"Error validating settings: {e}")
            return False 