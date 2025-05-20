document.addEventListener('DOMContentLoaded', () => {
    const suggestedFriendsList = document.getElementById('suggested-friends-list');

    suggestedFriendsList.addEventListener('click', (event) => {
        if (event.target.classList.contains('add-friend-btn') && !event.target.disabled) {
            const toUserId = event.target.dataset.userId;

            fetch('/social/friend/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(), // Ensure CSRF token is included
                },
                body: JSON.stringify({ to_user: toUserId }),
            })
                .then((response) => {
                    if (!response.ok) {
                        return response.json().then((data) => {
                            throw new Error(data.error || 'Failed to send friend request.');
                        });
                    }
                    return response.json();
                })
                .then((data) => {
                    // Display success message using displayToast
                    displayToast('Friend request sent successfully!', 'success');
                    event.target.innerText = 'Request Sent';
                    event.target.disabled = true;
                })
                .catch((error) => {
                    console.error('Error sending friend request:', error);
                    // Display error message using displayToast
                    displayToast(error.message || 'An error occurred while sending the friend request.', 'error');
                });
        }
    });
});

// Helper function to fetch CSRF token
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find((row) => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}
