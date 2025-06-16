// Global variables
let allImages = [];
let selectedQuestionImages = [];
let selectedAnswerImages = [];
let currentSelectionMode = 'question'; // 'question' or 'answer'
let editingQuestion = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    loadFolders();
    loadQuestions();
    setupEventListeners();
    setupJsonViewer();
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
        const modal = document.getElementById('editModal');
        if (event.target === modal) {
            closeEditModal();
        }
    });
}

function loadFolders() {
    fetch('/api/folders')
        .then(response => response.json())
        .then(folders => {
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
            showAlert('Lỗi khi tải danh sách folder', 'error');
        });
}

function loadImagesFromFolder() {
    const folderSelect = document.getElementById('folderSelect');
    const selectedFolder = folderSelect.value;
    
    if (!selectedFolder) {
        // Clear images grid
        const container = document.getElementById('imagesGrid');
        container.innerHTML = '<p class="no-images">Vui lòng chọn folder để xem ảnh</p>';
        allImages = [];
        return;
    }
    
    fetch(`/api/images/${selectedFolder}`)
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
        container.innerHTML = '<p class="no-images">Vui lòng chọn folder để xem ảnh</p>';
        return;
    }
    
    fetch(`/api/images/${folderName}`)
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
        img.src = `/images/${imagePath}`;
        img.alt = imagePath;

        imageItem.appendChild(img);
        imageItem.addEventListener('click', () => handleImageClick(imagePath, isEdit));

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
        image_answer: selectedAnswerImages
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
    fetch('/api/questions')
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
                    `<img src="/images/${img}" alt="Question image" title="Ảnh câu hỏi: ${img}">`
                ).join('')}
                ${(question.image_answer || []).map(img => 
                    `<img src="/images/${img}" alt="Answer image" title="Ảnh đáp án: ${img}">`
                ).join('')}
            </div>
        `;

        container.appendChild(questionDiv);
    });
}

function editQuestion(questionIndex) {
    fetch('/api/questions')
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
        image_answer: editingQuestion.image_answer || []
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
        fetch(`/api/questions/${questionIndex}`, {
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

// Remove unused tab management functions

// JSON Viewer Functions
function setupJsonViewer() {
    document.getElementById('loadJsonBtn').addEventListener('click', loadJsonContent);
    document.getElementById('saveJsonBtn').addEventListener('click', saveJsonContent);
    document.getElementById('formatJsonBtn').addEventListener('click', formatJson);
    document.getElementById('validateJsonBtn').addEventListener('click', validateJson);
}

function loadJsonContent() {
    fetch('/api/json/raw')
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
        body: JSON.stringify({ content: content })
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