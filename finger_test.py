#!/usr/bin/env python3
"""
DigitalPersona Finger Detection Test
Focus: Wake up device and detect finger placement
"""

import usb.core
import usb.util
import time
import sys
import threading

# DigitalPersona U.are.U 4500 device identifiers
VENDOR_ID = 0x05ba  # DigitalPersona/HID Global
PRODUCT_ID = 0x000a  # U.are.U 4500

def find_and_setup_device():
    """Find and set up the DigitalPersona device"""
    print("🔍 Finding DigitalPersona device...")
    
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        print("❌ Device not found!")
        return None
    
    print("✅ Device found!")
    
    try:
        device.set_configuration()
        print("✅ Configuration set")
        return device
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return None

def aggressive_wake_up(device):
    """Aggressively try to wake up the device"""
    print("\n🔋 Aggressive wake-up sequence...")
    
    # Try multiple rapid reads to wake it up
    for attempt in range(10):
        try:
            print(f"   Wake attempt {attempt + 1}/10...", end='\r')
            data = device.read(0x81, 64, timeout=500)
            if data and any(data):
                print(f"\n✅ Device woke up on attempt {attempt + 1}!")
                print(f"   Initial data: {list(data[:8])}...")
                return True
        except usb.core.USBTimeoutError:
            pass
        except Exception as e:
            print(f"\n❌ Wake error: {e}")
        
        time.sleep(0.1)
    
    print(f"\n⚠️  Device didn't wake up after 10 attempts")
    return False

def continuous_finger_detection(device, duration=60):
    """Continuously monitor for finger placement"""
    print(f"\n👆 Starting finger detection for {duration} seconds...")
    print("   Place and remove your finger on the scanner multiple times")
    print("   Watch for LED changes and data patterns")
    
    start_time = time.time()
    last_data = None
    data_count = 0
    finger_events = 0
    
    while time.time() - start_time < duration:
        try:
            # Read from interrupt endpoint
            data = device.read(0x81, 64, timeout=500)
            data_count += 1
            
            if data and any(data):
                # Convert to list for comparison
                data_list = list(data)
                
                # Check if data changed significantly (indicating finger placement/removal)
                if last_data is None:
                    print(f"\n📥 First data: {data_list[:8]}...")
                    last_data = data_list
                else:
                    # Calculate how much data changed
                    differences = sum(1 for i, (a, b) in enumerate(zip(data_list, last_data)) if a != b)
                    
                    if differences > 10:  # Significant change
                        finger_events += 1
                        print(f"\n👆 Finger event #{finger_events}: {data_list[:8]}... ({differences} bytes changed)")
                        last_data = data_list
                    elif data_count % 20 == 0:  # Periodic update
                        remaining = int(duration - (time.time() - start_time))
                        print(f"   📊 Monitoring... {remaining}s remaining, {data_count} reads, {finger_events} finger events", end='\r')
            
        except usb.core.USBTimeoutError:
            # No data available - device might be sleeping
            remaining = int(duration - (time.time() - start_time))
            print(f"   💤 Device quiet... {remaining}s remaining", end='\r')
            
            # Try to wake it up again
            try:
                device.read(0x81, 64, timeout=100)
            except:
                pass
                
        except Exception as e:
            print(f"\n❌ Read error: {e}")
            break
    
    print(f"\n📊 Detection complete:")
    print(f"   Total reads: {data_count}")
    print(f"   Finger events detected: {finger_events}")
    
    return finger_events > 0

def test_finger_patterns(device):
    """Test different finger placement patterns"""
    print("\n🧪 Testing finger placement patterns...")
    
    instructions = [
        ("Place finger on scanner", 5),
        ("Remove finger", 3),
        ("Place finger again", 5),
        ("Remove finger", 3),
        ("Quick tap (1 second)", 2),
        ("Hold finger firmly", 8),
    ]
    
    for instruction, duration in instructions:
        print(f"\n📋 {instruction} for {duration} seconds...")
        start_time = time.time()
        data_samples = []
        
        while time.time() - start_time < duration:
            try:
                data = device.read(0x81, 64, timeout=500)
                if data and any(data):
                    data_samples.append(list(data))
                    if len(data_samples) == 1:
                        print(f"   📥 Data: {list(data[:8])}...")
            except usb.core.USBTimeoutError:
                print("   💤 No data", end='\r')
            except Exception as e:
                print(f"   ❌ Error: {e}")
                break
        
        print(f"   📊 Collected {len(data_samples)} data samples")
    
    print("\n✅ Pattern testing complete")

def main():
    print("🚀 DigitalPersona Finger Detection Test")
    print("=" * 60)
    
    # Find device
    device = find_and_setup_device()
    if not device:
        return False
    
    # Wake up device
    if not aggressive_wake_up(device):
        print("⚠️  Device didn't wake up, but continuing anyway...")
    
    # Test finger detection
    print("\n" + "="*60)
    print("🔍 FINGER DETECTION TEST")
    print("Now place your finger on the scanner and see if we detect it!")
    
    success = continuous_finger_detection(device, 30)
    
    if success:
        print("\n🎉 SUCCESS! Finger detection working!")
        
        # Do pattern testing
        print("\n" + "="*60)
        print("🧪 PATTERN TESTING")
        test_finger_patterns(device)
    else:
        print("\n❌ No finger events detected")
        print("   The device might not be responding to finger placement")
    
    print("\n" + "="*60)
    print("🔍 FINAL STATUS:")
    print("   1. Check if LED is on/blinking")
    print("   2. Try placing finger on scanner")
    print("   3. Device should feel slightly warm when active")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Finger detection test successful!")
        else:
            print("\n⚠️  Device may need different activation method")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}") 