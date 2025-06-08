#!/usr/bin/env python3
"""
Test script to activate DigitalPersona device and verify LED status
"""

import time
from digitalpersona_driver import DigitalPersonaU4500

def test_device_led():
    print('🔍 Checking DigitalPersona device status...')
    device = DigitalPersonaU4500()
    
    # Connect to device
    connected, message = device.connect()
    print(f'Connection: {"✅ SUCCESS" if connected else "❌ FAILED"}')
    print(f'Message: {message}')

    if connected:
        info = device.get_device_info()
        print(f'LED Status: {info["led_status"]}')
        print('✨ Device should now have BLUE LED active!')
        print('Check your fingerprint scanner - the LED should be glowing BLUE')
        
        # Test capture cycle
        print('\n🔄 Testing capture cycle...')
        fingerprint, capture_message = device.capture_fingerprint()
        print(f'Capture result: {capture_message}')
        
        if fingerprint is not None:
            print(f'Fingerprint shape: {fingerprint.shape}')
            print('✅ Capture successful')
        
        print('\n📴 Disconnecting device...')
        device.disconnect()
        print('Device disconnected - LED should turn OFF')
        print('Check your scanner - the LED should now be OFF')
    else:
        print('❌ Device connection failed')

if __name__ == "__main__":
    test_device_led() 