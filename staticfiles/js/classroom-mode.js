let screenshotInterval;
let hasPromptedTeacher = false; 

  async function captureScreenshot(subjectId, attendanceId) {
    if (typeof html2canvas === "undefined") {
        console.error("html2canvas is not loaded!");
        return;
    }

    // console.log(`Capturing screenshot for Subject ID: ${subjectId}, Attendance ID: ${attendanceId}`);

    const canvas = await html2canvas(document.body);
    const imgData = canvas.toDataURL("image/png"); // This generates base64

    // console.log("Base64 Image Data:", imgData.substring(0, 100)); // Debugging: Print first 100 chars

    fetch(`/save-screenshot/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": "{{ csrf_token }}"
        },
        body: JSON.stringify({
            image: imgData,
            subject_id: subjectId,
            attendance_id: attendanceId
        })
    })
    .then(response => response.json())
    .then(data => {
      // console.log("✅ Screenshot saved:", data);
      localStorage.setItem("screenshotSession", JSON.stringify({
          subjectId: subjectId,
          attendanceId: attendanceId,
          lastCaptureTime: Date.now()
      }));
  })
    .catch(error => console.error("Screenshot Error:", error));
  }


  function checkClassEndTime(subjectId) {
    fetch(`/teacher_attendance/${subjectId}/get-end-time/`)
        .then(response => {
            if (!response.ok) {
                // console.warn(`⚠️ API returned error: ${response.status}`);
                throw new Error("API response not OK");
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.warn("⚠️ No scheduled end time found.");
                return;
            }

            const scheduledEndTime = data.end_time;
            // console.log(`⏳ Monitoring end time: ${scheduledEndTime}`);

            // Convert scheduledEndTime to JavaScript Date object
            const endTimeParts = scheduledEndTime.split(":");
            const now = new Date();
            const scheduledEnd = new Date(
                now.getFullYear(),
                now.getMonth(),
                now.getDate(),
                parseInt(endTimeParts[0]), // Hours
                parseInt(endTimeParts[1]), // Minutes
                parseInt(endTimeParts[2])  // Seconds
            );

            // Define warning times (5 minutes and 1 minute before end time)
            const warningThresholds = [5 * 60 * 1000, 1 * 60 * 1000]; // 5 minutes & 1 minute in ms
            let lastPromptTime = null; // Track last displayed prompt

            if (typeof classEndCheckInterval !== 'undefined') {
                clearInterval(classEndCheckInterval);
            }

            classEndCheckInterval = setInterval(() => {
                const currentTime = new Date();
                const timeLeft = scheduledEnd - currentTime;

                // console.log(`🕒 Current Time: ${currentTime.toTimeString().split(" ")[0]} | Time Left: ${timeLeft / 1000} seconds`);

                warningThresholds.forEach(threshold => {
                    if (timeLeft <= threshold && timeLeft > 0 && lastPromptTime !== threshold) {
                        console.log(`🚨 Prompting teacher: ${threshold === 300000 ? "a minutes" : "1 minute"} left!`);
                        hasPromptedTeacher = true;
                        lastPromptTime = threshold; // Mark this threshold as used

                        Swal.fire({
                            title: "Class Ending Soon",
                            text: `Your class is ending in ${threshold === 300000 ? "a minutes" : "1 minute"}. Do you want to end the class now?`,
                            icon: "warning",
                            showCancelButton: true,
                            confirmButtonText: "Yes, End Class",
                            cancelButtonText: "Not Now"
                        }).then((result) => {
                            if (result.isConfirmed) {
                                endClass(subjectId, true); // Pass true to trigger page reload
                            } else {
                                hasPromptedTeacher = false;
                            }
                        });
                    }
                });

                if (timeLeft <= 0) {
                    clearInterval(classEndCheckInterval);
                    // console.log("⏳ Scheduled end time has passed. No further checks.");
                }
            }, 30000); // Check every 30 seconds
        })
        .catch(error => console.error("❌ Error fetching end time:", error));
}



// Function to End the Class
function endClass(subjectId, shouldReload = false) {
  fetch(`/teacher_attendance/${subjectId}/end-class/`, {
      method: "POST",
      headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content')
      }
  })
  .then(response => response.json())
  .then(data => {
      if (data.error) {
          Swal.fire("Error", data.error, "error");
      } else {
          Swal.fire({
              title: "Class Ended",
              text: "Your class has been successfully ended.",
              icon: "success",
              confirmButtonText: "OK"
          }).then(() => {
              if (shouldReload) {
                  location.reload(); // Reload the page
              }
          });
      }
  })
  .catch(error => console.error("❌ Error ending class:", error));
}



  function startScreenshotLoop(subjectId, attendanceId) {
      if (!attendanceId) {
          console.error("Error: attendanceId is undefined. Screenshot loop will not start.");
          return;
      }

      // console.log(`Starting screenshot capture every 1 minute for Subject ID: ${subjectId}, Attendance ID: ${attendanceId}`);

      // Ensure no duplicate intervals
      if (screenshotInterval) {
          clearInterval(screenshotInterval);
      }

      const intervalDuration = 10 * 60 * 1000; // 10 minutes (600000 milliseconds)

      fetch(`/teacher_attendance/${subjectId}/current-state/`)
        .then(response => response.json())
        .then(data => {
            if (!data.is_active) {
                // console.log("🚫 Class is not active. Screenshot loop will not start.");
                stopScreenshotLoop(); // Stop capturing
                return;
            }

            let storedSession = localStorage.getItem("screenshotSession");
            let lastCaptureTime = storedSession ? JSON.parse(storedSession).lastCaptureTime : null;
            let now = Date.now();
            let elapsedTime = lastCaptureTime ? now - lastCaptureTime : intervalDuration;
            let timeUntilNextCapture = intervalDuration - (elapsedTime % intervalDuration);

            // console.log(`🕒 Elapsed Time: ${elapsedTime / 1000}s | Next screenshot in: ${timeUntilNextCapture / 1000}s`);

            if (elapsedTime >= intervalDuration) {
                // console.log("⏳ Time exceeded interval! Capturing an immediate screenshot.");
                captureScreenshot(subjectId, attendanceId);
                lastCaptureTime = Date.now();
            }

            localStorage.setItem("screenshotSession", JSON.stringify({
                subjectId: subjectId,
                attendanceId: attendanceId,
                lastCaptureTime: lastCaptureTime
            }));

            function scheduleScreenshot() {
                captureScreenshot(subjectId, attendanceId);
                let newTime = Date.now();
                localStorage.setItem("screenshotSession", JSON.stringify({
                    subjectId: subjectId,
                    attendanceId: attendanceId,
                    lastCaptureTime: newTime
                }));

                // console.log("📸 Screenshot Taken | New Time Recorded:", newTime);
            }

            setTimeout(() => {
                scheduleScreenshot();
                screenshotInterval = setInterval(() => {
                    scheduleScreenshot();
                }, intervalDuration);
            }, timeUntilNextCapture);

            checkClassEndTime(subjectId);
        })
        .catch(error => console.error("❌ Error checking class state:", error));
}


function stopScreenshotLoop() {
  // console.log("🛑 Stopping screenshot capture...");
  if (screenshotInterval) {
      clearInterval(screenshotInterval);
      screenshotInterval = null; // Ensure interval is fully cleared
  }
  localStorage.removeItem("screenshotSession"); // Clear session before reloading
}


document.addEventListener("DOMContentLoaded", function () {
  // console.log("🔍 Checking if html2canvas is available...");
  if (typeof html2canvas === "undefined") {
      console.error("❌ html2canvas not found. Make sure the script is included.");
      return;
  }

  // console.log("✅ html2canvas is ready!");

  // Restore Screenshot Session if Active
  const storedSession = localStorage.getItem("screenshotSession");
  if (storedSession) {
      const { subjectId, attendanceId } = JSON.parse(storedSession);

      fetch(`/teacher_attendance/${subjectId}/current-state/`)
          .then(response => response.json())
          .then(data => {
              if (data.is_active) {
                  // console.log("🔄 Resuming screenshot session...");
                  startScreenshotLoop(subjectId, attendanceId);
              } else {
                  // console.log("🚫 Class is not active. Screenshot session will NOT be restored.");
                  stopScreenshotLoop();
              }
          })
          .catch(error => console.error("❌ Error checking class state:", error));
  }
});

// Detect if the user navigates to another page and resumes the screenshot loop
window.addEventListener("focus", () => {
  // console.log("🌍 Page focus detected, checking screenshot session...");
  const storedSession = localStorage.getItem("screenshotSession");
  if (storedSession) {
      const { subjectId, attendanceId } = JSON.parse(storedSession);

      fetch(`/teacher_attendance/${subjectId}/current-state/`)
          .then(response => response.json())
          .then(data => {
              if (data.is_active) {
                  // console.log("🔄 Resuming screenshot loop after page change...");
                  startScreenshotLoop(subjectId, attendanceId);
              } else {
                  // console.log("🚫 Class is not active. Screenshot loop will NOT restart.");
                  stopScreenshotLoop();
              }
          })
          .catch(error => console.error("❌ Error checking class state:", error));
  }
});


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
      // console.log('Response Status:', response.status);
      if (response.ok) {
        return response.json();
      }
      return response.json().then(err => {
        // console.error('Error Response:', err);
        throw new Error(err.error || 'Network response was not ok.');
      });
    })
    .then(data => {

      // SweetAlert2 for success
      Swal.fire({
        icon: 'success',
        title: isActive
          ? 'Class ended successfully!'
          : 'Class started successfully!',
        confirmButtonText: 'OK'
      });

      if (isActive) {
        stopScreenshotLoop();

        classActionButton.setAttribute('data-is-active', 'false');
        classActionButton.innerHTML = '<i class="fas fa-chalkboard-teacher"></i> Start Class';
      } else {
        classActionButton.setAttribute('data-is-active', 'true');
        classActionButton.innerHTML = '<i class="fas fa-chalkboard-teacher"></i> End Class';


        startScreenshotLoop(subjectId, data.attendance_id);
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
