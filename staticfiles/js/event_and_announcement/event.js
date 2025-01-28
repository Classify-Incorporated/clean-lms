document.addEventListener("DOMContentLoaded", function () {
  fetchEvents();
});

function fetchEvents() {
  fetch("/events/")
    .then(response => response.json())
    .then(data => {
      let tableBody = document.querySelector("#dataTable tbody");
      tableBody.innerHTML = "";

      if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No events found</td></tr>';
      } else {
        data.forEach((event, index) => {
          let row = `<tr>
            <td>${index + 1}</td>
            <td>${event.title}</td>
            <td>${event.description || "No Description"}</td>
            <td>${event.date}</td>
            <td>${event.time || "N/A"}</td>
            <td>${event.location || "N/A"}</td>
            <td>
              <div class="dropdown">
                <button class="btn btn-white btn-sm no-caret" type="button" id="dropdownMenuButton${event.id}" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                  <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="dropdown-menu dropdown-menu-right" aria-labelledby="dropdownMenuButton${event.id}">
                  <a class="dropdown-item" href="javascript:void(0);" onclick="openEditModal(${event.id})">
                    <i class="fas fa-edit"></i> Update
                  </a>
                  <a class="dropdown-item text-danger" href="javascript:void(0);" onclick="confirmDelete(${event.id})">
                    <i class="fas fa-trash"></i> Delete
                  </a>
                </div>
              </div>
            </td>
          </tr>`;
          tableBody.innerHTML += row;
        });
      }
    })
    .catch(error => console.error("Error fetching events:", error));
}

function openEditModal(id) {
  fetch(`/events/${id}/`)
    .then(response => response.json())
    .then(data => {
    document.getElementById("eventId").value = data.id;
    document.getElementById("eventTitle").value = data.title;
    document.getElementById("eventDescription").value = data.description;
    document.getElementById("eventDate").value = data.date;
    document.getElementById("eventTime").value = data.time || "";
    document.getElementById("eventLocation").value = data.location || "";

    document.getElementById('editModal').classList.add('show');
    document.getElementById('editModalBackdrop').classList.add('show');
    })
    .catch(error => console.error("Error fetching event details:", error));
}

// Open Add Modal
document.getElementById("openAddModalBtn").addEventListener("click", function () {
    document.getElementById("addModal").classList.add("show");
    document.getElementById("addModalBackdrop").classList.add("show");
  });

// Close Add Modal
document.getElementById("closeAddModalBtn").addEventListener("click", function () {
document.getElementById("addModal").classList.remove("show");
document.getElementById("addModalBackdrop").classList.remove("show");
});

// Close the Update Modal
document.getElementById("close_update_modal").addEventListener("click", function () {
document.getElementById("editModal").classList.remove("show");
document.getElementById("editModalBackdrop").classList.remove("show");
});  

// Handle Add Announcement
document.getElementById("addEventForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const title = document.getElementById("newEventTitle").value;
    const description = document.getElementById("newEventDescription").value;
    const date = document.getElementById("newEventDate").value;
    const time = document.getElementById("newEventTime").value || null;
    const location = document.getElementById("newEventLocation").value || null;

    fetch("/events/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({ 
        title: title,
        description: description,
        date: date,
        time: time,  
        location: location,
    }),

    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status >= 200 && status < 300) {  // ✅ Only show success for valid responses
            displayToast("Event created successfully.", "success");

            // Close the modal safely
            const addModal = document.getElementById("addModal");
            const addModalBackdrop = document.getElementById("addModalBackdrop");

            if (addModal && addModalBackdrop) {
                addModal.classList.remove("show");
                addModalBackdrop.classList.remove("show");
            } else {
                console.warn("Add modal elements not found!");
            }

            fetchEvents(); // ✅ Refresh the table dynamically
        } else {
            throw new Error(body.detail || "Failed to create event.");
        }
        })
        .catch(error => {
            displayToast("Error creating event. Please try again.", "error");
            console.error("Error creating event:", error);
        });
    });

// Handle Update Form Submission
document.getElementById("updateEventForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const id = document.getElementById("eventId").value;
    const title = document.getElementById("eventTitle").value;
    const description = document.getElementById("eventDescription").value;
    const date = document.getElementById("eventDate").value;
    const time = document.getElementById("eventTime").value || null; // Ensure null if empty
    const location = document.getElementById("eventLocation").value || null;

    fetch(`/events/${id}/`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ 
            title: title,
            description: description,
            date: date,
            time: time,  
            location: location,
        }),
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status >= 200 && status < 300) {  // ✅ Only show success for valid responses
            displayToast("Event updated successfully.", "success");
            
            // Ensure modal exists before trying to close it
            const editModal = document.getElementById("editModal");
            const editModalBackdrop = document.getElementById("editModalBackdrop");

            if (editModal && editModalBackdrop) {
                editModal.classList.remove("show");
                editModalBackdrop.classList.remove("show");
            } else {
                console.warn("Edit modal elements not found!");
            }

            fetchEvents(); // ✅ Correct function to refresh table
        } else {
            throw new Error(body.detail || "Failed to update event.");
        }
    })
    .catch(error => {
        displayToast("Error updating event. Please try again.", "error");
        console.error("Error updating event:", error);
    });
});


function getCSRFToken() {
  let cookieValue = null;
  if (document.cookie) {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith("csrftoken=")) {
        cookieValue = cookie.substring(10);
        break;
      }
    }
  }
  return cookieValue;
}

// SweetAlert2 for Delete Confirmation
function confirmDelete(id) {
    Swal.fire({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#3085d6',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
      if (result.isConfirmed) {
        // Perform the deletion request via fetch API
        fetch(`/events/${id}/`, {
          method: 'DELETE',
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          }
        }).then((response) => {
          if (response.ok) {
            Swal.fire({
              title: 'Deleted!',
              text: 'The event has been deleted.',
              icon: 'success'
            }).then(() => {
              location.reload() // Reload the page after deletion
            })
          } else {
            Swal.fire({
              title: 'Error!',
              text: 'There was an issue deleting the event.',
              icon: 'error'
            })
          }
        })
      }
    })
  }

  $(document).ready(function() {
    $('.selectpicker').selectpicker('refresh');
});
