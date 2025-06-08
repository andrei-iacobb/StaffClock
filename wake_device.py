#!/usr/bin/env python3
"""
DigitalPersona Wake-up Test
Focus: Try to wake up the device by simply reading from it
"""

import usb.core
import usb.util
import time
import sys
import threading

# DigitalPersona U.are.U 4500 device identifiers
VENDOR_ID = 0x05ba  # DigitalPersona/HID Global
PRODUCT_ID = 0x000a  # U.are.U 4500

def find_device():
    """Find the DigitalPersona device"""
    print("🔍 Finding DigitalPersona device...")
    
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        print("❌ Device not found!")
        return None
    
    print("✅ Device found!")
    print(f"   Manufacturer: {usb.util.get_string(device, device.iManufacturer)}")
    print(f"   Product: {usb.util.get_string(device, device.iProduct)}")
    print(f"   Serial: {usb.util.get_string(device, device.iSerialNumber)}")
    
    return device

def setup_device(device):
    """Set up the device for communication"""
    print("\n🔧 Setting up device...")
    
    try:
        device.set_configuration()
        print("✅ Configuration set successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to set configuration: {e}")
        return False

def continuous_read_interrupt(device, duration=30):
    """Continuously read from interrupt endpoint to try to wake device"""
    print(f"\n📡 Starting continuous read from interrupt endpoint (0x81) for {duration} seconds...")
    print("   This should wake up the device and potentially turn on the LED")
    
    start_time = time.time()
    read_count = 0
    
    while time.time() - start_time < duration:
        try:
            # Try to read from interrupt endpoint 0x81
            data = device.read(0x81, 64, timeout=1000)
            read_count += 1
            
            if data and any(data):  # If we got non-zero data
                print(f"\n📥 Data received (read #{read_count}): {list(data[:16])}...")
                print("🎉 Device is responding! LED should be active now!")
                return True
            else:
                remaining = int(duration - (time.time() - start_time))
                print(f"   📊 Read #{read_count}, {remaining}s remaining, no data yet...", end='\r')
                
        except usb.core.USBTimeoutError:
            # This is expected when no data is available
            remaining = int(duration - (time.time() - start_time))
            print(f"   ⏰ Waiting for device response... {remaining}s remaining", end='\r')
            
        except Exception as e:
            print(f"\n❌ Read error: {e}")
            break
    
    print(f"\n📊 Completed {read_count} read attempts")
    return False

def continuous_read_bulk(device, duration=30):
    """Continuously read from bulk endpoint to try to wake device"""
    print(f"\n📡 Starting continuous read from bulk endpoint (0x82) for {duration} seconds...")
    
    start_time = time.time()
    read_count = 0
    
    while time.time() - start_time < duration:
        try:
            # Try to read from bulk endpoint 0x82
            data = device.read(0x82, 64, timeout=1000)
            read_count += 1
            
            if data and any(data):  # If we got non-zero data
                print(f"\n📥 Bulk data received (read #{read_count}): {list(data[:16])}...")
                print("🎉 Device is responding via bulk endpoint!")
                return True
            else:
                remaining = int(duration - (time.time() - start_time))
                print(f"   📊 Bulk read #{read_count}, {remaining}s remaining...", end='\r')
                
        except usb.core.USBTimeoutError:
            remaining = int(duration - (time.time() - start_time))
            print(f"   ⏰ Bulk waiting... {remaining}s remaining", end='\r')
            
        except Exception as e:
            print(f"\n❌ Bulk read error: {e}")
            break
    
    print(f"\n📊 Completed {read_count} bulk read attempts")
    return False

