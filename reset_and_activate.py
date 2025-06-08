#!/usr/bin/env python3
"""
DigitalPersona Reset and Activate Test
Focus: Reset device and try multiple activation methods
"""

import usb.core
import usb.util
import time
import sys
import subprocess

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
    return device

def reset_device(device):
    """Try to reset the USB device"""
    print("\n🔄 Attempting USB reset...")
    
    try:
        device.reset()
        print("✅ USB reset successful")
        time.sleep(2)  # Wait for device to reinitialize
        return True
    except Exception as e:
        print(f"❌ USB reset failed: {e}")
        return False

def try_multiple_configurations(device):
    """Try different USB configurations"""
    print("\n⚙️  Trying different configurations...")
    
    try:
        # Get all configurations
        configs = [cfg for cfg in device]
        print(f"   Available configurations: {len(configs)}")
        
        for i, cfg in enumerate(configs):
            try:
                print(f"   Trying configuration {i}: {cfg.bConfigurationValue}")
                device.set_configuration(cfg.bConfigurationValue)
                time.sleep(0.5)
                
                # Try to read after each configuration
                try:
                    data = device.read(0x81, 64, timeout=1000)
                    if data and any(data):
                        print(f"✅ Configuration {i} worked! Data: {list(data[:8])}...")
                        return True
                except usb.core.USBTimeoutError:
                    print(f"   ⏰ Configuration {i}: No immediate response")
                except Exception as e:
                    print(f"   ❌ Configuration {i}: {e}")
                    
            except Exception as e:
                print(f"   ❌ Failed to set configuration {i}: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ Configuration enumeration failed: {e}")
        return False

def try_claim_all_interfaces(device):
    """Try to claim all available interfaces"""
    print("\n🤝 Claiming all interfaces...")
    
    try:
        cfg = device.get_active_configuration()
        interfaces = [intf for intf in cfg]
        
        print(f"   Found {len(interfaces)} interfaces")
        
        for intf in interfaces:
            try:
                print(f"   Claiming interface {intf.bInterfaceNumber}")
                usb.util.claim_interface(device, intf.bInterfaceNumber)
                print(f"   ✅ Interface {intf.bInterfaceNumber} claimed")
            except Exception as e:
                print(f"   ❌ Failed to claim interface {intf.bInterfaceNumber}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Interface claiming failed: {e}")
        return False

def aggressive_continuous_read(device, duration=30):
    """Aggressively and continuously try to read from the device"""
    print(f"\n🔥 Aggressive continuous read for {duration} seconds...")
    print("   This will hammer the device with read requests")
    
    start_time = time.time()
    read_attempts = 0
    successful_reads = 0
    first_success = None
    
    while time.time() - start_time < duration:
        read_attempts += 1
        
        try:
            # Try reading with very short timeout
            data = device.read(0x81, 64, timeout=100)
            successful_reads += 1
            
            if first_success is None:
                first_success = time.time() - start_time
                print(f"\n🎉 FIRST SUCCESS after {first_success:.1f}s!")
                print(f"   Data: {list(data[:16])}...")
                print("   🔥 Keep placing/removing finger on scanner!")
            
            # Check for data changes (finger events)
            if successful_reads > 1 and any(data):
                remaining = int(duration - (time.time() - start_time))
                print(f"   📊 Read #{successful_reads}: {list(data[:4])}... ({remaining}s left)", end='\r')
            
        except usb.core.USBTimeoutError:
            # Expected when no data
            if read_attempts % 100 == 0:  # Every 100 attempts
                remaining = int(duration - (time.time() - start_time))
                print(f"   🔄 Attempt {read_attempts}, {successful_reads} successes, {remaining}s left", end='\r')
                
        except Exception as e:
            print(f"\n❌ Read error after {read_attempts} attempts: {e}")
            break
    
    print(f"\n📊 Aggressive read complete:")
    print(f"   🔄 Total attempts: {read_attempts}")
    print(f"   ✅ Successful reads: {successful_reads}")
    if first_success:
        print(f"   ⏱️  First success after: {first_success:.1f}s")
    
    return successful_reads > 0

def check_device_power_state():
    """Check if device is drawing power properly"""
    print("\n⚡ Checking device power state...")
    
    try:
        result = subprocess.run([
            'system_profiler', 'SPUSBDataType'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            output = result.stdout
            if "U.are.U" in output:
                print("✅ Device visible in system profiler")
                
                # Extract power info
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if "U.are.U" in line:
                        # Look for power info in next few lines
                        for j in range(i, min(i+15, len(lines))):
                            if "Current Required" in lines[j]:
                                print(f"   {lines[j].strip()}")
                            elif "Current Available" in lines[j]:
                                print(f"   {lines[j].strip()}")
                return True
        
        print("❌ Device not found in system profiler")
        return False
        
    except Exception as e:
        print(f"❌ Power check failed: {e}")
        return False

def main():
    print("🚀 DigitalPersona Reset and Activate Test")
    print("=" * 60)
    
    # Check power state first
    check_device_power_state()
    
    # Find device
    device = find_device()
    if not device:
        return False
    
    # Try reset
    print("\n" + "="*60)
    print("🔄 RESET PHASE")
    reset_device(device)
    
    # Re-find device after reset
    time.sleep(1)
    device = find_device()
    if not device:
        print("❌ Device not found after reset")
        return False
    
    # Try different configurations
    print("\n" + "="*60)
    print("⚙️  CONFIGURATION PHASE")
    config_success = try_multiple_configurations(device)
    
    if config_success:
        print("✅ Device responded during configuration!")
        return True
    
    # Try claiming interfaces
    print("\n" + "="*60)
    print("🤝 INTERFACE CLAIMING PHASE")
    try_claim_all_interfaces(device)
    
    # Aggressive read attempt
    print("\n" + "="*60)
    print("🔥 AGGRESSIVE READ PHASE")
    print("👆 PLACE YOUR FINGER ON THE SCANNER NOW!")
    
    read_success = aggressive_continuous_read(device, 45)
    
    # Final status
    print("\n" + "="*60)
    print("🔍 FINAL STATUS:")
    
    if read_success:
        print("✅ Device activated and responding!")
        print("🎉 SUCCESS: Scanner is working!")
    else:
        print("❌ Device did not respond to any activation attempts")
        print("⚠️  Device may require:")
        print("   - Specific driver software")
        print("   - Different activation sequence")
        print("   - Windows/specific OS environment")
    
    # Manual check
    print("\n🔍 Manual verification:")
    print("   1. Is the LED on or blinking?")
    print("   2. Does the device feel warm?")
    print("   3. Did you see any LED activity during the test?")
    
    return read_success

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Reset and activation successful!")
        else:
            print("\n⚠️  Device activation unsuccessful")
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}") 