#!/usr/bin/env python3
"""
Comprehensive DigitalPersona device status checker
"""

import subprocess
import usb.core
import usb.util
import time

def check_system_usb():
    """Check USB devices via system_profiler"""
    print("=== System USB Device Check ===")
    try:
        result = subprocess.run(['system_profiler', 'SPUSBDataType'], capture_output=True, text=True)
        
        if "DigitalPersona" in result.stdout or "U.are.U" in result.stdout:
            print("✅ DigitalPersona device found in system USB")
            
            # Extract relevant lines
            lines = result.stdout.split('\n')
            in_fingerprint_section = False
            for line in lines:
                if "U.are.U" in line or "DigitalPersona" in line:
                    in_fingerprint_section = True
                    print(f"   {line.strip()}")
                elif in_fingerprint_section and line.strip() and not line.startswith(' '):
                    break
                elif in_fingerprint_section and line.strip():
                    print(f"   {line.strip()}")
        else:
            print("❌ DigitalPersona device NOT found in system USB")
            print("   Make sure the device is properly connected")
        
    except Exception as e:
        print(f"❌ Error checking system USB: {e}")

def check_pyusb_devices():
    """Check USB devices via pyusb"""
    print("\n=== PyUSB Device Check ===")
    try:
        # Find all USB devices
        devices = list(usb.core.find(find_all=True))
        print(f"Found {len(devices)} USB devices total")
        
        # Look specifically for DigitalPersona
        dp_device = usb.core.find(idVendor=0x05ba, idProduct=0x000a)
        if dp_device:
            print("✅ DigitalPersona U.are.U 4500 found via PyUSB")
            print(f"   Vendor ID: 0x{dp_device.idVendor:04x}")
            print(f"   Product ID: 0x{dp_device.idProduct:04x}")
            
            try:
                print(f"   Manufacturer: {usb.util.get_string(dp_device, dp_device.iManufacturer)}")
                print(f"   Product: {usb.util.get_string(dp_device, dp_device.iProduct)}")
            except:
                print("   (Could not read device strings)")
                
            try:
                config = dp_device.get_active_configuration()
                print(f"   Active configuration: {config.bConfigurationValue}")
            except:
                print("   (Could not read active configuration)")
                
        else:
            print("❌ DigitalPersona U.are.U 4500 NOT found via PyUSB")
        
        # List all DigitalPersona devices
        dp_devices = list(usb.core.find(find_all=True, idVendor=0x05ba))
        if dp_devices:
            print(f"   Found {len(dp_devices)} DigitalPersona devices:")
            for device in dp_devices:
                print(f"     - Product ID: 0x{device.idProduct:04x}")
        
    except Exception as e:
        print(f"❌ Error checking PyUSB devices: {e}")

def check_device_permissions():
    """Check device permissions and access"""
    print("\n=== Device Permissions Check ===")
    try:
        device = usb.core.find(idVendor=0x05ba, idProduct=0x000a)
        if device:
            print("✅ Device found, testing access...")
            
            # Test different access patterns
            print("   Testing device access patterns:")
            
            # Test 1: Basic device info
            try:
                vendor = device.idVendor
                product = device.idProduct
                print(f"   ✅ Basic info access: Vendor=0x{vendor:04x}, Product=0x{product:04x}")
            except Exception as e:
                print(f"   ❌ Basic info access failed: {e}")
            
            # Test 2: Configuration
            try:
                config = device.get_active_configuration()
                print(f"   ✅ Configuration access: Config {config.bConfigurationValue}")
            except Exception as e:
                print(f"   ⚠️  Configuration access failed: {e}")
                
                # Try to set configuration
                try:
                    device.set_configuration()
                    print(f"   ✅ Configuration set successfully")
                except Exception as e2:
                    print(f"   ❌ Configuration setting failed: {e2}")
            
            # Test 3: Interface claim
            try:
                usb.util.claim_interface(device, 0)
                print(f"   ✅ Interface claim successful")
                usb.util.release_interface(device, 0)
                print(f"   ✅ Interface release successful")
            except Exception as e:
                print(f"   ⚠️  Interface claim failed: {e}")
        else:
            print("❌ No device found for permissions test")
            
    except Exception as e:
        print(f"❌ Error checking device permissions: {e}")

def check_device_led_status():
    """Try to determine actual LED status"""
    print("\n=== LED Status Check ===")
    print("Please visually check your DigitalPersona device:")
    print("🔵 BLUE LED = Device ready/standby")
    print("🔴 RED LED = Device scanning/active") 
    print("⚫ NO LED = Device off/disconnected")
    
    current_status = input("\nWhat do you see? (blue/red/off): ").lower().strip()
    
    if current_status == "blue":
        print("✅ Device appears to be in ready state")
        print("   This means the device is powered and ready for commands")
    elif current_status == "red":
        print("⚠️  Device appears to be in scanning state")
        print("   This might indicate it's stuck in scan mode")
    elif current_status == "off":
        print("❌ Device appears to be off")
        print("   Check USB connection and power")
    else:
        print("❓ Unknown status - please check device LED")

def main():
    print("🔍 DigitalPersona U.are.U 4500 Comprehensive Status Check")
    print("=" * 60)
    
    check_system_usb()
    check_pyusb_devices()
    check_device_permissions()
    check_device_led_status()
    
    print("\n" + "=" * 60)
    print("📋 RECOMMENDATIONS:")
    print("1. If device is not found: Check USB connection")
    print("2. If device found but access fails: Check permissions/drivers")
    print("3. If LED is off: Device may need power cycle")
    print("4. If LED is blue: Device is ready for use")
    print("5. If LED is red: Device may be stuck - try disconnect/reconnect")

if __name__ == "__main__":
    main() 