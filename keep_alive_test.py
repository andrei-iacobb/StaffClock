#!/usr/bin/env python3
"""
DigitalPersona Keep Alive Test
Focus: Wake up device and keep it active
"""

import usb.core
import usb.util
import time
import sys
import threading
from queue import Queue

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

def initial_wake_up(device):
    """Initial wake-up sequence that we know works"""
    print("\n🔋 Initial wake-up sequence...")
    
    for attempt in range(20):  # Try more attempts
        try:
            print(f"   Attempt {attempt + 1}/20...", end='\r')
            data = device.read(0x81, 64, timeout=2000)  # Longer timeout
            if data and any(data):
                print(f"\n✅ Device responded on attempt {attempt + 1}!")
                print(f"   Data: {list(data[:8])}...")
                return True
        except usb.core.USBTimeoutError:
            pass
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(0.2)
    
    print(f"\n❌ Device didn't respond after 20 attempts")
    return False

def keep_device_alive(device, data_queue, stop_event):
    """Keep reading from device to maintain active state"""
    print("\n🔄 Starting keep-alive thread...")
    
    consecutive_timeouts = 0
    max_timeouts = 10
    
    while not stop_event.is_set():
        try:
            data = device.read(0x81, 64, timeout=1000)
            consecutive_timeouts = 0  # Reset timeout counter
            
            if data and any(data):
                data_queue.put(('data', list(data)))
            else:
                data_queue.put(('empty', None))
                
        except usb.core.USBTimeoutError:
            consecutive_timeouts += 1
            data_queue.put(('timeout', consecutive_timeouts))
            
            if consecutive_timeouts >= max_timeouts:
                data_queue.put(('sleeping', None))
                print("\n💤 Device appears to have gone to sleep, trying to wake it...")
                # Try to wake it up again
                try:
                    wake_data = device.read(0x81, 64, timeout=2000)
                    if wake_data and any(wake_data):
                        consecutive_timeouts = 0
                        data_queue.put(('wake_success', list(wake_data)))
                except:
                    pass
                    
        except Exception as e:
            data_queue.put(('error', str(e)))
            break
    
    print("\n🛑 Keep-alive thread stopping...")

def monitor_with_finger_detection(device, duration=60):
    """Monitor device with finger detection"""
    print(f"\n👆 Starting {duration}-second monitoring with finger detection...")
    print("   🟢 Device is active - try placing/removing finger")
    print("   📊 Watching for data changes...")
    
    # Set up keep-alive thread
    data_queue = Queue()
    stop_event = threading.Event()
    
    keep_alive_thread = threading.Thread(
        target=keep_device_alive, 
        args=(device, data_queue, stop_event)
    )
    keep_alive_thread.start()
    
    # Monitor data
    start_time = time.time()
    last_data = None
    finger_events = 0
    total_data_packets = 0
    
    try:
        while time.time() - start_time < duration:
            try:
                # Get data from queue (non-blocking)
                event_type, data = data_queue.get(timeout=1)
                
                if event_type == 'data':
                    total_data_packets += 1
                    
                    # Check for significant changes (finger events)
                    if last_data is not None:
                        differences = sum(1 for a, b in zip(data, last_data) if a != b)
                        if differences > 15:  # Significant change threshold
                            finger_events += 1
                            print(f"\n👆 FINGER EVENT #{finger_events}!")
                            print(f"   📥 Data: {data[:8]}...")
                            print(f"   🔄 {differences} bytes changed from previous")
                            last_data = data
                    else:
                        print(f"\n📥 First data received: {data[:8]}...")
                        last_data = data
                    
                    # Periodic status update
                    if total_data_packets % 10 == 0:
                        remaining = int(duration - (time.time() - start_time))
                        print(f"   📊 Active: {total_data_packets} packets, {finger_events} finger events, {remaining}s left", end='\r')
                
                elif event_type == 'timeout':
                    if data == 1:  # First timeout
                        remaining = int(duration - (time.time() - start_time))
                        print(f"   ⏰ Waiting for activity... {remaining}s remaining", end='\r')
                
                elif event_type == 'sleeping':
                    print(f"\n💤 Device went to sleep after multiple timeouts")
                
                elif event_type == 'wake_success':
                    print(f"\n🔋 Device woke up again: {data[:8]}...")
                    last_data = data
                
                elif event_type == 'error':
                    print(f"\n❌ Device error: {data}")
                    break
                    
            except:
                # Queue timeout - continue monitoring
                remaining = int(duration - (time.time() - start_time))
                if remaining <= 0:
                    break
                    
    finally:
        # Stop keep-alive thread
        stop_event.set()
        keep_alive_thread.join(timeout=3)
    
    print(f"\n📊 Monitoring complete:")
    print(f"   📦 Total data packets: {total_data_packets}")
    print(f"   👆 Finger events detected: {finger_events}")
    print(f"   ⏱️  Duration: {duration} seconds")
    
    return finger_events > 0, total_data_packets > 0

def main():
    print("🚀 DigitalPersona Keep Alive Test")
    print("=" * 60)
    
    # Find device
    device = find_and_setup_device()
    if not device:
        return False
    
    # Initial wake up
    print("\n" + "="*60)
    print("🔋 INITIAL WAKE-UP")
    if not initial_wake_up(device):
        print("❌ Could not wake up device initially")
        return False
    
    print("✅ Device is now active!")
    print("\n📋 Instructions:")
    print("   1. Watch your device LED (should be on/blinking)")
    print("   2. Place your finger on the scanner")
    print("   3. Remove your finger")
    print("   4. Try multiple finger placements")
    
    # Monitor with finger detection
    print("\n" + "="*60)
    print("📊 ACTIVE MONITORING")
    
    finger_detected, device_active = monitor_with_finger_detection(device, 45)
    
    # Results
    print("\n" + "="*60)
    print("🔍 FINAL RESULTS:")
    
    if device_active:
        print("✅ Device remained active and sending data")
        if finger_detected:
            print("✅ Finger placement was detected!")
            print("🎉 SUCCESS: Fingerprint scanner is working!")
        else:
            print("⚠️  No finger events detected")
            print("   Try placing/removing finger more dramatically")
    else:
        print("❌ Device was not active during monitoring")
    
    print("\n🔍 Manual check:")
    print("   1. Is LED still on?")
    print("   2. Does device feel warm?")
    print("   3. Try touching scanner now")
    
    return finger_detected

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Keep-alive test successful!")
        else:
            print("\n⚠️  Test completed - check device status manually")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}") 