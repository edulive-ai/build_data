// Global variables
let currentBook = '';
let currentViewMode = 'detection';
let allDetectionImages = [];
let allCroppedImages = [];
let currentFolder = 'all';
let currentSort = 'name';
let filteredImages = [];
let currentImageIndex = 0;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Gallery.js loaded');
    setupEventListeners();
    loadBooks();
});

function setupEventListeners() {
    // Modal controls - check if elements exist first
    const imageModalClose = document.querySelector('#imageModal .close');
    const lightboxClose = document.querySelector('#lightbox .lightbox-close');
    const prevBtn = document.getElementById('prevImageBtn');
    const nextBtn = document.getElementById('nextImageBtn');
    const lightboxPrev = document.getElementById('lightboxPrev');
    const lightboxNext = document.getElementById('lightboxNext');
    const downloadBtn = document.getElementById('downloadImageBtn');

    if (imageModalClose) imageModalClose.addEventListener('click', closeImageModal);
    if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
    if (prevBtn) prevBtn.addEventListener('click', () => navigateImage(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateImage(1));
    if (lightboxPrev) lightboxPrev.addEventListener('click', () => navigateImage(-1));
    if (lightboxNext) lightboxNext.addEventListener('click', () => navigateImage(1));
    if (downloadBtn) downloadBtn.addEventListener('click', downloadCurrentImage);

    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        const imageModal = document.getElementById('imageModal');
        const lightbox = document.getElementById('lightbox');
        
        if (event.target === imageModal) {
            closeImageModal();
        }
        if (event.target === lightbox) {
            closeLightbox();
        }
    });

    // Keyboard navigation
    document.addEventListener('keydown', function(event) {
        const imageModal = document.getElementById('imageModal');
        const lightbox = document.getElementById('lightbox');
        
        if ((imageModal && imageModal.style.display === 'block') || 
            (lightbox && lightbox.style.display === 'block')) {
            switch(event.key) {
                case 'ArrowLeft':
                    navigateImage(-1);
                    break;
                case 'ArrowRight':
                    navigateImage(1);
                    break;
                case 'Escape':
                    if (lightbox && lightbox.style.display === 'block') {
                        closeLightbox();
                    } else {
                        closeImageModal();
                    }
                    break;
                case 'f':
                case 'F':
                    if (imageModal && imageModal.style.display === 'block') {
                        openLightbox();
                    }
                    break;
            }
        }
    });
}

function loadBooks() {
    console.log('Loading books...');
    showLoading(true);
    
    fetch('/api/gallery/books')
        .then(response => {
            console.log('Books response status:', response.status);
            return response.json();
        })
        .then(books => {
            console.log('Books loaded:', books);
            const bookSelect = document.getElementById('bookSelect');
            
            if (!bookSelect) {
                console.error('bookSelect element not found!');
                return;
            }
            
            bookSelect.innerHTML = '<option value="">-- Chọn sách --</option>';
            
            books.forEach(book => {
                const option = document.createElement('option');
                option.value = book;
                option.textContent = book;
                bookSelect.appendChild(option);
            });
            
            console.log('Added', books.length, 'books to dropdown');
            showLoading(false);
        })
        .catch(error => {
            console.error('Error loading books:', error);
            showAlert('Lỗi khi tải danh sách sách: ' + error.message, 'error');
            showLoading(false);
        });
}

function onBookChange() {
    const bookSelect = document.getElementById('bookSelect');
    currentBook = bookSelect.value;
    
    console.log('Book changed to:', currentBook);
    
    if (currentBook) {
        loadGallery();
    } else {
        clearGallery();
    }
}

function onViewModeChange() {
    const viewMode = document.getElementById('viewMode').value;
    currentViewMode = viewMode;
    updateViewMode();
}

function onSortChange() {
    const sortBy = document.getElementById('sortBy').value;
    currentSort = sortBy;
    sortAndDisplayImages();
}

function updateViewMode() {
    const detectionSection = document.getElementById('detectionSection');
    const croppedSection = document.getElementById('croppedSection');
    
    if (!detectionSection || !croppedSection) {
        console.error('Section elements not found');
        return;
    }
    
    switch(currentViewMode) {
        case 'detection':
            detectionSection.classList.remove('hidden');
            croppedSection.classList.add('hidden');
            break;
        case 'cropped':
            detectionSection.classList.add('hidden');
            croppedSection.classList.remove('hidden');
            break;
        case 'both':
            detectionSection.classList.remove('hidden');
            croppedSection.classList.remove('hidden');
            break;
    }
}

