# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
from pathlib import Path

app = Flask(__name__, 
           template_folder='templates',    # Chỉ định thư mục templates
           static_folder='static')         # Chỉ định thư mục static

# Cấu hình đường dẫn
CROPPED_DIR = "cropped"
JSON_FILE = os.path.join(CROPPED_DIR, "mapping.json")

def load_questions():
    """Load danh sách câu hỏi từ JSON file"""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_questions(questions):
    """Lưu danh sách câu hỏi vào JSON file"""
    os.makedirs(CROPPED_DIR, exist_ok=True)
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

def get_image_list():
    """Lấy danh sách tất cả ảnh PNG trong thư mục cropped"""
    images = []
    if os.path.exists(CROPPED_DIR):
        for folder in sorted(os.listdir(CROPPED_DIR)):
            folder_path = os.path.join(CROPPED_DIR, folder)
            if os.path.isdir(folder_path) and folder.startswith('image_'):
                for file in sorted(os.listdir(folder_path)):
                    if file.lower().endswith('.png'):
                        relative_path = os.path.join(folder, file).replace('\\', '/')
                        images.append(relative_path)
    return images

def get_next_index():
    """Lấy index tiếp theo cho câu hỏi mới"""
    questions = load_questions()
    if not questions:
        return 1
    return max(q.get('index', 0) for q in questions) + 1

@app.route('/')
def index():
    """Trang chính hiển thị danh sách câu hỏi và form thêm mới"""
    return render_template('index.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve ảnh từ thư mục cropped"""
    return send_from_directory(CROPPED_DIR, filename)

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """API lấy danh sách câu hỏi"""
    return jsonify(load_questions())

@app.route('/api/questions', methods=['POST'])
def add_question():
    """API thêm câu hỏi mới"""
    data = request.json
    
    # Tạo câu hỏi mới
    new_question = {
        'index': get_next_index(),
        'question': data.get('question', ''),
        'answer': data.get('answer', ''),
        'image_question': data.get('image_question', []),
        'image_answer': data.get('image_answer', []),
        'difficulty': data.get('difficulty', 'easy'),
        'chapter': data.get('chapter', ''),
        'subject': data.get('subject', ''),
        'lesson': data.get('lesson', '')
    }
    
    # Load và thêm vào danh sách
    questions = load_questions()
    questions.append(new_question)
    save_questions(questions)
    
    return jsonify({'success': True, 'question': new_question})

@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """API cập nhật câu hỏi"""
    data = request.json
    questions = load_questions()
    
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
                'lesson': data.get('lesson', q.get('lesson', ''))
            })
            save_questions(questions)
            return jsonify({'success': True, 'question': questions[i]})
    
    return jsonify({'success': False, 'error': 'Question not found'}), 404

@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """API xóa câu hỏi"""
    questions = load_questions()
    
    # Tìm và xóa câu hỏi
    for i, q in enumerate(questions):
        if q.get('index') == question_id:
            del questions[i]
            save_questions(questions)
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Question not found'}), 404

@app.route('/api/images')
def get_images():
    """API lấy danh sách ảnh"""
    return jsonify(get_image_list())

@app.route('/api/folders')
def get_folders():
    """API lấy danh sách folder ảnh"""
    folders = []
    if os.path.exists(CROPPED_DIR):
        for folder in sorted(os.listdir(CROPPED_DIR)):
            folder_path = os.path.join(CROPPED_DIR, folder)
            if os.path.isdir(folder_path) and folder.startswith('image_'):
                folders.append(folder)
    return jsonify(folders)

@app.route('/api/images/<folder_name>')
def get_images_by_folder(folder_name):
    """API lấy danh sách ảnh theo folder"""
    images = []
    folder_path = os.path.join(CROPPED_DIR, folder_name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith('.png'):
                relative_path = os.path.join(folder_name, file).replace('\\', '/')
                images.append(relative_path)
    return jsonify(images)

@app.route('/api/json/raw', methods=['GET'])
def get_json_raw():
    """API lấy nội dung JSON thô"""
    try:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
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
        
        # Validate JSON format
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            return jsonify({'success': False, 'error': f'JSON không hợp lệ: {str(e)}'}), 400
        
        # Save to file
        os.makedirs(CROPPED_DIR, exist_ok=True)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({'success': True, 'message': 'Cập nhật JSON thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)