#!/usr/bin/env python3
"""
Simple DigitalPersona Device Test Script
Focus: Just get the device to turn on and show LED activity
"""

import usb.core
import usb.util
import time
import sys

# DigitalPersona U.are.U 4500 device identifiers
VENDOR_ID = 0x05ba  # DigitalPersona/HID Global
PRODUCT_ID = 0x000a  # U.are.U 4500

def find_device():
    """Find the DigitalPersona device"""
    print("🔍 Searching for DigitalPersona U.are.U 4500...")
    
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        print("❌ DigitalPersona device not found!")
        print("   - Check USB connection")
        print("   - Check device is powered")
        return None
    
    print(f"✅ Device found: {device}")
    print(f"   Vendor ID: 0x{device.idVendor:04x}")
    print(f"   Product ID: 0x{device.idProduct:04x}")
    
    return device

def claim_device(device):
    """Claim the device for exclusive use"""
    print("\n🔧 Claiming device...")
    
    try:
        # Try to detach kernel driver if it's attached
        if device.is_kernel_driver_active(0):
            print("   Detaching kernel driver...")
            device.detach_kernel_driver(0)
    except:
        pass  # May not be necessary on all systems
    
    try:
        # Claim the interface
        usb.util.claim_interface(device, 0)
        print("✅ Device claimed successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to claim device: {e}")
        return False

def send_power_on_command(device):
    """Send power on command to the device"""
    print("\n⚡ Sending power on command...")
    
    try:
        # Common USB HID power on command
        power_on_cmd = [0x01, 0x00, 0x00, 0x00]  # Basic power on
        
        # Try to send via control transfer
        result = device.ctrl_transfer(
            bmRequestType=0x21,  # Host to device, class, interface
            bRequest=0x09,       # SET_REPORT
            wValue=0x0301,       # Report type and ID
            wIndex=0x00,         # Interface
            data_or_wLength=power_on_cmd,
            timeout=1000
        )
        
        print(f"✅ Power command sent, result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send power command: {e}")
        return False

def send_led_on_command(device):
    """Send LED on command to activate the blue LED"""
    print("\n💡 Sending LED activation command...")
    
    # Try multiple LED commands
    led_commands = [
        [0x02, 0x01, 0x00, 0x00],  # LED on command 1
        [0x03, 0x01, 0xFF, 0x00],  # LED on command 2
        [0x12, 0x01, 0x01, 0x00],  # LED control command
        [0x40, 0x01, 0x00, 0x00],  # Alternative LED command
    ]
    
    for i, cmd in enumerate(led_commands):
        try:
            print(f"   Trying LED command {i+1}: {cmd}")
            
            result = device.ctrl_transfer(
                bmRequestType=0x21,  # Host to device, class, interface
                bRequest=0x09,       # SET_REPORT
                wValue=0x0302,       # Report type and ID
                wIndex=0x00,         # Interface
                data_or_wLength=cmd,
                timeout=1000
            )
            
            print(f"   ✅ LED command {i+1} sent, result: {result}")
            time.sleep(0.5)  # Wait between commands
            
        except Exception as e:
            print(f"   ❌ LED command {i+1} failed: {e}")
    
    return True

def check_device_status(device):
    """Check if device is responding"""
    print("\n📊 Checking device status...")
    
    try:
        # Try to read device status
        result = device.ctrl_transfer(
            bmRequestType=0xa1,  # Device to host, class, interface
            bRequest=0x01,       # GET_REPORT
            wValue=0x0301,       # Report type and ID
            wIndex=0x00,         # Interface
            data_or_wLength=64,  # Buffer size
            timeout=1000
        )
        
        print(f"✅ Device status read: {list(result)}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to read device status: {e}")
        return False

def main():
    print("🚀 DigitalPersona Device Activation Test")
    print("=" * 50)
    
    # Step 1: Find device
    device = find_device()
    if not device:
        return False
    
    # Step 2: Claim device
    if not claim_device(device):
        return False
    
    # Step 3: Send power on command
    send_power_on_command(device)
    time.sleep(1)
    
    # Step 4: Send LED activation commands
    send_led_on_command(device)
    time.sleep(1)
    
    # Step 5: Check device status
    check_device_status(device)
    
    print("\n🔍 Device should now be active!")
    print("   Look for:")
    print("   - Blue LED should be on or flickering")
    print("   - Device should feel slightly warm")
    print("   - Scanner surface should be ready")
    
    # Keep checking for 10 seconds
    print("\n⏰ Monitoring for 10 seconds...")
    for i in range(10):
        print(f"   {10-i} seconds remaining...", end='\r')
        time.sleep(1)
    
    print("\n✅ Test complete!")
    
    # Clean up
    try:
        usb.util.release_interface(device, 0)
        print("🧹 Device released")
    except:
        pass
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Test completed - check if LED is now active!")
        else:
            print("\n❌ Test failed - device not activated")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}") 