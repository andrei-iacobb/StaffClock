#!/usr/bin/env python3
"""
Advanced Biometric Profile Enrollment System
Captures multiple fingerprint samples to build comprehensive biometric profiles
for high accuracy identification using DigitalPersona U.are.U 4500.
"""

import os
import sqlite3
import numpy as np
import cv2
import logging
import time
import hashlib
import pickle
import json
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from scipy import ndimage
import matplotlib.pyplot as plt

from digitalpersona_real import DigitalPersonaU4500

class BiometricProfileEnrollment:
    """Advanced biometric enrollment system with comprehensive profile building."""
    
    def __init__(self, db_path: str = "biometric_profiles.db", test_mode: bool = False):
        self.db_path = db_path
        self.device = DigitalPersonaU4500()
        self.required_samples = 5  # Number of samples needed for robust profile
        self.quality_threshold = 0.7  # Minimum quality score for acceptance
        self.similarity_threshold = 0.8  # Minimum similarity between samples
        self.test_mode = test_mode  # Test mode bypasses finger detection for demo
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._initialize_database()
        
        # Minutiae extraction parameters
        self.minutiae_params = {
            'ridge_threshold': 0.1,
            'bifurcation_threshold': 0.15,
            'min_minutiae': 10,
            'max_minutiae': 100
        }
    
    def _initialize_database(self):
        """Initialize the biometric profiles database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create enhanced biometric profiles table
            c.execute('''
                CREATE TABLE IF NOT EXISTS biometric_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_code TEXT UNIQUE NOT NULL,
                    staff_name TEXT NOT NULL,
                    enrollment_date TEXT NOT NULL,
                    profile_data BLOB NOT NULL,
                    quality_scores TEXT NOT NULL,
                    sample_count INTEGER NOT NULL,
                    minutiae_data BLOB,
                    fingerprint_class TEXT,
                    last_verification TEXT,
                    verification_count INTEGER DEFAULT 0,
                    false_rejection_rate REAL DEFAULT 0.0,
                    notes TEXT
                )
            ''')
            
            # Create enrollment samples table for tracking individual captures
            c.execute('''
                CREATE TABLE IF NOT EXISTS enrollment_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    sample_number INTEGER,
                    capture_timestamp TEXT,
                    image_data BLOB,
                    quality_score REAL,
                    minutiae_count INTEGER,
                    processing_time REAL,
                    FOREIGN KEY(profile_id) REFERENCES biometric_profiles(id)
                )
            ''')
            
            # Create verification logs table
            c.execute('''
                CREATE TABLE IF NOT EXISTS verification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_code TEXT,
                    verification_timestamp TEXT,
                    verification_result TEXT,
                    confidence_score REAL,
                    processing_time REAL,
                    device_status TEXT
                )
            ''')
            
            conn.commit()
            self.logger.info("Biometric database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()
    
    def connect_device(self) -> bool:
        """Connect to the DigitalPersona device."""
        try:
            success = self.device.connect()
            if success:
                self.logger.info("Successfully connected to DigitalPersona device")
                status = self.device.get_device_status()
                self.logger.info(f"Device status: {status}")
            else:
                self.logger.error("Failed to connect to DigitalPersona device")
            return success
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}")
            return False
    
    def enroll_biometric_profile(self, staff_code: str, staff_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enroll a comprehensive biometric profile by capturing multiple fingerprint samples.
        
        Returns:
            Tuple of (success, message, enrollment_stats)
        """
        try:
            self.logger.info(f"Starting biometric enrollment for {staff_name} ({staff_code})")
            
            if not self.device.connected:
                return False, "Device not connected", {}
            
            # Check if profile already exists
            if self._profile_exists(staff_code):
                return False, f"Biometric profile already exists for {staff_code}", {}
            
            # Collect multiple fingerprint samples
            samples = []
            quality_scores = []
            enrollment_stats = {
                'staff_code': staff_code,
                'staff_name': staff_name,
                'start_time': datetime.now().isoformat(),
                'samples_captured': 0,
                'average_quality': 0.0,
                'total_time': 0.0,
                'minutiae_count': 0
            }
            
            self.logger.info(f"Capturing {self.required_samples} fingerprint samples for enrollment...")
            
            for sample_num in range(1, self.required_samples + 1):
                self.logger.info(f"Capturing sample {sample_num}/{self.required_samples}")
                print(f"\n=== SAMPLE {sample_num}/{self.required_samples} ===")
                print(f"Please place your finger on the scanner for sample {sample_num}")
                
                # Capture fingerprint sample
                capture_start = time.time()
                
                if self.test_mode:
                    # Test mode: generate realistic fingerprint without waiting for finger
                    self.logger.info(f"Test mode: generating realistic fingerprint for sample {sample_num}")
                    print(f"TEST MODE: Generating realistic fingerprint sample {sample_num}...")
                    time.sleep(1)  # Simulate capture time
                    fingerprint_image = self.device._generate_realistic_fingerprint()
                else:
                    # Real mode: wait for actual finger detection
                    fingerprint_image = self.device.capture_fingerprint()
                
                capture_time = time.time() - capture_start
                
                if fingerprint_image is None:
                    self.logger.warning(f"Failed to capture sample {sample_num}")
                    print(f"Failed to capture sample {sample_num}. Please try again.")
                    continue
                
                # Analyze quality of captured sample
                quality_score = self._calculate_quality_score(fingerprint_image)
                self.logger.info(f"Sample {sample_num} quality score: {quality_score:.3f}")
                
                if quality_score < self.quality_threshold:
                    self.logger.warning(f"Sample {sample_num} quality too low ({quality_score:.3f})")
                    print(f"Sample quality too low ({quality_score:.3f}). Please try again.")
                    continue
                
                # Check similarity with existing samples
                if samples and not self._check_sample_consistency(fingerprint_image, samples):
                    self.logger.warning(f"Sample {sample_num} not consistent with previous samples")
                    print("Sample not consistent with previous captures. Please try again.")
                    continue
                
                # Extract minutiae from sample
                minutiae = self._extract_minutiae(fingerprint_image)
                
                # Store successful sample
                sample_data = {
                    'image': fingerprint_image,
                    'quality': quality_score,
                    'minutiae': minutiae,
                    'capture_time': capture_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                samples.append(sample_data)
                quality_scores.append(quality_score)
                enrollment_stats['samples_captured'] += 1
                
                print(f"✓ Sample {sample_num} captured successfully (Quality: {quality_score:.3f})")
                
                # Brief pause between samples
                if sample_num < self.required_samples:
                    print("Please lift your finger and place it again for the next sample...")
                    time.sleep(2)
            
            # Check if we have enough samples
            if len(samples) < self.required_samples:
                return False, f"Insufficient samples captured ({len(samples)}/{self.required_samples})", enrollment_stats
            
            # Build comprehensive biometric profile
            profile_data = self._build_biometric_profile(samples)
            
            # Calculate enrollment statistics
            enrollment_stats.update({
                'end_time': datetime.now().isoformat(),
                'average_quality': np.mean(quality_scores),
                'min_quality': np.min(quality_scores),
                'max_quality': np.max(quality_scores),
                'quality_std': np.std(quality_scores),
                'total_time': sum(s['capture_time'] for s in samples),
                'minutiae_count': np.mean([len(s['minutiae']) for s in samples])
            })
            
            # Store profile in database
            success = self._store_biometric_profile(
                staff_code, staff_name, profile_data, 
                quality_scores, samples, enrollment_stats
            )
            
            if success:
                message = f"Biometric profile enrolled successfully for {staff_name}"
                self.logger.info(message)
                print(f"\n🎉 {message}")
                print(f"   Average Quality: {enrollment_stats['average_quality']:.3f}")
                print(f"   Total Samples: {len(samples)}")
                print(f"   Minutiae Count: {enrollment_stats['minutiae_count']:.1f}")
            else:
                message = "Failed to store biometric profile"
                self.logger.error(message)
            
            return success, message, enrollment_stats
            
        except Exception as e:
            self.logger.error(f"Error during biometric enrollment: {e}")
            return False, f"Enrollment error: {str(e)}", enrollment_stats
    
    def _profile_exists(self, staff_code: str) -> bool:
        """Check if a biometric profile already exists for the given staff code."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if the table exists first
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='biometric_profiles'")
            if not c.fetchone():
                return False
            
            # Check if staff_code column exists
            c.execute("PRAGMA table_info(biometric_profiles)")
            columns = [column[1] for column in c.fetchall()]
            
            if 'staff_code' not in columns:
                # This is an old database, recreate it
                self.logger.warning("Old database schema detected, recreating...")
                c.execute("DROP TABLE IF EXISTS biometric_profiles")
                c.execute("DROP TABLE IF EXISTS enrollment_samples")
                c.execute("DROP TABLE IF EXISTS verification_logs")
                conn.commit()
                conn.close()
                self._initialize_database()
                return False
            
            c.execute("SELECT id FROM biometric_profiles WHERE staff_code = ?", (staff_code,))
            result = c.fetchone()
            return result is not None
        except Exception as e:
            self.logger.error(f"Error checking profile existence: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _calculate_quality_score(self, image: np.ndarray) -> float:
        """Calculate comprehensive quality score for fingerprint image."""
        try:
            # Normalize image
            if image.dtype != np.uint8:
                image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
            
            # Calculate multiple quality metrics
            scores = []
            
            # 1. Contrast and clarity
            contrast = np.std(image) / 255.0
            scores.append(min(contrast * 2, 1.0))
            
            # 2. Ridge clarity using gradient magnitude
            grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            ridge_clarity = np.mean(gradient_magnitude) / 128.0
            scores.append(min(ridge_clarity, 1.0))
            
            # 3. Focus measure using Laplacian variance
            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            focus_measure = np.var(laplacian) / 10000.0
            scores.append(min(focus_measure, 1.0))
            
            # 4. Check for sufficient ridge information
            # Use oriented gradients to detect ridge patterns
            angles = np.arctan2(grad_y, grad_x)
            ridge_consistency = 1.0 - (np.std(angles) / np.pi)
            scores.append(max(ridge_consistency, 0.0))
            
            # 5. Coverage - check for sufficient fingerprint area
            # Fingerprint area typically has higher gradient magnitudes
            high_gradient_pixels = np.sum(gradient_magnitude > np.mean(gradient_magnitude))
            coverage = high_gradient_pixels / image.size
            scores.append(min(coverage * 2, 1.0))
            
            # Combined quality score with weights
            weights = [0.2, 0.3, 0.2, 0.15, 0.15]  # Emphasize ridge clarity
            quality_score = np.average(scores, weights=weights)
            
            self.logger.debug(f"Quality components: contrast={scores[0]:.3f}, "
                            f"ridge_clarity={scores[1]:.3f}, focus={scores[2]:.3f}, "
                            f"consistency={scores[3]:.3f}, coverage={scores[4]:.3f}")
            
            return float(quality_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating quality score: {e}")
            return 0.0
    
    def _check_sample_consistency(self, new_sample: np.ndarray, existing_samples: List[Dict]) -> bool:
        """Check if new sample is consistent with existing samples."""
        try:
            # Extract features from new sample
            new_features = self._extract_image_features(new_sample)
            
            # Compare with existing samples
            similarities = []
            for sample in existing_samples:
                existing_features = self._extract_image_features(sample['image'])
                similarity = self._calculate_feature_similarity(new_features, existing_features)
                similarities.append(similarity)
            
            # Check if similarity is above threshold
            avg_similarity = np.mean(similarities)
            is_consistent = avg_similarity >= self.similarity_threshold
            
            self.logger.debug(f"Sample consistency: {avg_similarity:.3f} (threshold: {self.similarity_threshold})")
            return is_consistent
            
        except Exception as e:
            self.logger.error(f"Error checking sample consistency: {e}")
            return True  # Default to accepting if error occurs
    
    def _extract_image_features(self, image: np.ndarray) -> np.ndarray:
        """Extract features from fingerprint image for comparison."""
        try:
            # Resize to standard size for comparison
            resized = cv2.resize(image, (128, 128))
            
            # Extract multiple types of features
            features = []
            
            # 1. Intensity histogram
            hist = cv2.calcHist([resized], [0], None, [16], [0, 256])
            features.extend(hist.flatten())
            
            # 2. Local Binary Pattern (simplified)
            lbp_features = []
            for i in range(1, resized.shape[0]-1, 8):
                for j in range(1, resized.shape[1]-1, 8):
                    center = resized[i, j]
                    pattern = 0
                    pattern |= (resized[i-1, j-1] >= center) << 7
                    pattern |= (resized[i-1, j] >= center) << 6
                    pattern |= (resized[i-1, j+1] >= center) << 5
                    pattern |= (resized[i, j+1] >= center) << 4
                    pattern |= (resized[i+1, j+1] >= center) << 3
                    pattern |= (resized[i+1, j] >= center) << 2
                    pattern |= (resized[i+1, j-1] >= center) << 1
                    pattern |= (resized[i, j-1] >= center) << 0
                    lbp_features.append(pattern)
            
            features.extend(lbp_features[:32])  # Limit to 32 features
            
            # 3. Gradient features
            grad_x = cv2.Sobel(resized, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(resized, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Sample gradient features
            for i in range(0, resized.shape[0], 16):
                for j in range(0, resized.shape[1], 16):
                    features.append(gradient_magnitude[i, j])
            
            return np.array(features[:128])  # Fixed feature vector size
            
        except Exception as e:
            self.logger.error(f"Error extracting image features: {e}")
            return np.zeros(128)  # Return zero vector on error
    
    def _calculate_feature_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate similarity between two feature vectors."""
        try:
            # Normalize features
            features1_norm = features1 / (np.linalg.norm(features1) + 1e-8)
            features2_norm = features2 / (np.linalg.norm(features2) + 1e-8)
            
            # Calculate cosine similarity
            similarity = np.dot(features1_norm, features2_norm)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating feature similarity: {e}")
            return 0.0
    
    def _extract_minutiae(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Extract minutiae points (ridge endings and bifurcations) from fingerprint."""
        try:
            # Preprocess image
            if image.dtype != np.uint8:
                image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(image, (5, 5), 1.0)
            
            # Calculate gradients
            grad_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude and orientation
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            orientation = np.arctan2(grad_y, grad_x)
            
            # Find potential minutiae points
            minutiae = []
            
            # Ridge endings detection (simplified)
            ridge_threshold = np.mean(magnitude) + np.std(magnitude)
            for y in range(8, image.shape[0] - 8):
                for x in range(8, image.shape[1] - 8):
                    if magnitude[y, x] > ridge_threshold:
                        # Check local neighborhood for ridge ending pattern
                        local_region = magnitude[y-3:y+4, x-3:x+4]
                        if self._is_ridge_ending(local_region):
                            minutiae.append({
                                'type': 'ending',
                                'x': x,
                                'y': y,
                                'orientation': orientation[y, x],
                                'quality': magnitude[y, x] / ridge_threshold
                            })
                        elif self._is_bifurcation(local_region):
                            minutiae.append({
                                'type': 'bifurcation',
                                'x': x,
                                'y': y,
                                'orientation': orientation[y, x],
                                'quality': magnitude[y, x] / ridge_threshold
                            })
            
            # Sort by quality and limit number
            minutiae.sort(key=lambda m: m['quality'], reverse=True)
            minutiae = minutiae[:self.minutiae_params['max_minutiae']]
            
            self.logger.debug(f"Extracted {len(minutiae)} minutiae points")
            return minutiae
            
        except Exception as e:
            self.logger.error(f"Error extracting minutiae: {e}")
            return []
    
    def _is_ridge_ending(self, region: np.ndarray) -> bool:
        """Check if region contains a ridge ending pattern."""
        center = region[3, 3]
        # Simplified ridge ending detection
        high_pixels = np.sum(region > center * 0.8)
        return 2 <= high_pixels <= 4
    
    def _is_bifurcation(self, region: np.ndarray) -> bool:
        """Check if region contains a bifurcation pattern."""
        center = region[3, 3]
        # Simplified bifurcation detection
        high_pixels = np.sum(region > center * 0.8)
        return 5 <= high_pixels <= 8
    
    def _build_biometric_profile(self, samples: List[Dict]) -> Dict[str, Any]:
        """Build comprehensive biometric profile from multiple samples."""
        try:
            profile = {
                'version': '1.0',
                'creation_date': datetime.now().isoformat(),
                'sample_count': len(samples),
                'template_type': 'multi_sample_composite'
            }
            
            # Combine features from all samples
            all_features = []
            all_minutiae = []
            
            for sample in samples:
                # Extract and store features
                features = self._extract_image_features(sample['image'])
                all_features.append(features)
                
                # Combine minutiae
                all_minutiae.extend(sample['minutiae'])
            
            # Create composite feature template
            composite_features = np.mean(all_features, axis=0)
            feature_variance = np.var(all_features, axis=0)
            
            profile['composite_features'] = composite_features.tolist()
            profile['feature_variance'] = feature_variance.tolist()
            
            # Create minutiae template
            # Group similar minutiae and create stable points
            stable_minutiae = self._create_stable_minutiae_template(all_minutiae)
            profile['minutiae_template'] = stable_minutiae
            
            # Calculate profile statistics
            profile['statistics'] = {
                'total_minutiae': len(all_minutiae),
                'stable_minutiae': len(stable_minutiae),
                'feature_dimensions': len(composite_features),
                'quality_scores': [s['quality'] for s in samples]
            }
            
            self.logger.info(f"Built biometric profile with {len(stable_minutiae)} stable minutiae")
            return profile
            
        except Exception as e:
            self.logger.error(f"Error building biometric profile: {e}")
            return {}
    
    def _create_stable_minutiae_template(self, all_minutiae: List[Dict]) -> List[Dict]:
        """Create stable minutiae template from multiple samples."""
        try:
            # Group minutiae by spatial proximity
            groups = []
            used = set()
            
            for i, minutia in enumerate(all_minutiae):
                if i in used:
                    continue
                
                group = [minutia]
                used.add(i)
                
                # Find nearby minutiae in other samples
                for j, other in enumerate(all_minutiae):
                    if j in used:
                        continue
                    
                    # Check spatial distance
                    dx = minutia['x'] - other['x']
                    dy = minutia['y'] - other['y']
                    distance = np.sqrt(dx*dx + dy*dy)
                    
                    # Check orientation similarity
                    angle_diff = abs(minutia['orientation'] - other['orientation'])
                    angle_diff = min(angle_diff, 2*np.pi - angle_diff)
                    
                    if distance < 10 and angle_diff < 0.5:  # Thresholds for grouping
                        group.append(other)
                        used.add(j)
                
                if len(group) >= 2:  # Only include stable minutiae
                    groups.append(group)
            
            # Create stable minutiae from groups
            stable_minutiae = []
            for group in groups:
                stable_point = {
                    'type': group[0]['type'],  # Use type from first minutia
                    'x': np.mean([m['x'] for m in group]),
                    'y': np.mean([m['y'] for m in group]),
                    'orientation': np.mean([m['orientation'] for m in group]),
                    'quality': np.mean([m['quality'] for m in group]),
                    'stability': len(group) / len(all_minutiae),  # Stability score
                    'sample_count': len(group)
                }
                stable_minutiae.append(stable_point)
            
            # Sort by stability and quality
            stable_minutiae.sort(key=lambda m: m['stability'] * m['quality'], reverse=True)
            
            return stable_minutiae[:50]  # Limit to top 50 stable minutiae
            
        except Exception as e:
            self.logger.error(f"Error creating stable minutiae template: {e}")
            return []
    
    def _store_biometric_profile(self, staff_code: str, staff_name: str, 
                                profile_data: Dict, quality_scores: List[float],
                                samples: List[Dict], stats: Dict) -> bool:
        """Store biometric profile and samples in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Serialize profile data
            profile_blob = pickle.dumps(profile_data)
            quality_json = json.dumps(quality_scores)
            minutiae_blob = pickle.dumps(profile_data.get('minutiae_template', []))
            
            # Insert main profile
            c.execute('''
                INSERT INTO biometric_profiles 
                (staff_code, staff_name, enrollment_date, profile_data, 
                 quality_scores, sample_count, minutiae_data, fingerprint_class, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                staff_code, staff_name, datetime.now().isoformat(),
                profile_blob, quality_json, len(samples), minutiae_blob,
                'Unknown', f"Enrolled with {len(samples)} samples"
            ))
            
            profile_id = c.lastrowid
            
            # Store individual samples
            for i, sample in enumerate(samples):
                image_blob = pickle.dumps(sample['image'])
                c.execute('''
                    INSERT INTO enrollment_samples
                    (profile_id, sample_number, capture_timestamp, image_data,
                     quality_score, minutiae_count, processing_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    profile_id, i + 1, sample['timestamp'], image_blob,
                    sample['quality'], len(sample['minutiae']), sample['capture_time']
                ))
            
            conn.commit()
            self.logger.info(f"Stored biometric profile for {staff_code} with {len(samples)} samples")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing biometric profile: {e}")
            return False
        finally:
            conn.close()
    
    def verify_biometric(self, captured_image: np.ndarray) -> Tuple[Optional[str], float, str]:
        """
        Verify captured fingerprint against enrolled profiles.
        
        Returns:
            Tuple of (staff_code, confidence_score, message)
        """
        try:
            start_time = time.time()
            
            # Extract features from captured image
            captured_features = self._extract_image_features(captured_image)
            captured_minutiae = self._extract_minutiae(captured_image)
            
            # Get all enrolled profiles
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT staff_code, staff_name, profile_data FROM biometric_profiles")
            profiles = c.fetchall()
            conn.close()
            
            if not profiles:
                return None, 0.0, "No enrolled profiles found"
            
            # Compare against each profile
            best_match = None
            best_score = 0.0
            
            for staff_code, staff_name, profile_blob in profiles:
                try:
                    profile_data = pickle.loads(profile_blob)
                    
                    # Compare features
                    profile_features = np.array(profile_data['composite_features'])
                    feature_similarity = self._calculate_feature_similarity(captured_features, profile_features)
                    
                    # Compare minutiae
                    minutiae_similarity = self._compare_minutiae(captured_minutiae, profile_data['minutiae_template'])
                    
                    # Combined score
                    combined_score = (feature_similarity * 0.6 + minutiae_similarity * 0.4)
                    
                    self.logger.debug(f"Profile {staff_code}: feature={feature_similarity:.3f}, "
                                    f"minutiae={minutiae_similarity:.3f}, combined={combined_score:.3f}")
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = staff_code
                        
                except Exception as e:
                    self.logger.warning(f"Error comparing with profile {staff_code}: {e}")
                    continue
            
            # Log verification attempt
            processing_time = time.time() - start_time
            self._log_verification(best_match, best_score, processing_time)
            
            # Determine result
            if best_score >= 0.8:  # High confidence threshold
                return best_match, best_score, f"Verified with high confidence"
            elif best_score >= 0.6:  # Medium confidence threshold
                return best_match, best_score, f"Verified with medium confidence"
            else:
                return None, best_score, f"No match found (best score: {best_score:.3f})"
            
        except Exception as e:
            self.logger.error(f"Error during biometric verification: {e}")
            return None, 0.0, f"Verification error: {str(e)}"
    
    def _compare_minutiae(self, captured_minutiae: List[Dict], template_minutiae: List[Dict]) -> float:
        """Compare captured minutiae with template minutiae."""
        try:
            if not captured_minutiae or not template_minutiae:
                return 0.0
            
            # Find matching minutiae
            matches = 0
            total_template = len(template_minutiae)
            
            for template_point in template_minutiae:
                best_match_score = 0.0
                
                for captured_point in captured_minutiae:
                    # Calculate spatial distance
                    dx = template_point['x'] - captured_point['x']
                    dy = template_point['y'] - captured_point['y']
                    distance = np.sqrt(dx*dx + dy*dy)
                    
                    # Calculate orientation difference
                    angle_diff = abs(template_point['orientation'] - captured_point['orientation'])
                    angle_diff = min(angle_diff, 2*np.pi - angle_diff)
                    
                    # Calculate match score
                    if distance < 15 and angle_diff < 0.7 and template_point['type'] == captured_point['type']:
                        spatial_score = max(0, 1.0 - distance / 15.0)
                        orientation_score = max(0, 1.0 - angle_diff / 0.7)
                        match_score = spatial_score * orientation_score
                        best_match_score = max(best_match_score, match_score)
                
                if best_match_score > 0.7:  # Threshold for considering a match
                    matches += 1
            
            # Calculate similarity ratio
            similarity = matches / total_template if total_template > 0 else 0.0
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error comparing minutiae: {e}")
            return 0.0
    
    def _log_verification(self, staff_code: Optional[str], confidence: float, processing_time: float):
        """Log verification attempt."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            result = "SUCCESS" if staff_code else "FAILURE"
            device_status = json.dumps(self.device.get_device_status())
            
            c.execute('''
                INSERT INTO verification_logs
                (staff_code, verification_timestamp, verification_result, 
                 confidence_score, processing_time, device_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                staff_code, datetime.now().isoformat(), result,
                confidence, processing_time, device_status
            ))
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging verification: {e}")
        finally:
            conn.close()
    
    def get_enrollment_statistics(self) -> Dict[str, Any]:
        """Get comprehensive enrollment statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Basic counts
            c.execute("SELECT COUNT(*) FROM biometric_profiles")
            total_profiles = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM enrollment_samples")
            total_samples = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM verification_logs")
            total_verifications = c.fetchone()[0]
            
            # Quality statistics
            c.execute("SELECT quality_scores FROM biometric_profiles")
            quality_data = []
            for row in c.fetchall():
                try:
                    scores = json.loads(row[0])
                    quality_data.extend(scores)
                except:
                    pass
            
            # Verification success rate
            c.execute("SELECT COUNT(*) FROM verification_logs WHERE verification_result = 'SUCCESS'")
            successful_verifications = c.fetchone()[0]
            
            success_rate = (successful_verifications / total_verifications * 100) if total_verifications > 0 else 0
            
            stats = {
                'total_profiles': total_profiles,
                'total_samples': total_samples,
                'total_verifications': total_verifications,
                'verification_success_rate': success_rate,
                'average_quality': np.mean(quality_data) if quality_data else 0,
                'min_quality': np.min(quality_data) if quality_data else 0,
                'max_quality': np.max(quality_data) if quality_data else 0,
                'quality_std': np.std(quality_data) if quality_data else 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting enrollment statistics: {e}")
            return {}
        finally:
            conn.close()
    
    def remove_profile(self, staff_code: str) -> bool:
        """Remove biometric profile and all associated data."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get profile ID
            c.execute("SELECT id FROM biometric_profiles WHERE staff_code = ?", (staff_code,))
            result = c.fetchone()
            
            if not result:
                return False
            
            profile_id = result[0]
            
            # Delete samples
            c.execute("DELETE FROM enrollment_samples WHERE profile_id = ?", (profile_id,))
            
            # Delete profile
            c.execute("DELETE FROM biometric_profiles WHERE id = ?", (profile_id,))
            
            # Delete verification logs
            c.execute("DELETE FROM verification_logs WHERE staff_code = ?", (staff_code,))
            
            conn.commit()
            self.logger.info(f"Removed biometric profile for {staff_code}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing profile: {e}")
            return False
        finally:
            conn.close()
    
    def disconnect(self):
        """Disconnect from the device."""
        self.device.disconnect()


def test_enrollment():
    """Test the biometric enrollment system."""
    print("=== TESTING ADVANCED BIOMETRIC ENROLLMENT SYSTEM ===")
    
    # Ask user which mode to test
    print("\nSelect test mode:")
    print("1. TEST MODE - Generate realistic fingerprints automatically (for demonstration)")
    print("2. REAL MODE - Wait for actual finger placement (requires physical interaction)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    test_mode = choice == "1"
    
    if test_mode:
        print("✓ TEST MODE selected - will generate realistic biometric profiles automatically")
    else:
        print("✓ REAL MODE selected - will wait for actual finger placement")
    
    # Create enrollment system
    enrollment = BiometricProfileEnrollment(test_mode=test_mode)
    
    # Test device connection
    print("\nConnecting to DigitalPersona device...")
    if enrollment.connect_device():
        print("✓ Device connected for enrollment")
        
        # Test enrollment process
        print(f"\nStarting biometric enrollment in {'TEST' if test_mode else 'REAL'} mode...")
        if test_mode:
            print("This will automatically generate 5 realistic fingerprint samples.")
        else:
            print("This will capture 5 fingerprint samples - place your finger when prompted.")
        
        staff_code = "TEST001"
        staff_name = "Test User"
        
        success, message, stats = enrollment.enroll_biometric_profile(staff_code, staff_name)
        
        if success:
            print(f"\n🎉 {message}")
            print("\nEnrollment Statistics:")
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")
            
            # Test verification with a new sample
            print(f"\n=== TESTING VERIFICATION IN {'TEST' if test_mode else 'REAL'} MODE ===")
            if test_mode:
                print("Generating test fingerprint for verification...")
                verification_image = enrollment.device._generate_realistic_fingerprint()
            else:
                print("Place your finger for verification test...")
                verification_image = enrollment.device.capture_fingerprint()
            
            if verification_image is not None:
                result_code, confidence, msg = enrollment.verify_biometric(verification_image)
                print(f"Verification result: {msg}")
                print(f"Staff code: {result_code}")
                print(f"Confidence: {confidence:.3f}")
            
            # Show overall statistics
            overall_stats = enrollment.get_enrollment_statistics()
            print("\nOverall System Statistics:")
            for key, value in overall_stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")
                    
        else:
            print(f"\n❌ Enrollment failed: {message}")
        
        enrollment.disconnect()
    else:
        print("✗ Failed to connect to device")

if __name__ == "__main__":
    test_enrollment() 