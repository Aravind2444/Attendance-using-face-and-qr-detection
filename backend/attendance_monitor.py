import os
import time
import csv
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from face_detector import face_detector
import logging

# Configure logging
logging.basicConfig(
    filename='attendance.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 85  # Increase from default to require higher confidence

class AttendanceTracker:
    def __init__(self):
        self.upload_dir = face_detector.upload_dir
        self.csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.csv")
        self.processed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed")
        self.failed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed")
        
        # Create directories
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.failed_dir, exist_ok=True)
        
        # Create CSV file if it doesn't exist
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll Number', 'Subject', 'Timestamp', 'Status', 'Confidence'])
        
        logger.info(f"Attendance Tracker initialized. Monitoring folder: {self.upload_dir}")
        print(f"Attendance Tracker initialized. Monitoring folder: {self.upload_dir}")
        
        # Track recent submissions to prevent rapid duplicate attendance
        self.recent_submissions = {}
        self.cooldown_period = 300  # 5 minutes between submissions
    
    def record_attendance(self, roll_number, subject, status, confidence=0):
        """Record attendance in the CSV file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([roll_number, subject, timestamp, status, confidence])
        
        logger.info(f"Recorded attendance: {roll_number, subject, status, confidence}")
    
    def process_image(self, image_path):
        """Process an image to record attendance"""
        try:
            # Extract roll number and subject from filename
            filename = os.path.basename(image_path)
            name_part = os.path.splitext(filename)[0]
            if "_" not in name_part:
                logger.error(f"Invalid filename format: {filename}")
                self._move_to_failed(image_path)
                return False
                
            roll_number, subject = name_part.split("_", 1)
            logger.info(f"Processing attendance for roll number: {roll_number}, subject: {subject}")
            
            # Check for duplicate submission
            submission_key = f"{roll_number}_{subject}"
            current_time = time.time()
            
            if submission_key in self.recent_submissions:
                last_submission = self.recent_submissions[submission_key]
                time_since_last = current_time - last_submission
                
                if time_since_last < self.cooldown_period:
                    logger.warning(f"Duplicate submission attempt for {submission_key} - {time_since_last:.1f} seconds since last attempt")
                    self.record_attendance(roll_number, subject, "Rejected (duplicate)", 0)
                    self._move_to_failed(image_path)
                    return False
            
            # Use face recognition to verify identity
            from face_detector import face_detector
            result = face_detector.recognize_face(image_path)
            
            if result["success"]:
                # Direct verification instead of searching for matches
                if result["verified"]:
                    # The face matches the claimed ID AND passes threshold
                    confidence = result["best_confidence"]
                    self.record_attendance(roll_number, subject, "Present", confidence)
                    logger.info(f"Attendance marked PRESENT for {roll_number} in {subject} with confidence {confidence:.2f}%")
                    self._move_to_processed(image_path)
                    self.recent_submissions[submission_key] = current_time
                    return True
                else:
                    # Either not a match or didn't pass threshold
                    if result["best_match"] == roll_number:
                        reason = "low confidence"
                        confidence = result["best_confidence"]
                    else:
                        reason = "face mismatch"
                        confidence = 0
                        
                    self.record_attendance(roll_number, subject, f"Rejected ({reason})", confidence)
                    logger.warning(f"Face verification failed: {reason}. Roll: {roll_number}, Best match: {result['best_match']}, Confidence: {confidence:.2f}%")
                    self._move_to_failed(image_path)
                    return False
            else:
                # Face detection/recognition failed
                self.record_attendance(roll_number, subject, f"Rejected ({result['message']})", 0)
                logger.error(f"Face recognition error: {result['message']}")
                self._move_to_failed(image_path)
                return False
                
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            self._move_to_failed(image_path)
            return False
    
    def _move_to_processed(self, image_path):
        """Move processed image to processed directory"""
        filename = os.path.basename(image_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{timestamp}_{filename}"
        new_path = os.path.join(self.processed_dir, new_filename)
        
        try:
            os.rename(image_path, new_path)
            logger.info(f"Moved {image_path} to {new_path}")
        except Exception as e:
            logger.error(f"Failed to move file {image_path}: {str(e)}")
    
    def _move_to_failed(self, image_path):
        """Move failed image to failed directory"""
        filename = os.path.basename(image_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_filename = f"{timestamp}_{filename}"
        new_path = os.path.join(self.failed_dir, new_filename)
        
        try:
            os.rename(image_path, new_path)
            logger.info(f"Moved {image_path} to {new_path}")
        except Exception as e:
            logger.error(f"Failed to move file {image_path}: {str(e)}")


class ImageEventHandler(FileSystemEventHandler):
    def __init__(self, attendance_tracker):
        self.attendance_tracker = attendance_tracker
        self.image_extensions = ['.jpg', '.jpeg', '.png']
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        if any(event.src_path.lower().endswith(ext) for ext in self.image_extensions):
            logger.info(f"New image detected: {event.src_path}")
            
            # Wait a moment to ensure file is completely written
            time.sleep(1)
            
            # Process the image
            self.attendance_tracker.process_image(event.src_path)


def start_monitoring():
    """Start monitoring the uploads folder"""
    attendance_tracker = AttendanceTracker()
    event_handler = ImageEventHandler(attendance_tracker)
    
    observer = Observer()
    observer.schedule(event_handler, path=attendance_tracker.upload_dir, recursive=False)
    observer.start()
    
    try:
        print(f"Starting monitoring of {attendance_tracker.upload_dir}")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()


if __name__ == "__main__":
    start_monitoring()