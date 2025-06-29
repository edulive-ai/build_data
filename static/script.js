// Global variables
let allImages = [];
let selectedQuestionImages = [];
let selectedAnswerImages = [];
let currentSelectionMode = 'question'; // 'question' or 'answer'
let editingQuestion = null;
let currentBook = 'cropped'; // Default book
let processingStatusId = null;
let processingInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeAuth(); // Khởi tạo auth trước
    // Các initialization khác sẽ được gọi trong setupAuthenticatedApp()
});
function getBookDisplayName(bookPath) {
    if (bookPath.startsWith('books_cropped/')) {
        return bookPath.replace('books_cropped/', '');
    }
    return bookPath;
}

function getBookFullPath(displayName) {
    if (displayName === 'cropped' || displayName.includes('/')) {
        return displayName;
    }
    return 'books_cropped/' + displayName;
}
function setupEventListeners() {
    // Form submission
    document.getElementById('questionForm').addEventListener('submit', handleAddQuestion);
    document.getElementById('editForm').addEventListener('submit', handleEditQuestion);

    // Selection mode buttons
    document.getElementById('selectQuestionMode').addEventListener('click', () => setSelectionMode('question'));
    document.getElementById('selectAnswerMode').addEventListener('click', () => setSelectionMode('answer'));
    document.getElementById('clearSelection').addEventListener('click', clearAllSelections);

    // Edit modal buttons
    document.getElementById('editSelectQuestionMode').addEventListener('click', () => setSelectionMode('question', true));
    document.getElementById('editSelectAnswerMode').addEventListener('click', () => setSelectionMode('answer', true));
    document.getElementById('editClearSelection').addEventListener('click', () => clearAllSelections(true));

    // Modal controls
    document.querySelector('.close').addEventListener('click', closeEditModal);
    document.getElementById('cancelEdit').addEventListener('click', closeEditModal);

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const editModal = document.getElementById('editModal');
        const imageModal = document.getElementById('imagePreviewModal');
        const uploadModal = document.getElementById('uploadModal');
        
        if (event.target === editModal) {
            closeEditModal();
        }
        if (event.target === imageModal) {
            closeImagePreview();
        }
        if (event.target === uploadModal) {
            closeUploadModal();
        }
    });

    // Setup image preview modal close button
    const imageModalClose = document.querySelector('#imagePreviewModal .close');
    if (imageModalClose) {
        imageModalClose.addEventListener('click', closeImagePreview);
    }
}

// === PDF UPLOAD FUNCTIONS ===
function setupPDFUpload() {
    // Upload button click
    document.getElementById('uploadPDFBtn').addEventListener('click', showUploadModal);
    
    // Upload form submission
    document.getElementById('uploadForm').addEventListener('submit', handlePDFUpload);
    
    // File input change
    document.getElementById('pdfFile').addEventListener('change', handleFileSelect);
    
    // Upload modal close
    document.getElementById('uploadModal').querySelector('.close').addEventListener('click', closeUploadModal);
    document.getElementById('cancelUpload').addEventListener('click', closeUploadModal);
}

function showUploadModal() {
    const modal = document.getElementById('uploadModal');
    modal.style.display = 'block';
    
    // Reset form
    document.getElementById('uploadForm').reset();
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'none';
}

