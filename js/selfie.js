// Change this to point to your Flask backend (usually port 5000)
const API_BASE_URL = 'http://192.168.1.7:5000/';
const DEBUG_MODE = true;  // Set to false for production/normal operation

// Strict authorization check
function checkAuthorization() {
    if (!DEBUG_MODE) {
        const isAuthorized = sessionStorage.getItem("isAuthorized") === "true";
        const hasSubject = !!sessionStorage.getItem("verifiedSubject");
        const hasAuthKey = !!sessionStorage.getItem("verifiedAuthKey");  // Fixed missing closing parenthesis
        
        if (!isAuthorized || !hasSubject || !hasAuthKey) {
            console.error("Unauthorized access - redirecting");
            window.location.replace("../index.html");
            return false;
        }
    }
    return true;
}

// Immediate check before any other code runs
if (!checkAuthorization()) {
    throw new Error("Unauthorized");
}

document.addEventListener("DOMContentLoaded", function () {
    // Set debug values if in debug mode
    if (DEBUG_MODE) {
        sessionStorage.setItem("isAuthorized", "true");
        sessionStorage.setItem("verifiedSubject", "DEBUG_SUBJECT");
        sessionStorage.setItem("verifiedAuthKey", "DEBUG_KEY");
        sessionStorage.setItem("verifiedTimestamp", Date.now().toString());
    }

    // Double-check authorization
    if (!sessionStorage.getItem("isAuthorized") || !sessionStorage.getItem("verifiedSubject")) {
        console.error("Unauthorized access attempt");
        alert("Unauthorized access! Please scan QR code first.");
        window.location.replace("../index.html");
        return;
    }

    // Validate timestamp to prevent session reuse
    const verifiedTimestamp = parseInt(sessionStorage.getItem("verifiedTimestamp"));
    if (isNaN(verifiedTimestamp) || Date.now() - verifiedTimestamp > 300000) { // 5 minute maximum session
        console.error("Session expired");
        sessionStorage.clear();
        alert("Session expired! Please scan QR code again.");
        window.location.replace("../index.html");
        return;
    }

    // Check both storages for authorization
    const isAuthorized = sessionStorage.getItem("isAuthorized") === "true";
    const lastScan = localStorage.getItem("lastSuccessfulScan");
    
    console.log("Checking authorization:", {
        sessionAuth: isAuthorized,
        lastScan: lastScan ? JSON.parse(lastScan) : null,
        sessionStorage: {
            subject: sessionStorage.getItem("verifiedSubject"),
            authKey: sessionStorage.getItem("verifiedAuthKey"),
            timestamp: sessionStorage.getItem("verifiedTimestamp")
        }
    });

    // Try to recover from localStorage if session is missing
    if (!isAuthorized && lastScan) {
        try {
            const scanData = JSON.parse(lastScan);
            sessionStorage.setItem("isAuthorized", "true");
            sessionStorage.setItem("verifiedSubject", scanData.subject);
            sessionStorage.setItem("verifiedAuthKey", scanData.authKey);
            sessionStorage.setItem("verifiedTimestamp", scanData.timestamp);
            console.log("Recovered authorization from localStorage");
        } catch (error) {
            console.error("Failed to recover from localStorage:", error);
        }
    }

    // Final authorization check
    if (sessionStorage.getItem("isAuthorized") !== "true") {
        console.error("Not authorized");
        alert("Please scan QR code first!");
        window.location.replace("../index.html");
        return;
    }

    // Initialize UI after authorization confirmed
    const verifiedSubject = sessionStorage.getItem("verifiedSubject");
    const subjectDisplay = document.getElementById("subjectDisplay");
    if (subjectDisplay && verifiedSubject) {
        subjectDisplay.textContent = `Subject: ${verifiedSubject}`;
        subjectDisplay.style.display = "block";
    }

    // Rest of the selfie page initialization
    // Make sure canvas is visible after authorization
    const canvas = document.getElementById("canvas");
    canvas.style.display = "block";

    const captureBtn = document.getElementById("captureBtn");
    const selfieForm = document.getElementById("selfieForm");
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.capture = "user"; // This triggers the front camera

    // Handle capture button
    captureBtn.addEventListener("click", () => {
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.onload = () => {
                    const context = canvas.getContext("2d");
                    canvas.width = img.width;
                    canvas.height = img.height;
                    context.drawImage(img, 0, 0);
                    captureBtn.innerText = "Retake Selfie";
                };
                img.src = event.target.result;
            };
            reader.readAsDataURL(file);
        }
    });

    // Modified form submission
    selfieForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const rollNumber = document.getElementById("rollNumber").value.trim();
        if (!rollNumber) {
            alert("Please enter your roll number");
            return;
        }

        const canvas = document.getElementById("canvas");
        if (!canvas.toDataURL) {
            alert("Please capture your selfie first");
            return;
        }

        const imageData = canvas.toDataURL("image/png");
        const filename = `${rollNumber}_${Date.now()}.png`;

        console.log("Preparing to upload image:", {
            imageSize: imageData.length,
            filename: filename,
            endpoint: `${API_BASE_URL}/upload`
        });

        try {
            // Show loading indicator
            document.getElementById("submitBtn").disabled = true;
            document.getElementById("submitBtn").textContent = "Uploading...";
            
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    image: imageData,
                    filename: filename
                })
            });

            console.log("Server response status:", response.status);
            const result = await response.json();
            console.log("Server response:", result);
            
            if (response.ok) {
                alert("Attendance recorded successfully!");
                sessionStorage.clear();
                localStorage.removeItem("lastSuccessfulScan");
                window.location.replace("../index.html");
            } else {
                alert("Upload failed: " + (result.error || "Unknown error"));
            }
        } catch (err) {
            console.error("Upload Error:", err);
            alert("Failed to upload. Please try again. Error: " + err.message);
        } finally {
            // Reset button state
            document.getElementById("submitBtn").disabled = false;
            document.getElementById("submitBtn").textContent = "Submit";
        }
    });

    // Enhanced logout handler
    const logoutButton = document.getElementById("logoutButton");
    if (logoutButton) {
        logoutButton.addEventListener("click", function() {
            console.log("Logging out - clearing session");
            sessionStorage.clear();
            localStorage.removeItem("lastSuccessfulScan");
            window.location.replace("../index.html");
        });
    }

    // Add beforeunload handler to prevent accidental navigation
    window.addEventListener('beforeunload', function (e) {
        if (canvas.toDataURL && !selfieForm.submitted) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});
