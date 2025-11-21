# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect
import os
import json
import threading
import time
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Import các module xử lý
from modules.processing_manager import ProcessingManager
from modules.gallery_manager import GalleryManager

app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  # Thay đổi secret key này
app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=24)

# Cấu hình user credentials (thay thế bằng database trong production)
USERS = {
    'admin': {
        'password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'role': 'admin'
    },
    'user': {
        'password': hashlib.sha256('user123'.encode()).hexdigest(),
        'role': 'user'
    }
    # Thêm users khác ở đây
}

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check for token in header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Token format invalid'}), 401
        
        # THÊM DÒNG NÀY - Check for token in cookies
        elif 'auth_token' in request.cookies:
            token = request.cookies['auth_token']
        
        # Check for token in session
        elif 'auth_token' in request.form:
            token = request.form['auth_token']
        elif 'auth_token' in request.args:
            token = request.args['auth_token']
        
        if not token:
            return redirect('/login')
        
        try:
            # Decode token
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = payload['user']
            
            # Verify user still exists
            if current_user not in USERS:
                return redirect('/login')  # SỬA: redirect thay vì jsonify
                
        except jwt.ExpiredSignatureError:
            return redirect('/login')  # SỬA: redirect thay vì jsonify
        except jwt.InvalidTokenError:
            return redirect('/login')  # SỬA: redirect thay vì jsonify
        
        return f(current_user, *args, **kwargs)
    return decorated_function

def generate_token(username):
    """Generate JWT token for user"""
    payload = {
        'user': username,
        'role': USERS[username]['role'],
        'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA'],
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_password(username, password):
    """Verify user credentials"""
    if username not in USERS:
        return False
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return USERS[username]['password'] == password_hash

