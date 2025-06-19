# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
from pathlib import Path

app = Flask(__name__, 
           template_folder='templates',    # Chỉ định thư mục templates
           static_folder='static')         # Chỉ định thư mục static

# Cấu hình đường dẫn
BOOKS_DIR = "books_cropped"  # Thư mục chứa các sách
DEFAULT_BOOK = ""  # Sách mặc định
CROPPED_DIR = DEFAULT_BOOK  # Để tương thích
JSON_FILE = os.path.join(CROPPED_DIR, "mapping.json")

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
    """Lấy danh sách các sách có sẵn"""
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
                item not in ['static', 'templates', '__pycache__', '.git'] and
                not item.startswith('.')):
                # Kiểm tra xem có chứa file mapping.json hoặc folder image_ không
                has_mapping = os.path.exists(os.path.join(item_path, 'mapping.json'))
                has_images = any(f.startswith('image_') for f in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, f)))
                if has_mapping or has_images:
                    books.append(item)
    
    return list(set(books))  # Remove duplicates

@app.route('/')
def index():
    """Trang chính hiển thị danh sách câu hỏi và form thêm mới"""
    return render_template('index.html')

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

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """API lấy danh sách câu hỏi"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    return jsonify(load_questions(book_name))

@app.route('/api/questions', methods=['POST'])
def add_question():
    """API thêm câu hỏi mới"""
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
        'book': book_name
    }
    
    # Load và thêm vào danh sách
    questions = load_questions(book_name)
    questions.append(new_question)
    save_questions(questions, book_name)
    
    return jsonify({'success': True, 'question': new_question})

@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """API cập nhật câu hỏi"""
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
                'book': book_name
            })
            save_questions(questions, book_name)
            return jsonify({'success': True, 'question': questions[i]})
    
    return jsonify({'success': False, 'error': 'Question not found'}), 404

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """API xóa câu hỏi"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    questions = load_questions(book_name)
    
    # Tìm và xóa câu hỏi
    for i, q in enumerate(questions):
        if q.get('index') == question_id:
            del questions[i]
            save_questions(questions, book_name)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Question not found'}), 404

@app.route('/api/books')
def get_books():
    """API lấy danh sách sách"""
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

@app.route('/api/json/raw', methods=['GET'])
def get_json_raw():
    """API lấy nội dung JSON thô"""
    book_name = request.args.get('book', DEFAULT_BOOK)
    try:
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

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)