def parallel_read_test(device, duration=20):
    """Try reading from both endpoints in parallel"""
    print(f"\n🔄 Running parallel read test for {duration} seconds...")
    print("   This simulates what fingerprint software typically does")
    
    interrupt_active = threading.Event()
    bulk_active = threading.Event()
    results = {'interrupt': False, 'bulk': False}
    
    def interrupt_reader():
        try:
            start_time = time.time()
            while time.time() - start_time < duration and not interrupt_active.is_set():
                try:
                    data = device.read(0x81, 64, timeout=500)
                    if data and any(data):
                        print(f"\n🎯 Interrupt data: {list(data[:8])}...")
                        results['interrupt'] = True
                        interrupt_active.set()
                        return
                except usb.core.USBTimeoutError:
                    pass
        except Exception as e:
            print(f"\n❌ Interrupt thread error: {e}")
    
    def bulk_reader():
        try:
            start_time = time.time()
            while time.time() - start_time < duration and not bulk_active.is_set():
                try:
                    data = device.read(0x82, 64, timeout=500)
                    if data and any(data):
                        print(f"\n🎯 Bulk data: {list(data[:8])}...")
                        results['bulk'] = True
                        bulk_active.set()
                        return
                except usb.core.USBTimeoutError:
                    pass
        except Exception as e:
            print(f"\n❌ Bulk thread error: {e}")
    
    # Start both reading threads
    interrupt_thread = threading.Thread(target=interrupt_reader)
    bulk_thread = threading.Thread(target=bulk_reader)
    
    interrupt_thread.start()
    bulk_thread.start()
    
    # Monitor progress
    start_time = time.time()
    while time.time() - start_time < duration:
        if interrupt_active.is_set() or bulk_active.is_set():
            break
        remaining = int(duration - (time.time() - start_time))
        print(f"   🔄 Parallel reading... {remaining}s remaining", end='\r')
        time.sleep(1)
    
    # Signal threads to stop
    interrupt_active.set()
    bulk_active.set()
    
    # Wait for threads to finish
    interrupt_thread.join(timeout=2)
    bulk_thread.join(timeout=2)
    
    print(f"\n📊 Parallel test results:")
    print(f"   Interrupt endpoint response: {'✅' if results['interrupt'] else '❌'}")
    print(f"   Bulk endpoint response: {'✅' if results['bulk'] else '❌'}")
    
    return results['interrupt'] or results['bulk']

def main():
    print("🚀 DigitalPersona Wake-up Test")
    print("=" * 50)
    print("Goal: Wake up the device by reading from it")
    print("Expected: LED should turn on when device becomes active")
    
    # Find device
    device = find_device()
    if not device:
        return False
    
    # Setup device
    if not setup_device(device):
        return False
    
    print("\n👀 LOOK AT YOUR DEVICE NOW!")
    print("   Watch for ANY LED activity during the following tests:")
    
    # Test 1: Interrupt endpoint continuous read
    print("\n" + "="*50)
    print("TEST 1: Interrupt Endpoint Wake-up")
    success1 = continuous_read_interrupt(device, 15)
    
    if success1:
        print("🎉 SUCCESS! Device responded to interrupt reads!")
        return True
    
    # Test 2: Bulk endpoint continuous read
    print("\n" + "="*50)
    print("TEST 2: Bulk Endpoint Wake-up")
    success2 = continuous_read_bulk(device, 15)
    
    if success2:
        print("🎉 SUCCESS! Device responded to bulk reads!")
        return True
    
    # Test 3: Parallel reading
    print("\n" + "="*50)
    print("TEST 3: Parallel Endpoint Reading")
    success3 = parallel_read_test(device, 20)
    
    if success3:
        print("🎉 SUCCESS! Device responded to parallel reads!")
        return True
    
    print("\n❌ Device did not respond to any wake-up attempts")
    print("   However, the attempts themselves might have activated it")
    print("   Check if the LED is now on or if the device feels warm")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        print("\n" + "="*50)
        print("🔍 FINAL CHECK:")
        print("   1. Is the LED on or blinking?")
        print("   2. Does the device feel slightly warm?")
        print("   3. Try placing a finger on the scanner")
        if success:
            print("✅ Test indicated device activation!")
        else:
            print("⚠️  Device may still be inactive")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}") 