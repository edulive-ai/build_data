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
    loadBooks();
    loadFolders();
    loadQuestions();
    setupEventListeners();
    setupJsonViewer();
    setupPDFUpload();
    loadJsonContent(); // Auto-load JSON on startup
});

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
                    option.textContent = book === 'cropped' ? 'Sách mặc định (cropped)' : book;
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
    
    showAlert(`Đã chuyển sang sách: ${currentBook}`, 'success');
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
    document.getElementById('formatJsonBtn').addEventListener('click', formatJson);
    document.getElementById('validateJsonBtn').addEventListener('click', validateJson);
}

function loadJsonContent() {
    fetch(`/api/json/raw?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const editor = document.getElementById('jsonEditor');
                editor.value = data.content;
                updateJsonStats(data.content);
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
            updateJsonStats(content);
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
        updateJsonStats(formatted);
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
        updateJsonStats(content);
    } catch (e) {
        showAlert('JSON không hợp lệ: ' + e.message, 'error');
        editor.classList.add('error');
    }
}

function updateJsonStats(jsonContent) {
    const statsElement = document.getElementById('jsonStats');
    
    try {
        const parsed = JSON.parse(jsonContent);
        const questionsCount = Array.isArray(parsed) ? parsed.length : 0;
        const chars = jsonContent.length;
        const lines = jsonContent.split('\n').length;
        
        // Count unique subjects, chapters and lessons
        const subjects = new Set();
        const chapters = new Set();
        const lessons = new Set();
        const difficulties = { easy: 0, medium: 0, hard: 0 };
        
        if (Array.isArray(parsed)) {
            parsed.forEach(q => {
                if (q.subject) subjects.add(q.subject);
                if (q.chapter) chapters.add(q.chapter);
                if (q.lesson) lessons.add(q.lesson);
                if (q.difficulty) difficulties[q.difficulty] = (difficulties[q.difficulty] || 0) + 1;
            });
        }
        
        statsElement.innerHTML = `
            <strong>Thống kê:</strong> 
            ${questionsCount} câu hỏi | 
            ${subjects.size} môn học | 
            ${chapters.size} chương | 
            ${lessons.size} bài học | 
            ${lines} dòng | 
            ${chars} ký tự |
            Độ khó: Dễ(${difficulties.easy}) Vừa(${difficulties.medium}) Khó(${difficulties.hard})
        `;
    } catch (e) {
        statsElement.textContent = 'JSON không hợp lệ - không thể thống kê';
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