# === AUTHENTICATION ROUTES ===
@app.route('/login')
def login_page():
    """Trang đăng nhập"""
    # Kiểm tra xem đã đăng nhập chưa
    token = request.cookies.get('auth_token') or request.headers.get('Authorization')
    if token:
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            # Nếu token hợp lệ, chuyển hướng về trang chính
            return redirect('/')
        except:
            pass  # Token không hợp lệ, tiếp tục hiển thị trang login
    
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
   """API đăng nhập"""
   try:
       data = request.json
       username = data.get('username', '').strip()
       password = data.get('password', '')
       remember_me = data.get('remember_me', False)
       
       # Validate input
       if not username or not password:
           return jsonify({
               'success': False,
               'message': 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu'
           }), 400
       
       # Verify credentials
       if not verify_password(username, password):
           return jsonify({
               'success': False,
               'message': 'Tên đăng nhập hoặc mật khẩu không đúng'
           }), 401
       
       # Generate token
       token = generate_token(username)
       
       response_data = {
           'success': True,
           'message': 'Đăng nhập thành công',
           'token': token,
           'user': {
               'username': username,
               'role': USERS[username]['role']
           }
       }
       
       # Set session cookie - luôn set cookie
       response = jsonify(response_data)
       response.set_cookie('auth_token', token, 
                         max_age=int(app.config['JWT_EXPIRATION_DELTA'].total_seconds()),
                         httponly=False, secure=False)  # httponly=False để JS có thể đọc
       
       return response
       
   except Exception as e:
       return jsonify({
           'success': False,
           'message': 'Lỗi server: ' + str(e)
       }), 500

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verify JWT token"""
    try:
        token = None
        
        # Get token from various sources
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                pass
        
        if not token and 'auth_token' in request.cookies:
            token = request.cookies['auth_token']
        
        if not token:
            return jsonify({'valid': False, 'message': 'No token provided'}), 401
        
        # Decode and verify token
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        username = payload['user']
        
        # Check if user still exists
        if username not in USERS:
            return jsonify({'valid': False, 'message': 'User not found'}), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'username': username,
                'role': USERS[username]['role']
            }
        }) , 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'message': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'message': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """API đăng xuất"""
    response = jsonify({'success': True, 'message': 'Đăng xuất thành công'})
    response.set_cookie('auth_token', '', expires=0)
    return response

@app.route('/api/change-password', methods=['POST'])
@require_auth
def change_password(current_user):
    """API đổi mật khẩu"""
    try:
        data = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        # Validate input
        if not old_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập đầy đủ mật khẩu cũ và mật khẩu mới'
            }), 400
        
        if len(new_password) < 4:
            return jsonify({
                'success': False,
                'message': 'Mật khẩu mới phải có ít nhất 4 ký tự'
            }), 400
        
        # Verify old password
        if not verify_password(current_user, old_password):
            return jsonify({
                'success': False,
                'message': 'Mật khẩu cũ không đúng'
            }), 401
        
        # Update password
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        USERS[current_user]['password'] = new_password_hash
        
        return jsonify({
            'success': True,
            'message': 'Đổi mật khẩu thành công'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Lỗi server: ' + str(e)
        }), 500

# === PROTECT EXISTING ROUTES ===
# Thêm decorator @require_auth vào các routes cần bảo vệ

# Ví dụ bảo vệ trang chính:
@app.route('/')
@require_auth
def index_protected(current_user):
    """Trang chính có bảo vệ"""
    return render_template('index.html', user=current_user)

# === USER MANAGEMENT (OPTIONAL) ===
@app.route('/api/users', methods=['GET'])
@require_auth
def get_users(current_user):
    """API lấy danh sách users (chỉ admin)"""
    if USERS[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    users_list = []
    for username, user_data in USERS.items():
        users_list.append({
            'username': username,
            'role': user_data['role']
        })
    
    return jsonify(users_list)

@app.route('/api/add-user', methods=['POST'])
@require_auth
def add_user(current_user):
    """API thêm user mới (chỉ admin)"""
    if USERS[current_user]['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập đầy đủ thông tin'
            }), 400
        
        if username in USERS:
            return jsonify({
                'success': False,
                'message': 'Tên đăng nhập đã tồn tại'
            }), 400
        
        # Add new user
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        USERS[username] = {
            'password': password_hash,
            'role': role
        }
        
        return jsonify({
            'success': True,
            'message': f'Thêm user {username} thành công'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Lỗi server: ' + str(e)
        }), 500

# Cấu hình upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Tạo thư mục uploads nếu chưa tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Cấu hình đường dẫn
BOOKS_DIR = "books_cropped"
DEFAULT_BOOK = "cropped"

# Khởi tạo Managers
processing_manager = ProcessingManager()
gallery_manager = GalleryManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === UTILITY FUNCTIONS ===
def load_questions(book_name=None):
    """Load danh sách câu hỏi từ JSON file"""
    if book_name is None:
        book_name = DEFAULT_BOOK
    
    json_file = os.path.join(book_name, "mapping.json")
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_questions(questions, book_name=None):
    """Lưu danh sách câu hỏi vào JSON file"""
    if book_name is None:
        book_name = DEFAULT_BOOK
    
    os.makedirs(book_name, exist_ok=True)
    json_file = os.path.join(book_name, "mapping.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

def get_image_list(book_name=None):
    """Lấy danh sách tất cả ảnh PNG trong thư mục book"""
    if book_name is None:
        book_name = DEFAULT_BOOK
    
    images = []
    if os.path.exists(book_name):
        for folder in sorted(os.listdir(book_name)):
            folder_path = os.path.join(book_name, folder)
            if os.path.isdir(folder_path) and folder.startswith('image_'):
                for file in sorted(os.listdir(folder_path)):
                    if file.lower().endswith('.png'):
                        relative_path = os.path.join(folder, file).replace('\\', '/')
                        images.append(relative_path)
    return images

def get_next_index(book_name=None):
    """Lấy index tiếp theo cho câu hỏi mới"""
    questions = load_questions(book_name)
    if not questions:
        return 1
    return max(q.get('index', 0) for q in questions) + 1

def get_book_list():
    """Lấy danh sách các sách có sẵn cho mapping questions (không phải Gallery)"""
    books = []
    
    # Kiểm tra thư mục gốc (cropped)
    if os.path.exists(DEFAULT_BOOK):
        books.append(DEFAULT_BOOK)
    
    # Kiểm tra thư mục books
    if os.path.exists(BOOKS_DIR):
        for folder in sorted(os.listdir(BOOKS_DIR)):
            folder_path = os.path.join(BOOKS_DIR, folder)
            if os.path.isdir(folder_path):
                books.append(os.path.join(BOOKS_DIR, folder))
    
    # Tìm các thư mục khác cùng cấp với cropped
    current_dir = os.path.dirname(os.path.abspath(DEFAULT_BOOK)) if DEFAULT_BOOK != 'cropped' else '.'
    if os.path.exists(current_dir):
        for item in sorted(os.listdir(current_dir)):
            item_path = os.path.join(current_dir, item) if current_dir != '.' else item
            if (os.path.isdir(item_path) and 
                item != DEFAULT_BOOK and 
                item != BOOKS_DIR and
                item not in ['static', 'templates', '__pycache__', '.git', 'uploads', 'books_to_images', 'modules'] and
                not item.startswith('.')):
                # Kiểm tra xem có chứa file mapping.json hoặc folder image_ không
                has_mapping = os.path.exists(os.path.join(item_path, 'mapping.json'))
                has_images = any(f.startswith('image_') for f in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, f)))
                if has_mapping or has_images:
                    books.append(item)
    
    return list(set(books))  # Remove duplicates

# === BACKGROUND PROCESSING ===
def process_pdf_background(pdf_path, book_name, status_id, processing_mode='complete'):
    """
    Xử lý PDF trong background thread
    
    Args:
        pdf_path (str): Đường dẫn file PDF
        book_name (str): Tên sách
        status_id (str): ID theo dõi trạng thái
        processing_mode (str): 'complete' hoặc 'step_by_step'
    """
    try:
        if processing_mode == 'complete':
            result = processing_manager.process_pdf_complete(pdf_path, book_name, status_id)
        else:
            # Có thể mở rộng để xử lý từng bước riêng biệt
            result = processing_manager.process_pdf_complete(pdf_path, book_name, status_id)
        
        # Cleanup file upload sau khi xử lý xong
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass  # Không quan trọng nếu không xóa được
        
    except Exception as e:
        processing_manager._set_error(status_id, f"Lỗi trong background processing: {str(e)}")

# === GALLERY ROUTES ===
@app.route('/gallery')
def gallery():
    """Trang gallery để xem ảnh detection và crop"""
    return render_template('gallery.html')

@app.route('/api/gallery/books')
def get_gallery_books():
    """API lấy danh sách sách cho Gallery (riêng biệt với mapping)"""
    books = gallery_manager.get_available_books()
    return jsonify(books)

@app.route('/api/gallery/detection')
def get_detection_images():
    """API lấy danh sách ảnh detection"""
    book_name = request.args.get('book', '')
    result = gallery_manager.get_detection_images(book_name)
    return jsonify(result)

@app.route('/api/gallery/cropped')
def get_cropped_images():
    """API lấy danh sách ảnh crop"""
    book_name = request.args.get('book', '')
    result = gallery_manager.get_cropped_images(book_name)
    return jsonify(result)

@app.route('/api/gallery/book-info/<book_name>')
def get_gallery_book_info(book_name):
    """API lấy thông tin chi tiết về một sách trong Gallery"""
    info = gallery_manager.get_book_info(book_name)
    return jsonify(info)

@app.route('/api/gallery/debug')
def get_gallery_debug():
    """API debug cho Gallery"""
    debug_info = gallery_manager.get_debug_info()
    return jsonify(debug_info)

@app.route('/detection_images/<book_name>/<filename>')
def serve_detection_image(book_name, filename):
    """Serve ảnh detection"""
    detection_dir = f"books_detections/{book_name}"
    if os.path.exists(detection_dir):
        return send_from_directory(detection_dir, filename)
    else:
        return "Detection images not found", 404

# === PDF PROCESSING ROUTES ===
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    """API upload và bắt đầu xử lý PDF"""
    try:
        # Kiểm tra file upload
        if 'pdf_file' not in request.files:
            return jsonify({'success': False, 'error': 'Không có file được chọn'})
        
        file = request.files['pdf_file']
        book_name = request.form.get('book_name', '').strip()
        processing_mode = request.form.get('processing_mode', 'complete')  # complete hoặc step_by_step
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Không có file được chọn'})
        
        if not book_name:
            return jsonify({'success': False, 'error': 'Vui lòng nhập tên sách'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File không hợp lệ. Chỉ chấp nhận file PDF'})
        
        # Lưu file upload
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{book_name}_{int(time.time())}_{filename}")
        file.save(file_path)
        
        # Validate inputs
        is_valid, error_message = processing_manager.validate_inputs(file_path, book_name)
        if not is_valid:
            os.remove(file_path)  # Xóa file nếu không hợp lệ
            return jsonify({'success': False, 'error': error_message})
        
        # Tạo unique ID cho quá trình xử lý
        status_id = f"{book_name}_{int(time.time())}"
        
        # Bắt đầu xử lý trong background thread
        thread = threading.Thread(
            target=process_pdf_background,
            args=(file_path, book_name, status_id, processing_mode)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'File đã được upload và bắt đầu xử lý',
            'status_id': status_id,
            'book_name': book_name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Lỗi server: {str(e)}'})

@app.route('/processing_status/<status_id>')
def get_processing_status(status_id):
    """API lấy trạng thái xử lý"""
    status = processing_manager.get_status(status_id)
    return jsonify(status)

@app.route('/processing_summary/<status_id>')
def get_processing_summary(status_id):
    """API lấy tóm tắt kết quả xử lý"""
    summary = processing_manager.get_processing_summary(status_id)
    if summary is None:
        return jsonify({'error': 'Không tìm thấy kết quả xử lý'}), 404
    return jsonify(summary)

@app.route('/cleanup_status/<status_id>', methods=['DELETE'])
def cleanup_processing_status(status_id):
    """API xóa trạng thái xử lý sau khi hoàn thành"""
    processing_manager.cleanup_status(status_id)
    return jsonify({'success': True, 'message': 'Đã xóa trạng thái xử lý'})

@app.route('/all_processing_statuses')
def get_all_processing_statuses():
    """API lấy tất cả trạng thái đang xử lý (debug)"""
    statuses = processing_manager.get_all_statuses()
    return jsonify(statuses)

# === IMAGE SERVING ROUTES ===
@app.route('/images/<book_name>/<path:filename>')
def serve_image(book_name, filename):
    """Serve ảnh từ thư mục book cụ thể"""
    if book_name == 'cropped' or os.path.exists(book_name):
        return send_from_directory(book_name, filename)
    else:
        return "Book not found", 404

@app.route('/images/<path:filename>')
def serve_image_legacy(filename):
    """Serve ảnh từ thư mục cropped (tương thích với cách cũ)"""
    return send_from_directory(DEFAULT_BOOK, filename)

# === QUESTIONS MANAGEMENT ROUTES ===
@app.route('/api/questions', methods=['GET'])
def get_questions():
    """API lấy danh sách câu hỏi"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    return jsonify(load_questions(book_name))

