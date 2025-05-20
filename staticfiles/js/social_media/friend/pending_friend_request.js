document.addEventListener('DOMContentLoaded', () => {
    const friendRequestsTab = document.getElementById('friend-requests-tab');
    const friendRequestsList = document.getElementById('friend-requests-list');

    friendRequestsTab.addEventListener('click', () => {
        friendRequestsList.innerHTML = '<p>Loading friend requests...</p>';

        fetch('/social/friend/pending-requests/')
            .then((response) => {
                if (!response.ok) {
                    throw new Error('Failed to fetch friend requests.');
                }
                return response.json();
            })
            .then((data) => {
                friendRequestsList.innerHTML = '';

                if (data.length === 0) {
                    friendRequestsList.innerHTML = '<p>No friend requests at the moment.</p>';
                    return;
                }

                data.forEach((request) => {
                    const listItem = document.createElement('div');
                    listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                    listItem.innerHTML = `
                        <div class="d-flex align-items-center">
                            <img src="${request.from_user_photo || '/static/assets/img/def_user.jpg'}" 
                                 alt="${request.from_user_name}" 
                                 class="rounded-circle mr-3" 
                                 style="width: 50px; height: 50px; object-fit: cover;">
                            <span>${request.from_user_name}</span>
                        </div>
                        <div>
                            <button class="btn btn-success btn-sm accept-friend-btn" data-request-id="${request.id}">Accept</button>
                            <button class="btn btn-danger btn-sm reject-friend-btn" data-request-id="${request.id}">Reject</button>
                        </div>
                    `;
                    friendRequestsList.appendChild(listItem);
                });
            })
            .catch((error) => {
                console.error(error);
                friendRequestsList.innerHTML = '<p>Error loading friend requests. Please try again later.</p>';
            });
    });
});
