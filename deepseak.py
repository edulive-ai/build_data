import requests
import base64
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- Cấu hình API ---
API_ENDPOINT = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
API_KEY = os.getenv("DEEPSEAK_API_KEY")  # **THAY THẾ BẰNG API KEY THỰC CỦA BẠN**
MODEL_NAME = "skylark-vision-250515"

# --- Cấu hình ảnh ---
# Đường dẫn đến file ảnh cục bộ của bạn
# ĐẢM BẢO FILE ẢNH NÀY TỒN TẠI TRONG CÙNG THƯ MỤC VỚI SCRIPT HOẶC CUNG CẤP ĐƯỜNG DẪN TUYỆT ĐỐI CHÍNH XÁC
IMAGE_PATH = "/home/batien/Desktop/build_data/books_cropped/test/image_0000/crop_000_cls1.png" 

# --- Hàm chuyển đổi ảnh sang Base64 ---
def image_to_base64(image_path):
    """
    Chuyển đổi một file ảnh thành chuỗi base64 với tiền tố Data URI.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File ảnh không tồn tại tại đường dẫn: {image_path}")
    
    # Xác định loại ảnh để tạo tiền tố Data URI phù hợp
    # Bạn có thể mở rộng để hỗ trợ các định dạng khác như .jpg, .jpeg
    if image_path.lower().endswith(('.png')):
        mime_type = "image/png"
    elif image_path.lower().endswith(('.jpg', '.jpeg')):
        mime_type = "image/jpeg"
    else:
        # Nếu là định dạng khác, bạn có thể cân nhắc báo lỗi hoặc chọn một mặc định
        raise ValueError("Định dạng ảnh không được hỗ trợ (chỉ .png, .jpg, .jpeg).")

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{encoded_string}"

# --- Hàm gửi yêu cầu đến API ---
def call_deepseek_vision_api(image_base64_url, prompt_text):
    """
    Gửi yêu cầu đến DeepSeek Vision API với ảnh base64 và câu hỏi.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64_url  # Sử dụng URL base64 đã tạo
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
            }
        ]
    }

    print("Đang gửi yêu cầu đến API...")
    try:
        response = requests.post(API_ENDPOINT, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Ném lỗi cho các mã trạng thái HTTP không thành công (4xx hoặc 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Phản hồi lỗi từ server: {e.response.text}")
        return None

# --- Thực thi chương trình ---
if __name__ == "__main__":
    try:
        # Bước 1: Chuyển đổi ảnh sang base64
        base64_image_url = image_to_base64(IMAGE_PATH)
        print(f"Ảnh '{IMAGE_PATH}' đã được chuyển đổi sang Base64.")

        # Bước 2: Chuẩn bị câu hỏi cho ảnh
        question = """Extract the text from the following image exactly as it appears. 
                        Do not add, remove, or modify any words or characters. 
                        Preserve the original language and formatting of the text in the image."""

        # Bước 3: Gọi API DeepSeek Vision
        api_response = call_deepseek_vision_api(base64_image_url, question)

        # Bước 4: Xử lý và in kết quả
        if api_response:
            print("\n--- Phản hồi từ DeepSeek Vision API ---")
            # In toàn bộ phản hồi để kiểm tra
            # print(json.dumps(api_response, indent=2, ensure_ascii=False))

            # Trích xuất và in nội dung phản hồi chính
            if api_response.get("choices"):
                for choice in api_response["choices"]:
                    if choice.get("message") and choice["message"].get("content"):
                        print(f"{choice['message']['content']}")
            else:
                print("Không tìm thấy nội dung phản hồi trong cấu trúc dự kiến.")
        else:
            print("Không nhận được phản hồi từ API hoặc có lỗi xảy ra.")

    except FileNotFoundError as fnf_error:
        print(f"Lỗi: {fnf_error}")
        print("Vui lòng kiểm tra lại đường dẫn file ảnh.")
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn: {e}")