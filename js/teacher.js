let qrInterval;
let countdownInterval;
let countdownElement;

document.getElementById("generateQR").addEventListener("click", function () {
    const subject = document.getElementById("subject").value;
    if (!subject) {
        alert("Please enter a subject name.");
        return;
    }

    // Clear any previous intervals
    if (qrInterval) {
        clearInterval(qrInterval);
    }
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    // Remove existing countdown element if it exists
    if (countdownElement) {
        countdownElement.remove();
    }

    // Generate first QR code immediately
    generateAndDisplayQR(subject);

    // Update QR code every 5 seconds instead of 2
    qrInterval = setInterval(() => {
        generateAndDisplayQR(subject);
    }, 2000);  // Changed to 5000ms (5 seconds)

    // Add countdown timer
    countdownElement = document.createElement("div");
    countdownElement.id = "countdown";
    const qrElement = document.getElementById("qrcode");
    qrElement.parentNode.insertBefore(countdownElement, qrElement);

    let timeLeft = 2;  // Changed to 5 seconds
    updateCountdown();

    countdownInterval = setInterval(() => {
        timeLeft--;
        if (timeLeft < 0) timeLeft = 1;  // Reset to 4 so it shows 5,4,3,2,1
        updateCountdown();
    }, 1000);

    function updateCountdown() {
        countdownElement.textContent = `Next QR in: ${timeLeft + 1} second${timeLeft !== 0 ? 's' : ''}`;
    }
});

function generateAndDisplayQR(subject) {
    const authKey = generateAuthKey();
    const timestamp = Date.now();
    
    // Create QR data with longer validity (6 seconds to account for delay)
    const qrData = JSON.stringify({ 
        subject,
        authKey,
        timestamp,
        validUntil: timestamp + 2000 // 6 second validity for overlap
    });

    // Generate QR code
    const qrElement = document.getElementById("qrcode");
    qrElement.innerHTML = "";
    new QRCode(qrElement, {
        text: qrData,
        width: 500,
        height: 500,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });

    console.log("Generated new QR code:", {
        subject,
        authKey,
        timestamp: new Date(timestamp).toISOString()
    });
}

function generateAuthKey() {
    return Math.random().toString(36).substr(2, 8);
}

// Clean up intervals when leaving the page
window.addEventListener('beforeunload', () => {
    if (qrInterval) clearInterval(qrInterval);
    if (countdownInterval) clearInterval(countdownInterval);
});
