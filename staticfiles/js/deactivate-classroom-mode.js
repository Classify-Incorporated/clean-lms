document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM fully loaded");
    const exitButton = document.querySelector('.btn-light');
    console.log("Exit button found:", exitButton);

    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (!csrfTokenMeta) {
        console.error("CSRF token meta tag not found!");
        return; // Exit the function early
    }

    const csrfToken = csrfTokenMeta.getAttribute('content');

    if (exitButton) { // Check if the button exists
        exitButton.addEventListener('click', function (event) {
            // Prevent default action to stop immediate navigation
            event.preventDefault();

            const redirectUrl = exitButton.getAttribute('href'); // Capture the redirect URL
            console.log("Redirect URL:", redirectUrl); // Log the captured URL

            fetch('/toggle_mode/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                console.log("Fetch response received");
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Classroom mode deactivated:', data.is_classroom_mode);
                if (!data.is_classroom_mode) {
                    // Use the captured redirect URL
                    console.log("Redirecting to:", redirectUrl);
                    window.location.href = redirectUrl;
                }
            })
            .catch(error => {
                console.error('Error deactivating classroom mode:', error);
            });
        });
    } else {
        console.warn('Exit button not found in the DOM.');
    }
});
