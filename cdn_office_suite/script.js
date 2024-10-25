async function checkService(serviceName, port) {
    // Show the loading overlay and disable pointer events on the body
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.body.classList.add('loading-active');

    // Get the user's IP address (assumes they're accessing from the desired IP)
    let ip = window.location.hostname;
    
    // Construct the target URL
    let targetUrl = `http://${ip}:${port}`;
    
    // Create a URL-friendly name for the service to match your file naming convention
    let serviceFileName = serviceName.toLowerCase().replace(" ", "_") + "_not_installed.html";
    let notInstalledUrl = `/${serviceFileName}`;

    try {
        // Check if the service is active
        const response = await fetch(targetUrl, { method: 'HEAD', mode: 'no-cors' });
        if (response.ok || response.type === 'opaque') {
            // Open the service in a new tab if active
            window.open(targetUrl, '_blank');
        } else {
            // Open "not installed" page in a new tab if inactive
            window.open(notInstalledUrl, '_blank');
        }
    } catch (error) {
        // Open "not installed" page in a new tab on error
        window.open(notInstalledUrl, '_blank');
    } finally {
        // Hide the loading overlay and re-enable pointer events after the check is complete
        document.getElementById('loadingOverlay').style.display = 'none';
        document.body.classList.remove('loading-active');
    }
}
