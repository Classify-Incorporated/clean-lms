document.getElementById('chat-tab').addEventListener('click', () => {
    const chatList = document.getElementById('chat-list');
    chatList.innerHTML = '<p>Loading friends...</p>';

    // Fetch the list of friends from the backend
    fetch('/social/friend/friends/')
        .then(response => response.json())
        .then(friends => {
            chatList.innerHTML = ''; // Clear the previous content

            if (friends.length === 0) {
                chatList.innerHTML = '<p>You have no friends yet.</p>';
                return;
            }

            friends.forEach(friend => {
                const profileImage = friend.photo || '/static/assets/img/def_user.jpg';
                const listItem = document.createElement('div');
                listItem.className = 'list-group-item d-flex align-items-center';

                listItem.innerHTML = `
                    <img src="${profileImage}" 
                         alt="${friend.name}" 
                         class="rounded-circle mr-3" 
                         style="width: 50px; height: 50px; object-fit: cover;">
                    <span class="flex-grow-1"><strong>${friend.name}</strong></span>
                    <button class="btn btn-primary btn-sm chat-btn" 
                        data-user-id="${friend.id}" 
                        data-user-name="${friend.name}"
                        data-user-photo="${profileImage}">
                        <i class="fas fa-comments"></i> Chat
                    </button>
                `;

                chatList.appendChild(listItem);
            });

            // Attach event listener to each chat button
            document.querySelectorAll('.chat-btn').forEach(button => {
                button.addEventListener('click', (event) => {
                    const userId = event.currentTarget.dataset.userId;
                    const userName = event.currentTarget.dataset.userName;
                    const userPhoto = event.currentTarget.dataset.userPhoto;
                    openChatWindow(userId, userName, userPhoto);
                });
            });
        })
        .catch(error => {
            console.error('Error loading friends:', error);
            chatList.innerHTML = '<p>Error loading friends. Please try again later.</p>';
        });
});

// Function to open chat window
function openChatWindow(userId, userName, userPhoto) {
    let chatModal = document.getElementById(`chatModal-${userId}`);

    // If the chat modal already exists, show it
    if (chatModal) {
        chatModal.style.display = 'flex';
        return;
    }

    // If userPhoto is not available, use a default image
    const userImage = userPhoto || '/static/assets/dist/images/def_user.jpg';

    // Create a new chat modal
    chatModal = document.createElement('div');
    chatModal.classList.add('chat-modal');
    chatModal.id = `chatModal-${userId}`;

    chatModal.innerHTML = `
        <div class="chat-modal-header">
            <img src="${userImage}" alt="${userName}" class="chat-modal-user-photo">
            <span class="chat-user-name">${userName}</span>
            <button class="close-chat-btn" data-user-id="${userId}">&times;</button>
        </div>
        <div class="chat-modal-body" id="chatMessages-${userId}">
            <p>Loading messages...</p>
        </div>
        <div class="chat-modal-footer">
            <textarea id="chatInput-${userId}" class="chat-textarea" placeholder="Type a message..."></textarea>
            <button class="send-message-btn" data-user-id="${userId}" data-user-name="${userName}">
                <i class="fas fa-paper-plane"></i>
            </button>
        </div>
    `;

    document.body.appendChild(chatModal);
    chatModal.style.display = 'flex';

    // Load messages
    loadChatMessages(userId, userName);

    // Close chat window
    document.querySelector(`.close-chat-btn[data-user-id="${userId}"]`).addEventListener('click', () => {
        chatModal.style.display = 'none';
    });

    // Send message
    document.querySelector(`.send-message-btn[data-user-id="${userId}"]`).addEventListener('click', () => {
        sendMessage(userId, userName);
    });
}


// Function to load chat messages
function loadChatMessages(userId) {
    fetch(`/social/chat/?receiver=${userId}`)
        .then(response => response.json())
        .then(messages => {
            const chatMessagesDiv = document.getElementById(`chatMessages-${userId}`);
            chatMessagesDiv.innerHTML = '';

            messages.forEach(message => {
                const messageDiv = document.createElement('div');

                // Use is_sent from the backend
                const isSent = message.is_sent;

                messageDiv.classList.add('chat-message', isSent ? 'sent' : 'received');

                const senderPhoto = message.sender_photo || '/static/assets/dist/images/def_user.jpg'; 

                messageDiv.innerHTML = `
                    ${!isSent ? `<img src="${senderPhoto}" alt="User Photo" class="chat-message-photo">` : ''}
                    <div class="chat-message-content ${isSent ? 'sent-message' : 'received-message'}">
                        <div class="chat-message-text">${message.message}</div>
                    </div>
                `;

                chatMessagesDiv.appendChild(messageDiv);
            });

            // Auto-scroll to the latest message
            chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
        })
        .catch(error => {
            console.error('Error loading messages:', error);
        });
}


// Function to send a chat message
function sendMessage(userId, userName) {
    const chatInput = document.getElementById(`chatInput-${userId}`);
    const message = chatInput.value.trim();

    if (!message) return;

    fetch('/social/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            receiver: userId,
            message: message,
        })
    })
    .then(response => response.json())
    .then(data => {
        const chatMessagesDiv = document.getElementById(`chatMessages-${userId}`);
        const newMessage = document.createElement('div');
        newMessage.innerHTML = `<strong>You:</strong> ${data.message}`;
        chatMessagesDiv.appendChild(newMessage);
        chatInput.value = '';
    })
    .catch(error => {
        console.error('Error sending message:', error);
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
