document.getElementById('friend-suggestions-tab').addEventListener('click', () => {
    const suggestedFriendsList = document.getElementById('suggested-friends-list');
    suggestedFriendsList.innerHTML = '<p>Loading friend suggestions...</p>';

    // Fetch users, sent friend requests, and friends concurrently
    Promise.all([
        fetch('/social/users/').then((response) => response.json()),
        fetch('/social/friend/sent-requests/').then((response) => response.json()),
        fetch('/social/friend/friends/').then((response) => response.json())
    ])
    .then(([users, sentRequests, friends]) => {
        suggestedFriendsList.innerHTML = '';

        // Convert friends and sent requests to Sets for quick lookup
        const friendIds = new Set(friends.map(friend => friend.id));
        const sentRequestIds = new Set(sentRequests);

        // Filter users: Exclude those who are already friends
        const filteredUsers = users.filter(user => !friendIds.has(user.id));

        if (filteredUsers.length === 0) {
            suggestedFriendsList.innerHTML = '<p>No new friend suggestions available.</p>';
            return;
        }

        // Render user list
        filteredUsers.forEach((user) => {
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item d-flex align-items-center';

            const isRequestSent = sentRequestIds.has(user.id);

            const displayName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username;

            listItem.innerHTML = `
                <img src="${user.student_photo || '/static/assets/dist/images/def_user.jpg'}" 
                     alt="${displayName}" 
                     class="rounded-circle mr-3" 
                     style="width: 60px; height: 60px; object-fit: cover;">
                <span class="flex-grow-1"><strong>${displayName}</strong></span>
                <button class="btn btn-${isRequestSent ? 'secondary' : 'primary'} btn-sm add-friend-btn" 
                        data-user-id="${user.id}" 
                        ${isRequestSent ? 'disabled' : ''}>
                    ${isRequestSent ? 'Request Sent' : 'Add Friend'}
                </button>
            `;
            suggestedFriendsList.appendChild(listItem);
        });

        // Attach event listeners to add friend buttons
        document.querySelectorAll('.add-friend-btn').forEach((button) => {
            button.addEventListener('click', (event) => {
                const userId = event.currentTarget.dataset.userId;
                sendFriendRequest(userId, event.currentTarget);
            });
        });
    })
    .catch((error) => {
        console.error('Error fetching friend suggestions or requests:', error);
        suggestedFriendsList.innerHTML = '<p>Error loading friend suggestions. Please try again later.</p>';
    });
});

// Function to send a friend request
function sendFriendRequest(userId, buttonElement) {
    fetch('/social/friend/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            to_user: userId,
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            buttonElement.textContent = "Request Sent";
            buttonElement.classList.remove("btn-primary");
            buttonElement.classList.add("btn-secondary");
            buttonElement.disabled = true;
        } else {
            console.error("Error sending request:", data.error);
        }
    })
    .catch(error => {
        console.error("Error sending request:", error);
    });
}

// Function to get CSRF token
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// Pending Friend Requests Tab
document.getElementById('friend-requests-tab').addEventListener('click', () => {
    const pendingRequestsList = document.getElementById('friend-requests-list');
    pendingRequestsList.innerHTML = '<p>Loading pending requests...</p>';

    fetch('/social/friend/pending-requests/')
    .then(response => response.json())
    .then(requests => {
        pendingRequestsList.innerHTML = '';

        if (requests.length === 0) {
            pendingRequestsList.innerHTML = '<p>No pending friend requests.</p>';
            return;
        }

        requests.forEach((request) => {
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item d-flex align-items-center';

            listItem.innerHTML = `
                <img src="${request.from_user_photo || '/static/assets/dist/images/def_user.jpg'}" 
                     alt="${request.from_user_name}" 
                     class="rounded-circle mr-3" 
                     style="width: 60px; height: 60px; object-fit: cover;">
                <span class="flex-grow-1"><strong>${request.from_user_name}</strong></span>
                <button class="btn btn-success btn-sm accept-btn" data-request-id="${request.id}">Accept</button>
                <button class="btn btn-danger btn-sm reject-btn ml-2" data-request-id="${request.id}">Reject</button>
            `;
            pendingRequestsList.appendChild(listItem);
        });

        // Attach event listeners for accept and reject buttons
        document.querySelectorAll('.accept-btn').forEach((button) => {
            button.addEventListener('click', (event) => {
                const requestId = event.currentTarget.dataset.requestId;
                handleFriendRequest(requestId, true, event.currentTarget.closest('.list-group-item'));
            });
        });

        document.querySelectorAll('.reject-btn').forEach((button) => {
            button.addEventListener('click', (event) => {
                const requestId = event.currentTarget.dataset.requestId;
                handleFriendRequest(requestId, false, event.currentTarget.closest('.list-group-item'));
            });
        });
    })
    .catch(error => {
        console.error('Error loading pending requests:', error);
        pendingRequestsList.innerHTML = '<p>Error loading requests. Please try again later.</p>';
    });
});

// Function to accept or reject friend requests
function handleFriendRequest(requestId, isAccepted, listItem) {
    const endpoint = isAccepted ? `/social/friend/${requestId}/accept/` : `/social/friend/${requestId}/reject/`;

    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            listItem.remove();
        } else {
            console.error("Error updating request:", data.error);
        }
    })
    .catch(error => {
        console.error("Error updating request:", error);
    });
}