function closeUploadModal() {
    const modal = document.getElementById('uploadModal');
    modal.style.display = 'none';
    
    // Stop processing status check if running
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    const fileInfo = document.getElementById('fileInfo');
    
    if (file) {
        // Validate file type
        if (!file.type.includes('pdf')) {
            showAlert('Vui lòng chọn file PDF', 'error');
            event.target.value = '';
            fileInfo.style.display = 'none';
            return;
        }
        
        // Validate file size (100MB)
        const maxSize = 100 * 1024 * 1024;
        if (file.size > maxSize) {
            showAlert(`File quá lớn (tối đa 100MB). File hiện tại: ${(file.size / 1024 / 1024).toFixed(1)}MB`, 'error');
            event.target.value = '';
            fileInfo.style.display = 'none';
            return;
        }
        
        // Show file info
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB`;
        fileInfo.style.display = 'block';
    } else {
        fileInfo.style.display = 'none';
    }
}

function handlePDFUpload(event) {
    event.preventDefault();
    
    const formData = new FormData();
    const pdfFile = document.getElementById('pdfFile').files[0];
    const bookName = document.getElementById('bookName').value.trim();
    
    // Validation
    if (!pdfFile) {
        showAlert('Vui lòng chọn file PDF', 'error');
        return;
    }
    
    if (!bookName) {
        showAlert('Vui lòng nhập tên sách', 'error');
        return;
    }
    
    // Validate book name format
    if (!/^[a-zA-Z0-9_-]+$/.test(bookName)) {
        showAlert('Tên sách chỉ được chứa chữ cái, số, dấu gạch dưới và gạch ngang', 'error');
        return;
    }
    
    // Prepare form data
    formData.append('pdf_file', pdfFile);
    formData.append('book_name', bookName);
    formData.append('processing_mode', 'complete');
    
    // Show progress
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const uploadBtn = document.getElementById('submitUpload');
    
    progressDiv.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Đang upload file...';
    uploadBtn.disabled = true;
    
    // Upload file
    fetch('/upload_pdf', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            processingStatusId = data.status_id;
            progressText.textContent = 'Upload thành công! Bắt đầu xử lý...';
            
            // Start monitoring processing status
            startProcessingMonitor();
            
            showAlert('Upload thành công! Đang xử lý PDF...', 'success');
        } else {
            throw new Error(data.error || 'Lỗi upload file');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showAlert('Lỗi upload: ' + error.message, 'error');
        
        // Reset UI
        progressDiv.style.display = 'none';
        uploadBtn.disabled = false;
    });
}

function startProcessingMonitor() {
    if (!processingStatusId) return;
    
    processingInterval = setInterval(() => {
        checkProcessingStatus();
    }, 2000); // Check every 2 seconds
}

function checkProcessingStatus() {
    if (!processingStatusId) return;
    
    fetch(`/processing_status/${processingStatusId}`)
        .then(response => response.json())
        .then(status => {
            updateProcessingProgress(status);
            
            if (status.status === 'completed') {
                handleProcessingComplete(status);
            } else if (status.status === 'error') {
                handleProcessingError(status);
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
        });
}

function updateProcessingProgress(status) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    const progress = status.progress || 0;
    const message = status.message || 'Đang xử lý...';
    
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${message} (${progress}%)`;
    
    // Add stage-specific information
    if (status.stage) {
        let stageText = '';
        switch (status.stage) {
            case 'pdf_convert':
                stageText = 'Chuyển đổi PDF thành ảnh';
                if (status.current_page && status.total_pages) {
                    stageText += ` (${status.current_page}/${status.total_pages})`;
                }
                break;
            case 'yolo_detect':
                stageText = 'YOLO Detection';
                if (status.current_image && status.total_images) {
                    stageText += ` (${status.current_image}/${status.total_images})`;
                }
                break;
            case 'ocr':
                stageText = 'OCR Text Recognition';
                if (status.current_folder) {
                    stageText += ` (Folder ${status.current_folder})`;
                }
                break;
            default:
                stageText = status.stage;
        }
        
        progressText.textContent = `${stageText}: ${message}`;
    }
}
function handleProcessingComplete(status) {
    // Stop monitoring
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const uploadBtn = document.getElementById('submitUpload');
    
    progressBar.style.width = '100%';
    progressText.textContent = 'Hoàn thành xử lý PDF!';
    uploadBtn.disabled = false;
    
    showAlert(`Hoàn thành xử lý PDF cho sách: ${status.book_name}`, 'success');
    
    // Refresh books list and questions
    setTimeout(() => {
        loadBooks();
        if (status.book_name) {
            // Switch to the new book
            const bookSelect = document.getElementById('bookSelect');
            const newBookPath = `books_cropped/${status.book_name}`;
            
            // Add option if not exists
            let optionExists = false;
            // XÓA DÒNG TRÙNG LẶP: const newBookPath = `books_cropped/${status.book_name}`;
            for (let option of bookSelect.options) {
                if (option.value === newBookPath) {
                    optionExists = true;
                    break;
                }
            }

            if (!optionExists) {
                const option = document.createElement('option');
                option.value = newBookPath;
                option.textContent = status.book_name;
                bookSelect.appendChild(option);
            }
            
            // Switch to new book
            bookSelect.value = newBookPath;
            onBookChange();
        }
        
        // Auto close modal after 3 seconds
        setTimeout(() => {
            closeUploadModal();
        }, 3000);
    }, 1000);
    
    // Cleanup status
    setTimeout(() => {
        if (processingStatusId) {
            fetch(`/cleanup_status/${processingStatusId}`, { method: 'DELETE' });
            processingStatusId = null;
        }
    }, 10000);
}
function handleProcessingError(status) {
    // Stop monitoring
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    const progressText = document.getElementById('progressText');
    const uploadBtn = document.getElementById('submitUpload');
    
    progressText.textContent = `Lỗi: ${status.message}`;
    uploadBtn.disabled = false;
    
    showAlert(`Lỗi xử lý PDF: ${status.message}`, 'error');
    
    // Cleanup status
    setTimeout(() => {
        if (processingStatusId) {
            fetch(`/cleanup_status/${processingStatusId}`, { method: 'DELETE' });
            processingStatusId = null;
        }
    }, 5000);
}

// === EXISTING FUNCTIONS ===
function loadBooks() {
    console.log('Loading books...');
    fetch('/api/books')
        .then(response => {
            console.log('Books response status:', response.status);
            return response.json();
        })
        .then(books => {
            console.log('Books loaded:', books);
            const bookSelect = document.getElementById('bookSelect');
            
            // Clear existing options
            bookSelect.innerHTML = '';
            
            // Add book options
            if (books.length > 0) {
                books.forEach(book => {
                    const option = document.createElement('option');
                    option.value = book;
                    // Hiển thị tên sạch
                    const displayName = getBookDisplayName(book);
                    option.textContent = book === 'cropped' ? 'Sách mặc định (cropped)' : displayName;
                    bookSelect.appendChild(option);
                    
                    if (book === currentBook) {
                        option.selected = true;
                    }
                });
            } else {
                // Add default option if no books found
                const option = document.createElement('option');
                option.value = 'cropped';
                option.textContent = 'Sách mặc định (cropped)';
                bookSelect.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error loading books:', error);
            showAlert('Lỗi khi tải danh sách sách: ' + error.message, 'error');
            
            // Add fallback option
            const bookSelect = document.getElementById('bookSelect');
            bookSelect.innerHTML = '<option value="cropped">Sách mặc định (cropped)</option>';
        });
}
function onBookChange() {
    const bookSelect = document.getElementById('bookSelect');
    currentBook = bookSelect.value;
    
    // Reload folders and questions for the new book
    loadFolders();
    loadQuestions();
    loadJsonContent();
    
    // Clear current selections
    selectedQuestionImages = [];
    selectedAnswerImages = [];
    
    // Clear images grid
    const container = document.getElementById('imagesGrid');
    
    // Clear folder selection
    const folderSelect = document.getElementById('folderSelect');
    folderSelect.value = '';
    
    // Hiển thị tên sạch trong alert
    const displayName = getBookDisplayName(currentBook);
    showAlert(`Đã chuyển sang sách: ${displayName}`, 'success');
}

function loadFolders() {
    console.log('Loading folders for book:', currentBook);
    fetch(`/api/folders?book=${currentBook}`)
        .then(response => {
            console.log('Folders response status:', response.status);
            return response.json();
        })
        .then(folders => {
            console.log('Folders loaded:', folders);
            const folderSelect = document.getElementById('folderSelect');
            const editFolderSelect = document.getElementById('editFolderSelect');
            
            // Clear existing options
            folderSelect.innerHTML = '<option value="">-- Chọn folder ảnh --</option>';
            if (editFolderSelect) {
                editFolderSelect.innerHTML = '<option value="">-- Chọn folder ảnh --</option>';
            }
            
            // Add folder options
            folders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder;
                option.textContent = folder;
                folderSelect.appendChild(option);
                
                if (editFolderSelect) {
                    const editOption = document.createElement('option');
                    editOption.value = folder;
                    editOption.textContent = folder;
                    editFolderSelect.appendChild(editOption);
                }
            });
        })
        .catch(error => {
            console.error('Error loading folders:', error);
            showAlert('Lỗi khi tải danh sách folder: ' + error.message, 'error');
        });
}

