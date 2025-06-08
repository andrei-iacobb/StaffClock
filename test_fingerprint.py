#!/usr/bin/env python3
"""
Test script for DigitalPersona U.are.U 4500 Fingerprint Reader on Mac
"""

import sys
import os
import sqlite3
from fingerprint_manager import FingerprintManager, detect_digitalPersona_device

def test_device_detection():
    """Test if the DigitalPersona device is detected."""
    print("=== Testing Device Detection ===")
    
    detected, message = detect_digitalPersona_device()
    print(f"Device Detection: {'✅ PASS' if detected else '❌ FAIL'}")
    print(f"Message: {message}")
    print()
    
    return detected

def test_fingerprint_manager():
    """Test the FingerprintManager class."""
    print("=== Testing FingerprintManager ===")
    
    # Create a temporary database for testing
    test_db = "test_fingerprint.db"
    
    try:
        # Initialize the fingerprint manager
        fp_manager = FingerprintManager(test_db)
        print("✅ FingerprintManager initialized successfully")
        
        # Test device availability
        device_available = fp_manager.is_device_available()
        print(f"Device Available: {'✅ YES' if device_available else '❌ NO'}")
        
        # Create a test staff member
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        
        # Create staff table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                name TEXT NOT NULL,
                code TEXT UNIQUE PRIMARY KEY,
                fingerprint TEXT,
                role TEXT,
                notes TEXT
            )
        ''')
        
        # Add a test staff member
        c.execute('INSERT OR REPLACE INTO staff (name, code, role) VALUES (?, ?, ?)', 
                 ('Test User', '9999', 'Tester'))
        conn.commit()
        conn.close()
        
        print("✅ Test staff member created")
        
        # Test fingerprint enrollment (if device is available)
        if device_available:
            print("\n--- Testing Fingerprint Enrollment ---")
            print("Note: This would require actual finger placement on scanner")
            print("Enrollment test skipped in automated testing")
        else:
            print("⚠️  Fingerprint enrollment test skipped - device not available")
        
        print("✅ FingerprintManager tests completed")
        
    except Exception as e:
        print(f"❌ Error testing FingerprintManager: {e}")
        return False
    
    finally:
        # Clean up test database
        if os.path.exists(test_db):
            os.remove(test_db)
            print("🧹 Test database cleaned up")
    
    return True

def test_opencv_installation():
    """Test if OpenCV is properly installed."""
    print("=== Testing OpenCV Installation ===")
    
    try:
        import cv2
        print(f"✅ OpenCV version: {cv2.__version__}")
        
        # Test ORB detector (used for fingerprint feature extraction)
        orb = cv2.ORB_create()
        print("✅ ORB detector created successfully")
        
        # Test FLANN matcher (used for fingerprint comparison)
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        print("✅ FLANN matcher created successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ OpenCV import error: {e}")
        return False
    except Exception as e:
        print(f"❌ OpenCV test error: {e}")
        return False

def test_system_requirements():
    """Test system requirements."""
    print("=== Testing System Requirements ===")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major >= 3 and python_version.minor >= 8:
        print("✅ Python version compatible")
    else:
        print("❌ Python version too old (requires 3.8+)")
    
    # Check required modules
    required_modules = ['sqlite3', 'json', 'base64', 'subprocess', 'datetime']
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            print(f"❌ {module} not available")
    
    print()

def main():
    """Run all tests."""
    print("🔍 DigitalPersona U.are.U 4500 Fingerprint Reader Test Suite")
    print("=" * 60)
    
    # Test system requirements
    test_system_requirements()
    
    # Test OpenCV installation
    opencv_ok = test_opencv_installation()
    print()
    
    # Test device detection
    device_detected = test_device_detection()
    
    # Test fingerprint manager
    if opencv_ok:
        manager_ok = test_fingerprint_manager()
    else:
        print("⚠️  Skipping FingerprintManager tests - OpenCV not available")
        manager_ok = False
    
    # Summary
    print("=" * 60)
    print("🏁 TEST SUMMARY")
    print(f"Device Detected: {'✅ YES' if device_detected else '❌ NO'}")
    print(f"OpenCV Working: {'✅ YES' if opencv_ok else '❌ NO'}")
    print(f"Manager Tests: {'✅ PASS' if manager_ok else '❌ FAIL'}")
    
    if device_detected and opencv_ok and manager_ok:
        print("\n🎉 All tests passed! Fingerprint system is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
        
        if not device_detected:
            print("   • Ensure the DigitalPersona device is connected")
        if not opencv_ok:
            print("   • Install OpenCV: pip install opencv-python")
        if not manager_ok:
            print("   • Check the error messages above")

if __name__ == "__main__":
    main() 