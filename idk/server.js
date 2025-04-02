const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// Create uploads directory if it doesn't exist
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

// Test endpoint
app.get('/', (req, res) => {
    res.json({ status: 'Server is running' });
});

// Upload endpoint
app.post('/upload', (req, res) => {
    try {
        const { image, filename } = req.body;
        const authKey = req.headers['auth-key'];

        if (!authKey) {
            return res.status(401).json({ 
                success: false, 
                message: 'Authentication required' 
            });
        }

        // Remove the data:image/png;base64 prefix
        const base64Data = image.replace(/^data:image\/\w+;base64,/, '');
        const filePath = path.join(uploadDir, filename);

        // Save the image
        fs.writeFileSync(filePath, base64Data, { encoding: 'base64' });

        res.json({
            success: true,
            message: 'File uploaded successfully'
        });
    } catch (error) {
        console.error('Upload error:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to upload file'
        });
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});