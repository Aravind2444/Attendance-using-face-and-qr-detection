import cv2
import numpy as np
import time
import os

# Define constants directly in the module (no config import)
BLINK_THRESHOLD = 0.3
BLINK_CONSECUTIVE_FRAMES = 3
LIVENESS_THRESHOLD = 0.7

class LivenessDetector:
    def __init__(self):
        print("Initializing liveness detector...")
        
        # Liveness detection parameters
        self.BLINK_THRESHOLD = BLINK_THRESHOLD
        self.BLINK_CONSECUTIVE_FRAMES = BLINK_CONSECUTIVE_FRAMES
        self.LIVENESS_THRESHOLD = LIVENESS_THRESHOLD
        
        # Load face detector
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Load eye detector
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Create debug directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.debug_dir = os.path.join(self.base_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def detect_faces_and_eyes(self, frame):
        """Detect faces and eyes in a frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        results = []
        
        for (x, y, w, h) in faces:
            face_gray = gray[y:y+h, x:x+w]
            face_color = frame[y:y+h, x:x+w]
            
            # Detect eyes within the face
            eyes = self.eye_cascade.detectMultiScale(
                face_gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(20, 20)
            )
            
            results.append({
                "face": (x, y, w, h),
                "eyes": eyes,
                "face_gray": face_gray,
                "face_color": face_color
            })
        
        return results, gray, frame
    
    def calculate_texture_variance(self, face_gray):
        """Calculate texture variance as a liveness feature"""
        # Apply Laplacian filter to get texture details
        laplacian = cv2.Laplacian(face_gray, cv2.CV_64F)
        
        # Calculate variance - real faces have more texture variance
        variance = laplacian.var()
        
        # Normalize to 0-1 range (empirical values)
        normalized_variance = min(1.0, max(0.0, variance / 500.0))
        
        return normalized_variance
    
    def detect_eye_blinks(self, frames, min_blinks=1, timeout=5):
        """
        Detect eye blinks in a sequence of frames
        
        Args:
            frames: A list of frames or a webcam capture object
            min_blinks: Minimum number of blinks required
            timeout: Maximum time in seconds
            
        Returns:
            dict with liveness result
        """
        blink_counter = 0
        eye_state = True  # Eyes open
        consecFrames = 0
        
        start_time = time.time()
        frame_count = 0
        
        # Store liveness score components
        texture_scores = []
        has_sufficient_eye_movements = False
        
        # For eye tracking
        prev_eye_positions = None
        eye_movements = []
        
        if isinstance(frames, cv2.VideoCapture):
            # If webcam capture is provided
            webcam = frames
            using_webcam = True
        else:
            # If list of frames provided
            using_webcam = False
            
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                break
                
            # Get frame
            if using_webcam:
                ret, frame = webcam.read()
                if not ret:
                    break
            else:
                if frame_count >= len(frames):
                    break
                frame = frames[frame_count]
            
            frame_count += 1
            
            # Detect faces and eyes
            detections, gray, frame = self.detect_faces_and_eyes(frame)
            
            # Process each face
            for detection in detections:
                face_rect = detection["face"]
                eyes = detection["eyes"]
                face_gray = detection["face_gray"]
                
                # Calculate texture variance for this face
                texture_score = self.calculate_texture_variance(face_gray)
                texture_scores.append(texture_score)
                
                # Draw face rectangle
                x, y, w, h = face_rect
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Check for eye state change (blinking)
                if len(eyes) < 2:
                    # Eyes closed or not fully detected
                    if eye_state:
                        consecFrames += 1
                        if consecFrames >= self.BLINK_CONSECUTIVE_FRAMES:
                            eye_state = False
                            cv2.putText(frame, "Blink detected!", (x, y-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            blink_counter += 1
                            consecFrames = 0
                else:
                    # Eyes open
                    eye_state = True
                    consecFrames = 0
                    
                    # Track eye positions for movement detection
                    current_eye_positions = []
                    for (ex, ey, ew, eh) in eyes:
                        # Draw eye rectangle
                        cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (255, 0, 0), 2)
                        current_eye_positions.append((ex+ew//2, ey+eh//2))
                    
                    if prev_eye_positions and len(current_eye_positions) == len(prev_eye_positions):
                        # Calculate movement
                        for i in range(len(current_eye_positions)):
                            dx = current_eye_positions[i][0] - prev_eye_positions[i][0]
                            dy = current_eye_positions[i][1] - prev_eye_positions[i][1]
                            movement = np.sqrt(dx*dx + dy*dy)
                            if movement > 2:  # Threshold for considering movement
                                eye_movements.append(movement)
                    
                    prev_eye_positions = current_eye_positions
                
                # Display blink count
                cv2.putText(frame, f"Blinks: {blink_counter}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display frame
            cv2.imshow("Liveness Detection", frame)
            
            # Check if we've met the blink requirement
            if blink_counter >= min_blinks:
                if len(eye_movements) > 10:
                    # Check if there's sufficient eye movement variation
                    movement_std = np.std(eye_movements)
                    if movement_std > 1.0:
                        has_sufficient_eye_movements = True
            
            # Break on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Clean up
        if using_webcam and not isinstance(frames, list):
            webcam.release()
        cv2.destroyAllWindows()
        
        # Calculate final liveness score
        avg_texture = np.mean(texture_scores) if texture_scores else 0
        blink_score = min(1.0, blink_counter / min_blinks)
        movement_score = 1.0 if has_sufficient_eye_movements else 0.0
        
        # Combined liveness score (weighted)
        liveness_score = (0.5 * blink_score) + (0.3 * avg_texture) + (0.2 * movement_score)
        
        is_live = liveness_score >= self.LIVENESS_THRESHOLD
        
        return {
            "is_live": is_live,
            "score": liveness_score,
            "blinks_detected": blink_counter,
            "texture_score": avg_texture,
            "movement_score": movement_score,
            "frames_processed": frame_count
        }
    
    def verify_liveness(self, image_path=None, challenge_mode=False):
        """
        Verify if the face is live using either a single image or webcam feed
        
        Args:
            image_path: Path to image file (None for webcam)
            challenge_mode: Whether to require specific user actions
            
        Returns:
            dict with liveness results
        """
        if image_path:
            # Single image analysis (less reliable)
            frame = cv2.imread(image_path)
            if frame is None:
                return {"is_live": False, "error": "Could not load image"}
            
            # Detect faces
            detections, _, frame = self.detect_faces_and_eyes(frame)
            
            if not detections:
                return {"is_live": False, "error": "No face detected"}
            
            # Calculate texture variance for liveness detection
            texture_score = self.calculate_texture_variance(detections[0]["face_gray"])
            
            # Check for eyes
            has_eyes = len(detections[0]["eyes"]) >= 2
            
            # For single image, primarily rely on texture
            is_live = texture_score > 0.5 and has_eyes
            
            # Save debug image
            debug_path = os.path.join(self.debug_dir, f"liveness_check_{time.time()}.jpg")
            cv2.imwrite(debug_path, frame)
            
            return {
                "is_live": is_live,
                "score": texture_score,
                "has_eyes": has_eyes,
                "debug_image": debug_path
            }
        else:
            # Video-based liveness detection
            print("Starting webcam liveness verification...")
            print("Please look at the camera and blink naturally.")
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return {"is_live": False, "error": "Could not open webcam"}
            
            # Set minimum blinks higher in challenge mode
            min_blinks = 2 if challenge_mode else 1
            timeout = 10 if challenge_mode else 5
            
            if challenge_mode:
                print("Challenge mode: Please blink twice and move your eyes slightly.")
            
            result = self.detect_eye_blinks(cap, min_blinks, timeout)
            
            return result

# Create singleton instance
liveness_detector = LivenessDetector()

# Test function if run directly
if __name__ == "__main__":
    print("\nLiveness Detection Test")
    print("1. Test with webcam")
    print("2. Test with challenge mode (more strict)")
    print("3. Test with a single image")
    
    choice = input("Enter your choice (1-3): ")
    
    if choice == "1":
        result = liveness_detector.verify_liveness()
        print("\nLiveness Result:")
        for key, value in result.items():
            print(f"{key}: {value}")
            
        if result["is_live"]:
            print("\nLiveness verification PASSED!")
        else:
            print("\nLiveness verification FAILED!")
            
    elif choice == "2":
        result = liveness_detector.verify_liveness(challenge_mode=True)
        print("\nLiveness Result (Challenge Mode):")
        for key, value in result.items():
            print(f"{key}: {value}")
            
        if result["is_live"]:
            print("\nLiveness verification PASSED!")
        else:
            print("\nLiveness verification FAILED!")
            
    elif choice == "3":
        image_path = input("Enter path to the image file: ")
        result = liveness_detector.verify_liveness(image_path)
        print("\nLiveness Result (Single Image):")
        for key, value in result.items():
            print(f"{key}: {value}")
            
        if result["is_live"]:
            print("\nLiveness verification PASSED!")
        else:
            print("\nLiveness verification FAILED!")
    else:
        print("Invalid choice!")