# 📚 PDF Processing Application - Hệ thống Xử lý PDF và Quản lý Câu hỏi

Ứng dụng web tự động xử lý file PDF thành câu hỏi và đáp án sử dụng YOLO Detection và DeepSeek OCR API, kết hợp với giao diện quản lý câu hỏi và gallery xem ảnh.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3+-green)
![YOLO](https://img.shields.io/badge/YOLO-v10-red)
![DeepSeek](https://img.shields.io/badge/OCR-DeepSeek%20API-orange)

## 🎯 Tính năng chính

### 🔄 Xử lý PDF tự động
- **Upload PDF**: Upload file PDF trực tiếp qua web interface
- **Convert cao cấp**: Chuyển PDF thành ảnh 300 DPI chất lượng cao
- **YOLO Detection**: Tự động phát hiện và tách câu hỏi, đáp án bằng AI
- **DeepSeek OCR**: Nhận diện text tiếng Việt và tiếng Anh với AI API

### 📝 Quản lý câu hỏi
- **CRUD hoàn chỉnh**: Thêm, sửa, xóa câu hỏi với ảnh đính kèm
- **Phân loại chi tiết**: Tổ chức theo môn học, chương, bài học, độ khó
- **JSON Editor**: Chỉnh sửa trực tiếp database JSON với validate
- **Export/Import**: Backup và restore dữ liệu dễ dàng

### 🖼️ Gallery hiển thị
- **Dual view**: Xem ảnh detection (có bbox) và ảnh crop riêng biệt
- **Multi-format**: Hỗ trợ hiển thị theo folder, class, timeline
- **Interactive**: Preview fullscreen, download, keyboard navigation
- **Search & Filter**: Tìm kiếm và lọc ảnh theo nhiều tiêu chí

### 🛠️ Command Line Processing
- **Standalone CLI**: Xử lý PDF/images mà không cần web server
- **Batch processing**: Xử lý nhiều file cùng lúc
- **Fixed directory structure**: Tự động tạo cấu trúc thư mục `image_0001, image_0002...`
- **Real-time monitoring**: Theo dõi tiến trình xử lý

### 🎨 Giao diện hiện đại
- **Responsive design**: Tối ưu cho desktop, tablet, mobile
- **Real-time progress**: Theo dõi tiến trình xử lý live
- **Dark mode ready**: Hỗ trợ chế độ tối
- **Touch-friendly**: Điều khiển cảm ứng cho mobile

## 🚀 Cài đặt nhanh

### Yêu cầu hệ thống
- **Python**: 3.8 trở lên
- **RAM**: 8GB+ (khuyến nghị cho YOLO)
- **GPU**: CUDA-compatible (tùy chọn, tăng tốc xử lý)
- **Storage**: 5GB+ free space
- **OS**: Windows, macOS, Linux
- **DeepSeek API Key**: Đăng ký tại [deepseek.com](https://deepseek.com)

### 1. Clone repository
```bash
git clone <repository-url>
cd pdf-processing-app
```

### 2. Tạo virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu hình API Key
Tạo file `.env` trong thư mục gốc:
```bash
# .env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**Lấy DeepSeek API Key:**
1. Truy cập [https://deepseek.com](https://deepseek.com)
2. Đăng ký tài khoản
3. Vào phần API Management
4. Tạo API Key mới
5. Copy và paste vào file `.env`

### 5. Tạo cấu trúc thư mục
```bash
mkdir -p uploads books_to_images books_detections books_cropped
```

### 6. Chạy ứng dụng

#### Web Application:
```bash
python app.py
```
Truy cập: `http://localhost:5000`

#### Command Line Processing:
```bash
# Xử lý single PDF
python run.py path/to/file.pdf

# Xử lý folder PDFs
python run.py path/to/pdf_folder/

# Xử lý single image
python run.py path/to/image.png

# Xử lý folder images
python run.py path/to/image_folder/

# Với custom output directory
python run.py input_path -o custom_output_dir

# Verbose mode để debug
python run.py input_path --verbose
```

## 📁 Cấu trúc thư mục

```
pdf-processing-app/
├── app.py                  # Flask web server
├── run.py                  # CLI processing tool
├── requirements.txt        # Dependencies
├── .env                    # API keys (tạo thủ công)
├── README.md              # Tài liệu này
│
├── modules/               # Web application modules
│   ├── __init__.py
│   ├── pdf_processor.py    # PDF → Images
│   ├── yolo_processor.py   # YOLO Detection & Crop
│   ├── ocr_processor.py    # OCR Text Recognition
│   ├── processing_manager.py # Web Orchestrator
│   └── gallery_manager.py  # Gallery Management
│
├── modules_auto_mapping/  # CLI processing modules
│   ├── __init__.py
│   ├── pdf_processor.py    # PDF conversion
│   ├── detector.py         # YOLO detection
│   ├── ocr_service.py      # DeepSeek OCR
│   ├── bbox_processor.py   # Document structure
│   ├── question_classifier.py # Question identification
│   ├── mapping_generator.py # Mapping format
│   └── utils.py           # Utilities
│
├── pipeline.py            # Main processing pipeline
│
├── templates/             # HTML Templates
│   ├── index.html         # Main page
│   ├── gallery.html       # Gallery page
│   └── login.html         # Login page
│
├── static/               # Frontend Assets
│   ├── style.css         # Main CSS
│   ├── gallery.css       # Gallery CSS
│   ├── login.css         # Login CSS
│   ├── script.js         # Main JS
│   ├── gallery.js        # Gallery JS
│   └── login.js          # Login JS
│
├── uploads/              # PDF uploads (auto-created)
├── books_to_images/      # PDF → Images (auto-created)
├── books_detections/     # Images with bboxes (auto-created)
├── books_cropped/        # Cropped images (auto-created)
│   └── <book_name>/      # Each book folder
│       ├── image_0001/   # Fixed directory structure
│       │   ├── bbox_001_question_cls0.png
│       │   ├── bbox_002_answer_cls1.png
│       │   └── text.txt  # OCR results
│       ├── image_0002/
│       ├── mapping.json  # Question database
│       └── folder_processing_summary.json
│
└── cropped/              # Default book (legacy)
    └── mapping.json      # Default database
```

## 🎯 Hướng dẫn sử dụng

### 🖥️ Command Line Processing (Khuyên dùng)

CLI tool `run.py` cung cấp xử lý standalone mạnh mẽ với cấu trúc thư mục cố định.

#### Xử lý PDF:
```bash
# Single PDF
python run.py document.pdf
# → Tạo: books_to_images/document/ và books_cropped/document/

# Folder chứa nhiều PDFs
python run.py pdf_folder/
# → Xử lý tất cả PDFs trong folder

# Custom output
python run.py document.pdf -o my_results/
```

#### Xử lý Images:
```bash
# Single image
python run.py image.png
# → Tạo: books_cropped/image_0001/

# Folder images
python run.py images_folder/
# → Xử lý tất cả images, tạo image_0001/, image_0002/...
```

#### Options:
```bash
python run.py --help

# Verbose debugging
python run.py input.pdf --verbose

# Custom DPI for PDF conversion
python run.py input.pdf --dpi 300

# Custom worker threads
python run.py input.pdf --workers 4

# Custom directories
python run.py input.pdf --images-dir converted_images/ -o final_results/
```

#### Output Structure:
```
books_cropped/document_name/
├── image_0001/
│   ├── bbox_001_question_cls0.png    # Cropped question
│   ├── bbox_002_answer_cls1.png      # Cropped answer
│   ├── bbox_003_other_cls2.png       # Other elements
│   └── text.txt                      # OCR text content
├── image_0002/
│   └── ...
├── mapping.json                      # Auto-generated questions
└── folder_processing_summary.json   # Processing statistics
```

### 📤 Web Interface

#### Upload và xử lý PDF:

1. **Truy cập trang chính**: `http://localhost:5000`

2. **Click "📤 Upload PDF"** trên header

3. **Upload file**:
   - Chọn file PDF (tối đa 100MB)
   - Nhập tên sách (chỉ chữ cái, số, `_`, `-`)
   - Click "Bắt đầu xử lý"

4. **Theo dõi tiến trình**:
   - 📄 **PDF → Images**: Chuyển đổi thành ảnh 300 DPI
   - 🤖 **YOLO Detection**: Phát hiện câu hỏi/đáp án
   - 🔍 **DeepSeek OCR**: Nhận diện text từ ảnh

5. **Hoàn thành**: Sách mới sẽ xuất hiện trong dropdown

#### Quản lý câu hỏi:

**Thêm câu hỏi mới:**
1. **Chọn sách** từ dropdown
2. **Điền thông tin**:
   - Môn học, chương, bài học
   - Độ khó (Dễ/Trung bình/Khó)
   - Nội dung câu hỏi và đáp án
3. **Chọn folder ảnh** chứa ảnh crop
4. **Chọn ảnh**:
   - Click "Chọn ảnh Câu hỏi" (nút xanh)
   - Click vào ảnh câu hỏi
   - Click "Chọn ảnh Đáp án" (nút cam)
   - Click vào ảnh đáp án
5. **Lưu**: Click "Thêm câu hỏi"

**JSON Editor:**
1. **Click "Tải JSON"** để load dữ liệu
2. **Chỉnh sửa** trực tiếp JSON
3. **Validate**: Click "Kiểm tra JSON"
4. **Format**: Click "Format JSON" để căn chỉnh
5. **Lưu**: Click "Lưu JSON"

### 🖼️ Sử dụng Gallery

1. **Truy cập Gallery**: Click "🖼️ Gallery" hoặc `/gallery`

2. **Chọn sách** từ dropdown

3. **Chọn chế độ xem**:
   - **🎯 Detection Images**: Ảnh có bbox được vẽ
   - **✂️ Cropped Images**: Ảnh đã crop theo class
   - **📋 Cả hai**: Hiển thị đồng thời

4. **Tương tác với ảnh**:
   - **Single click**: Mở modal preview
   - **Double click**: Fullscreen lightbox
   - **Ctrl/Cmd + Click**: Quick preview

5. **Điều khiển**:
   - **Arrow keys**: Navigate qua ảnh
   - **F**: Toggle fullscreen
   - **Escape**: Đóng modal
   - **Download**: Tải ảnh về máy

## ⚙️ Cấu hình nâng cao

### Environment Variables
```bash
# .env file
DEEPSEEK_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=1
CUDA_VISIBLE_DEVICES=0  # Chọn GPU
```

### Tùy chỉnh DeepSeek OCR
```python
# modules_auto_mapping/ocr_service.py
# Thay đổi model hoặc parameters
self.api_key = os.getenv('DEEPSEEK_API_KEY')
self.model = "deepseek-chat"  # Model name
```

### Tùy chỉnh YOLO
```python
# modules_auto_mapping/detector.py
# Thay đổi confidence threshold
det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.2, device="cuda")
```

### Performance Tuning
```python
# run.py command line options
python run.py input.pdf --dpi 300 --workers 4

# app.py web server
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
```

### Authentication Setup
```python
# app.py - Default credentials
USERS = {
    'admin': {
        'password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'role': 'admin'
    },
    'user': {
        'password': hashlib.sha256('user123'.encode()).hexdigest(),
        'role': 'user'
    }
}
```

## 🔧 API Documentation

### CLI Processing (`run.py`)
```bash
# Auto-detect input type and process
python run.py input_path [options]

# Input types supported:
# - Single PDF file
# - Single image file  
# - Folder with PDFs
# - Folder with images
# - Mixed folder (PDFs + images)
```

### Web APIs

#### PDF Processing
```http
POST /upload_pdf
Content-Type: multipart/form-data

pdf_file: <file>
book_name: string
processing_mode: "complete"
```

#### Gallery APIs
```http
GET /api/gallery/books                    # Danh sách sách
GET /api/gallery/detection?book={name}    # Ảnh detection
GET /api/gallery/cropped?book={name}      # Ảnh crop
GET /api/gallery/book-info/{name}         # Thông tin sách
GET /api/gallery/debug                    # Debug info
```

#### Questions Management
```http
GET /api/questions?book={name}            # Lấy câu hỏi
POST /api/questions                       # Thêm câu hỏi
PUT /api/questions/{id}                   # Cập nhật câu hỏi
DELETE /api/questions/{id}                # Xóa câu hỏi
```

#### Authentication
```http
POST /api/login                           # Đăng nhập
POST /api/verify-token                    # Verify token
POST /api/logout                          # Đăng xuất
```

## 🐛 Troubleshooting

### Lỗi thường gặp

#### 1. Missing DeepSeek API Key
```bash
Error: DEEPSEEK_API_KEY not found in environment

# Fix: Tạo file .env với API key
echo "DEEPSEEK_API_KEY=your_key_here" > .env
```

#### 2. Module not found
```bash
# Kiểm tra virtual environment
which python
pip list

# Cài lại dependencies
pip install -r requirements.txt
```

#### 3. CUDA out of memory
```python
# Sử dụng CPU thay vì GPU trong detector.py
det_res = self.model.predict(str(image_path), device="cpu")
```

#### 4. Upload file quá lớn
```python
# Tăng limit trong app.py
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
```

#### 5. DeepSeek API quota exceeded
```bash
# Kiểm tra usage tại deepseek.com
# Hoặc switch sang OCR offline:
pip install easyocr
# Và thay đổi trong modules_auto_mapping/ocr_service.py
```

#### 6. CLI không detect được input type
```bash
# Check file extensions
ls -la input_folder/

# Force processing với verbose
python run.py input_path --verbose
```

### Debug Mode

1. **CLI Debug**:
```bash
python run.py input_path --verbose
```

2. **Web Debug**:
```python
# app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

3. **API Debug**:
```bash
# Test endpoints
curl http://localhost:5000/api/gallery/debug
curl http://localhost:5000/api/gallery/books
```

## 📊 Performance

### Benchmarks
- **PDF → Images**: ~2-5 giây/trang
- **YOLO Detection**: ~1-3 giây/ảnh (GPU)
- **DeepSeek OCR**: ~1-2 giây/crop (API call)
- **Total**: ~5-15 phút cho PDF 50 trang

### CLI vs Web Performance
- **CLI (`run.py`)**: Faster, no web overhead, batch processing
- **Web interface**: Real-time monitoring, user-friendly, concurrent uploads

### Tối ưu hóa
- **GPU**: Tăng tốc YOLO 5-10x
- **SSD**: Tăng tốc I/O 2-3x  
- **API Key tier**: DeepSeek Pro API nhanh hơn
- **Batch size**: Process multiple images concurrent

## 🔐 Security Notes

- **API Keys**: Lưu trong `.env`, không commit vào Git
- **File upload**: Chỉ chấp nhận PDF, giới hạn 100MB
- **Path traversal**: Validate tên sách với regex
- **Authentication**: JWT tokens cho web interface
- **Rate limiting**: DeepSeek API có giới hạn calls/minute

## 🤝 Contributing

1. **Fork** repository
2. **Tạo branch**: `git checkout -b feature/new-feature`
3. **Test CLI**: `python run.py test_input/`
4. **Test Web**: Start server và test UI
5. **Commit**: `git commit -m 'Add new feature'`
6. **Push**: `git push origin feature/new-feature`
7. **Pull Request**: Tạo PR với mô tả chi tiết

## 📝 License

MIT License - Xem file LICENSE để biết chi tiết

## 📞 Support

- **Issues**: Tạo issue trên GitHub
- **Documentation**: Xem README này
- **CLI Help**: `python run.py --help`
- **Web Debug**: `/api/gallery/debug`

## 🚀 Roadmap

### v2.0 (Coming Soon)
- [ ] **Multiple OCR providers**: EasyOCR, Tesseract fallback
- [ ] **Cloud deployment**: Docker, AWS/GCP support
- [ ] **Advanced PDF parsing**: Table detection, formula recognition
- [ ] **API rate limiting**: Built-in quota management
- [ ] **Webhook support**: Real-time processing notifications

### v2.1
- [ ] **Parallel processing**: Multi-GPU YOLO, concurrent OCR
- [ ] **Export formats**: Word, Excel, SCORM packages
- [ ] **Question templates**: Subject-specific templates
- [ ] **Analytics dashboard**: Processing statistics, accuracy metrics
- [ ] **Multi-language UI**: English, Vietnamese, Chinese

---

## 🎉 Quick Start Examples

### Example 1: Xử lý single PDF với CLI
```bash
# Download sample PDF
curl -o sample.pdf https://example.com/sample.pdf

# Process với CLI (khuyên dùng)
python run.py sample.pdf

# Kết quả trong books_cropped/sample/
ls books_cropped/sample/
# → image_0001/, image_0002/, mapping.json
```

### Example 2: Xử lý batch PDFs
```bash
# Tạo folder PDFs
mkdir pdf_batch/
cp *.pdf pdf_batch/

# Process tất cả PDFs
python run.py pdf_batch/ --verbose

# Check results
ls books_cropped/
# → book1/, book2/, book3/...
```

### Example 3: Web interface full workflow
```bash
# Start server
python app.py

# Login: admin/admin123
# Upload PDF → Process → View Gallery → Create Questions
```

### Example 4: API-only processing
```bash
# Get books
curl http://localhost:5000/api/gallery/books

# Get detection images
curl "http://localhost:5000/api/gallery/detection?book=sample"

# Get mapping questions
curl "http://localhost:5000/api/questions?book=sample"
```

## 🔑 DeepSeek API Setup Guide

1. **Đăng ký tài khoản**: 
   - Truy cập [https://platform.deepseek.com](https://platform.deepseek.com)
   - Đăng ký với email

2. **Tạo API Key**:
   - Vào **API Keys** section
   - Click **Create new secret key**
   - Copy key (chỉ hiển thị 1 lần)

3. **Cấu hình local**:
   ```bash
   # Tạo .env file
   echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
   
   # Hoặc set environment variable
   export DEEPSEEK_API_KEY=sk-your-key-here
   ```

4. **Test API**:
   ```bash
   python -c "
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print('API Key loaded:', bool(os.getenv('DEEPSEEK_API_KEY')))
   "
   ```

**Bắt đầu ngay!** 

```bash
git clone <repository-url>
cd pdf-processing-app
python -m venv venv
source venv/bin/activate  # hoặc venv\Scripts\activate trên Windows
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=your_key_here" > .env
python run.py sample.pdf  # CLI processing
# HOẶC
python app.py  # Web interface
```

Truy cập `http://localhost:5000` hoặc dùng CLI `python run.py --help` để bắt đầu! 🚀