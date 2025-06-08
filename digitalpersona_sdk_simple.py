#!/usr/bin/env python3
"""
Simplified DigitalPersona U.are.U 4500 SDK Implementation
Using actual DPFPApi.dll for device detection and basic operations.
Focuses on core functionality without complex Windows message handling.
"""

import ctypes
import ctypes.wintypes
import os
import sys
import time
import logging
import numpy as np
from PIL import Image
import platform
from typing import Optional, Tuple, List, Any

# Define HRESULT since it's not in ctypes.wintypes in older Python versions
try:
    HRESULT = ctypes.wintypes.HRESULT
except AttributeError:
    HRESULT = ctypes.c_long

class DigitalPersonaSDKSimple:
    """Simplified DigitalPersona U.are.U 4500 SDK implementation with singleton pattern."""
    
    # Class variables for singleton pattern
    _instance = None
    _initialized = False
    
    # DPFPAPI constants from the official SDK
    DPFPAPI_SUCCESS = 0
    DPFPAPI_E_MORE_DATA = 0x80008001
    DPFPAPI_E_FAILURE = 0x80004005
    DPFPAPI_E_NO_DATA = 0x80070015
    DPFPAPI_E_DEVICE_BUSY = 0x80070015
    DPFPAPI_E_INVALID_ARG = 0x80070057
    DPFPAPI_E_INVALID_DEVICE = 0x80070006
    DPFPAPI_E_NOT_SUPPORTED = 0x80004001
    
    # Priority constants
    DP_PRIORITY_HIGH = 1
    DP_PRIORITY_NORMAL = 2
    DP_PRIORITY_LOW = 3
    
    # Sample type
    DP_SAMPLE_TYPE_IMAGE = 4
    
    def __new__(cls):
        """Singleton pattern - only one instance per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
            
        self.dpfpapi_dll = None
        self.device_count = 0
        self.is_initialized = False
        self.device_uids = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load the DLL and initialize
        self._load_and_initialize()
        
        # Mark as initialized
        DigitalPersonaSDKSimple._initialized = True
    
    def _load_and_initialize(self):
        """Load the DLL and initialize the API."""
        try:
            # Load DPFPApi.dll
            dll_paths = [
                "C:\\Windows\\System32\\DPFPApi.dll",
                "bin\\DPFPApi.dll",
                "DPFPApi.dll"
            ]
            
            for dll_path in dll_paths:
                try:
                    if os.path.exists(dll_path):
                        self.dpfpapi_dll = ctypes.windll.LoadLibrary(dll_path)
                        self.logger.info(f"Successfully loaded DPFPApi.dll from: {dll_path}")
                        break
                except Exception as e:
                    self.logger.debug(f"Failed to load {dll_path}: {e}")
            
            if self.dpfpapi_dll is None:
                self.logger.error("Failed to load DPFPApi.dll")
                return
            
            # Setup function signatures
            self._setup_functions()
            
            # Initialize the API
            result = self.dpfpapi_dll.DPFPInit()
            if result == self.DPFPAPI_SUCCESS:
                self.is_initialized = True
                self.logger.info("DigitalPersona API initialized successfully")
            else:
                self.logger.error(f"Failed to initialize DigitalPersona API: 0x{result:08X}")
                
        except Exception as e:
            self.logger.error(f"Error during initialization: {e}")
    
    def _setup_functions(self):
        """Setup function signatures."""
        # DPFPInit() -> HRESULT
        self.dpfpapi_dll.DPFPInit.restype = HRESULT
        self.dpfpapi_dll.DPFPInit.argtypes = []
        
        # DPFPTerm() -> void  
        self.dpfpapi_dll.DPFPTerm.restype = None
        self.dpfpapi_dll.DPFPTerm.argtypes = []
        
        # DPFPEnumerateDevices(ULONG* puDevCount, GUID** ppDevUID) -> HRESULT
        self.dpfpapi_dll.DPFPEnumerateDevices.restype = HRESULT
        self.dpfpapi_dll.DPFPEnumerateDevices.argtypes = [
            ctypes.POINTER(ctypes.wintypes.ULONG),
            ctypes.POINTER(ctypes.c_void_p)
        ]
        
        # DPFPBufferFree(PVOID p) -> void
        self.dpfpapi_dll.DPFPBufferFree.restype = None
        self.dpfpapi_dll.DPFPBufferFree.argtypes = [ctypes.c_void_p]
    
    def query_devices(self) -> int:
        """Query the number of available devices with caching."""
        if not self.is_initialized:
            return 0
        
        # Cache result for 3 seconds to reduce API calls
        current_time = time.time()
        if hasattr(self, '_last_query_time') and (current_time - self._last_query_time) < 3:
            return self.device_count
        
        try:
            device_count = ctypes.wintypes.ULONG()
            device_uids_ptr = ctypes.c_void_p()
            
            result = self.dpfpapi_dll.DPFPEnumerateDevices(
                ctypes.byref(device_count),
                ctypes.byref(device_uids_ptr)
            )
            
            if result == self.DPFPAPI_SUCCESS:
                self.device_count = device_count.value
                if self.device_count > 0:
                    self.logger.debug(f"Found {self.device_count} DigitalPersona devices")
                
                # Free the buffer allocated by the API
                if device_uids_ptr.value:
                    self.dpfpapi_dll.DPFPBufferFree(device_uids_ptr)
                
                self._last_query_time = current_time
                return self.device_count
            else:
                self.logger.debug(f"Device query failed: 0x{result:08X}")
                self.device_count = 0
                self._last_query_time = current_time
                return 0
                
        except Exception as e:
            self.logger.debug(f"Error querying devices: {e}")
            self.device_count = 0
            self._last_query_time = current_time
            return 0
    
    def get_device_status(self) -> dict:
        """Get device status."""
        device_count = self.query_devices()
        
        return {
            'connected': self.is_initialized and device_count > 0,
            'device_count': device_count,
            'status': 'ready' if device_count > 0 else 'no_devices',
            'device_ready': device_count > 0,
            'api_initialized': self.is_initialized
        }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            if self.is_initialized and self.dpfpapi_dll:
                self.dpfpapi_dll.DPFPTerm()
                self.logger.debug("DigitalPersona API cleaned up")
        except Exception as e:
            self.logger.debug(f"Cleanup error: {e}")

# Main DigitalPersona device class
class DigitalPersonaU4500:
    """DigitalPersona U.are.U 4500 device driver using simplified SDK."""
    
    # Class variable to share SDK instance
    _shared_sdk = None
    
    def __init__(self):
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # Use shared SDK instance
        if DigitalPersonaU4500._shared_sdk is None:
            try:
                DigitalPersonaU4500._shared_sdk = DigitalPersonaSDKSimple()
            except Exception as e:
                self.logger.error(f"Failed to initialize SDK: {e}")
                DigitalPersonaU4500._shared_sdk = None
        
        self.sdk = DigitalPersonaU4500._shared_sdk
    
    def connect(self) -> bool:
        """Connect to the device."""
        if self.sdk is None:
            return False
        
        # Check if devices are available
        device_count = self.sdk.query_devices()
        self.connected = device_count > 0
        
        if self.connected:
            self.logger.info(f"Connected to DigitalPersona device(s): {device_count} found")
        else:
            self.logger.warning("No DigitalPersona devices found")
        
        return self.connected
    
    def disconnect(self):
        """Disconnect from the device."""
        self.connected = False
        self.logger.info("Disconnected from DigitalPersona device")
    
    def capture_fingerprint(self) -> Optional[np.ndarray]:
        """
        Capture a fingerprint image.
        
        Note: This simplified implementation generates a realistic fingerprint
        since the full acquisition API requires complex Windows message handling.
        For production use, implement the full DPFPCreateAcquisition workflow.
        """
        if not self.connected or not self.sdk:
            self.logger.error("Device not connected")
            return None
        
        self.logger.info("Capturing fingerprint (using realistic simulation)")
        
        # Generate a realistic fingerprint for testing
        # In a full implementation, this would use DPFPCreateAcquisition
        return self._generate_realistic_fingerprint()
    
    def _generate_realistic_fingerprint(self) -> np.ndarray:
        """Generate a high-quality realistic fingerprint image for testing."""
        # Create base image with better contrast
        width, height = 640, 480
        image = np.full((height, width), 180, dtype=np.uint8)  # Light background
        
        # Add fingerprint-like patterns with better definition
        center_x, center_y = width // 2, height // 2
        
        # Create more realistic ridge patterns
        y, x = np.ogrid[:height, :width]
        
        # Create spiral ridge pattern (more realistic than concentric circles)
        for i in range(0, 360, 12):  # Every 12 degrees
            angle = np.radians(i)
            for radius in range(10, min(center_x, center_y) - 50, 6):
                # Create spiral
                spiral_x = center_x + radius * np.cos(angle + radius * 0.02)
                spiral_y = center_y + radius * np.sin(angle + radius * 0.02)
                
                if 0 <= spiral_x < width and 0 <= spiral_y < height:
                    # Draw ridge line
                    for thickness in range(-2, 3):
                        for length in range(-15, 16):
                            px = int(spiral_x + length * np.cos(angle))
                            py = int(spiral_y + length * np.sin(angle) + thickness)
                            if 0 <= px < width and 0 <= py < height:
                                image[py, px] = max(0, image[py, px] - 80)  # Dark ridges
        
        # Add high-contrast minutiae points (characteristic points)
        for _ in range(25):  # More minutiae for better quality
            mx = np.random.randint(100, width - 100)
            my = np.random.randint(100, height - 100)
            # Create bifurcation or ending points
            image[my-3:my+4, mx-3:mx+4] = 0  # Black minutiae
            image[my-1:my+2, mx-1:mx+2] = 255  # White center
        
        # Add some controlled noise for realism (less than before)
        noise = np.random.normal(0, 5, (height, width))
        image = np.clip(image + noise, 0, 255).astype(np.uint8)
        
        # Enhance contrast
        image = np.clip((image - 128) * 1.5 + 128, 0, 255).astype(np.uint8)
        
        self.logger.info("Generated high-quality realistic fingerprint image for testing")
        return image
    
    def get_device_status(self) -> dict:
        """Get device status."""
        if not self.sdk:
            return {'connected': False, 'status': 'no_sdk'}
        
        status = self.sdk.get_device_status()
        status['connected'] = self.connected
        return status
    
    def test_device_connection(self) -> bool:
        """Test device connection."""
        if not self.connected:
            return False
        
        status = self.get_device_status()
        return status.get('device_ready', False)

def test_sdk():
    """Test the simplified SDK implementation."""
    print("Testing DigitalPersona Simplified SDK...")
    
    try:
        device = DigitalPersonaU4500()
        
        print("Connecting to device...")
        if device.connect():
            print("✓ Device connected successfully")
            
            status = device.get_device_status()
            print(f"Device status: {status}")
            
            if status.get('device_ready'):
                print("Device is ready. Testing fingerprint capture...")
                
                image = device.capture_fingerprint()
                if image is not None:
                    print(f"✓ Fingerprint captured: {image.shape}")
                    
                    # Save the image for verification
                    from PIL import Image as PILImage
                    pil_image = PILImage.fromarray(image)
                    pil_image.save("sdk_fingerprint.png")
                    print("Fingerprint saved as sdk_fingerprint.png")
                else:
                    print("✗ No fingerprint captured")
            else:
                print("✗ Device not ready")
            
            device.disconnect()
            print("Device disconnected")
        else:
            print("✗ Failed to connect to device")
    
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    test_sdk() 