function loadImagesFromFolder() {
    const folderSelect = document.getElementById('folderSelect');
    const selectedFolder = folderSelect.value;
    
    if (!selectedFolder) {
        // Clear images grid
        const container = document.getElementById('imagesGrid');
        allImages = [];
        return;
    }
    
    fetch(`/api/images/${selectedFolder}?book=${currentBook}`)
        .then(response => response.json())
        .then(images => {
            allImages = images;
            renderImagesGrid('imagesGrid', false);
        })
        .catch(error => {
            console.error('Error loading images:', error);
            showAlert('Lỗi khi tải ảnh từ folder', 'error');
        });
}

function loadImagesFromFolderForEdit(folderName) {
    if (!folderName) {
        const container = document.getElementById('editImagesGrid');
        return;
    }
    
    fetch(`/api/images/${folderName}?book=${currentBook}`)
        .then(response => response.json())
        .then(images => {
            allImages = images;
            renderImagesGrid('editImagesGrid', true);
        })
        .catch(error => {
            console.error('Error loading images for edit:', error);
            showAlert('Lỗi khi tải ảnh cho edit', 'error');
        });
}

function renderImagesGrid(containerId, isEdit = false) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    allImages.forEach(imagePath => {
        const imageItem = document.createElement('div');
        imageItem.className = 'image-item';
        imageItem.dataset.path = imagePath;

        const img = document.createElement('img');
        img.src = `/images/${currentBook}/${imagePath}`;
        img.alt = imagePath;

        imageItem.appendChild(img);
        
        // Add selection click handler
        imageItem.addEventListener('click', (e) => {
            if (e.ctrlKey || e.metaKey) {
                // Ctrl/Cmd click for image preview
                showImagePreview(imagePath);
            } else {
                // Normal click for selection
                handleImageClick(imagePath, isEdit);
            }
        });

        container.appendChild(imageItem);
    });

    updateImageSelection(isEdit);
}

