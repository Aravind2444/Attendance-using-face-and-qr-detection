from flask import Flask, request, jsonify
import os
import base64
import pandas as pd  # For handling CSV files
from flask_cors import CORS  # Import CORS
from werkzeug.utils import secure_filename  # Import secure_filename

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Ensure the "uploads" folder exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Route for displaying attendance data from CSV
@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    try:
        df = pd.read_csv('attendance.csv')  # Modify filename if needed
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route for handling image uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        data = request.json
        if not data or 'image' not in data or 'filename' not in data:
            return jsonify({'error': 'Missing required data'}), 400
        
        # Get the image data and filename
        image_data = data['image']
        filename = data['filename']
        
        # Make sure filename is safe
        filename = secure_filename(filename)
        
        # Ensure we're using the correct uploads directory path
        # Use an absolute path to the backend/uploads directory
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Complete file path
        file_path = os.path.join(upload_dir, filename)
        
        # Process the image (base64 format)
        if image_data.startswith('data:image'):
            # Split the base64 string to get only the data part
            image_data = image_data.split(',')[1]
        
        # Decode and save the image
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        # Log the upload
        app.logger.info(f"File saved to {file_path}")
        
        return jsonify({'success': True, 'message': 'File uploaded successfully'}), 200
    
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)