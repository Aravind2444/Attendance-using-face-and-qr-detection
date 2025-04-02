import os
import time
import cv2
import argparse
from face_detector import face_detector

# Define the new output directory
OUTPUT_DIR = "C:\\Users\\lokes\\Downloads\\face detect realtime\\Attendance-using-face-qr-system\\backend\\uploads"

def capture_test_images(subjects, output_dir):
    """Capture test images for a batch of students/subjects
    
    Args:
        subjects: List of tuples (roll_number, subject_name)
        output_dir: Directory to save images
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open webcam")
        return False
    
    for roll_number, subject in subjects:
        print(f"\nCapturing test image for Roll: {roll_number}, Subject: {subject}")
        print("Position subject in frame and press 'c' to capture or 's' to skip")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Could not read frame")
                break
            
            # Add text instructions
            cv2.putText(
                frame,
                f"Roll: {roll_number}, Subject: {subject}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            cv2.putText(
                frame,
                "Press 'c' to capture or 's' to skip",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Detect faces to provide feedback
            faces, _, _ = face_detector.detect_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            cv2.imshow("Capture Test Images", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                # Create filename in the required format
                filename = f"{roll_number}_{subject}.jpg"
                output_path = os.path.join(output_dir, filename)
                cv2.imwrite(output_path, frame)
                print(f"Saved: {output_path}")
                break
            elif key == ord('s'):
                print(f"Skipped Roll: {roll_number}")
                break
            elif key == ord('q'):
                print("Exiting capture process")
                cap.release()
                cv2.destroyAllWindows()
                return
    
    cap.release()
    cv2.destroyAllWindows()
    return True

if __name__ == "__main__":
    print("Batch Test Image Capture Tool")
    print("-" * 30)
    
    subjects = []
    try:
        num_students = int(input("How many students to test? "))
        for i in range(num_students):
            roll = input(f"[Student {i+1}] Enter roll number: ")
            subject = input(f"[Student {i+1}] Enter subject: ")
            subjects.append((roll, subject))
    except ValueError:
        print("Please enter a valid number")
        exit(1)
    
    capture_test_images(subjects, OUTPUT_DIR)
    print(f"\nAll done! {len(subjects)} test images captured.")
    print(f"Images saved to: {OUTPUT_DIR}")
    print("The attendance system should automatically process these images.")
