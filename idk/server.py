from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure uploads folder
UPLOAD_FOLDER = 'upload'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Created upload directory at {os.path.abspath(UPLOAD_FOLDER)}")

@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'Server is running'})

@app.route('/upload', methods=['POST'])  # Note: changed from /uploads to /upload
def upload_file():
    try:
        logger.info("Received upload request")
        logger.debug(f"Headers: {request.headers}")
        
        data = request.json
        if not data:
            raise ValueError("No JSON data received")
            
        image_data = data.get('image', '').split(',')[1]
        filename = data.get('filename')
        
        logger.info(f"Processing upload for file: {filename}")
        
        # Save the image
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        logger.info(f"File saved successfully at {file_path}")
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully'
        })
    
    except Exception as e:
        logger.error(f"Upload Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = 5000
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)