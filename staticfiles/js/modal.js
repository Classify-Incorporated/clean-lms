function selectActivityTypeAndRedirect(activityTypeName, subjectId, activityTypeId, isCM = false) {
  if (activityTypeId) {
    const baseUrl = isCM ? `/subject/${subjectId}/add_activityCM/` : `/subject/${subjectId}/add_activity/`;
    const url = `${baseUrl}?activity_type_id=${activityTypeId}`;
    window.location.href = url;
  } else {
    console.error('Activity Type ID is undefined');
    alert('Activity Type is not defined for ' + activityTypeName);
  }
}

// Open Module Modal for Standard Mode
function openModuleModalStandard(subjectId, type) {
  // Hide the Standard Mode modal properly
  $('#addActivityLessonModalStandard').modal('hide');

  // Wait for the modal transition to complete before proceeding
  setTimeout(() => {
    fetch(`/createModule/${subjectId}/`)
      .then((response) => response.text())
      .then((html) => {
        // Update modal content
        document.getElementById('moduleModalBody').innerHTML = html;
        document.getElementById('moduleModal').classList.add('show');
        document.getElementById('moduleModalBackdrop').classList.add('show');

        // Hide all input fields initially
        document.getElementById('fileInputDiv').style.display = 'none';
        document.getElementById('urlInputDiv').style.display = 'none';
        document.getElementById('embedInputDiv').style.display = 'none';
        document.querySelector('.form-check').style.display = 'none';

        // Conditionally show the correct input based on `type`
        if (type === 'lesson') {
          document.getElementById('fileInputDiv').style.display = 'block';
        } else if (type === 'url') {
          document.getElementById('urlInputDiv').style.display = 'block';
        } else if (type === 'embed') {
          document.getElementById('embedInputDiv').style.display = 'block';
        }

        // Set up input fields visibility
        handleModuleInputDisplay(type);

        // Refresh Bootstrap Selectpicker
        $('.selectpicker').selectpicker('refresh');

      })
      .catch((error) => console.error('Error fetching module content:', error));
  }, 300);
}

// Open Module Modal for Classroom Mode
function openModuleModalClassroom(subjectId, type) {
  // Hide the Classroom Mode modal properly
  $('#addActivityLessonModalCM').modal('hide');

  // Wait for the modal transition to complete before proceeding
  setTimeout(() => {
    fetch(`/createModuleCM/${subjectId}/`)
      .then((response) => response.text())
      .then((html) => {
        // Update modal content
        document.getElementById('moduleModalBody').innerHTML = html;
        document.getElementById('moduleModal').classList.add('show');
        document.getElementById('moduleModalBackdrop').classList.add('show');

        // Hide all input fields initially
        document.getElementById('fileInputDiv').style.display = 'none';
        document.getElementById('urlInputDiv').style.display = 'none';
        document.getElementById('embedInputDiv').style.display = 'none';
        document.querySelector('.form-check').style.display = 'none';

        // Conditionally show the correct input based on `type`
        if (type === 'lesson') {
          document.getElementById('fileInputDiv').style.display = 'block';
        } else if (type === 'url') {
          document.getElementById('urlInputDiv').style.display = 'block';
        } else if (type === 'embed') {
          document.getElementById('embedInputDiv').style.display = 'block';
        }

        // Set up input fields visibility
        handleModuleInputDisplay(type);

        // Refresh Bootstrap Selectpicker
        $('.selectpicker').selectpicker('refresh');

      })
      .catch((error) => console.error('Error fetching module content:', error));
  }, 300);
}


// Utility function to manage input display
function handleModuleInputDisplay(type) {
  if (type === 'lesson') {
    document.getElementById('fileInputDiv').style.display = 'block'; // Show file input
    document.getElementById('urlInputDiv').style.display = 'none'; // Hide URL input
    document.querySelector('.form-check').style.display = 'none';
  } else if (type === 'url') {
    document.getElementById('fileInputDiv').style.display = 'none'; // Hide file input
    document.getElementById('urlInputDiv').style.display = 'block'; // Show URL input
    document.querySelector('.form-check').style.display = 'none';
  }
}


function initializeCustomFileUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const filePreview = document.getElementById('filePreview');
  const dropzoneText = document.getElementById('dropzone-text');

  // Trigger file explorer when clicking the dropzone
  dropzone.addEventListener('click', () => fileInput.click());

  // Drag over event
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  // Drag leave event
  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  // Drop event
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const files = e.dataTransfer.files;

    if (files.length > 0) {
      fileInput.files = files; // Assign files to the hidden input
      displayUploadedFile(files[0]); // Display the file details
    }
  });

  // File input change event
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      displayUploadedFile(fileInput.files[0]);
    }
  });

  // Function to display uploaded file details
  function displayUploadedFile(file) {
    // Clear existing preview
    filePreview.innerHTML = '';

    // Determine file icon based on file type
    let fileIcon = '<i class="far fa-file file-icon text-secondary"></i>'; // Default file icon
    const fileType = file.type;

    if (fileType.startsWith('image/')) {
      fileIcon = '<i class="far fa-file-image file-icon text-success"></i>';
    } else if (fileType === 'application/pdf') {
      fileIcon = '<i class="far fa-file-pdf file-icon text-danger"></i>';
    } else if (fileType.startsWith('video/')) {
      fileIcon = '<i class="far fa-file-video file-icon text-primary"></i>';
    } else if (fileType.startsWith('audio/')) {
      fileIcon = '<i class="far fa-file-audio file-icon text-warning"></i>';
    } else if (fileType.startsWith('text/')) {
      fileIcon = '<i class="far fa-file-alt file-icon text-info"></i>';
    }

    // Create the file preview element
    const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item';

    // Add the file icon and details
    previewItem.innerHTML = `
      ${fileIcon}
      <div class="file-details">
        <span class="file-name" title="${file.name}">${file.name}</span>
        <span class="file-type">${fileType || 'Unknown type'}</span>
      </div>
    `;

    // Append the file preview element to the preview container
    filePreview.appendChild(previewItem);

    // Hide the default dropzone text
    dropzoneText.style.display = 'none';
  }
}

// Initialize the custom file upload functionality
document.addEventListener('DOMContentLoaded', initializeCustomFileUpload);

   

document.getElementById('closeParticipationModalBtn').addEventListener('click', function () {
  document.getElementById('participationModal').classList.remove('show')
  document.getElementById('participationModalBackdrop').classList.remove('show')
})

document.getElementById('closeModuleModalBtn').addEventListener('click', function () {
  document.getElementById('moduleModal').classList.remove('show')
  document.getElementById('moduleModalBackdrop').classList.remove('show')
})

function openCopyActivityModal(subjectId) {
  fetch(`/subject/${subjectId}/copy_activities/`)
    .then((response) => response.text())
    .then((html) => {
      document.getElementById('copyActivityModalBody').innerHTML = html
      document.getElementById('copyActivityModal').classList.add('show')
      document.getElementById('copyActivityModalBackdrop').classList.add('show')

      initializeActivityCheckboxScript(subjectId)
    })
}

function initializeActivityCheckboxScript(subjectId) {
  $('#from_semester').change(function () {
    var semesterId = $(this).val()

    if (semesterId) {
      // Make AJAX call to fetch activities grouped by term
      $.ajax({
        url: '/get-activities/' + subjectId + '/' + semesterId + '/',
        type: 'GET',
        success: function (response) {
          var groupedActivities = response.grouped_activities
          console.log('Grouped Activities for selected semester:', groupedActivities)

          var activityList = ''
          if (groupedActivities.length > 0) {
            // Loop through each term and list activities under each
            $.each(groupedActivities, function (index, group) {
              var termName = group.term
              var activities = group.activities

              activityList += '<h5>' + termName + '</h5><ul>'

              $.each(activities, function (index, activity) {
                activityList += '<li><input type="checkbox" name="activities" value="' + activity.id + '"> ' + activity.activity_name + ' (' + activity.activity_type + ')</li>'
              })

              activityList += '</ul>'
            })
          } else {
            activityList = '<p>No activities found for the selected semester.</p>'
          }

          $('#activityList').html(activityList) // Update the activity list in the DOM
        },
        error: function () {
          $('#activityList').html('<p>There was an error fetching activities.</p>')
        }
      })
    } else {
      $('#activityList').html('') // Clear the activity list if no semester is selected
    }
  })
}

document.getElementById('closeCopyActivityModalBtn').addEventListener('click', function () {
  document.getElementById('copyActivityModal').classList.remove('show')
  document.getElementById('copyActivityModalBackdrop').classList.remove('show')
})

// Open Copy Lesson Modal
function openCopyLessonModal(subjectId) {
  fetch(`/subject/${subjectId}/copy_lessons/`)
    .then((response) => response.text())
    .then((html) => {
      document.getElementById('copyLessonModalBody').innerHTML = html
      document.getElementById('copyLessonModal').classList.add('show')
      document.getElementById('copyLessonModalBackdrop').classList.add('show')

      initializeLessonCheckboxes(subjectId)
    })
}

// Close Copy Lesson Modal
document.getElementById('closeCopyLessonModalBtn').addEventListener('click', function () {
  document.getElementById('copyLessonModal').classList.remove('show')
  document.getElementById('copyLessonModalBackdrop').classList.remove('show')
})

document.addEventListener('DOMContentLoaded', function () {
  console.log('DOM fully loaded and parsed.') // Debugging

  function checkAll(statusId) {
    console.log('checkAll function called with statusId:', statusId) // Debugging
    document.querySelectorAll(`.status-${statusId}`).forEach((radio) => {
      console.log('Checking radio button for statusId:', statusId, radio) // Debugging
      radio.checked = true
    })
  }

  // Attach event listeners to each "Select All" radio button
  document.querySelectorAll('.selectAll').forEach((selectAllButton) => {
    selectAllButton.addEventListener('click', function () {
      const statusId = this.getAttribute('data-status')
      console.log('Select All button clicked with statusId:', statusId) // Debugging
      checkAll(statusId)
    })
  })
})