function handleImageClick(imagePath, isEdit = false) {
    const questionImages = isEdit ? editingQuestion?.image_question || [] : selectedQuestionImages;
    const answerImages = isEdit ? editingQuestion?.image_answer || [] : selectedAnswerImages;

    if (currentSelectionMode === 'question') {
        if (questionImages.includes(imagePath)) {
            // Remove from selection
            const index = questionImages.indexOf(imagePath);
            questionImages.splice(index, 1);
        } else {
            // Add to selection
            questionImages.push(imagePath);
        }
        
        if (isEdit) {
            editingQuestion.image_question = questionImages;
        } else {
            selectedQuestionImages = questionImages;
        }
    } else {
        if (answerImages.includes(imagePath)) {
            // Remove from selection
            const index = answerImages.indexOf(imagePath);
            answerImages.splice(index, 1);
        } else {
            // Add to selection
            answerImages.push(imagePath);
        }

        if (isEdit) {
            editingQuestion.image_answer = answerImages;
        } else {
            selectedAnswerImages = answerImages;
        }
    }

    updateImageSelection(isEdit);
}

function updateImageSelection(isEdit = false) {
    const containerId = isEdit ? 'editImagesGrid' : 'imagesGrid';
    const container = document.getElementById(containerId);
    const questionImages = isEdit ? editingQuestion?.image_question || [] : selectedQuestionImages;
    const answerImages = isEdit ? editingQuestion?.image_answer || [] : selectedAnswerImages;

    container.querySelectorAll('.image-item').forEach(item => {
        const imagePath = item.dataset.path;
        
        // Remove all selection classes
        item.classList.remove('selected-question', 'selected-answer');
        
        // Remove existing badges
        const existingBadge = item.querySelector('.image-badge');
        if (existingBadge) {
            existingBadge.remove();
        }

        // Add appropriate selection class and badge
        if (questionImages.includes(imagePath)) {
            item.classList.add('selected-question');
            const badge = document.createElement('div');
            badge.className = 'image-badge badge-question';
            badge.textContent = 'Q';
            item.appendChild(badge);
        } else if (answerImages.includes(imagePath)) {
            item.classList.add('selected-answer');
            const badge = document.createElement('div');
            badge.className = 'image-badge badge-answer';
            badge.textContent = 'A';
            item.appendChild(badge);
        }
    });
}

function setSelectionMode(mode, isEdit = false) {
    currentSelectionMode = mode;
    
    const questionBtn = document.getElementById(isEdit ? 'editSelectQuestionMode' : 'selectQuestionMode');
    const answerBtn = document.getElementById(isEdit ? 'editSelectAnswerMode' : 'selectAnswerMode');
    
    if (mode === 'question') {
        questionBtn.style.background = '#45a049';
        answerBtn.style.background = '#FF9800';
    } else {
        questionBtn.style.background = '#4CAF50';
        answerBtn.style.background = '#f57c00';
    }
}

function clearAllSelections(isEdit = false) {
    if (isEdit) {
        if (editingQuestion) {
            editingQuestion.image_question = [];
            editingQuestion.image_answer = [];
        }
    } else {
        selectedQuestionImages = [];
        selectedAnswerImages = [];
    }
    updateImageSelection(isEdit);
}

function handleAddQuestion(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const questionData = {
        subject: formData.get('subject'),
        chapter: formData.get('chapter'),
        lesson: formData.get('lesson'),
        question: formData.get('question'),
        answer: formData.get('answer'),
        difficulty: formData.get('difficulty'),
        image_question: selectedQuestionImages,
        image_answer: selectedAnswerImages,
        book: currentBook
    };

    fetch('/api/questions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(questionData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Thêm câu hỏi thành công!', 'success');
            event.target.reset();
            selectedQuestionImages = [];
            selectedAnswerImages = [];
            updateImageSelection();
            loadQuestions();
            // Refresh JSON viewer
            loadJsonContent();
        } else {
            showAlert('Lỗi khi thêm câu hỏi', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Lỗi khi thêm câu hỏi', 'error');
    });
}

function loadQuestions() {
    fetch(`/api/questions?book=${currentBook}`)
        .then(response => response.json())
        .then(questions => {
            renderQuestionsList(questions);
        })
        .catch(error => {
            console.error('Error loading questions:', error);
            showAlert('Lỗi khi tải danh sách câu hỏi', 'error');
        });
}

function renderQuestionsList(questions) {
    const container = document.getElementById('questionsList');
    container.innerHTML = '';

    questions.forEach(question => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        
        questionDiv.innerHTML = `
            <div class="question-header">
                <span class="question-index">#${question.index}</span>
                <div class="question-actions">
                    <button class="btn btn-primary" onclick="editQuestion(${question.index})">Sửa</button>
                    <button class="btn btn-danger" onclick="deleteQuestion(${question.index})">Xóa</button>
                </div>
            </div>
            <div class="question-content">
                <strong>Môn:</strong> ${question.subject || 'N/A'} | <strong>Chương:</strong> ${question.chapter || 'N/A'} | <strong>Bài:</strong> ${question.lesson || 'N/A'} | <strong>Độ khó:</strong> ${question.difficulty}
                <br><strong>Câu hỏi:</strong> ${question.question || 'N/A'}
                <br><strong>Đáp án:</strong> ${question.answer || 'N/A'}
            </div>
            <div class="question-images">
                ${(question.image_question || []).map(img => 
                    `<img src="/images/${currentBook}/${img}" alt="Question image" title="Ảnh câu hỏi: ${img}" onclick="showImagePreview('${img}')" style="cursor: pointer;">`
                ).join('')}
                ${(question.image_answer || []).map(img => 
                    `<img src="/images/${currentBook}/${img}" alt="Answer image" title="Ảnh đáp án: ${img}" onclick="showImagePreview('${img}')" style="cursor: pointer;">`
                ).join('')}
            </div>
        `;

        container.appendChild(questionDiv);
    });
}

