import os
import cv2
import numpy as np
import pickle
import face_recognition  # Need to install: pip install face-recognition
from datetime import datetime
import shutil
import logging
import threading
from mtcnn.mtcnn import MTCNN  # Need to install: pip install mtcnn tensorflow
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('face_detector')

class FaceDetector:
    def __init__(self):
        print("Initializing advanced face detector...")
        # Set up directories
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, "known_faces")
        self.upload_dir = os.path.join(self.base_dir, "uploads")
        self.debug_dir = os.path.join(self.base_dir, "debug")
        
        # Create directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # Configuration
        self.debug = True
        self.min_confidence = 0.92  # Minimum confidence for face match (very strict)
        self.min_face_size = (96, 96)  # Minimum face size for detection
        
        # Advanced face detector using MTCNN (Multi-task Cascaded Convolutional Networks)
        try:
            # Try with parameters (newer versions)
            self.mtcnn_detector = MTCNN(min_face_size=80, scale_factor=0.709)
        except TypeError:
            try:
                # Try with just scale factor (some versions)
                self.mtcnn_detector = MTCNN(scale_factor=0.709)
            except TypeError:
                # Fall back to defaults (all versions)
                self.mtcnn_detector = MTCNN()
                print("Using default MTCNN parameters")
        
        # Face database
        self.face_db = {}
        self.lock = threading.RLock()
        self.load_database()
    
    def load_database(self):
        """Load the face database from disk"""
        db_path = os.path.join(self.data_dir, "face_db.pickle")
        if os.path.exists(db_path):
            try:
                with open(db_path, 'rb') as f:
                    self.face_db = pickle.load(f)
                print(f"Loaded face database with {len(self.face_db)} student records")
            except Exception as e:
                print(f"Error loading face database: {str(e)}")
                self.face_db = {}
        else:
            print("No face database found, creating new one")
            self.face_db = {}
    
    def save_database(self):
        """Save the face database to disk"""
        try:
            db_path = os.path.join(self.data_dir, "face_db.pickle")
            with open(db_path, 'wb') as f:
                pickle.dump(self.face_db, f)
            print(f"Saved face database with {len(self.face_db)} student records")
        except Exception as e:
            print(f"Error saving face database: {str(e)}")
    
    def detect_faces(self, image):
        """Detect faces using MTCNN"""
        if image is None:
            return [], None, None
        
        # Convert to RGB for face_recognition library
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces using MTCNN
        faces = self.mtcnn_detector.detect_faces(rgb_image)
        
        detected_faces = []
        face_images = []
        
        for face in faces:
            # Check confidence
            if face['confidence'] < 0.9:  # Only accept high confidence detections
                continue
                
            # Get face coordinates
            x, y, w, h = face['box']
            
            # Add some margin to include entire face
            margin_x = int(w * 0.2)
            margin_y = int(h * 0.2)
            
            # Ensure within image bounds
            x_min = max(0, x - margin_x)
            y_min = max(0, y - margin_y)
            x_max = min(image.shape[1], x + w + margin_x)
            y_max = min(image.shape[0], y + h + margin_y)
            
            # Extract face with margin
            face_img = image[y_min:y_max, x_min:x_max]
            
            if face_img.size == 0 or face_img.shape[0] < 20 or face_img.shape[1] < 20:
                continue
                
            detected_faces.append((x_min, y_min, x_max - x_min, y_max - y_min))
            face_images.append(face_img)
        
        return detected_faces, face_images, rgb_image
    
    def extract_face_encoding(self, face_image):
        """Extract 128D face encoding using face_recognition library"""
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        
        # Get face landmarks and compute encoding
        face_encodings = face_recognition.face_encodings(rgb_face)
        
        if not face_encodings:
            return None
        
        # Return first face encoding (we're assuming one face per image)
        return face_encodings[0]
    
    def register_face(self, image_path, student_id):
        """Register a new face for the student ID"""
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "message": "Could not read image"}
            
            # Detect faces
            faces, face_images, rgb_image = self.detect_faces(image)
            
            if not faces or not face_images:
                return {"success": False, "message": "No faces detected in the image"}
            
            if len(faces) > 1:
                return {"success": False, "message": "Multiple faces detected in the image"}
            
            # Extract face encoding for deep learning-based comparison
            face_encoding = self.extract_face_encoding(face_images[0])
            if face_encoding is None:
                return {"success": False, "message": "Could not extract face features"}
            
            # Create the student directory if it doesn't exist
            student_dir = os.path.join(self.data_dir, student_id)
            os.makedirs(student_dir, exist_ok=True)
            
            # Save face image for reference
            face_path = os.path.join(student_dir, f"face_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
            cv2.imwrite(face_path, face_images[0])
            
            # Check if student already exists and handle database structure issues
            with self.lock:
                # Reset the database entry if it has an incorrect structure
                if student_id in self.face_db:
                    # Check if the structure is correct (has 'encodings' key)
                    if not isinstance(self.face_db[student_id], dict) or "encodings" not in self.face_db[student_id]:
                        logger.warning(f"Fixing corrupted database entry for student {student_id}")
                        # Create a new entry with the correct structure
                        self.face_db[student_id] = {
                            "encodings": [],
                            "image_paths": [],
                            "registered_on": datetime.now().isoformat()
                        }
                        
                    # Add this face encoding to the existing student record
                    self.face_db[student_id]["encodings"].append(face_encoding)
                    self.face_db[student_id]["image_paths"].append(face_path)
                else:
                    # Create a new student record
                    self.face_db[student_id] = {
                        "encodings": [face_encoding],
                        "image_paths": [face_path],
                        "registered_on": datetime.now().isoformat()
                    }
                
                # Save the updated database
                self.save_database()
            
            return {"success": True, "message": f"Face registered for student {student_id}"}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error registering face: {str(e)}"}
    
    def recognize_face(self, image_path):
        """Recognize a face in an image and return the student ID"""
        try:
            # Load the image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "message": "Could not read image"}
            
            # Extract claimed student ID from filename
            claimed_id = None
            try:
                filename = os.path.basename(image_path)
                name_part = os.path.splitext(filename)[0]
                if "_" in name_part:
                    claimed_id = name_part.split("_")[0]
                    logger.info(f"Claimed student ID from filename: {claimed_id}")
            except Exception as e:
                logger.error(f"Error extracting ID from filename: {str(e)}")
            
            # Detect faces
            faces, face_images, rgb_image = self.detect_faces(image)
            
            if not faces or not face_images:
                return {"success": False, "message": "No faces detected in the image"}
            
            if len(faces) > 1:
                return {"success": False, "message": "Multiple faces detected in the image"}
            
            # Debug: save detected face
            if self.debug:
                debug_path = os.path.join(self.debug_dir, f"recognize_{os.path.basename(image_path)}")
                cv2.imwrite(debug_path, face_images[0])
                
            # Extract face encoding
            face_encoding = self.extract_face_encoding(face_images[0])
            if face_encoding is None:
                return {"success": False, "message": "Could not extract face features"}
            
            # Compare with all registered faces
            results = []
            
            with self.lock:
                # If no registered faces, return failure
                if not self.face_db:
                    return {"success": False, "message": "No registered faces found"}
                
                # Compare with each student's face encodings
                for student_id, student_data in self.face_db.items():
                    best_match_score = 0
                    
                    # Compare with all encodings for this student
                    for encoding in student_data["encodings"]:
                        # Calculate similarity score (higher is better)
                        similarity = 1 - face_recognition.face_distance([encoding], face_encoding)[0]
                        
                        # Keep track of best score
                        if similarity > best_match_score:
                            best_match_score = similarity
                    
                    # Convert to percentage for easier understanding
                    confidence = best_match_score * 100
                    
                    # Only add results that meet minimum threshold
                    # or add all results but mark them as passing/failing threshold
                    results.append({
                        "student_id": student_id,
                        "confidence": confidence,
                        "passes_threshold": confidence >= (self.min_confidence * 100)
                    })
            
            # Sort by confidence (highest first)
            results.sort(key=lambda x: x["confidence"], reverse=True)
            
            # Get the best match
            best_match = results[0] if results else None
            
            # Check if the best match passes the threshold
            is_match = best_match and best_match["passes_threshold"]
            
            # Special verification for claimed ID
            verified = False
            if claimed_id and best_match:
                if claimed_id == best_match["student_id"]:
                    if best_match["passes_threshold"]:
                        verified = True
                        logger.info(f"Verified claimed ID '{claimed_id}' with confidence {best_match['confidence']:.2f}%")
                    else:
                        logger.warning(f"Claimed ID '{claimed_id}' matched but below threshold: {best_match['confidence']:.2f}%")
                else:
                    logger.warning(f"Claimed ID '{claimed_id}' does not match best match '{best_match['student_id']}'")
            
            # Return enhanced results
            return {
                "success": True,
                "student_ids": results[:3],  # Return top 3 matches
                "best_match": best_match["student_id"] if best_match else None,
                "best_confidence": best_match["confidence"] if best_match else 0,
                "passes_threshold": is_match,
                "verified": verified,
                "claimed_id": claimed_id,
                "threshold": self.min_confidence * 100
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error recognizing face: {str(e)}"}
    
    def register_faces_in_bulk(self, directory_path):
        """Register multiple faces from a directory
        Images should be named: student_id.jpg"""
        results = {"success": 0, "failed": 0, "details": []}
        
        if not os.path.exists(directory_path):
            return {"success": False, "message": f"Directory {directory_path} does not exist"}
        
        for filename in os.listdir(directory_path):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                try:
                    # Extract student_id from filename
                    student_id = os.path.splitext(filename)[0]
                    if "_" in student_id:
                        student_id = student_id.split("_")[0]
                        
                    image_path = os.path.join(directory_path, filename)
                    
                    # Register the face
                    result = self.register_face(image_path, student_id)
                    
                    if result["success"]:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["details"].append({
                        "student_id": student_id,
                        "result": result
                    })
                    
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({
                        "filename": filename,
                        "error": str(e)
                    })
        
        return results
    
    def register_face_multi(self, student_id, num_photos=5, delay=1):
        """Capture multiple training photos of a person
        
        Args:
            student_id: The ID of the student to register
            num_photos: Number of photos to capture (default: 5)
            delay: Delay between photos in seconds (default: 1)
        
        Returns:
            dict: Results of the registration process
        """
        results = {"success": 0, "failed": 0, "details": []}
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return {"success": False, "message": "Could not open webcam"}
        
        print(f"Starting multi-photo capture for student ID: {student_id}")
        print(f"Will capture {num_photos} photos with {delay}s delay")
        print("Position the face properly in the frame")
        
        # Add a countdown before starting
        for i in range(3, 0, -1):
            ret, frame = cap.read()
            if not ret:
                return {"success": False, "message": "Could not read from webcam"}
            
            # Display countdown
            h, w = frame.shape[:2]
            cv2.putText(
                frame,
                f"Starting in {i}...",
                (w//2 - 100, h//2),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2
            )
            cv2.imshow("Register Face", frame)
            cv2.waitKey(1000)
        
        for i in range(num_photos):
            # Show instructions
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect faces to ensure quality
            faces, face_images, _ = self.detect_faces(frame)
            
            if len(faces) == 0:
                cv2.putText(
                    frame,
                    "No face detected! Adjust position",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )
                cv2.imshow("Register Face", frame)
                cv2.waitKey(500)
                continue
            
            if len(faces) > 1:
                cv2.putText(
                    frame,
                    "Multiple faces detected! Only one person should be in frame",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )
                cv2.imshow("Register Face", frame)
                cv2.waitKey(500)
                continue
            
            # Draw face rectangle
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Display countdown for this photo
            cv2.putText(
                frame,
                f"Capturing photo {i+1}/{num_photos} in...",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            cv2.imshow("Register Face", frame)
            cv2.waitKey(1000)
            
            # Final capture
            ret, frame = cap.read()
            if not ret:
                break
            
            # Save temporary image
            temp_path = os.path.join(self.upload_dir, f"{student_id}_temp_{i}.jpg")
            cv2.imwrite(temp_path, frame)
            
            # Register the face
            result = self.register_face(temp_path, student_id)
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "photo_num": i+1,
                "result": result
            })
            
            # Remove temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Show success/failure message
            ret, frame = cap.read()
            if not ret:
                break
            
            color = (0, 255, 0) if result["success"] else (0, 0, 255)
            message = f"Photo {i+1}: {'Succeeded' if result['success'] else 'Failed'}"
            cv2.putText(
                frame,
                message,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
            cv2.imshow("Register Face", frame)
            
            # Wait before next capture
            if i < num_photos - 1:
                cv2.waitKey(delay * 1000)
        
        cap.release()
        cv2.destroyAllWindows()
        
        return results

# Create a singleton instance
face_detector = FaceDetector()

if __name__ == "__main__":
    import sys
    
    print("Advanced Face Detection and Recognition System")
    print("1. Test webcam detection")
    print("2. Register a face (single photo)")
    print("3. Recognize faces")
    print("4. Register a face (multiple photos)")
    print("5. Bulk register from directory")
    
    choice = input("Enter your choice (1-5): ")
    
    if choice == "1":
        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Could not open webcam")
            sys.exit()
        
        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            # Detect faces
            faces, face_images, _ = face_detector.detect_faces(frame)
            
            # Draw rectangles around detected faces
            for i, (x, y, w, h) in enumerate(faces):
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"Face {i+1}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Display info
            cv2.putText(frame, f"Detected faces: {len(faces)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display the frame
            cv2.imshow("Face Detection Test", frame)
            
            # Exit on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                cap.release()
        cv2.destroyAllWindows()

    elif choice == "2":
        image_path = input("Enter the path of the image to register: ")
        student_id = input("Enter student ID: ")
        result = face_detector.register_face(image_path, student_id)
        print(result)

    elif choice == "3":
        image_path = input("Enter the path of the image to recognize: ")
        result = face_detector.recognize_face(image_path)
        print(result)

    elif choice == "4":
        student_id = input("Enter student ID: ")
        num_photos = int(input("Enter number of photos to capture (default 5): ") or 5)
        delay = int(input("Enter delay between photos in seconds (default 1): ") or 1)
        result = face_detector.register_face_multi(student_id, num_photos, delay)
        print(result)

    elif choice == "5":
        directory_path = input("Enter the directory path for bulk registration: ")
        result = face_detector.register_faces_in_bulk(directory_path)
        print(result)

    else:
        print("Invalid choice. Exiting.")
