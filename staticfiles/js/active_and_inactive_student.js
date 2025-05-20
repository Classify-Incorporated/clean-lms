document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () { // Delay execution slightly to ensure DOM is ready
        const tableBody = document.querySelector("#studentTable tbody");

        if (!tableBody) {
            console.error("Table body not found! Retrying...");
            return;
        }

        fetch('/last_login/') // Ensure correct API endpoint
            .then(response => response.json())
            .then(data => {
                console.log("Fetched Data:", data); // Debugging

                const activeStudentCountElement = document.querySelector("#activeStudentCount");

                // Display Active Student Count
                if (activeStudentCountElement) {
                    activeStudentCountElement.textContent = `Active Students: ${data.active_now_count}`;
                }

                // Clear previous data
                tableBody.innerHTML = "";

                // Ensure 'students' key exists in API response
                if (!data.students || data.students.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="4" class="text-center">No students found</td></tr>`;
                    return;
                }

                function createRow(student, index) {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${index + 1}</td> <!-- Replaced student.id with row number -->
                        <td>${student.name}</td>
                        <td><span class="badge ${student.status_class}">${student.status}</span></td>
                        <td>${student.last_login}</td>
                    `;
                    tableBody.appendChild(row);
                }

                // Populate all students
                data.students.forEach((student, index) => createRow(student, index));

                // Initialize DataTable
                if ($.fn.DataTable.isDataTable("#studentTable")) {
                    $("#studentTable").DataTable().destroy();
                }
                $("#studentTable").DataTable();
            })
            .catch(error => console.error("Error loading student data:", error));
    }, 500); // Small delay to ensure DOM is ready
});