function editQuestion(questionIndex) {
    fetch(`/api/questions?book=${currentBook}`)
        .then(response => response.json())
        .then(questions => {
            const question = questions.find(q => q.index === questionIndex);
            if (question) {
                editingQuestion = { ...question };
                
                // Fill form with current data
                document.getElementById('editSubject').value = question.subject || '';
                document.getElementById('editChapter').value = question.chapter || '';
                document.getElementById('editLesson').value = question.lesson || '';
                document.getElementById('editQuestion').value = question.question || '';
                document.getElementById('editAnswer').value = question.answer || '';
                document.getElementById('editDifficulty').value = question.difficulty || 'easy';
                
                // Try to detect folder from image paths
                const editFolderSelect = document.getElementById('editFolderSelect');
                if (question.image_question && question.image_question.length > 0) {
                    const firstImage = question.image_question[0];
                    const folderName = firstImage.split('/')[0];
                    editFolderSelect.value = folderName;
                    loadImagesFromFolderForEdit(folderName);
                } else if (question.image_answer && question.image_answer.length > 0) {
                    const firstImage = question.image_answer[0];
                    const folderName = firstImage.split('/')[0];
                    editFolderSelect.value = folderName;
                    loadImagesFromFolderForEdit(folderName);
                } else {
                    editFolderSelect.value = '';
                    loadImagesFromFolderForEdit('');
                }
                
                // Show modal
                document.getElementById('editModal').style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading question:', error);
            showAlert('Lỗi khi tải thông tin câu hỏi', 'error');
        });
}

function handleEditQuestion(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const questionData = {
        subject: formData.get('subject'),
        chapter: formData.get('chapter'),
        lesson: formData.get('lesson'),
        question: formData.get('question'),
        answer: formData.get('answer'),
        difficulty: formData.get('difficulty'),
        image_question: editingQuestion.image_question || [],
        image_answer: editingQuestion.image_answer || [],
        book: currentBook
    };

    fetch(`/api/questions/${editingQuestion.index}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(questionData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Cập nhật câu hỏi thành công!', 'success');
            closeEditModal();
            loadQuestions();
            // Refresh JSON viewer
            loadJsonContent();
        } else {
            showAlert('Lỗi khi cập nhật câu hỏi', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Lỗi khi cập nhật câu hỏi', 'error');
    });
}

function deleteQuestion(questionIndex) {
    if (confirm('Bạn có chắc chắn muốn xóa câu hỏi này không?')) {
        fetch(`/api/questions/${questionIndex}?book=${currentBook}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
                    if (data.success) {
            showAlert('Xóa câu hỏi thành công!', 'success');
            loadQuestions();
            // Refresh JSON viewer
            loadJsonContent();
        } else {
            showAlert('Lỗi khi xóa câu hỏi', 'error');
        }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Lỗi khi xóa câu hỏi', 'error');
        });
    }
}