function loadGallery() {
    if (!currentBook) {
        showAlert('Vui lòng chọn sách trước', 'warning');
        return;
    }
    
    console.log('Loading gallery for book:', currentBook);
    showLoading(true);
    
    Promise.all([
        loadDetectionImages(),
        loadCroppedImages()
    ]).then(() => {
        updateViewMode();
        updateImageStats();
        showLoading(false);
    }).catch(error => {
        console.error('Error loading gallery:', error);
        showAlert('Lỗi khi tải gallery: ' + error.message, 'error');
        showLoading(false);
    });
}

function loadDetectionImages() {
    console.log('Loading detection images for:', currentBook);
    return fetch(`/api/gallery/detection?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            console.log('Detection images response:', data);
            if (data.success) {
                allDetectionImages = data.images || [];
                displayDetectionImages();
            } else {
                console.warn('Detection images failed:', data.error);
                allDetectionImages = [];
                displayDetectionImages();
            }
        });
}

function loadCroppedImages() {
    console.log('Loading cropped images for:', currentBook);
    return fetch(`/api/gallery/cropped?book=${currentBook}`)
        .then(response => response.json())
        .then(data => {
            console.log('Cropped images response:', data);
            if (data.success) {
                allCroppedImages = data.images || [];
                displayCroppedImages();
                createFolderTabs();
            } else {
                console.warn('Cropped images failed:', data.error);
                allCroppedImages = [];
                displayCroppedImages();
                createFolderTabs();
            }
        });
}

function displayDetectionImages() {
    const container = document.getElementById('detectionGrid');
    const countElement = document.getElementById('detectionCount');
    
    if (!container || !countElement) {
        console.error('Detection display elements not found');
        return;
    }
    
    if (allDetectionImages.length === 0) {
        container.innerHTML = '<div class="no-images">Không có ảnh detection nào</div>';
        countElement.textContent = '0';
        return;
    }
    
    countElement.textContent = allDetectionImages.length;
    
    const sortedImages = sortImages(allDetectionImages);
    container.innerHTML = '';
    
    sortedImages.forEach((image, index) => {
        const imageCard = createImageCard(image, 'detection', index);
        container.appendChild(imageCard);
    });
    
    console.log('Displayed', allDetectionImages.length, 'detection images');
}

function displayCroppedImages() {
    const container = document.getElementById('croppedGrid');
    const countElement = document.getElementById('croppedCount');
    
    if (!container || !countElement) {
        console.error('Cropped display elements not found');
        return;
    }
    
    let imagesToShow = allCroppedImages;
    
    // Filter by folder if selected
    if (currentFolder !== 'all') {
        imagesToShow = allCroppedImages.filter(img => img.folder === currentFolder);
    }
    
    if (imagesToShow.length === 0) {
        container.innerHTML = '<div class="no-images">Không có ảnh crop nào</div>';
        countElement.textContent = '0';
        return;
    }
    
    countElement.textContent = imagesToShow.length;
    
    const sortedImages = sortImages(imagesToShow);
    container.innerHTML = '';
    
    sortedImages.forEach((image, index) => {
        const imageCard = createImageCard(image, 'cropped', index);
        container.appendChild(imageCard);
    });
    
    console.log('Displayed', imagesToShow.length, 'cropped images');
}

function createFolderTabs() {
    const container = document.getElementById('folderTabs');
    
    if (!container) {
        console.error('folderTabs element not found');
        return;
    }
    
    if (allCroppedImages.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    // Get unique folders
    const folders = [...new Set(allCroppedImages.map(img => img.folder))];
    const folderCounts = {};
    
    folders.forEach(folder => {
        folderCounts[folder] = allCroppedImages.filter(img => img.folder === folder).length;
    });
    
    container.innerHTML = '';
    
    // All tab
    const allTab = document.createElement('div');
    allTab.className = `folder-tab ${currentFolder === 'all' ? 'active' : ''}`;
    allTab.innerHTML = `📁 Tất cả <span class="tab-count">${allCroppedImages.length}</span>`;
    allTab.onclick = () => selectFolder('all');
    container.appendChild(allTab);
    
    // Individual folder tabs
    folders.sort().forEach(folder => {
        const tab = document.createElement('div');
        tab.className = `folder-tab ${currentFolder === folder ? 'active' : ''}`;
        tab.innerHTML = `📂 ${folder} <span class="tab-count">${folderCounts[folder]}</span>`;
        tab.onclick = () => selectFolder(folder);
        container.appendChild(tab);
    });
}

function selectFolder(folder) {
    currentFolder = folder;
    displayCroppedImages();
    
    // Update tab active state
    document.querySelectorAll('.folder-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    const activeTab = [...document.querySelectorAll('.folder-tab')].find(tab => {
        const tabText = tab.textContent;
        return (folder === 'all' && tabText.includes('Tất cả')) || 
               (folder !== 'all' && tabText.includes(folder));
    });
    
    if (activeTab) {
        activeTab.classList.add('active');
    }
}

function createImageCard(image, type, index) {
    const card = document.createElement('div');
    card.className = 'image-card';
    card.dataset.type = type;
    card.dataset.index = index;
    
    const img = document.createElement('img');
    img.src = image.url;
    img.alt = image.name;
    img.loading = 'lazy';
    
    // Error handling for images
    img.onerror = function() {
        console.error('Failed to load image:', image.url);
        this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg==';
    };
    
    const info = document.createElement('div');
    info.className = 'image-card-info';
    
    const title = document.createElement('div');
    title.className = 'image-card-title';
    title.textContent = image.name;
    
    const meta = document.createElement('div');
    meta.className = 'image-card-meta';
    
    const size = document.createElement('span');
    size.textContent = image.size || 'N/A';
    
    const date = document.createElement('span');
    date.textContent = image.date || 'N/A';
    
    meta.appendChild(size);
    meta.appendChild(date);
    
    info.appendChild(title);
    info.appendChild(meta);
    
    // Add badge
    const badge = document.createElement('div');
    badge.className = 'image-badge';
    
    if (type === 'detection') {
        badge.className += ' badge-detection';
        badge.textContent = '🎯 Detection';
    } else {
        badge.className += ' badge-crop';
        if (image.class !== undefined) {
            badge.className += ` badge-cls${image.class}`;
            badge.textContent = `✂️ cls${image.class}`;
        } else {
            badge.textContent = '✂️ Crop';
        }
    }
    
    card.appendChild(img);
    card.appendChild(info);
    card.appendChild(badge);
    
    // Click handlers
    card.addEventListener('click', () => openImageModal(image, type, index));
    
    // Double click for lightbox
    card.addEventListener('dblclick', (e) => {
        e.preventDefault();
        openImageModal(image, type, index);
        setTimeout(() => openLightbox(), 100);
    });
    
    return card;
}

function sortImages(images) {
    return [...images].sort((a, b) => {
        switch(currentSort) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'date':
                return new Date(b.date) - new Date(a.date);
            case 'size':
                const sizeA = parseSize(a.size);
                const sizeB = parseSize(b.size);
                return sizeB - sizeA;
            default:
                return 0;
        }
    });
}

function parseSize(sizeStr) {
    if (!sizeStr) return 0;
    const match = sizeStr.match(/(\d+\.?\d*)\s*(KB|MB|GB)/i);
    if (!match) return 0;
    
    const value = parseFloat(match[1]);
    const unit = match[2].toUpperCase();
    
    switch(unit) {
        case 'KB': return value * 1024;
        case 'MB': return value * 1024 * 1024;
        case 'GB': return value * 1024 * 1024 * 1024;
        default: return value;
    }
}

function sortAndDisplayImages() {
    displayDetectionImages();
    displayCroppedImages();
}

function filterImages() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.toLowerCase();
    
    if (!searchTerm) {
        // Show all images
        document.querySelectorAll('.image-card').forEach(card => {
            card.style.display = 'block';
        });
        updateImageStats();
        return;
    }
    
    let visibleCount = 0;
    
    document.querySelectorAll('.image-card').forEach(card => {
        const title = card.querySelector('.image-card-title');
        if (title) {
            const titleText = title.textContent.toLowerCase();
            
            if (titleText.includes(searchTerm)) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        }
    });
    
    updateSearchStats(visibleCount);
}

function updateImageStats() {
    const detectionCount = allDetectionImages.length;
    const croppedCount = allCroppedImages.length;
    const totalCount = detectionCount + croppedCount;
    
    const statsElement = document.getElementById('imageStats');
    if (statsElement) {
        statsElement.textContent = `Tổng: ${totalCount} ảnh (${detectionCount} detection, ${croppedCount} crop)`;
    }
}

function updateSearchStats(visibleCount) {
    const totalCount = allDetectionImages.length + allCroppedImages.length;
    const statsElement = document.getElementById('imageStats');
    if (statsElement) {
        statsElement.textContent = `Hiển thị: ${visibleCount}/${totalCount} ảnh`;
    }
}

function openImageModal(image, type, index) {
    const modal = document.getElementById('imageModal');
    if (!modal) return;
    
    const modalImage = document.getElementById('modalImage');
    const modalTitle = document.getElementById('modalImageTitle');
    const modalPath = document.getElementById('modalImagePath');
    const modalSize = document.getElementById('modalImageSize');
    const modalType = document.getElementById('modalImageType');
    const modalClass = document.getElementById('modalImageClass');
    const modalCropInfo = document.getElementById('modalCropInfo');
    
    // Set current image data
    currentImageIndex = index;
    filteredImages = type === 'detection' ? allDetectionImages : 
                    (currentFolder === 'all' ? allCroppedImages : 
                     allCroppedImages.filter(img => img.folder === currentFolder));
    
    // Update modal content
    if (modalImage) modalImage.src = image.url;
    if (modalTitle) modalTitle.textContent = image.name;
    if (modalPath) modalPath.textContent = image.path || image.url;
    if (modalSize) modalSize.textContent = image.size || 'N/A';
    if (modalType) modalType.textContent = type === 'detection' ? '🎯 Detection Image' : '✂️ Cropped Image';
    
    if (modalClass && modalCropInfo) {
        if (type === 'cropped' && image.class !== undefined) {
            modalClass.textContent = `cls${image.class}`;
            modalCropInfo.style.display = 'block';
        } else {
            modalCropInfo.style.display = 'none';
        }
    }
    
    // Update navigation buttons
    updateNavigationButtons();
    
    modal.style.display = 'block';
}

function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openLightbox() {
    const modalImage = document.getElementById('modalImage');
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxTitle = document.getElementById('lightboxTitle');
    const lightboxCounter = document.getElementById('lightboxCounter');
    
    if (!modalImage || !lightbox) return;
    
    if (lightboxImage) lightboxImage.src = modalImage.src;
    if (lightboxTitle) lightboxTitle.textContent = document.getElementById('modalImageTitle')?.textContent || '';
    if (lightboxCounter) lightboxCounter.textContent = `${currentImageIndex + 1} / ${filteredImages.length}`;
    
    updateLightboxButtons();
    lightbox.style.display = 'block';
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.style.display = 'none';
    }
}

function navigateImage(direction) {
    if (!filteredImages.length) return;
    
    currentImageIndex += direction;
    
    if (currentImageIndex < 0) {
        currentImageIndex = filteredImages.length - 1;
    } else if (currentImageIndex >= filteredImages.length) {
        currentImageIndex = 0;
    }
    
    const newImage = filteredImages[currentImageIndex];
    
    // Update modal
    const modalImage = document.getElementById('modalImage');
    const modalTitle = document.getElementById('modalImageTitle');
    const modalPath = document.getElementById('modalImagePath');
    const modalSize = document.getElementById('modalImageSize');
    
    if (modalImage) modalImage.src = newImage.url;
    if (modalTitle) modalTitle.textContent = newImage.name;
    if (modalPath) modalPath.textContent = newImage.path || newImage.url;
    if (modalSize) modalSize.textContent = newImage.size || 'N/A';
    
    // Update lightbox if open
    const lightbox = document.getElementById('lightbox');
    if (lightbox && lightbox.style.display === 'block') {
        const lightboxImage = document.getElementById('lightboxImage');
        const lightboxTitle = document.getElementById('lightboxTitle');
        const lightboxCounter = document.getElementById('lightboxCounter');
        
        if (lightboxImage) lightboxImage.src = newImage.url;
        if (lightboxTitle) lightboxTitle.textContent = newImage.name;
        if (lightboxCounter) lightboxCounter.textContent = `${currentImageIndex + 1} / ${filteredImages.length}`;
        
        updateLightboxButtons();
    }
    
    updateNavigationButtons();
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prevImageBtn');
    const nextBtn = document.getElementById('nextImageBtn');
    
    if (prevBtn) prevBtn.disabled = filteredImages.length <= 1;
    if (nextBtn) nextBtn.disabled = filteredImages.length <= 1;
}

function updateLightboxButtons() {
    const prevBtn = document.getElementById('lightboxPrev');
    const nextBtn = document.getElementById('lightboxNext');
    
    if (prevBtn) prevBtn.disabled = filteredImages.length <= 1;
    if (nextBtn) nextBtn.disabled = filteredImages.length <= 1;
}

function downloadCurrentImage() {
    const modalImage = document.getElementById('modalImage');
    const modalTitle = document.getElementById('modalImageTitle');
    
    if (!modalImage || !modalImage.src) return;
    
    const link = document.createElement('a');
    link.href = modalImage.src;
    link.download = modalTitle?.textContent || 'image.jpg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function clearGallery() {
    const detectionGrid = document.getElementById('detectionGrid');
    const croppedGrid = document.getElementById('croppedGrid');
    const folderTabs = document.getElementById('folderTabs');
    const detectionCount = document.getElementById('detectionCount');
    const croppedCount = document.getElementById('croppedCount');
    const imageStats = document.getElementById('imageStats');
    
    if (detectionGrid) detectionGrid.innerHTML = '<div class="no-images">Chưa chọn sách</div>';
    if (croppedGrid) croppedGrid.innerHTML = '<div class="no-images">Chưa chọn sách</div>';
    if (folderTabs) folderTabs.innerHTML = '';
    if (detectionCount) detectionCount.textContent = '0';
    if (croppedCount) croppedCount.textContent = '0';
    if (imageStats) imageStats.textContent = 'Chưa có dữ liệu';
    
    allDetectionImages = [];
    allCroppedImages = [];
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'block' : 'none';
    }
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        console.warn('Alert container not found, showing console message:', message);
        return;
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}