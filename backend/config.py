import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths for face recognition
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance.csv")

# Face recognition settings
FACE_RECOGNITION_TOLERANCE = 0.6
MODEL_COMPLEXITY = "hog"
REQUIRED_FACE_SIZE = 20

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Print confirmation
print("Config loaded successfully")
print(f"KNOWN_FACES_DIR: {KNOWN_FACES_DIR}")
print(f"UPLOAD_FOLDER: {UPLOAD_FOLDER}")