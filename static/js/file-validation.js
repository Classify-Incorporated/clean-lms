
function initializeFileValidation() {
  // Fetch validation rules from the backend
  fetch("{% url 'file_validation_data' %}")
      .then(response => response.json())
      .then(validationData => {

          // Allowed file extensions and maximum size in bytes from the backend
          const allowedExtensions = validationData.allowed_extensions;
          const maxFileSize = validationData.max_file_size_mb * 1024 * 1024; // Convert MB to bytes

          // Get the file input element and file error element
          const fileInputElement = document.querySelector('.custom-file-input');
          const fileErrorElement = document.getElementById('file-error');

          if (fileInputElement) {
              fileInputElement.addEventListener('change', function (e) {
                  const file = e.target.files[0]; // Get the selected file
                  if (file) {
                      // Validate the file
                      const fileName = file.name;
                      const fileExtension = fileName.split('.').pop().toLowerCase();
                      const fileSize = file.size;

                      // Clear previous error
                      fileErrorElement.style.display = 'none';
                      fileInputElement.classList.remove('is-invalid');

                      // Validate file type
                      if (!allowedExtensions.includes(fileExtension)) {
                          fileErrorElement.textContent = `Invalid file type. Allowed types: ${allowedExtensions.join(', ')}`;
                          fileErrorElement.style.display = 'block';
                          fileInputElement.classList.add('is-invalid');
                          e.target.value = ''; // Clear the invalid file
                          const fileLabel = document.querySelector('.custom-file-label');
                          fileLabel.textContent = 'Choose file'; // Reset the label
                          return;
                      }

                      // Validate file size
                      if (fileSize > maxFileSize) {
                          fileErrorElement.textContent = `File size exceeds the maximum limit of ${(maxFileSize / (1024 * 1024)).toFixed(2)}MB. Your file size: ${(fileSize / (1024 * 1024)).toFixed(2)}MB`;
                          fileErrorElement.style.display = 'block';
                          fileInputElement.classList.add('is-invalid');
                          e.target.value = ''; // Clear the invalid file
                          const fileLabel = document.querySelector('.custom-file-label');
                          fileLabel.textContent = 'Choose file'; // Reset the label
                          return;
                      }

                      // If everything is valid, update the label to show the file name
                      const fileLabel = document.querySelector('.custom-file-label');
                      fileLabel.textContent = fileName;
                  }
              });
          } else {
              console.error("File input element not found!");
          }
      })
      .catch(error => console.error("Error fetching validation data:", error));
      
}