function closeEditModal() {
    document.getElementById('editModal').style.display = 'none';
    editingQuestion = null;
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alertContainer');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    
    // Auto remove alert after 3 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// JSON Viewer Functions
function setupJsonViewer() {
    document.getElementById('loadJsonBtn').addEventListener('click', loadJsonContent);
    document.getElementById('saveJsonBtn').addEventListener('click', saveJsonContent);
}

function loadJsonContent() {
    fetch(`/api/json/raw?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const editor = document.getElementById('jsonEditor');
                editor.value = data.content;
                showAlert('Tải JSON thành công!', 'success');
                editor.classList.remove('error');
                editor.classList.add('success');
            } else {
                showAlert('Lỗi khi tải JSON: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Lỗi khi tải JSON', 'error');
        });
}

function saveJsonContent() {
    const editor = document.getElementById('jsonEditor');
    const content = editor.value;
    
    // Validate before saving
    try {
        JSON.parse(content);
    } catch (e) {
        showAlert('JSON không hợp lệ! Vui lòng kiểm tra lại.', 'error');
        editor.classList.add('error');
        return;
    }
    
    fetch('/api/json/raw', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: content, book: currentBook })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            editor.classList.remove('error');
            editor.classList.add('success');
            // Reload questions list to reflect changes
            setTimeout(() => {
                loadQuestions();
            }, 500);
        } else {
            showAlert('Lỗi khi lưu JSON: ' + data.error, 'error');
            editor.classList.add('error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Lỗi khi lưu JSON', 'error');
        editor.classList.add('error');
    });
}

function formatJson() {
    const editor = document.getElementById('jsonEditor');
    const content = editor.value;
    
    try {
        const parsed = JSON.parse(content);
        const formatted = JSON.stringify(parsed, null, 2);
        editor.value = formatted;
        showAlert('Format JSON thành công!', 'success');
        editor.classList.remove('error');
        editor.classList.add('success');
    } catch (e) {
        showAlert('JSON không hợp lệ! Không thể format.', 'error');
        editor.classList.add('error');
    }
}

function validateJson() {
    const editor = document.getElementById('jsonEditor');
    const content = editor.value;
    
    try {
        const parsed = JSON.parse(content);
        const questionsCount = Array.isArray(parsed) ? parsed.length : 0;
        showAlert(`JSON hợp lệ! Có ${questionsCount} câu hỏi.`, 'success');
        editor.classList.remove('error');
        editor.classList.add('success');
    } catch (e) {
        showAlert('JSON không hợp lệ: ' + e.message, 'error');
        editor.classList.add('error');
    }
}

// Image Preview Functions
function showImagePreview(imagePath) {
    const modal = document.getElementById('imagePreviewModal');
    const previewImage = document.getElementById('previewImage');
    const imagePathElement = document.getElementById('imagePath');
    
    previewImage.src = `/images/${currentBook}/${imagePath}`;
    imagePathElement.textContent = `Đường dẫn: ${currentBook}/${imagePath}`;
    
    modal.style.display = 'block';
}

function closeImagePreview() {
    const modal = document.getElementById('imagePreviewModal');
    modal.style.display = 'none';
}
let currentTextContent = '';
let currentTextFolder = '';
let isEditingText = false;

// Thêm vào hàm setupEventListeners()
function setupEventListeners() {
    // ... existing code ...
    
    // Text content editing
    document.getElementById('editTextBtn').addEventListener('click', startTextEditing);
    document.getElementById('saveTextBtn').addEventListener('click', saveTextContent);
    document.getElementById('cancelTextBtn').addEventListener('click', cancelTextEditing);
}

// Sửa hàm loadImagesFromFolder()
function loadImagesFromFolder() {
    const folderSelect = document.getElementById('folderSelect');
    const selectedFolder = folderSelect.value;
    
    if (!selectedFolder) {
        const container = document.getElementById('imagesGrid');
        allImages = [];
        hideTextContent();
        return;
    }
    
    fetch(`/api/images/${selectedFolder}?book=${currentBook}`)
        .then(response => response.json())
        .then(images => {
            allImages = images;
            renderImagesGrid('imagesGrid', false);
            loadTextFromFolder(selectedFolder);
        })
        .catch(error => {
            console.error('Error loading images:', error);
            showAlert('Lỗi khi tải ảnh từ folder', 'error');
        });
}

// Text content functions
function loadTextFromFolder(folderName) {
    currentTextFolder = folderName;
    
    fetch(`/api/text/${folderName}?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            const textGroup = document.getElementById('textContentGroup');
            const textDisplay = document.getElementById('textDisplay');
            
            if (data.success && data.content.trim()) {
                currentTextContent = data.content;
                textDisplay.textContent = data.content;
                textDisplay.classList.remove('empty');
                textGroup.style.display = 'block';
            } else {
                currentTextContent = '';
                textDisplay.textContent = 'Không có file text.txt trong folder này';
                textDisplay.classList.add('empty');
                textGroup.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading text:', error);
            hideTextContent();
        });
}

function hideTextContent() {
    const textGroup = document.getElementById('textContentGroup');
    textGroup.style.display = 'none';
    currentTextContent = '';
    currentTextFolder = '';
    cancelTextEditing();
}

function startTextEditing() {
    if (!currentTextFolder) return;
    
    isEditingText = true;
    const textDisplay = document.getElementById('textDisplay');
    const textEditor = document.getElementById('textEditor');
    const editBtn = document.getElementById('editTextBtn');
    const saveBtn = document.getElementById('saveTextBtn');
    const cancelBtn = document.getElementById('cancelTextBtn');
    
    textEditor.value = currentTextContent;
    textDisplay.style.display = 'none';
    textEditor.style.display = 'block';
    editBtn.style.display = 'none';
    saveBtn.style.display = 'inline-block';
    cancelBtn.style.display = 'inline-block';
    
    textEditor.focus();
}

function saveTextContent() {
    if (!currentTextFolder) return;
    
    const textEditor = document.getElementById('textEditor');
    const newContent = textEditor.value;
    
    fetch(`/api/text/${currentTextFolder}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            content: newContent, 
            book: currentBook 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentTextContent = newContent;
            const textDisplay = document.getElementById('textDisplay');
            
            if (newContent.trim()) {
                textDisplay.textContent = newContent;
                textDisplay.classList.remove('empty');
            } else {
                textDisplay.textContent = 'File text.txt trống';
                textDisplay.classList.add('empty');
            }
            
            cancelTextEditing();
            showAlert('Lưu nội dung text thành công!', 'success');
        } else {
            showAlert('Lỗi khi lưu text: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error saving text:', error);
        showAlert('Lỗi khi lưu nội dung text', 'error');
    });
}

function cancelTextEditing() {
    isEditingText = false;
    const textDisplay = document.getElementById('textDisplay');
    const textEditor = document.getElementById('textEditor');
    const editBtn = document.getElementById('editTextBtn');
    const saveBtn = document.getElementById('saveTextBtn');
    const cancelBtn = document.getElementById('cancelTextBtn');
    
    textDisplay.style.display = 'block';
    textEditor.style.display = 'none';
    editBtn.style.display = 'inline-block';
    saveBtn.style.display = 'none';
    cancelBtn.style.display = 'none';
}
// Thêm vào setupEventListeners()
document.getElementById('editTextBtnModal').addEventListener('click', () => startTextEditingModal());
document.getElementById('saveTextBtnModal').addEventListener('click', () => saveTextContentModal());
document.getElementById('cancelTextBtnModal').addEventListener('click', () => cancelTextEditingModal());

// Sửa hàm loadImagesFromFolderForEdit()
function loadImagesFromFolderForEdit(folderName) {
    if (!folderName) {
        const container = document.getElementById('editImagesGrid');
        const textGroup = document.getElementById('editTextContentGroup');
        textGroup.style.display = 'none';
        return;
    }
    
    fetch(`/api/images/${folderName}?book=${currentBook}`)
        .then(response => response.json())
        .then(images => {
            allImages = images;
            renderImagesGrid('editImagesGrid', true);
            loadTextFromFolderModal(folderName);
        })
        .catch(error => {
            console.error('Error loading images for edit:', error);
            showAlert('Lỗi khi tải ảnh cho edit', 'error');
        });
}

function loadTextFromFolderModal(folderName) {
    fetch(`/api/text/${folderName}?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            const textGroup = document.getElementById('editTextContentGroup');
            const textDisplay = document.getElementById('editTextDisplay');
            
            if (data.success && data.content.trim()) {
                textDisplay.textContent = data.content;
                textDisplay.classList.remove('empty');
                textGroup.style.display = 'block';
            } else {
                textDisplay.textContent = 'Không có file text.txt trong folder này';
                textDisplay.classList.add('empty');
                textGroup.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading text for modal:', error);
            const textGroup = document.getElementById('editTextContentGroup');
            textGroup.style.display = 'none';
        });
}
// Authentication Middleware - Thêm vào đầu file script.js

// Global auth state
let currentUser = null;
let authToken = null;

// Initialize authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeAuth();
    // ... existing initialization code
});

