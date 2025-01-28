document.addEventListener("DOMContentLoaded", function () {
    fetch('/last_login/') // Ensure correct API endpoint
        .then(response => response.json())
        .then(data => {
            console.log("Fetched Data:", data); // Debugging

            const tableBody = document.querySelector("#studentTable tbody");
            const activeStudentCountElement = document.querySelector("#activeStudentCount");

            if (!tableBody) {
                console.error("Table body not found!");
                return;
            }

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

            function createRow(student) {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${student.id}</td>
                    <td>${student.name}</td>
                    <td><span class="badge ${student.status_class}">${student.status}</span></td>
                    <td>${student.last_login}</td>
                `;
                tableBody.appendChild(row);
            }

            // Populate all students
            data.students.forEach(student => createRow(student));

            // Initialize DataTable (Ensure jQuery & DataTables.js are included in base.html)
            if ($.fn.DataTable.isDataTable("#studentTable")) {
                $("#studentTable").DataTable().destroy();
            }
            $("#studentTable").DataTable();
        })
        .catch(error => console.error("Error loading student data:", error));
});