@app.route('/api/questions', methods=['POST'])
def add_question():
    """API thêm câu hỏi mới"""
    try:
        data = request.json
        book_name = data.get('book', DEFAULT_BOOK)
        
        # Tạo câu hỏi mới
        new_question = {
            'index': get_next_index(book_name),
            'question': data.get('question', ''),
            'answer': data.get('answer', ''),
            'image_question': data.get('image_question', []),
            'image_answer': data.get('image_answer', []),
            'difficulty': data.get('difficulty', 'easy'),
            'chapter': data.get('chapter', ''),
            'subject': data.get('subject', ''),
            'lesson': data.get('lesson', ''),
            'page_number': data.get('page_number', 0),
            'book': book_name.removeprefix("books_cropped/")
        }
        
        # Load và thêm vào danh sách
        questions = load_questions(book_name)
        questions.append(new_question)
        save_questions(questions, book_name)
        
        return jsonify({'success': True, 'question': new_question})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """API cập nhật câu hỏi"""
    try:
        data = request.json
        book_name = data.get('book', DEFAULT_BOOK)
        questions = load_questions(book_name)
        
        # Tìm và cập nhật câu hỏi
        for i, q in enumerate(questions):
            if q.get('index') == question_id:
                questions[i].update({
                    'question': data.get('question', q.get('question', '')),
                    'answer': data.get('answer', q.get('answer', '')),
                    'image_question': data.get('image_question', q.get('image_question', [])),
                    'image_answer': data.get('image_answer', q.get('image_answer', [])),
                    'difficulty': data.get('difficulty', q.get('difficulty', 'easy')),
                    'chapter': data.get('chapter', q.get('chapter', '')),
                    'subject': data.get('subject', q.get('subject', '')),
                    'lesson': data.get('lesson', q.get('lesson', '')),
                    'page_number': data.get('page_number', q.get('page_number', 0)),
                    'book': book_name.removeprefix("books_cropped/")
                })
                save_questions(questions, book_name)
                return jsonify({'success': True, 'question': questions[i]})
        
        return jsonify({'success': False, 'error': 'Question not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """API xóa câu hỏi"""
    try:
        book_name = request.args.get('book', DEFAULT_BOOK)
        questions = load_questions(book_name)
        
        # Tìm và xóa câu hỏi
        for i, q in enumerate(questions):
            if q.get('index') == question_id:
                del questions[i]
                save_questions(questions, book_name)
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Question not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === BOOKS AND IMAGES ROUTES (cho mapping questions) ===
@app.route('/api/books')
def get_books():
    """API lấy danh sách sách cho mapping questions"""
    return jsonify(get_book_list())

@app.route('/api/images')
def get_images():
    """API lấy danh sách ảnh"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    return jsonify(get_image_list(book_name))

@app.route('/api/folders')
def get_folders():
    """API lấy danh sách folder ảnh"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    folders = []
    if os.path.exists(book_name):
        for folder in sorted(os.listdir(book_name)):
            folder_path = os.path.join(book_name, folder)
            if os.path.isdir(folder_path) and folder.startswith('image_'):
                folders.append(folder)
    return jsonify(folders)

@app.route('/api/images/<folder_name>')
def get_images_by_folder(folder_name):
    """API lấy danh sách ảnh theo folder"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    images = []
    folder_path = os.path.join(book_name, folder_name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith('.png'):
                relative_path = os.path.join(folder_name, file).replace('\\', '/')
                images.append(relative_path)
    return jsonify(images)
@app.route('/api/text/<folder_name>')
def get_text_content(folder_name):
    """API lấy nội dung file text.txt trong folder ảnh"""
    try:
        book_name = request.args.get('book', "books_cropped/cropped_hdhtoan1_q3")
        text_file_path = os.path.join(book_name, folder_name, 'text.txt')
        
        if os.path.exists(text_file_path):
            with open(text_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True, 
                'content': content,
                'folder': folder_name,
                'book': book_name.removeprefix("books_cropped/")
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'Không tìm thấy file text.txt trong folder {folder_name}',
                'folder': folder_name,
                'book': book_name.removeprefix("books_cropped/")
            })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Lỗi khi đọc file: {str(e)}'}), 500
# === JSON EDITOR ROUTES ===
@app.route('/api/json/raw', methods=['GET'])
def get_json_raw():
    """API lấy nội dung JSON thô"""
    try:
        book_name = request.args.get('book', DEFAULT_BOOK)
        json_file = os.path.join(book_name, "mapping.json")
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'success': True, 'content': content})
        else:
            return jsonify({'success': True, 'content': '[]'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/json/raw', methods=['POST'])
def update_json_raw():
    """API cập nhật nội dung JSON thô"""
    try:
        data = request.json
        content = data.get('content', '')
        book_name = data.get('book', DEFAULT_BOOK)
        
        # Validate JSON format
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'JSON không hợp lệ: {str(e)}'}), 400
        
        # Save to file
        os.makedirs(book_name, exist_ok=True)
        json_file = os.path.join(book_name, "mapping.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({'success': True, 'message': 'Cập nhật JSON thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# === ERROR HANDLERS ===
@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File quá lớn (tối đa 100MB)'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'error': 'Lỗi server internal'}), 500

if __name__ == '__main__':
    # Import và setup CORS
    from flask_cors import CORS
    CORS(app, supports_credentials=True)
    
    print("🚀 Starting PDF Processing Application...")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📚 Default book: {DEFAULT_BOOK}")
    print(f"📂 Books directory: {BOOKS_DIR}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)