#!/usr/bin/env python3
"""
Test script for biometric enrollment system.
"""

from biometric_enrollment import BiometricEnrollment
import logging

logging.basicConfig(level=logging.INFO)

def test_enrollment():
    """Test the biometric enrollment system."""
    print("=== TESTING BIOMETRIC ENROLLMENT SYSTEM ===")
    
    # Create enrollment system
    enrollment = BiometricEnrollment()
    
    # Test device connection
    print("Connecting to DigitalPersona device...")
    if enrollment.connect_device():
        print("✓ Device connected for enrollment")
        
        # Test enrollment process
        print("\nStarting test enrollment...")
        print("This will capture 5 fingerprint samples for a test user.")
        
        success, message, stats = enrollment.enroll_user('test_user_001', 'Test Employee')
        
        print(f"\nEnrollment Result: {success}")
        print(f"Message: {message}")
        if stats:
            print(f"Stats: {stats}")
        
        # Clean up
        enrollment.disconnect_device()
        print("✓ Device disconnected")
        
    else:
        print("✗ Failed to connect to device")
        return False
    
    return success

if __name__ == "__main__":
    test_enrollment() 