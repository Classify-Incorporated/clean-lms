const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
const classActionButton = document.getElementById('classActionButton');

document.addEventListener('DOMContentLoaded', function () {
  const subjectId = classActionButton.getAttribute('data-subject-id');
  const currentStateUrl = `/teacher_attendance/${subjectId}/current-state/`;

  // Fetch current state on page load
  fetch(currentStateUrl, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  })
    .then(response => {
      if (response.ok) {
        return response.json();
      }
      throw new Error('Failed to fetch current state.');
    })
    .then(data => {
      const isActive = data.is_active;
      classActionButton.setAttribute('data-is-active', isActive);
      classActionButton.innerHTML = isActive
        ? '<i class="fas fa-chalkboard-teacher"></i> End Class'
        : '<i class="fas fa-chalkboard-teacher"></i> Start Class';
    })
    .catch(error => console.error('Error fetching current state:', error));
});

// Handle start/end class actions
classActionButton.addEventListener('click', function () {
  const subjectId = this.getAttribute('data-subject-id');
  const isActive = this.getAttribute('data-is-active') === 'true';

  const url = isActive
    ? `/teacher_attendance/${subjectId}/end-class/`
    : `/teacher_attendance/${subjectId}/start-class/`;

  const action = isActive ? 'ending' : 'starting';

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    }
  })
    .then(response => {
      console.log('Response Status:', response.status);
      if (response.ok) {
        return response.json();
      }
      return response.json().then(err => {
        console.error('Error Response:', err);
        throw new Error(err.error || 'Network response was not ok.');
      });
    })
    .then(data => {
      console.log('Success:', data);

      // SweetAlert2 for success
      Swal.fire({
        icon: 'success',
        title: isActive
          ? 'Class ended successfully!'
          : 'Class started successfully!',
        confirmButtonText: 'OK'
      });

      if (isActive) {
        classActionButton.setAttribute('data-is-active', 'false');
        classActionButton.innerHTML = '<i class="fas fa-chalkboard-teacher"></i> Start Class';
      } else {
        classActionButton.setAttribute('data-is-active', 'true');
        classActionButton.innerHTML = '<i class="fas fa-chalkboard-teacher"></i> End Class';

        // Open the attendance modal when starting the class
        openAttendanceModalCM(subjectId);
      }
    })
    .catch(error => {
      console.error('Error:', error);

      // SweetAlert2 for error
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: error.message,
        confirmButtonText: 'OK'
      });
    });
});
