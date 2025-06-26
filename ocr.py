import easyocr
import openai
import cv2
import os
from dotenv import load_dotenv

load_dotenv()

# === Cấu hình API ChatGPT ===
openai.api_key = os.getenv("OPENAI_API_KEY")  # Hoặc gán trực tiếp nếu bạn test nhanh
# openai.api_key = "sk-..."
print(openai.api_key)
# === Hàm sắp xếp kết quả OCR theo dòng ===
def sort_easyocr_results(results, y_thresh=15):
    lines = []
    for box, text, conf in results:
        x = min(pt[0] for pt in box)
        y = min(pt[1] for pt in box)
        matched = False
        for line in lines:
            if abs(line[0][1] - y) < y_thresh:
                line.append((x, y, text))
                matched = True
                break
        if not matched:
            lines.append([(x, y, text)])
    lines = sorted(lines, key=lambda l: min(y for _, y, _ in l))
    final_lines = []
    for line in lines:
        sorted_line = sorted(line, key=lambda t: t[0])
        final_lines.append(" ".join([t[2] for t in sorted_line]))
    return "\n".join(final_lines)

# === Hàm gọi ChatGPT để sửa kết quả OCR ===
def clean_ocr_text_with_gpt(ocr_raw_text):
    prompt = f"""
Văn bản sau được sinh ra từ hệ thống OCR nên có thể mắc lỗi như: sai chính tả, thiếu dấu câu, từ ngữ bị sắp xếp sai thứ tự.

Yêu cầu của bạn là:
- **Không** tự suy luận, không tính toán, không bổ sung nội dung.
- Chỉ **giữ nguyên nội dung gốc** và **sửa các lỗi** như: chính tả, dấu câu, và thứ tự từ để câu trở nên **tự nhiên, đúng ngữ pháp tiếng Việt**.
- Nếu văn bản có nhiều câu, hãy nối lại thành đoạn văn rõ ràng.

Dưới đây là văn bản cần xử lý:

"{ocr_raw_text}"

Hãy trả về **chỉ văn bản đã được chỉnh sửa**, không giải thích thêm.
"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # hoặc "gpt-3.5-turbo" nếu bạn muốn tiết kiệm
        messages=[{"role": "user", "content": prompt}],
        temperature=0.01,
    )
    return response.choices[0].message['content'].strip()

# === Đường dẫn ảnh OCR ===
IMAGE_PATH = "/home/batien/Desktop/build_data/books_cropped/cropped_hdhtoan1_q4/image_0052/crop_002_cls1.png"

# === Thực hiện OCR bằng EasyOCR ===
reader = easyocr.Reader(['vi', 'en'])
results = reader.readtext(IMAGE_PATH)

# === In kết quả gốc (thô) ===
# print("=== Kết quả OCR ban đầu (thô) ===")
# for r in results:
#     print(r[1])

# === Sắp xếp lại kết quả theo dòng (top-bottom, left-right) ===
sorted_text = sort_easyocr_results(results)
print("\n=== Văn bản sau sắp xếp ===")
print(sorted_text)

# === Gửi văn bản lên GPT để sửa lỗi và định dạng lại ===
refined_text = clean_ocr_text_with_gpt(sorted_text)
print("\n=== Văn bản sau khi GPT sửa lại ===")
print(refined_text)
