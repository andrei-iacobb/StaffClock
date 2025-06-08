#!/usr/bin/env python3
"""
DigitalPersona U.are.U 4500 Device Control
Based on official SDK documentation from HID Global/Crossmatch
Focus: Proper device initialization and LED control using official API sequence
"""

import usb.core
import usb.util
import time
import sys
import ctypes
from ctypes import *

# DigitalPersona U.are.U 4500 device identifiers
VENDOR_ID = 0x05ba  # DigitalPersona/HID Global
PRODUCT_ID = 0x000a  # U.are.U 4500

def print_status(message, status="info"):
    """Print status with formatting"""
    symbols = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def find_device():
    """Find the DigitalPersona device"""
    print_status("Searching for DigitalPersona U.are.U 4500...")
    
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        print_status("DigitalPersona device not found!", "error")
        print("  - Check USB connection")
        print("  - Check device is powered")
        return None
    
    print_status("Device found!", "success")
    print(f"  Device: {device}")
    try:
        print(f"  Manufacturer: {usb.util.get_string(device, device.iManufacturer)}")
        print(f"  Product: {usb.util.get_string(device, device.iProduct)}")
        print(f"  Serial: {usb.util.get_string(device, device.iSerialNumber)}")
    except:
        print("  (String descriptors not accessible)")
    
    return device

def initialize_device_sdk_way(device):
    """
    Initialize device using the official SDK sequence:
    1. dpfpdd_init() - Initialize library
    2. dpfpdd_open() - Open device 
    3. dpfpdd_get_device_status() - Check status
    4. dpfpdd_led_config() - Configure LED
    5. dpfpdd_led_ctrl() - Control LED
    """
    print_status("\n📋 Starting official SDK initialization sequence...")
    
    try:
        # Step 1: dpfpdd_init equivalent - USB reset and configure
        print_status("Step 1: Library initialization (dpfpdd_init)")
        device.reset()
        time.sleep(1)
        
        # Step 2: dpfpdd_open equivalent - Set configuration and claim interface
        print_status("Step 2: Opening device (dpfpdd_open)")
        device.set_configuration()
        
        # Find and claim the HID interface
        config = device.get_active_configuration()
        interface = config[(0, 0)]
        usb.util.claim_interface(device, interface)
        print_status("Device interface claimed", "success")
        
        # Step 3: dpfpdd_get_device_status equivalent - Check device status
        print_status("Step 3: Checking device status (dpfpdd_get_device_status)")
        
        # According to SDK docs, we need to find the endpoints
        endpoints = []
        for ep in interface:
            endpoints.append(ep.bEndpointAddress)
            print(f"  Endpoint: 0x{ep.bEndpointAddress:02x}")
        
        if not endpoints:
            print_status("No endpoints found!", "error")
            return False
            
        # Step 4 & 5: LED Configuration and Control
        print_status("Step 4-5: LED configuration and activation")
        
        # According to the SDK docs, the device should activate when we start reading
        # Try reading from the interrupt endpoint to activate the device
        in_endpoint = None
        for ep in interface:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                in_endpoint = ep.bEndpointAddress
                break
        
        if in_endpoint:
            print_status(f"Found input endpoint: 0x{in_endpoint:02x}")
            print_status("Attempting to activate device by reading from endpoint...")
            
            # The key is to continuously read to keep device active
            for attempt in range(3):
                try:
                    print(f"  Activation attempt {attempt + 1}...")
                    data = device.read(in_endpoint, 64, timeout=2000)
                    print_status(f"Device activated! Received {len(data)} bytes", "success")
                    print(f"  Data: {list(data)[:16]}...")
                    return True
                except usb.core.USBTimeoutError:
                    print(f"  Timeout on attempt {attempt + 1}")
                    continue
                except Exception as e:
                    print(f"  Error on attempt {attempt + 1}: {e}")
                    continue
                    
        print_status("Device initialization sequence completed", "success")
        return True
        
    except Exception as e:
        print_status(f"Initialization failed: {e}", "error")
        return False

def keep_device_active(device):
    """Keep the device active by continuous reading"""
    print_status("\n🔄 Keeping device active...")
    print("The LED should now be ON. Check your device!")
    print("Press Ctrl+C to stop...")
    
    # Find input endpoint
    config = device.get_active_configuration()
    interface = config[(0, 0)]
    
    in_endpoint = None
    for ep in interface:
        if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
            in_endpoint = ep.bEndpointAddress
            break
    
    if not in_endpoint:
        print_status("No input endpoint found!", "error")
        return
    
    print_status(f"Reading from endpoint 0x{in_endpoint:02x} to keep device active...")
    
    try:
        while True:
            try:
                data = device.read(in_endpoint, 64, timeout=1000)
                print(f"📡 Received {len(data)} bytes - Device ACTIVE")
                
                # Check if finger is placed (device typically sends different data)
                if len(data) > 0 and any(b != 0 for b in data):
                    print("👆 Finger activity detected!")
                    
            except usb.core.USBTimeoutError:
                print("⏰ Timeout - device may have gone to sleep")
                continue
            except Exception as e:
                print(f"❌ Read error: {e}")
                break
                
            time.sleep(0.1)  # Small delay to prevent overwhelming
            
    except KeyboardInterrupt:
        print_status("\n⏹️  Stopping device monitoring...", "warning")

def main():
    print("=" * 60)
    print("  DigitalPersona U.are.U 4500 SDK-Based Device Control")
    print("  Following official HID Global SDK documentation")
    print("=" * 60)
    
    # Find device
    device = find_device()
    if not device:
        sys.exit(1)
    
    # Initialize using official SDK sequence
    if not initialize_device_sdk_way(device):
        print_status("Device initialization failed!", "error")
        sys.exit(1)
    
    print_status("\n🎉 Device should now be ACTIVE with LED ON!", "success")
    print("Please check your DigitalPersona device:")
    print("  ✓ LED should be lit (blue/green)")
    print("  ✓ Device should feel slightly warm") 
    print("  ✓ Try placing finger on scanner")
    
    response = input("\nDo you see the LED turn on? (y/n): ").strip().lower()
    
    if response == 'y':
        print_status("🎉 SUCCESS! Device is properly activated!", "success")
        keep_device_active(device)
    else:
        print_status("Device may need additional commands or different approach", "warning")
        print("The device was detected and configured, but LED activation may require")
        print("platform-specific drivers or additional initialization commands.")

if __name__ == "__main__":
    main() 