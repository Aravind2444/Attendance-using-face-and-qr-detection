document.addEventListener("DOMContentLoaded", function () {
    const video = document.getElementById("camera");
    const canvas = document.getElementById("canvas");
    const captureBtn = document.getElementById("captureBtn");
    const selfieForm = document.getElementById("selfieForm");

    // Get subject and auth key from local storage
    const subject = localStorage.getItem("latestSubject");
    const storedAuthKey = localStorage.getItem("latestAuthKey");

    if (!subject || !storedAuthKey) {
        alert("Invalid access! Please scan the QR code again.");
        window.location.href = "../index.html"; // Redirect back
        return;
    }

    console.log("Subject:", subject);
    console.log("Auth Key:", storedAuthKey);

    // Access user camera
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error("Camera access denied:", err);
            alert("Camera access is required for attendance.");
        });

    // Capture image
    captureBtn.addEventListener("click", () => {
        const context = canvas.getContext("2d");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        captureBtn.innerText = "Retake Selfie";
        console.log("Image captured on canvas");
    });

    // Submit form
    selfieForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const rollNumber = document.getElementById("rollNumber").value.trim();
        if (!rollNumber) {
            alert("Please enter your roll number.");
            return;
        }

        const imageData = canvas.toDataURL("image/png");
        const filename = `${subject}_${rollNumber}.png`;

        console.log("Filename:", filename);
        console.log("Sending Image Data...");

        try {
            const response = await fetch("/upload", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: imageData, filename })
            });

            const result = await response.json();
            console.log("Upload Response:", result);

            if (result.success) {
                alert("Photo Taken Successfully!");
                window.location.href = "../index.html"; // Redirect home
            } else {
                alert("Upload failed: " + result.message);
            }
        } catch (err) {
            console.error("Error uploading:", err);
            alert("Error uploading selfie.");
        }
    });
});
