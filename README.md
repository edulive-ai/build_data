# 📚 PDF Processing Application - Hệ thống Xử lý PDF và Quản lý Câu hỏi

Ứng dụng web tự động xử lý file PDF thành câu hỏi và đáp án sử dụng YOLO Detection và OCR, kết hợp với giao diện quản lý câu hỏi và gallery xem ảnh.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3+-green)
![YOLO](https://img.shields.io/badge/YOLO-v10-red)
![OCR](https://img.shields.io/badge/OCR-EasyOCR-orange)

## 🎯 Tính năng chính

### 🔄 Xử lý PDF tự động
- **Upload PDF**: Upload file PDF trực tiếp qua web interface
- **Convert cao cấp**: Chuyển PDF thành ảnh 300 DPI chất lượng cao
- **YOLO Detection**: Tự động phát hiện và tách câu hỏi, đáp án bằng AI
- **OCR thông minh**: Nhận diện text tiếng Việt và tiếng Anh từ ảnh

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

### 4. Tạo cấu trúc thư mục
```bash
mkdir -p uploads books_to_images books_detections books_cropped
```

### 5. Chạy ứng dụng
```bash
python app.py
```

Truy cập: `http://localhost:5000`

## 📁 Cấu trúc thư mục

```
pdf-processing-app/
├── app.py                  # File chính Flask
├── requirements.txt        # Dependencies
├── README.md              # Tài liệu này
│
├── modules/               # Các module xử lý
│   ├── __init__.py
│   ├── pdf_processor.py    # Xử lý PDF → Images
│   ├── yolo_processor.py   # YOLO Detection & Crop
│   ├── ocr_processor.py    # OCR Text Recognition
│   ├── processing_manager.py # Orchestrator
│   └── gallery_manager.py  # Gallery Management
│
├── templates/             # HTML Templates
│   ├── index.html         # Trang chính
│   └── gallery.html       # Trang Gallery
│
├── static/               # Frontend Assets
│   ├── style.css         # CSS chính
│   ├── gallery.css       # CSS Gallery
│   ├── script.js         # JS trang chính
│   └── gallery.js        # JS Gallery
│
├── uploads/              # File PDF upload (tự tạo)
├── books_to_images/      # Ảnh từ PDF (tự tạo)
├── books_detections/     # Ảnh có bbox (tự tạo)
├── books_cropped/        # Ảnh đã crop (tự tạo)
│
└── cropped/              # Sách mặc định (legacy)
    └── mapping.json      # Database câu hỏi
```

## 🎯 Hướng dẫn sử dụng

### 📤 Upload và xử lý PDF

1. **Truy cập trang chính**: `http://localhost:5000`

2. **Click "📤 Upload PDF"** trên header

3. **Upload file**:
   - Chọn file PDF (tối đa 100MB)
   - Nhập tên sách (chỉ chữ cái, số, `_`, `-`)
   - Click "Bắt đầu xử lý"

4. **Theo dõi tiến trình**:
   - 📄 **PDF → Images**: Chuyển đổi thành ảnh 300 DPI
   - 🤖 **YOLO Detection**: Phát hiện câu hỏi/đáp án
   - 🔍 **OCR**: Nhận diện text từ ảnh

5. **Hoàn thành**: Sách mới sẽ xuất hiện trong dropdown

### 📝 Quản lý câu hỏi

#### Thêm câu hỏi mới:
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

#### Chỉnh sửa câu hỏi:
1. **Click "Sửa"** ở câu hỏi muốn chỉnh sửa
2. **Thay đổi** thông tin trong modal
3. **Lưu**: Click "Cập nhật"

#### JSON Editor:
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

6. **Tìm kiếm**: Dùng search box để lọc theo tên file

## ⚙️ Cấu hình nâng cao

### Environment Variables
```bash
# Tùy chọn
export FLASK_ENV=development
export FLASK_DEBUG=1
export CUDA_VISIBLE_DEVICES=0  # Chọn GPU
```

### Tùy chỉnh YOLO
```python
# modules/yolo_processor.py
# Thay đổi confidence threshold
det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.2, device="cuda")
```

### Tùy chỉnh OCR
```python
# modules/ocr_processor.py
# Thêm ngôn ngữ
self.reader = easyocr.Reader(['vi', 'en', 'zh'])
```

### Performance Tuning
```python
# app.py
# Tăng file upload limit
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
```

## 🔧 API Documentation

### PDF Processing
```http
POST /upload_pdf
Content-Type: multipart/form-data

pdf_file: <file>
book_name: string
processing_mode: "complete"
```

### Gallery APIs
```http
GET /api/gallery/books                    # Danh sách sách
GET /api/gallery/detection?book={name}    # Ảnh detection
GET /api/gallery/cropped?book={name}      # Ảnh crop
GET /api/gallery/book-info/{name}         # Thông tin sách
GET /api/gallery/debug                    # Debug info
```

### Questions Management
```http
GET /api/questions?book={name}            # Lấy câu hỏi
POST /api/questions                       # Thêm câu hỏi
PUT /api/questions/{id}                   # Cập nhật câu hỏi
DELETE /api/questions/{id}                # Xóa câu hỏi
```

### Status Tracking
```http
GET /processing_status/{status_id}        # Trạng thái xử lý
GET /processing_summary/{status_id}       # Tóm tắt kết quả
DELETE /cleanup_status/{status_id}        # Cleanup
```

## 🐛 Troubleshooting

### Lỗi thường gặp

#### 1. Module not found
```bash
# Kiểm tra virtual environment
which python
pip list

# Cài lại dependencies
pip install -r requirements.txt
```

#### 2. CUDA out of memory
```python
# Sử dụng CPU thay vì GPU
det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.2, device="cpu")
```

#### 3. Upload file quá lớn
```python
# Tăng limit trong app.py
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
```

#### 4. OCR không nhận diện
- Kiểm tra chất lượng ảnh crop
- Thử điều chỉnh confidence threshold
- Kiểm tra ngôn ngữ được hỗ trợ

#### 5. Gallery không hiển thị sách
```bash
# Kiểm tra cấu trúc thư mục
ls -la books_detections/
ls -la books_cropped/

# Debug API
curl http://localhost:5000/api/gallery/debug
```

### Debug Mode

1. **Bật debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Kiểm tra API trực tiếp**:
```bash
# Test book list
curl http://localhost:5000/api/gallery/books

# Test detection images
curl "http://localhost:5000/api/gallery/detection?book=30-de-thi"
```

3. **Browser Console**: Mở F12 > Console để xem lỗi JavaScript

## 📊 Performance

### Benchmarks
- **PDF → Images**: ~2-5 giây/trang
- **YOLO Detection**: ~1-3 giây/ảnh (GPU)
- **OCR**: ~0.5-2 giây/crop (tùy kích thước)
- **Total**: ~5-15 phút cho PDF 50 trang

### Tối ưu hóa
- **GPU**: Tăng tốc YOLO 5-10x
- **SSD**: Tăng tốc I/O 2-3x
- **RAM**: 16GB+ cho PDF lớn
- **CPU**: Multi-core giúp OCR nhanh hơn

## 🔐 Security Notes

- **File upload**: Chỉ chấp nhận PDF, giới hạn 100MB
- **Path traversal**: Validate tên sách với regex
- **XSS**: Escape HTML trong JSON editor
- **CSRF**: Session-based cho production

## 🤝 Contributing

1. **Fork** repository
2. **Tạo branch**: `git checkout -b feature/new-feature`
3. **Commit**: `git commit -m 'Add new feature'`
4. **Push**: `git push origin feature/new-feature`
5. **Pull Request**: Tạo PR với mô tả chi tiết

## 📝 License

MIT License - Xem file LICENSE để biết chi tiết

## 📞 Support

- **Issues**: Tạo issue trên GitHub
- **Documentation**: Xem README này
- **Debug**: Sử dụng API `/api/gallery/debug`

## 🚀 Roadmap

### v2.0 (Coming Soon)
- [ ] **Multi-language**: Thêm hỗ trợ tiếng Trung, Nhật
- [ ] **Cloud storage**: S3, Google Drive integration
- [ ] **Advanced OCR**: Handwriting recognition
- [ ] **API Authentication**: JWT tokens
- [ ] **Batch processing**: Xử lý nhiều PDF cùng lúc

### v2.1
- [ ] **Export formats**: Word, Excel, JSON
- [ ] **Question templates**: Templates cho từng môn học
- [ ] **Statistics**: Analytics và reporting
- [ ] **Collaborative**: Multi-user editing

---

## 🎉 Bắt đầu ngay!

```bash
git clone <repository-url>
cd pdf-processing-app
python -m venv venv
source venv/bin/activate  # hoặc venv\Scripts\activate trên Windows
pip install -r requirements.txt
python app.py
```

Truy cập `http://localhost:5000` và bắt đầu xử lý PDF! 🚀