document.addEventListener('DOMContentLoaded', () => {
    const friendRequestsList = document.getElementById('friend-requests-list');

    friendRequestsList.addEventListener('click', (event) => {
        if (event.target.classList.contains('accept-friend-btn')) {
            const requestId = event.target.dataset.requestId;

            fetch(`/social/friend/${requestId}/accept/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error('Failed to accept friend request.');
                    }
                    return response.json();
                })
                .then((data) => {
                    alert(data.message || 'Friend request accepted.');
                    event.target.closest('.list-group-item').remove();
                })
                .catch((error) => {
                    console.error(error);
                    alert('An error occurred while accepting the friend request.');
                });
        }

        if (event.target.classList.contains('reject-friend-btn')) {
            const requestId = event.target.dataset.requestId;

            fetch(`/social/friend/${requestId}/reject/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                },
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error('Failed to reject friend request.');
                    }
                    return response.json();
                })
                .then((data) => {
                    alert(data.message || 'Friend request rejected.');
                    event.target.closest('.list-group-item').remove();
                })
                .catch((error) => {
                    console.error(error);
                    alert('An error occurred while rejecting the friend request.');
                });
        }
    });
});

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find((row) => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}