// Open Attendance Modal for Standard Mode (Bootstrap 5 Fix Applied)
function openAttendanceModalCM(subjectId) {
  // Close Bootstrap 5 modal properly
  let bootstrapModal = document.getElementById('addActivityLessonModalCM');
  if (bootstrapModal) {
    let modalInstance = bootstrap.Modal.getInstance(bootstrapModal);
    if (modalInstance) {
      modalInstance.hide(); // Close the modal safely
    }
  }

  // Fetch the attendance modal content
  fetch(`/attendance/record_attendanceCM/${subjectId}/`)
    .then(response => response.text())
    .then(html => {
      let attendanceModalBody = document.getElementById('attendanceModalBody');
      let attendanceModal = document.getElementById('attendanceModal');
      let attendanceModalBackdrop = document.getElementById('attendanceModalBackdrop');

      if (attendanceModalBody && attendanceModal) {
        attendanceModalBody.innerHTML = html;

        // Ensure modal appears on top of the backdrop
        attendanceModal.style.zIndex = '1050';
        attendanceModalBackdrop.style.zIndex = '1040';

        // Show modal and backdrop
        attendanceModal.classList.add('show');
        attendanceModalBackdrop.classList.add('show');
      } else {
        console.error("🚨 Element 'attendanceModalBody' not found in the DOM.");
      }
    })
    .catch(error => console.error('Error loading attendance modal:', error));
}

// Close Attendance Modal Properly
document.getElementById('closeAttendanceModalBtn').addEventListener('click', function () {
  document.getElementById('attendanceModal').classList.remove('show');
  document.getElementById('attendanceModalBackdrop').classList.remove('show');
});


// Open Attendance Modal for Standard Mode (Bootstrap 5 Fix Applied)
function openAttendanceModal(subjectId) {
  // Close Bootstrap 5 modal properly
  let bootstrapModal = document.getElementById('addActivityLessonModalStandard');
  if (bootstrapModal) {
    let modalInstance = bootstrap.Modal.getInstance(bootstrapModal);
    if (modalInstance) {
      modalInstance.hide(); // Close the modal safely
    }
  }

  // Fetch the attendance modal content
  fetch(`/attendance/record/${subjectId}/`)
    .then(response => response.text())
    .then(html => {
      let attendanceModalBody = document.getElementById('attendanceModalBody');
      let attendanceModal = document.getElementById('attendanceModal');
      let attendanceModalBackdrop = document.getElementById('attendanceModalBackdrop');

      if (attendanceModalBody && attendanceModal) {
        attendanceModalBody.innerHTML = html;

        // Ensure modal appears on top of the backdrop
        attendanceModal.style.zIndex = '1050';
        attendanceModalBackdrop.style.zIndex = '1040';

        // Show modal and backdrop
        attendanceModal.classList.add('show');
        attendanceModalBackdrop.classList.add('show');
      } else {
        console.error("🚨 Element 'attendanceModalBody' not found in the DOM.");
      }
    })
    .catch(error => console.error('Error loading attendance modal:', error));
}

// Close Attendance Modal Properly
document.getElementById('closeAttendanceModalBtn').addEventListener('click', function () {
  document.getElementById('attendanceModal').classList.remove('show');
  document.getElementById('attendanceModalBackdrop').classList.remove('show');
});




// Function to initialize lesson checkboxes
function initializeLessonCheckboxes(subjectId) {
  document.querySelectorAll('.lesson-checkbox').forEach((checkbox) => {
    checkbox.addEventListener('change', function () {
      let lessonId = this.value

      // Make AJAX request to check if the lesson exists in the current semester
      fetch(`/subject/${subjectId}/check_lesson_exists/?lesson_id=${lessonId}`, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then((response) => response.json())
        .then((data) => {
          let warningElement = document.getElementById(`duplicate-warning-${lessonId}`)
          let listItemElement = document.getElementById(`lesson-item-${lessonId}`)

          if (data.exists) {
            // If the lesson already exists, show the warning message and disable the checkbox
            warningElement.style.display = 'inline'
            checkbox.disabled = true

            // Add a gray-out class to the lesson item
            listItemElement.style.backgroundColor = '#e0e0e0' // Light gray background
            listItemElement.style.cursor = 'not-allowed' // Show not-allowed cursor
            listItemElement.style.opacity = '0.6' // Make the text a bit faded
          } else {
            // If the lesson doesn't exist, hide the warning message and enable the checkbox
            warningElement.style.display = 'none'
            checkbox.disabled = false

            // Remove the gray-out class
            listItemElement.style.backgroundColor = ''
            listItemElement.style.cursor = 'pointer' // Normal cursor
            listItemElement.style.opacity = '1' // Reset opacity
          }
        })
        .catch((error) => console.error('Error:', error))
    })
  })
}