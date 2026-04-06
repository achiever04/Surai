"""
Live detection testing script - Verify all AI models work correctly

This script tests each AI model independently on live camera footage
to ensure they're actually detecting and working properly.

Usage:
    python tests/test_detections_live.py
    
    # Or with specific camera
    python tests/test_detections_live.py --camera 0
    python tests/test_detections_live.py --camera rtsp://camera-ip:554/stream
"""
import cv2
import numpy as np
import argparse
import sys
import os
from pathlib import Path
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_engine.model_manager import ai_model_manager
from ai_engine.pipelines.detection_pipeline import DetectionPipeline


class DetectionTester:
    """Test all detection models on live footage"""
    
    def __init__(self):
        self.results = {
            'face_detection': {'tested': 0, 'detected': 0},
            'weapon_detection': {'tested': 0, 'detected': 0},
            'emotion_detection': {'tested': 0, 'detected': 0},
            'age_estimation': {'tested': 0, 'detected': 0},
            'pose_detection': {'tested': 0, 'detected': 0},
            'watchlist_matching': {'tested': 0, 'detected': 0},
        }
    
    def test_face_detection(self, frame):
        """Test if face detection works"""
        self.results['face_detection']['tested'] += 1
        
        try:
            faces = ai_model_manager.face_detector.detect_faces(frame)
            
            if faces and len(faces) > 0:
                self.results['face_detection']['detected'] += 1
                logger.info(f"✓ Face Detection: Found {len(faces)} faces")
                
                # Draw bounding boxes
                for i, face in enumerate(faces):
                    x, y, w, h = face['box']
                    confidence = face.get('confidence', 0)
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Face {i+1}: {confidence:.2f}", 
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                return frame, faces
            else:
                logger.debug("No faces detected")
                return frame, []
                
        except Exception as e:
            logger.error(f"✗ Face Detection Error: {e}")
            return frame, []
    
    def test_weapon_detection(self, frame):
        """Test if weapon detection works"""
        self.results['weapon_detection']['tested'] += 1
        
        try:
            weapons = ai_model_manager.weapon_detector.detect(frame)
            
            if weapons and len(weapons) > 0:
                self.results['weapon_detection']['detected'] += 1
                logger.warning(f"⚠ Weapon Detection: Found {len(weapons)} weapons!")
                
                for weapon in weapons:
                    bbox = weapon['bbox']
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # RED for weapons (CRITICAL)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    
                    label = f"⚠ {weapon['class'].upper()} {weapon['confidence']:.2f}"
                    cv2.putText(frame, label, (x1, y1-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                return frame, weapons
            else:
                logger.debug("No weapons detected")
                return frame, []
                
        except Exception as e:
            logger.error(f"✗ Weapon Detection Error: {e}")
            return frame, []
    
    def test_emotion_detection(self, frame, face_bbox):
        """Test if emotion detection works"""
        if not face_bbox:
            return frame, None
        
        self.results['emotion_detection']['tested'] += 1
        
        try:
            x, y, w, h = face_bbox
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return frame, None
            
            emotion = ai_model_manager.emotion_detector.detect_emotion(face_roi)
            
            if emotion and 'dominant_emotion' in emotion:
                self.results['emotion_detection']['detected'] += 1
                logger.info(f"✓ Emotion: {emotion['dominant_emotion']} ({emotion.get('confidence', 0):.2f})")
                
                cv2.putText(frame, f"{emotion['dominant_emotion']}", 
                            (x, y+h+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                return frame, emotion
            else:
                return frame, None
                
        except Exception as e:
            logger.error(f"✗ Emotion Detection Error: {e}")
            return frame, None
    
    def test_age_estimation(self, frame, face_bbox):
        """Test if age estimation works"""
        if not face_bbox:
            return frame, None
        
        self.results['age_estimation']['tested'] += 1
        
        try:
            x, y, w, h = face_bbox
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return frame, None
            
            age = ai_model_manager.age_estimator.estimate_age(face_roi)
            
            if age is not None:
                self.results['age_estimation']['detected'] += 1
                logger.info(f"✓ Age Estimation: {age} years")
                
                cv2.putText(frame, f"Age: {age}", 
                            (x, y+h+40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                
                return frame, age
            else:
                return frame, None
                
        except Exception as e:
            logger.error(f"✗ Age Estimation Error: {e}")
            return frame, None
    
    def test_pose_detection(self, frame):
        """Test if pose detection works"""
        self.results['pose_detection']['tested'] += 1
        
        try:
            pose_result = ai_model_manager.pose_estimator.detect_pose(frame)
            
            if pose_result and pose_result.get('landmarks'):
                self.results['pose_detection']['detected'] += 1
                landmarks = pose_result['landmarks']
                logger.info(f"✓ Pose Detection: Found {len(landmarks)} landmarks")
                
                # Draw pose landmarks (simplified)
                for landmark in landmarks[:10]:  # Draw first 10 for visibility
                    x = int(landmark['x'] * frame.shape[1])
                    y = int(landmark['y'] * frame.shape[0])
                    cv2.circle(frame, (x, y), 3, (0, 255, 255), -1)
                
                return frame, pose_result
            else:
                logger.debug("No pose detected")
                return frame, None
                
        except Exception as e:
            logger.error(f"✗ Pose Detection Error: {e}")
            return frame, None
    
    def test_watchlist_matching(self, frame, face_bbox, watchlist_embeddings):
        """Test if watchlist matching works"""
        if not face_bbox or not watchlist_embeddings:
            return frame, None
        
        self.results['watchlist_matching']['tested'] += 1
        
        try:
            x, y, w, h = face_bbox
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return frame, None
            
            # Get embedding
            embedding = ai_model_manager.face_recognizer.get_embedding(face_roi)
            
            if embedding is None:
                return frame, None
            
            # Match against watchlist
            best_match = None
            best_similarity = 0
            
            for person_id, person_embedding, person_name in watchlist_embeddings:
                similarity = ai_model_manager.face_recognizer.compare_embeddings(
                    embedding, person_embedding
                )
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (person_id, person_name)
            
            # Threshold for match
            if best_similarity > 0.6:
                self.results['watchlist_matching']['detected'] += 1
                person_id, person_name = best_match
                logger.success(f"✓ WATCHLIST MATCH: {person_name} (ID: {person_id}, similarity: {best_similarity:.2f})")
                
                # Yellow box for watchlist match
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 3)
                
                # Label with ID and name
                label = f"MATCH: {person_name}"
                cv2.putText(frame, label, (x, y-30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, f"ID: {person_id} | {best_similarity:.2f}", 
                            (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                return frame, best_match
            else:
                return frame, None
                
        except Exception as e:
            logger.error(f"✗ Watchlist Matching Error: {e}")
            return frame, None
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("DETECTION TEST SUMMARY")
        print("="*60)
        
        for detection_type, stats in self.results.items():
            tested = stats['tested']
            detected = stats['detected']
            
            if tested > 0:
                success_rate = (detected / tested) * 100
                status = "✓" if success_rate > 0 else "✗"
                print(f"{status} {detection_type.replace('_', ' ').title()}: "
                      f"{detected}/{tested} ({success_rate:.1f}%)")
            else:
                print(f"- {detection_type.replace('_', ' ').title()}: Not tested")
        
        print("="*60 + "\n")


def run_live_test(camera_source, watchlist_embeddings=None, test_duration=60):
    """
    Run live detection test on camera feed
    
    Args:
        camera_source: Camera index (0) or RTSP URL
        watchlist_embeddings: List of (id, embedding, name) tuples for testing
        test_duration: How long to run test in seconds
    """
    logger.info(f"Opening camera: {camera_source}")
    cap = cv2.VideoCapture(camera_source)
    
    if not cap.isOpened():
        logger.error(f"Failed to open camera: {camera_source}")
        return
    
    tester = DetectionTester()
    
    print("\n" + "="*60)
    print("LIVE DETECTION TEST")
    print("="*60)
    print(f"Camera: {camera_source}")
    print(f"Duration: {test_duration}s")
    print("Press 'q' to quit early")
    print("="*60 + "\n")
    
    frame_count = 0
    test_interval = 30  # Test every 30 frames (~1 second at 30fps)
    
    import time
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame")
            break
        
        frame_count += 1
        
        # Test every N frames
        if frame_count % test_interval == 0:
            elapsed = time.time() - start_time
            
            if elapsed > test_duration:
                logger.info(f"Test duration ({test_duration}s) reached")
                break
            
            print(f"\n--- Frame {frame_count} (t={elapsed:.1f}s) ---")
            
            test_frame = frame.copy()
            
            # 1. Face Detection
            test_frame, faces = tester.test_face_detection(test_frame)
            
            # 2. Weapon Detection
            test_frame, weapons = tester.test_weapon_detection(test_frame)
            
            # If face detected, test face-based detections
            if faces and len(faces) > 0:
                face_bbox = faces[0]['box']
                
                # 3. Emotion Detection
                test_frame, emotion = tester.test_emotion_detection(test_frame, face_bbox)
                
                # 4. Age Estimation
                test_frame, age = tester.test_age_estimation(test_frame, face_bbox)
                
                # 5. Watchlist Matching
                if watchlist_embeddings:
                    test_frame, match = tester.test_watchlist_matching(
                        test_frame, face_bbox, watchlist_embeddings
                    )
            
            # 6. Pose Detection
            test_frame, pose = tester.test_pose_detection(test_frame)
            
            # Show annotated frame
            cv2.imshow('Detection Test - Press Q to quit', test_frame)
        
        # Show live feed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            logger.info("User quit test")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print summary
    tester.print_summary()


def main():
    parser = argparse.ArgumentParser(description='Test all detection models on live camera')
    parser.add_argument('--camera', type=str, default='0', 
                        help='Camera source (0 for webcam, or RTSP URL)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Test duration in seconds (default: 60)')
    parser.add_argument('--test-watchlist', action='store_true',
                        help='Test with sample watchlist embeddings')
    
    args = parser.parse_args()
    
    # Convert camera to int if it's a digit
    camera_source = int(args.camera) if args.camera.isdigit() else args.camera
    
    # Create sample watchlist for testing
    watchlist_embeddings = None
    if args.test_watchlist:
        logger.info("Creating sample watchlist for testing...")
        # In real usage, load from database
        # For now, just test without watchlist
        watchlist_embeddings = []
    
    # Run test
    run_live_test(camera_source, watchlist_embeddings, args.duration)


if __name__ == "__main__":
    main()
