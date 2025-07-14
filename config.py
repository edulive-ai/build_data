import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # YOLO Model Settings
    YOLO_REPO_ID = "juliozhao/DocLayout-YOLO-DocStructBench"
    YOLO_FILENAME = "doclayout_yolo_docstructbench_imgsz1024.pt"
    YOLO_IMAGE_SIZE = 1024
    YOLO_DEVICE = "cuda"
    
    # Detection Settings - COMPLETE VERSION
    IOU_THRESHOLD = 0.7
    CONFIDENCE_THRESHOLD = 0.2
    TARGET_CLASSES = None  # None = detect all classes, [0,1,2] = specific classes
    OCR_CLASSES = [0, 1, 2]  # Classes that need OCR processing
    
    # DeepSeek Vision API
    DEEPSEAK_API_ENDPOINT = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
    DEEPSEAK_API_KEY = os.getenv("DEEPSEAK_API_KEY")
    DEEPSEAK_MODEL = "skylark-vision-250515"
    
    # OpenAI API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = "gpt-4"
    
    # Retry Settings
    MAX_RETRIES = 5
    RETRY_DELAY = 2  # seconds
    
    # OCR Settings
    OCR_BATCH_SIZE = 5
    OCR_PROMPT = (
        "Extract the text from the following image exactly as it appears. "
        "Do not add, remove, or modify any words or characters. "
        "Preserve the original language and formatting of the text in the image."
        "If no text is found, return exactly three dots: ."
    )
    
    # Question Classification
    QUESTION_PROMPT = """
Bạn là một mô hình chuyên đánh giá nội dung trong sách bài tập, có nhiệm vụ xác định xem một đoạn văn có phải là một "câu hỏi bài tập" hay không.

Định nghĩa: 
- "Câu hỏi bài tập" là những câu có mục đích kiểm tra kiến thức, yêu cầu học sinh trả lời hoặc thực hiện hành động.
- Câu hỏi thường bắt đầu bằng từ như **"Bài", "Câu","Ví dụ" "Hãy", "Em hãy", "Tại sao", "Vì sao", "Ai", "Gì", "Tính", "Như thế nào"...**
- Câu hỏi có thể kết thúc bằng dấu **hỏi (?)**, hoặc dấu **hai chấm (:)** để liệt kê yêu cầu.
- Không coi là câu hỏi nếu:
  - Nếu không có chứ Bài, Câu ở đầu thì không được phép coi là câu hỏi
  - Đó chỉ là một biểu thức toán học, công thức, phép tính (vd: 5 + 3 = ...)
  - Kết thúc bằng dấu ba chấm (...) mang tính gợi mở hoặc bỏ lửng.
  - Không có động từ yêu cầu hành động (ví dụ: chỉ là dữ kiện hoặc đề bài phụ).

Hãy đọc đoạn văn dưới đây và **trả lời duy nhất một từ**:
- Trả lời **"YES"** nếu đây là một **câu hỏi bài tập**
- Trả lời **"NO"** nếu không phải

Đoạn văn:
\"\"\"{text}\"\"\"

Trả lời (chỉ YES hoặc NO):
"""