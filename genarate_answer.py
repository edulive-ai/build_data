import openai
import base64
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Hàm mã hoá ảnh base64 ===
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# === Hàm gọi GPT: Có thể dùng ảnh hoặc chỉ dùng câu hỏi ===
def generate_answer(question_text: str, image_path: str = None) -> str:
    print("📤 Đang gửi yêu cầu tới GPT...")
    messages = [
        {
            "role": "system",
            "content": "Bạn là một giáo viên Toán tiểu học, hãy trả lời ngắn gọn, chính xác. Không giải thích, chỉ nêu đáp án."
        }
    ]

    user_content = []

    if image_path and Path(image_path).exists():
        base64_image = encode_image(image_path)
        user_content.append({"type": "text", "text": "Hãy đọc nội dung sau và điền đáp án vào chỗ trống:"})
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        })

    # Luôn gửi thêm câu hỏi văn bản nếu có
    if question_text:
        user_content.append({"type": "text", "text": f"Câu hỏi: {question_text}"})

    messages.append({
        "role": "user",
        "content": user_content
    })

    # Gọi API
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=100,
        temperature=0.3,
    )

    answer = response.choices[0].message['content'].strip()
    return answer

# === Xử lý dict đầu vào ===
def process_question_entry(entry: dict, base_dir: str) -> dict:
    question_text = entry.get("question", "").strip()
    image_path = None

    if entry.get("image_question"):
        image_rel_path = entry["image_question"][0]
        # Loại bỏ 'books_cropped' khỏi entry["book"] nếu có
        book_path = entry["book"]
        if book_path.startswith("books_cropped/"):
            book_path = book_path[len("books_cropped/"):]  # Bỏ phần 'books_cropped/'
        full_path = os.path.join(base_dir, book_path, image_rel_path)
        if Path(full_path).exists():
            image_path = full_path
        else:
            print(f"⚠️ Ảnh không tồn tại: {full_path}. Sẽ chỉ dùng câu hỏi văn bản.")

    if not question_text and not image_path:
        print("❌ Không có dữ liệu để gửi GPT.")
        return entry

    answer = generate_answer(question_text, image_path)
    entry["answer"] = answer
    print(f"✅ Đáp án GPT tạo: {answer}")
    return entry

# === Xử lý toàn bộ file JSON ===
def process_json_file(input_json_path: str, output_json_path: str, base_dir: str) -> None:
    # Đọc file JSON đầu vào
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File JSON không tồn tại: {input_json_path}")
        return
    except json.JSONDecodeError:
        print(f"❌ Lỗi định dạng JSON trong file: {input_json_path}")
        return

    # Kiểm tra xem data có phải là danh sách
    if not isinstance(data, list):
        print("❌ File JSON phải chứa một danh sách các câu hỏi.")
        return

    # Xử lý từng entry
    updated_data = []
    for entry in data:
        updated_entry = process_question_entry(entry, base_dir)
        updated_data.append(updated_entry)

    # Lưu kết quả ra file JSON mới
    try:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu kết quả vào: {output_json_path}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file JSON: {e}")

# === MAIN TEST ===
if __name__ == "__main__":
    BASE_IMAGE_FOLDER = "books_cropped"  # Thư mục chứa các ảnh
    INPUT_JSON_PATH = "books_cropped/30-de-thi-toan1/mapping.json"  # File JSON đầu vào
    OUTPUT_JSON_PATH = "books_cropped/30-de-thi-toan1/mapping_answer.json"  # File JSON đầu ra

    process_json_file(INPUT_JSON_PATH, OUTPUT_JSON_PATH, BASE_IMAGE_FOLDER)