function initializeAuth() {
    // Get token from storage
    authToken = sessionStorage.getItem('authToken') || localStorage.getItem('authToken');
    
    if (!authToken) {
        // No token, redirect to login
        redirectToLogin();
        return;
    }
    
    // Verify token with server
    verifyAuthToken()
        .then(isValid => {
            if (!isValid) {
                redirectToLogin();
            } else {
                // Continue with app initialization
                setupAuthenticatedApp();
            }
        })
        .catch(error => {
            console.error('Auth verification error:', error);
            redirectToLogin();
        });
}

function verifyAuthToken() {
    return fetch('/api/verify-token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid) {
            currentUser = data.user;
            return true;
        }
        return false;
    })
    .catch(error => {
        console.error('Token verification failed:', error);
        return false;
    });
}

function setupAuthenticatedApp() {
    // Setup logout functionality
    setupLogout();
    
    // Setup user info display
    displayUserInfo();
    
    // Setup auto token refresh
    setupTokenRefresh();
    
    // Add auth headers to all API requests
    setupAuthenticatedRequests();
    
    // Initialize app after auth is verified
    loadBooks();
    loadFolders();
    loadQuestions();
    setupEventListeners();
    setupJsonViewer();
    setupPDFUpload();
    loadJsonContent();
}

function setupLogout() {
    // Add logout button if not exists
    let logoutBtn = document.getElementById('logoutBtn');
    if (!logoutBtn) {
        logoutBtn = document.createElement('button');
        logoutBtn.id = 'logoutBtn';
        logoutBtn.className = 'logout-btn';
        logoutBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
            </svg>
            Đăng xuất
        `;
        
        // Add to header or appropriate location
        const header = document.querySelector('header') || document.querySelector('.header') || document.body;
        header.appendChild(logoutBtn);
    }
    
    logoutBtn.addEventListener('click', handleLogout);
}

function displayUserInfo() {
    if (!currentUser) return;
    
    // Add user info display
    let userInfo = document.getElementById('userInfo');
    if (!userInfo) {
        userInfo = document.createElement('div');
        userInfo.id = 'userInfo';
        userInfo.className = 'user-info';
        
        const header = document.querySelector('header') || document.querySelector('.header') || document.body;
        header.appendChild(userInfo);
    }
    
    userInfo.innerHTML = `
        <div class="user-details">
            <span class="user-name">Xin chào, ${currentUser.username}</span>
            <span class="user-role">(${currentUser.role})</span>
        </div>
    `;
}

function setupTokenRefresh() {
    // Refresh token every 30 minutes
    setInterval(() => {
        verifyAuthToken().then(isValid => {
            if (!isValid) {
                redirectToLogin();
            }
        });
    }, 30 * 60 * 1000); // 30 minutes
}

function setupAuthenticatedRequests() {
    // Override fetch to include auth headers
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Add auth header to all API requests
        if (url.startsWith('/api/') && authToken) {
            options.headers = options.headers || {};
            options.headers['Authorization'] = `Bearer ${authToken}`;
        }
        
        return originalFetch(url, options)
            .then(response => {
                // Handle auth errors
                if (response.status === 401) {
                    redirectToLogin();
                    throw new Error('Authentication required');
                }
                return response;
            });
    };
}

function handleLogout() {
    if (confirm('Bạn có chắc chắn muốn đăng xuất?')) {
        // Call logout API
        fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        })
        .then(() => {
            logout();
        })
        .catch(error => {
            console.error('Logout error:', error);
            logout(); // Force logout even if API fails
        });
    }
}

function logout() {
    // Clear tokens
    sessionStorage.removeItem('authToken');
    localStorage.removeItem('authToken');
    
    // Clear user data
    currentUser = null;
    authToken = null;
    
    // Show logout message
    showAlert('Đã đăng xuất thành công', 'success');
    
    // Redirect to login after short delay
    setTimeout(() => {
        redirectToLogin();
    }, 1000);
}

function redirectToLogin() {
    window.location.href = '/login';
}

// CSS for auth components
const authCSS = `
.logout-btn {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 25px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
    backdrop-filter: blur(10px);
}

.logout-btn:hover {
    background: linear-gradient(135deg, #ee5a52 0%, #e74c3c 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(255, 107, 107, 0.4);
}

.logout-btn:active {
    transform: translateY(0);
    box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
}

.logout-btn svg {
    transition: transform 0.3s ease;
}

.logout-btn:hover svg {
    transform: translateX(2px);
}

.user-info {
    position: fixed;
    top: 20px;
    right: 180px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(15px);
    padding: 12px 20px;
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    z-index: 999;
    transition: all 0.3s ease;
}

.user-info:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.user-details {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}

.user-name {
    font-weight: 700;
    color: #2c3e50;
    font-size: 14px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.user-role {
    font-size: 11px;
    color: #7f8c8d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 500;
    padding: 2px 8px;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
    border-radius: 10px;
    font-size: 10px;
}

/* Animation cho user info */
@keyframes slideInFromRight {
    from {
        opacity: 0;
        transform: translateX(100px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.user-info {
    animation: slideInFromRight 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.logout-btn {
    animation: slideInFromRight 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
}

/* Responsive design */
@media (max-width: 768px) {
    .logout-btn {
        top: 15px;
        right: 15px;
        padding: 8px 16px;
        font-size: 12px;
        border-radius: 20px;
    }
    
    .user-info {
        top: 15px;
        right: 120px;
        padding: 8px 15px;
        border-radius: 15px;
    }
    
    .user-name {
        font-size: 12px;
    }
    
    .user-role {
        font-size: 9px;
        padding: 2px 6px;
    }
}

@media (max-width: 480px) {
    .user-info {
        position: relative;
        top: auto;
        right: auto;
        margin: 10px;
        display: inline-block;
    }
    
    .logout-btn {
        position: relative;
        top: auto;
        right: auto;
        margin: 10px;
        display: inline-block;
    }
    
    .user-details {
        align-items: center;
        text-align: center;
    }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    .user-info {
        background: rgba(44, 62, 80, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .user-name {
        color: #ecf0f1;
    }
}

/* Hover effects cho mobile */
@media (hover: none) {
    .logout-btn:hover {
        transform: none;
    }
    
    .user-info:hover {
        transform: none;
    }
}
`;
function displayUserInfo() {
    if (!currentUser) return;
    
    // Add user info display
    let userInfo = document.getElementById('userInfo');
    if (!userInfo) {
        userInfo = document.createElement('div');
        userInfo.id = 'userInfo';
        userInfo.className = 'user-info';
        
        const header = document.querySelector('header') || document.querySelector('.header') || document.body;
        header.appendChild(userInfo);
    }
    
    userInfo.innerHTML = `
        <div class="user-details">
            <span class="user-name">👋 Xin chào, ${currentUser.username}</span>
            <span class="user-role">${currentUser.role}</span>
        </div>
    `;
}

// Inject auth CSS
const authStyle = document.createElement('style');
authStyle.textContent = authCSS;
document.head.appendChild(authStyle);