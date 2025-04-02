let qrScanner;

document.getElementById("startScanner").addEventListener("click", function () {
    document.getElementById("reader").style.display = "block";
    document.getElementById("stopScanner").style.display = "inline-block";
    document.getElementById("startScanner").style.display = "none";

    qrScanner = new Html5Qrcode("reader");

    // Get available cameras
    Html5Qrcode.getCameras().then(devices => {
        if (devices.length === 0) {
            alert("No cameras found! Please check permissions.");
            return;
        }

        let cameraId = devices[0].id; // Default to first camera
        for (let device of devices) {
            if (device.label.toLowerCase().includes("back") || device.label.toLowerCase().includes("rear")) {
                cameraId = device.id; // Prefer rear camera
                break;
            }
        }

        // Properly initialize the scanner
        qrScanner.start(
            cameraId,
            { fps: 10, qrbox: { width: 250, height: 250 } },
            (decodedText) => {
                document.getElementById("result").innerText = decodedText;
                alert("Attendance Marked for Roll No: " + decodedText);
                stopQRScanner();
            },
            (error) => {
                console.warn("QR Scan Error:", error);
            }
        ).catch(err => {
            console.error("Error starting QR scanner:", err);
            alert("Failed to start camera: " + err);
            stopQRScanner();
        });
    }).catch(err => {
        console.error("Camera access error:", err);
        alert("Error accessing camera. Please allow camera permissions.");
    });
});

document.getElementById("stopScanner").addEventListener("click", stopQRScanner);

function stopQRScanner() {
    if (qrScanner) {
        qrScanner.stop().then(() => {
            document.getElementById("reader").style.display = "none";
            document.getElementById("startScanner").style.display = "inline-block";
            document.getElementById("stopScanner").style.display = "none";
        }).catch((err) => {
            console.error("Error stopping scanner:", err);
        });
    }
}
