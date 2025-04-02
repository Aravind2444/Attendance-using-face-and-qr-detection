let qrInterval;

document.getElementById("generateQR").addEventListener("click", function () {
    generateAndDisplayQR(); // Generate the first QR code immediately

    // Clear any previous intervals
    if (qrInterval) {
        clearInterval(qrInterval);
    }

    // Update QR code every 10 seconds
    qrInterval = setInterval(() => {
        generateAndDisplayQR();
    }, 2000);
});

function generateAndDisplayQR() {
    const subject = document.getElementById("subject").value;
    if (!subject) {
        alert("Please enter a subject name.");
        return;
    }

    const authKey = generateAuthKey();
    const qrData = JSON.stringify({ subject, authKey });

    document.getElementById("qrcode").innerHTML = ""; // Clear previous QR
    new QRCode(document.getElementById("qrcode"), {
        text: qrData,
        width: 300,  // Increased size
        height: 300, // Increased size
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H // Highest error correction level
    });

    // Store the latest key for verification in localStorage (for frontend-only validation)
    localStorage.setItem("latestAuthKey", authKey);
    localStorage.setItem("latestSubject", subject);

    console.log("New QR Code Generated: ", qrData);
}

function generateAuthKey() {
    return Math.random().toString(36).substr(2, 8); // Generates a random 8-character key
}
