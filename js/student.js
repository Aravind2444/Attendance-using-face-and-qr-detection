document.addEventListener('DOMContentLoaded', function() {
    // Clear authorization on page load/reload
    if (performance.navigation.type === 1) { // Check if it's a page reload
        sessionStorage.clear();
        localStorage.removeItem("lastSuccessfulScan");
    }

    // Check if already authorized
    const isAuthorized = sessionStorage.getItem("isAuthorized");
    const currentPage = window.location.pathname;
    
    if (isAuthorized && currentPage.includes("index.html")) {
        // Redirect to selfie page if already authorized
        window.location.href = "selfie.html";
        return;
    }

    let qrScanner;

    document.getElementById("startScanner").addEventListener("click", function () {
        // Initialize UI
        document.getElementById("reader").style.display = "block";
        document.getElementById("stopScanner").style.display = "inline-block";
        document.getElementById("startScanner").style.display = "none";

        // Log initial localStorage state
        console.log("Starting QR Scanner. Initial values:", {
            authKey: localStorage.getItem("latestAuthKey"),
            subject: localStorage.getItem("latestSubject"),
            timestamp: new Date().toISOString()
        });

        qrScanner = new Html5Qrcode("reader");

        Html5Qrcode.getCameras().then(devices => {
            if (devices.length === 0) {
                alert("No cameras found! Please check permissions.");
                return;
            }

            let cameraId = devices[0].id;
            for (let device of devices) {
                if (device.label.toLowerCase().includes("back")) {
                    cameraId = device.id;
                    break;
                }
            }

            const config = {
                fps: 10,
                qrbox: undefined,
                aspectRatio: 1.0,
                formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE]
            };

            // Start QR scanner
            qrScanner.start(
                cameraId,
                config,
                (decodedText) => {
                    try {
                        console.log("Raw QR Data:", decodedText);
                        
                        // Parse QR data and validate timestamp
                        let qrData = JSON.parse(decodedText);
                        const currentTime = Date.now();
                        const scanTime = new Date().toISOString();
                        const age = currentTime - qrData.timestamp;
                        
                        // Debug timing information with millisecond precision
                        console.log("Timing Check:", {
                            currentTime,
                            qrTimestamp: qrData.timestamp,
                            timeSinceCreation: age,
                            maxAllowedAge: 200,
                            validUntil: new Date(qrData.timestamp + 200).toISOString(),
                            scannedAt: scanTime
                        });

                        // Strict 2000ms (2 second) validation
                        if (age > 200) {
                            console.log("QR Expired:", {
                                currentTime: new Date(currentTime).toISOString(),
                                qrCreated: new Date(qrData.timestamp).toISOString(),
                                ageMs: age,
                                maxAgeMs: 200
                            });
                            throw new Error("QR code has expired. Please scan the current QR code.");
                        }

                        // Store in both session and local storage for backup
                        sessionStorage.setItem("isAuthorized", "true");
                        sessionStorage.setItem("verifiedSubject", qrData.subject);
                        sessionStorage.setItem("verifiedAuthKey", qrData.authKey);
                        sessionStorage.setItem("verifiedTimestamp", qrData.timestamp);
                        
                        // Backup to localStorage
                        localStorage.setItem("lastSuccessfulScan", JSON.stringify({
                            subject: qrData.subject,
                            authKey: qrData.authKey,
                            timestamp: qrData.timestamp,
                            scannedAt: scanTime
                        }));

                        console.log("Storage set:", {
                            session: {
                                isAuthorized: sessionStorage.getItem("isAuthorized"),
                                subject: sessionStorage.getItem("verifiedSubject"),
                                authKey: sessionStorage.getItem("verifiedAuthKey")
                            },
                            local: localStorage.getItem("lastSuccessfulScan")
                        });

                        // Success case
                        document.getElementById("reader").style.border = "3px solid green";
                        console.log("Valid QR code detected!");
                        
                        // Set a specific flag for valid QR scan
                        sessionStorage.setItem("qrScanned", "true");
                        alert("Access granted for subject: " + qrData.subject);
                        
                        stopQRScanner();
                        setTimeout(() => {
                            window.location.href = "selfie.html";
                        }, 1000);
                        
                    } catch (error) {
                        console.error("QR Processing Error:", error);
                        document.getElementById("reader").style.border = "3px solid red";
                        alert(error.message);
                    }
                },
                (error) => console.warn("Scanner Error:", error)
            ).catch(err => {
                console.error("Scanner Start Error:", err);
                stopQRScanner();
            });
        });
    });

    // Stop scanner button handler
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

    // Add this to handle logout/reset
    function resetAuthorization() {
        sessionStorage.clear();
        window.location.href = "index.html";
    }
});
