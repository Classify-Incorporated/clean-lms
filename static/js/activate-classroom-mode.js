document.addEventListener("DOMContentLoaded", () => {
    const toggleButton = document.querySelector('.btn-primary.float-right');

    toggleButton.addEventListener('click', function (event) {
        // Prevent default action to stop immediate navigation
        event.preventDefault();

        fetch('/toggle_mode/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Classroom mode toggled:', data.is_classroom_mode);
            // Redirect to the classroom_mode page
            window.location.href = this.href;
        })
        .catch(error => {
            console.error('Error toggling classroom mode:', error);
        });
    });
});
