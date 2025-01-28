document.addEventListener("DOMContentLoaded", function () {
    fetchAnnouncements();
});

function fetchAnnouncements() {
    fetch("/announcement/")
    .then(response => response.json())
    .then(data => {
        let tableBody = document.querySelector("#dataTable tbody");
        tableBody.innerHTML = "";

        if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No announcements found</td></tr>';
        } else {
        data.forEach((announcement, index) => {
            let row = `<tr>
            <td>${index + 1}</td>
            <td>${announcement.title}</td>
            <td>${announcement.description || "No Description"}</td>
            <td>${announcement.date}</td>
            <td>
                <div class="dropdown">
                <button class="btn btn-white btn-sm no-caret" type="button" id="dropdownMenuButton${announcement.id}" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="dropdown-menu dropdown-menu-right" aria-labelledby="dropdownMenuButton${announcement.id}">
                    <a class="dropdown-item" href="javascript:void(0);" onclick="openEditModal(${announcement.id})">
                    <i class="fas fa-edit"></i> Update
                    </a>
                    <a class="dropdown-item text-danger" href="javascript:void(0);" onclick="confirmDelete(${announcement.id})">
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
    .catch(error => console.error("Error fetching announcements:", error));
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


// Open Update Modal and Load Announcement Data
function openEditModal(id) {
    fetch(`/announcement/${id}/`)
    .then(response => response.json())
    .then(data => {
        document.getElementById("announcementId").value = data.id;
        document.getElementById("announcementTitle").value = data.title;
        document.getElementById("announcementDescription").value = data.description;
        document.getElementById("announcementDate").value = data.date;

        document.getElementById('editModal').classList.add('show');
        document.getElementById('editModalBackdrop').classList.add('show');
    })
    .catch(error => console.error("Error fetching announcement details:", error));
}

// Close the Update Modal
document.getElementById("close_update_modal").addEventListener("click", function () {
    document.getElementById("editModal").classList.remove("show");
    document.getElementById("editModalBackdrop").classList.remove("show");
});

// Handle Add Announcement
document.getElementById("addAnnouncementForm").addEventListener("submit", function (e) {
    e.preventDefault();

    const title = document.getElementById("newAnnouncementTitle").value;
    const description = document.getElementById("newAnnouncementDescription").value;
    const date = document.getElementById("newAnnouncementDate").value;

    fetch("/announcement/", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ title, description, date }),
    })
    .then(() => {
        displayToast("Announcement created successfully.", "success");  
        fetchAnnouncements(); 
        document.getElementById("addModal").classList.remove("show");
        document.getElementById("addModalBackdrop").classList.remove("show");
        })
        .catch(error => {
        displayToast("Error creating announcement. Please try again.", "error"); 
        console.error("Error creating announcement:", error);
        });
    });

// Handle Update Form Submission
document.getElementById("updateAnnouncementForm").addEventListener("submit", function (e) {
    e.preventDefault();
    
    const id = document.getElementById("announcementId").value;
    const title = document.getElementById("announcementTitle").value;
    const description = document.getElementById("announcementDescription").value;
    const date = document.getElementById("announcementDate").value;
    
    fetch(`/announcement/${id}/`, {
        method: "PUT",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ 
            title: title,
            description: description,
            date: date,
        }),
    })
    .then(response => {
        if (!response.ok) {
        return response.json().then(err => { throw err; });
        }
        return response.json();
    })
    .then(data => {
        displayToast("Announcement updated successfully.", "success");  // ✅ Success Toast
        document.getElementById("editModal").classList.remove("show");
        document.getElementById("editModalBackdrop").classList.remove("show");
        fetchAnnouncements(); // Refresh data
    })
    .catch(error => {
        displayToast("Error updating announcement. Please try again.", "error");  // ❌ Error Toast
        console.error("Error updating announcement:", error);
    });
    });

// Get CSRF Token
function getCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith("csrftoken=")) {
        cookieValue = decodeURIComponent(cookie.substring(10));
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
        fetch(`/announcement/${id}/`, {
            method: 'DELETE',
            headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            }
        }).then((response) => {
            if (response.ok) {
            Swal.fire({
                title: 'Deleted!',
                text: 'The Announcement has been deleted.',
                icon: 'success'
            }).then(() => {
                location.reload() // Reload the page after deletion
            })
            } else {
            Swal.fire({
                title: 'Error!',
                text: 'There was an issue deleting the Announcement.',
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

