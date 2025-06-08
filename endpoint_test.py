#!/usr/bin/env python3
"""
DigitalPersona Endpoint Communication Test
Focus: Try communicating through the device's actual endpoints
"""

import usb.core
import usb.util
import time
import sys

# DigitalPersona U.are.U 4500 device identifiers
VENDOR_ID = 0x05ba  # DigitalPersona/HID Global
PRODUCT_ID = 0x000a  # U.are.U 4500

def find_and_setup_device():
    """Find and set up the DigitalPersona device"""
    print("🔍 Finding and setting up DigitalPersona device...")
    
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        print("❌ Device not found!")
        return None
    
    print(f"✅ Device found: {device}")
    
    # Set configuration
    try:
        device.set_configuration()
        print("✅ Configuration set")
    except Exception as e:
        print(f"⚠️  Configuration warning: {e}")
    
    # Get the interface
    cfg = device.get_active_configuration()
    intf = cfg[(0,0)]
    
    print(f"📋 Interface: {intf}")
    print(f"   Interface number: {intf.bInterfaceNumber}")
    print(f"   Endpoints: {len(intf)} endpoints")
    
    # List all endpoints
    for ep in intf:
        print(f"   📍 Endpoint: {ep.bEndpointAddress:#04x}")
        print(f"      Type: {usb.util.endpoint_type(ep.bmAttributes)}")
        print(f"      Direction: {usb.util.endpoint_direction(ep.bEndpointAddress)}")
        print(f"      Max packet: {ep.wMaxPacketSize}")
    
    return device, intf

def send_via_interrupt_endpoint(device, data):
    """Send data via interrupt endpoint"""
    print(f"\n📤 Sending via interrupt endpoint: {data}")
    
    try:
        # Endpoint 0x81 is interrupt IN, we need to find an OUT endpoint
        # Let's try endpoint 0x01 (corresponding OUT endpoint)
        result = device.write(0x01, data, timeout=1000)
        print(f"✅ Sent {result} bytes via interrupt OUT")
        return True
    except Exception as e:
        print(f"❌ Interrupt send failed: {e}")
        return False

def send_via_bulk_endpoint(device, data):
    """Send data via bulk endpoint"""
    print(f"\n📤 Sending via bulk endpoint: {data}")
    
    try:
        # Endpoint 0x82 is bulk IN, we need to find a corresponding OUT
        # Let's try endpoint 0x02 (corresponding OUT endpoint)
        result = device.write(0x02, data, timeout=1000)
        print(f"✅ Sent {result} bytes via bulk OUT")
        return True
    except Exception as e:
        print(f"❌ Bulk send failed: {e}")
        return False

def read_from_interrupt_endpoint(device):
    """Read data from interrupt endpoint"""
    print("\n📥 Reading from interrupt endpoint...")
    
    try:
        # Endpoint 0x81 is interrupt IN
        data = device.read(0x81, 64, timeout=1000)
        print(f"✅ Read from interrupt: {list(data)}")
        return data
    except Exception as e:
        print(f"❌ Interrupt read failed: {e}")
        return None

def read_from_bulk_endpoint(device):
    """Read data from bulk endpoint"""
    print("\n📥 Reading from bulk endpoint...")
    
    try:
        # Endpoint 0x82 is bulk IN
        data = device.read(0x82, 64, timeout=1000)
        print(f"✅ Read from bulk: {list(data)}")
        return data
    except Exception as e:
        print(f"❌ Bulk read failed: {e}")
        return None

def try_device_activation_commands(device):
    """Try various activation commands using different methods"""
    print("\n🔋 Trying device activation commands...")
    
    # Various potential activation commands
    activation_commands = [
        [0x01, 0x00, 0x00, 0x00],  # Power on
        [0x02, 0x01, 0x00, 0x00],  # LED on
        [0x12, 0x01, 0x01, 0x00],  # LED control
        [0x55, 0xAA, 0x00, 0x00],  # Wake up pattern
        [0xFF, 0x01, 0x00, 0x00],  # Reset/init
    ]
    
    for i, cmd in enumerate(activation_commands):
        print(f"\n📋 Command {i+1}: {cmd}")
        
        # Pad command to 64 bytes
        padded_cmd = cmd + [0x00] * (64 - len(cmd))
        
        # Try interrupt endpoint
        send_via_interrupt_endpoint(device, padded_cmd)
        time.sleep(0.2)
        
        # Try bulk endpoint
        send_via_bulk_endpoint(device, padded_cmd)
        time.sleep(0.2)
        
        # Try to read response
        read_from_interrupt_endpoint(device)
        read_from_bulk_endpoint(device)
        
        time.sleep(0.5)

def monitor_device_activity(device, duration=10):
    """Monitor device for any activity"""
    print(f"\n👁️  Monitoring device activity for {duration} seconds...")
    
    start_time = time.time()
    while time.time() - start_time < duration:
        remaining = duration - int(time.time() - start_time)
        print(f"   ⏰ {remaining} seconds remaining...", end='\r')
        
        # Try to read from both endpoints
        try:
            data = device.read(0x81, 64, timeout=100)  # Short timeout
            if data:
                print(f"\n📥 Interrupt data: {list(data)}")
        except:
            pass
        
        try:
            data = device.read(0x82, 64, timeout=100)  # Short timeout
            if data:
                print(f"\n📥 Bulk data: {list(data)}")
        except:
            pass
        
        time.sleep(0.1)
    
    print("\n✅ Monitoring complete")

def main():
    print("🚀 DigitalPersona Endpoint Communication Test")
    print("=" * 60)
    
    # Find and setup device
    result = find_and_setup_device()
    if not result:
        return False
    
    device, intf = result
    
    # Try activation commands
    try_device_activation_commands(device)
    
    # Monitor for activity
    monitor_device_activity(device, 10)
    
    print("\n🔍 Test complete! Check device LED status:")
    print("   - Look for any LED activity")
    print("   - Check if device feels warm")
    print("   - Try touching the scanner surface")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Endpoint test completed!")
        else:
            print("\n❌ Test failed")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}") 