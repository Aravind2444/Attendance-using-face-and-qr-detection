import os
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

class AttendanceDB:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.attendance_file = os.path.join(self.base_dir, "attendance.csv")
        
        # Create attendance file if it doesn't exist
        if not os.path.exists(self.attendance_file):
            self._initialize_file()
            
        print(f"Attendance database initialized: {self.attendance_file}")
    
    def _initialize_file(self):
        """Create a new attendance file"""
        df = pd.DataFrame(columns=[
            "Student ID", "Date", "Time", "Status", "Method"
        ])
        df.to_csv(self.attendance_file, index=False)
        print(f"Created new attendance file: {self.attendance_file}")
    
    def mark_attendance(self, student_id, status="Present", method="Face"):
        """Mark attendance for a student"""
        try:
            # Load existing data
            df = pd.read_csv(self.attendance_file)
            
            # Get current date and time
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M:%S")
            
            # Check if student already has entry for today
            today_record = df[(df["Student ID"] == student_id) & (df["Date"] == current_date)]
            
            if len(today_record) == 0:
                # Create new record
                new_record = {
                    "Student ID": student_id,
                    "Date": current_date,
                    "Time": current_time,
                    "Status": status,
                    "Method": method
                }
                df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            else:
                # Update existing record
                df.loc[(df["Student ID"] == student_id) & (df["Date"] == current_date), 
                      ["Time", "Status", "Method"]] = [current_time, status, method]
            
            # Save updated data
            df.to_csv(self.attendance_file, index=False)
            
            return {"success": True, "message": f"Attendance marked for {student_id}"}
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error marking attendance: {str(e)}"}
    
    def get_attendance(self, date=None, student_id=None):
        """Get attendance records"""
        try:
            if not os.path.exists(self.attendance_file):
                print(f"Attendance file not found: {self.attendance_file}")
                return {"success": False, "message": "Attendance file not found", "data": []}
                
            df = pd.read_csv(self.attendance_file)
            
            # Apply filters
            if date:
                df = df[df["Date"] == date]
            
            if student_id:
                df = df[df["Student ID"] == student_id]
            
            # Convert to records format
            records = df.to_dict(orient="records")
            return {"success": True, "data": records}
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error getting attendance: {str(e)}", "data": []}

    def export_csv(self, output_path=None, date=None):
        """Export attendance to CSV file"""
        try:
            df = pd.read_csv(self.attendance_file)
            
            # Apply date filter if provided
            if date:
                df = df[df["Date"] == date]
            
            # Use default path if none provided
            if not output_path:
                date_str = date or datetime.now().strftime("%Y%m%d")
                output_path = os.path.join(self.base_dir, f"attendance_export_{date_str}.csv")
            
            # Export to CSV
            df.to_csv(output_path, index=False)
            
            return {"success": True, "path": output_path, "message": f"Exported {len(df)} records to CSV"}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error exporting to CSV: {str(e)}"}

@app.route('/process_now', methods=['POST'])
def process_now():
    """Manually trigger processing of all files in upload folder"""
    try:
        data = request.get_json() or {}
        check_liveness = data.get('check_liveness', False)
        
        image_files = [f for f in os.listdir(UPLOAD_FOLDER) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        results = []
        for image_file in image_files:
            filepath = os.path.join(UPLOAD_FOLDER, image_file)
            # Skip liveness check for manual processing
            result = process_image(filepath, skip_liveness=True)
            results.append(result)
        
        return jsonify({
            "success": True,
            "processed_count": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

attendance_db = AttendanceDB()