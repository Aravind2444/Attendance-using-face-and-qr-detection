import os
import cv2
import time
import json
import pandas as pd
import threading
import shutil
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file

# Import your existing components
from face_detector import face_detector
from liveness_detection import liveness_detector
from database import attendance_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("attendance.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("attendance")

# Set up directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "processed")
REJECTED_FOLDER = os.path.join(BASE_DIR, "rejected")
TEMPLATES_FOLDER = os.path.join(BASE_DIR, "templates")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(REJECTED_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, 
            template_folder=TEMPLATES_FOLDER,
            static_folder=STATIC_FOLDER)

# Global statistics - defined as a dictionary (not a class)
stats = {
    "processed_count": 0,
    "successful_count": 0,
    "rejected_count": 0,
    "today_attendance_count": 0,
    "last_processed": "-",
    "last_recognized": "-",
    "recent_entries": []
}

# System settings with default values
system_settings = {
    "enableLiveness": False  # Default to OFF for uploaded photos
}

# Load settings if available
settings_file = os.path.join(BASE_DIR, "settings.json")
if os.path.exists(settings_file):
    try:
        with open(settings_file, "r") as f:
            loaded_settings = json.load(f)
            system_settings.update(loaded_settings)
            logger.info(f"Loaded settings: {system_settings}")
    except Exception as e:
        logger.error(f"Error loading settings: {e}")

# Save settings
def save_settings():
    try:
        with open(settings_file, "w") as f:
            json.dump(system_settings, f)
        logger.info("Settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

# Process a single image
def process_image(image_path, skip_liveness=None):
    """Process a single image for face recognition and attendance marking"""
    if skip_liveness is None:
        skip_liveness = not system_settings.get("enableLiveness", False)
        
    filename = os.path.basename(image_path)
    logger.info(f"Processing image: {filename} (skip_liveness={skip_liveness})")
    
    # Update stats
    global stats
    stats["processed_count"] += 1
    stats["last_processed"] = filename
    
    try:
        # Step 1: Check liveness if required
        if not skip_liveness:
            logger.info(f"Performing liveness check on {filename}")
            liveness_result = liveness_detector.verify_liveness(image_path)
            
            if not liveness_result.get("is_live", False):
                logger.warning(f"Liveness check failed for {filename}")
                # Move to rejected folder
                rejected_path = os.path.join(REJECTED_FOLDER, filename)
                shutil.move(image_path, rejected_path)
                stats["rejected_count"] += 1
                return {
                    "success": False,
                    "message": "Failed liveness check",
                    "filename": filename
                }
        
        # Step 2: Recognize face
        logger.info(f"Performing face recognition on {filename}")
        recognition_result = face_detector.recognize_face(image_path)
        
        if not recognition_result.get("success", False):
            logger.warning(f"Face recognition failed for {filename}")
            # Extract student ID from filename as fallback
            filename_without_ext = os.path.splitext(filename)[0]
            student_id = filename_without_ext.upper()
            
            # Register this face
            logger.info(f"Registering new face from {filename} as {student_id}")
            register_result = face_detector.register_face(image_path, student_id)
            
            if register_result.get("success", False):
                # Mark attendance
                attendance_db.mark_attendance(
                    student_id,
                    status="Present",
                    method="New Registration"
                )
                
                # Update stats
                stats["successful_count"] += 1
                stats["last_recognized"] = student_id
                stats["recent_entries"].insert(0, {
                    "roll_number": student_id,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "method": "New Registration",
                    "file": filename
                })
                if len(stats["recent_entries"]) > 10:
                    stats["recent_entries"].pop()
                
                # Move to processed folder
                processed_path = os.path.join(PROCESSED_FOLDER, filename)
                shutil.move(image_path, processed_path)
                
                return {
                    "success": True,
                    "message": "New face registered",
                    "student_id": student_id,
                    "filename": filename
                }
            else:
                # Move to rejected folder
                rejected_path = os.path.join(REJECTED_FOLDER, filename)
                shutil.move(image_path, rejected_path)
                stats["rejected_count"] += 1
                return {
                    "success": False,
                    "message": "Face recognition and registration failed",
                    "filename": filename
                }
        
        # If recognition successful, mark attendance
        recognized_students = recognition_result.get("student_ids", [])
        for student in recognized_students:
            student_id = student.get("student_id")
            confidence = student.get("confidence", 0)
            
            if confidence >= 0.6:  # Minimum confidence threshold
                # Mark attendance
                attendance_db.mark_attendance(
                    student_id,
                    status="Present",
                    method="Face Recognition"
                )
                
                # Update stats
                stats["successful_count"] += 1
                stats["last_recognized"] = student_id
                stats["recent_entries"].insert(0, {
                    "roll_number": student_id,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "confidence": f"{confidence:.2f}",
                    "method": "Face Recognition",
                    "file": filename
                })
                if len(stats["recent_entries"]) > 10:
                    stats["recent_entries"].pop()
        
        # Move to processed folder
        processed_path = os.path.join(PROCESSED_FOLDER, filename)
        shutil.move(image_path, processed_path)
        
        return {
            "success": True,
            "message": "Processing completed",
            "recognized_students": [s.get("student_id") for s in recognized_students],
            "filename": filename
        }
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {e}", exc_info=True)
        try:
            # Move to rejected folder
            rejected_path = os.path.join(REJECTED_FOLDER, filename)
            shutil.move(image_path, rejected_path)
        except:
            pass
        stats["rejected_count"] += 1
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "filename": filename
        }

# Background worker function
def background_processor():
    """Process images in the background"""
    logger.info("Starting background processor")
    
    while True:
        try:
            # Get all image files in upload folder
            image_files = [f for f in os.listdir(UPLOAD_FOLDER) 
                         if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            if image_files:
                logger.info(f"Found {len(image_files)} images to process")
                
                # Process each image
                for image_file in image_files:
                    image_path = os.path.join(UPLOAD_FOLDER, image_file)
                    
                    # Skip files that are still being written
                    try:
                        if os.path.getsize(image_path) == 0:
                            continue
                            
                        # Wait a moment to ensure the file is fully written
                        time.sleep(0.5)
                        
                        # Process the image
                        skip_liveness = not system_settings.get("enableLiveness", False)
                        process_image(image_path, skip_liveness=skip_liveness)
                    except Exception as e:
                        logger.error(f"Error processing {image_file}: {e}")
            
            # Sleep before next check
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in background processor: {e}")
            time.sleep(10)  # Wait longer if there's an error

# Flask routes
@app.route('/')
def index():
    """Main dashboard page"""
    logger.info(f"Loading dashboard template from {os.path.join(TEMPLATES_FOLDER, 'dashboard.html')}")
    return render_template('dashboard.html')

@app.route('/stats')
def get_stats():
    """Get current statistics"""
    try:
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Try to get attendance data - handle both formats
        try:
            attendance_data = attendance_db.get_attendance(date=today)
            
            # Check what format it's in
            if isinstance(attendance_data, dict):
                if "data" in attendance_data and isinstance(attendance_data["data"], list):
                    stats["today_attendance_count"] = len(attendance_data["data"])
                else:
                    stats["today_attendance_count"] = 0
            elif isinstance(attendance_data, list):
                stats["today_attendance_count"] = len(attendance_data)
            else:
                stats["today_attendance_count"] = 0
        except:
            stats["today_attendance_count"] = 0
        
        # Add settings to response
        response_data = {
            "processed_count": stats["processed_count"],
            "successful_count": stats["successful_count"],
            "rejected_count": stats["rejected_count"],
            "today_attendance_count": stats["today_attendance_count"],
            "last_processed": stats["last_processed"],
            "last_recognized": stats["last_recognized"],
            "recent_entries": stats["recent_entries"],
            "settings": system_settings
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        # Return a basic response even on error
        return jsonify({
            "processed_count": stats["processed_count"],
            "successful_count": stats["successful_count"],
            "rejected_count": stats["rejected_count"],
            "today_attendance_count": 0,
            "last_processed": stats["last_processed"],
            "last_recognized": stats["last_recognized"],
            "recent_entries": stats["recent_entries"],
            "settings": system_settings,
            "error": str(e)
        })

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update system settings"""
    try:
        data = request.get_json()
        if data:
            # Update settings
            system_settings.update(data)
            logger.info(f"Updated settings: {system_settings}")
            
            # Save settings
            save_settings()
            
        return jsonify({"success": True, "settings": system_settings})
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/process_now', methods=['POST'])
def process_now():
    """Manually process all images in upload folder"""
    try:
        data = request.get_json() or {}
        check_liveness = data.get('check_liveness', system_settings.get('enableLiveness', False))
        
        # Get all image files
        image_files = [f for f in os.listdir(UPLOAD_FOLDER) 
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        results = []
        for image_file in image_files:
            image_path = os.path.join(UPLOAD_FOLDER, image_file)
            result = process_image(image_path, skip_liveness=not check_liveness)
            results.append(result)
        
        return jsonify({
            "success": True,
            "processed_count": len(results),
            "results": results
        })
    except Exception as e:
        logger.error(f"Error in process_now: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/download_attendance')
def download_attendance():
    """Download attendance CSV file"""
    try:
        date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # Create a simple CSV with available data
        output_file = os.path.join(BASE_DIR, f"attendance_{date}.csv")
        
        try:
            # Get attendance data - handle multiple formats
            attendance_data = attendance_db.get_attendance(date=date)
            
            # Extract data based on format
            if isinstance(attendance_data, dict) and "data" in attendance_data:
                data_rows = attendance_data["data"]
            elif isinstance(attendance_data, list):
                data_rows = attendance_data
            else:
                data_rows = []
                
            # Create DataFrame
            if data_rows and len(data_rows) > 0:
                df = pd.DataFrame(data_rows)
            else:
                # Empty dataframe with headers
                df = pd.DataFrame(columns=["Student ID", "Date", "Time", "Status", "Method"])
                
            # Save CSV
            df.to_csv(output_file, index=False)
            
            return send_file(
                output_file,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"attendance_{date}.csv"
            )
        except Exception as e:
            logger.error(f"Error creating attendance CSV: {e}", exc_info=True)
            
            # Create an empty CSV as fallback
            df = pd.DataFrame(columns=["Student ID", "Date", "Time", "Status", "Method"])
            df.to_csv(output_file, index=False)
            
            return send_file(
                output_file,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"attendance_{date}.csv"
            )
            
    except Exception as e:
        logger.error(f"Error downloading attendance: {e}", exc_info=True)
        return jsonify({"error": str(e)})

# Create dashboard.html template
dashboard_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Attendance System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-bottom: 50px; }
        .status-card { transition: all 0.3s; }
        .recent-entry { animation: fadeIn 1s; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .toggle-switch { transform: scale(1.5); margin-left: 10px; }
        .settings-card { background-color: #f8f9fa; border-left: 4px solid #0d6efd; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-primary mb-4">
        <div class="container">
            <span class="navbar-brand">Automated Attendance System</span>
        </div>
    </nav>
    
    <div class="container">
        <!-- Settings Card -->
        <div class="card mb-4 settings-card">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h5>System Settings</h5>
                        <div class="form-check form-switch mt-3">
                            <label class="form-check-label me-3" for="livenessToggle">
                                <strong>Liveness Detection:</strong>
                            </label>
                            <input class="form-check-input toggle-switch" type="checkbox" id="livenessToggle">
                            <span class="ms-2 text-muted" id="livenessStatus">(OFF)</span>
                        </div>
                        <small class="text-muted d-block mt-1">Enable to detect fake photos. Disable to process all images.</small>
                    </div>
                    <div class="col-md-6 text-end">
                        <button id="saveSettings" class="btn btn-sm btn-outline-primary me-2">Save Settings</button>
                        <button id="processNow" class="btn btn-primary">Process All Images</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Stats Row -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-info text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Processed</h5>
                        <h2 id="processedCount">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Successful</h5>
                        <h2 id="successfulCount">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-danger text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Rejected</h5>
                        <h2 id="rejectedCount">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body text-center">
                        <h5 class="card-title">Today's Attendance</h5>
                        <h2 id="todayCount">0</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Activity and Download Row -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Recent Activity</div>
                    <div class="card-body">
                        <p><strong>Last processed:</strong> <span id="lastProcessed">-</span></p>
                        <p><strong>Last recognized:</strong> <span id="lastRecognized">-</span></p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Download Attendance</div>
                    <div class="card-body">
                        <div class="input-group">
                            <input type="date" id="attendanceDate" class="form-control">
                            <button class="btn btn-outline-secondary" id="downloadBtn">Download CSV</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Recent Entries Table -->
        <div class="card">
            <div class="card-header">Recent Entries</div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Roll Number</th>
                                <th>Time</th>
                                <th>Confidence</th>
                                <th>Method</th>
                                <th>File</th>
                            </tr>
                        </thead>
                        <tbody id="recentEntries">
                            <!-- Entries will be added here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Set default date to today
        document.getElementById('attendanceDate').valueAsDate = new Date();
        
        // Settings object
        let settings = {
            enableLiveness: false
        };
        
        // Initialize toggle based on saved settings
        function loadSettings() {
            // Try to get from localStorage first
            const savedSettings = localStorage.getItem('attendanceSettings');
            if (savedSettings) {
                try {
                    settings = JSON.parse(savedSettings);
                } catch (e) {
                    console.error('Error parsing saved settings:', e);
                }
            }
            
            // Update UI
            document.getElementById('livenessToggle').checked = settings.enableLiveness;
            updateLivenessStatus();
        }
        
        // Update the status text next to toggle
        function updateLivenessStatus() {
            const status = settings.enableLiveness ? 'ON' : 'OFF';
            document.getElementById('livenessStatus').textContent = `(${status})`;
        }
        
        // Save settings
        document.getElementById('saveSettings').addEventListener('click', function() {
            // Update settings from UI
            settings.enableLiveness = document.getElementById('livenessToggle').checked;
            
            // Save to localStorage
            localStorage.setItem('attendanceSettings', JSON.stringify(settings));
            
            // Send to server
            fetch('/update_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                alert('Settings saved successfully');
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                alert('Error saving settings');
            });
            
            // Update UI
            updateLivenessStatus();
        });
        
        // Process now button
        document.getElementById('processNow').addEventListener('click', function() {
            const button = this;
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            
            fetch('/process_now', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ check_liveness: settings.enableLiveness })
            })
            .then(response => response.json())
            .then(data => {
                updateStats();
                alert(`Processed ${data.processed_count} images`);
                button.disabled = false;
                button.textContent = 'Process All Images';
            })
            .catch(error => {
                console.error('Error processing images:', error);
                alert('Error processing images');
                button.disabled = false;
                button.textContent = 'Process All Images';
            });
        });
        
        // Toggle switch
        document.getElementById('livenessToggle').addEventListener('change', function() {
            settings.enableLiveness = this.checked;
            updateLivenessStatus();
        });
        
        // Download button
        document.getElementById('downloadBtn').addEventListener('click', function() {
            const date = document.getElementById('attendanceDate').value;
            window.location.href = `/download_attendance?date=${date}`;
        });
        
        // Update stats from server
        function updateStats() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    // Update counters
                    document.getElementById('processedCount').textContent = data.processed_count || 0;
                    document.getElementById('successfulCount').textContent = data.successful_count || 0;
                    document.getElementById('rejectedCount').textContent = data.rejected_count || 0;
                    document.getElementById('todayCount').textContent = data.today_attendance_count || 0;
                    document.getElementById('lastProcessed').textContent = data.last_processed || '-';
                    document.getElementById('lastRecognized').textContent = data.last_recognized || '-';
                    
                    // Update server settings if available
                    if (data.settings && data.settings.enableLiveness !== undefined) {
                        settings.enableLiveness = data.settings.enableLiveness;
                        document.getElementById('livenessToggle').checked = settings.enableLiveness;
                        updateLivenessStatus();
                    }
                    
                    // Update recent entries
                    const entriesTable = document.getElementById('recentEntries');
                    entriesTable.innerHTML = '';
                    
                    if (data.recent_entries && data.recent_entries.length > 0) {
                        data.recent_entries.forEach(entry => {
                            const row = document.createElement('tr');
                            row.className = 'recent-entry';
                            row.innerHTML = `
                                <td>${entry.roll_number || '-'}</td>
                                <td>${entry.time || '-'}</td>
                                <td>${entry.confidence || '-'}</td>
                                <td>${entry.method || '-'}</td>
                                <td>${entry.file || '-'}</td>
                            `;
                            entriesTable.appendChild(row);
                        });
                    } else {
                        entriesTable.innerHTML = '<tr><td colspan="5" class="text-center">No recent entries</td></tr>';
                    }
                })
                .catch(error => {
                    console.error('Error updating stats:', error);
                    // Still show something in case of error
                    document.getElementById('recentEntries').innerHTML = 
                        '<tr><td colspan="5" class="text-center text-muted">Error loading data</td></tr>';
                });
        }
        
        // Initialize
        loadSettings();
        updateStats();
        
        // Update stats periodically
        setInterval(updateStats, 3000);
    </script>
</body>
</html>"""

# Write dashboard.html to templates folder
with open(os.path.join(TEMPLATES_FOLDER, "dashboard.html"), "w") as f:
    f.write(dashboard_html)

# Start background thread
def start_background_thread():
    thread = threading.Thread(target=background_processor)
    thread.daemon = True
    thread.start()
    logger.info("Background thread started")

# Main entry point
if __name__ == "__main__":
    print("=" * 50)
    print("AUTOMATED ATTENDANCE SYSTEM")
    print("=" * 50)
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Web interface: http://localhost:3000")
    print("Images placed in the uploads folder will be automatically processed")
    print("=" * 50)
    
    # Start background thread
    start_background_thread()
    
    # Run Flask app
    app.run(debug=True, host="0.0.0.0", port=3000, use_reloader=False)