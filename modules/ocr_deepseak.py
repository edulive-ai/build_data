# modules/ocr_processor.py
import os
import glob
import re
import json
import base64
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Tuple, Dict, Any, Optional, Callable

load_dotenv()


class OCRProcessor:
    """OCR Processor sử dụng DeepSeek Vision API"""
    
    # Constants
    NUM_CLASSES = 3  # cls0, cls1, cls2
    IMAGE_FOLDER_PREFIX = 'image_'
    IMAGE_FOLDER_LENGTH = 10
    OUTPUT_FILENAME = 'text.txt'
    CROP_PATTERN = 'crop*_cls{}.png'
    
    # DeepSeek API Configuration
    DEEPSEEK_API_ENDPOINT = "https://ark.ap-southeast.bytepluses.com/api/v3/chat/completions"
    DEEPSEEK_MODEL_NAME = "skylark-vision-250515"
    DEEPSEEK_API_KEY = os.getenv("DEEPSEAK_API_KEY")
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        self.api_key = self.DEEPSEEK_API_KEY
        
        if not self.api_key:
            raise ValueError("DEEPSEAK_API_KEY không được tìm thấy trong biến môi trường")
    
    def _update_status(self, callback: Optional[Callable], **kwargs) -> None:
        """Helper method để update status qua callback"""
        if callback:
            callback(kwargs)
    
    def _handle_error(self, operation: str, error: Exception, 
                     callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Centralized error handling"""
        error_msg = f"Lỗi khi {operation}: {str(error)}"
        self._update_status(callback, stage='error', message=error_msg)
        return False, error_msg
    
    def _image_to_base64(self, image_path: str) -> str:
        """Chuyển đổi ảnh thành base64 string với Data URI"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File ảnh không tồn tại: {image_path}")
        
        # Xác định MIME type
        if image_path.lower().endswith('.png'):
            mime_type = "image/png"
        elif image_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = "image/jpeg"
        else:
            raise ValueError("Định dạng ảnh không được hỗ trợ (chỉ .png, .jpg, .jpeg)")
        
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        return f"data:{mime_type};base64,{encoded_string}"
    
    def _create_deepseek_prompt(self) -> str:
        """Tạo prompt cho DeepSeek Vision API - giống file thứ 2"""
        return """Extract the text from the following image exactly as it appears. 
                        Do not add, remove, or modify any words or characters. 
                        Preserve the original language and formatting of the text in the image."""
    
    def _call_deepseek_vision_api_with_retry(self, image_base64_url: str, prompt_text: str) -> Optional[str]:
        """Gọi DeepSeek Vision API với retry logic"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.DEEPSEEK_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_base64_url
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
        
        last_error = None
        
        # Retry logic - thử tối đa 3 lần
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                response = requests.post(
                    self.DEEPSEEK_API_ENDPOINT, 
                    headers=headers, 
                    data=json.dumps(payload),
                    timeout=30
                )
                response.raise_for_status()
                
                api_response = response.json()
                
                if api_response.get("choices"):
                    for choice in api_response["choices"]:
                        if choice.get("message") and choice["message"].get("content"):
                            return choice["message"]["content"].strip()
                
                # Nếu không có content, coi như lỗi và retry
                last_error = "Không nhận được nội dung từ API"
                
            except requests.exceptions.RequestException as e:
                last_error = f"Lỗi khi gọi DeepSeek API (lần {attempt + 1}): {e}"
                print(last_error)
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Phản hồi lỗi từ server: {e.response.text}")
                    
            except Exception as e:
                last_error = f"Lỗi không mong muốn (lần {attempt + 1}): {e}"
                print(last_error)
            
            # Nếu không phải lần cuối, chờ trước khi retry
            if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                print(f"Đang thử lại sau {self.RETRY_DELAY} giây...")
                time.sleep(self.RETRY_DELAY)
        
        print(f"Đã thử {self.MAX_RETRY_ATTEMPTS} lần nhưng vẫn thất bại. Lỗi cuối: {last_error}")
        return None
    
    def load_reader(self, status_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Kiểm tra kết nối API DeepSeek"""
        try:
            self._update_status(status_callback, 
                              stage='ocr_init', 
                              message='Đang kiểm tra kết nối DeepSeek API...')
            
            # Kiểm tra API key
            if not self.api_key:
                return False, "API key DeepSeek không được cấu hình"
            
            success_msg = 'DeepSeek Vision API đã sẵn sàng!'
            self._update_status(status_callback, message=success_msg)
            
            return True, success_msg
            
        except Exception as e:
            return self._handle_error('kiểm tra API DeepSeek', e, status_callback)
    
    def _ensure_reader_loaded(self, status_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Đảm bảo API đã sẵn sàng"""
        return self.load_reader(status_callback)
    
    def _find_image_folders(self, base_path: str) -> List[str]:
        """Tìm tất cả thư mục image_xxxx"""
        if not os.path.exists(base_path):
            return []
        
        image_folders = []
        for item in sorted(os.listdir(base_path)):
            item_path = os.path.join(base_path, item)
            
            if (os.path.isdir(item_path) and 
                item.startswith(self.IMAGE_FOLDER_PREFIX) and 
                len(item) == self.IMAGE_FOLDER_LENGTH):
                image_folders.append(item_path)
        
        return image_folders
    
    def _count_images_in_folder(self, folder_path: str) -> int:
        """Đếm tổng số ảnh cần xử lý trong folder"""
        total = 0
        for cls_num in range(self.NUM_CLASSES):
            pattern = os.path.join(folder_path, self.CROP_PATTERN.format(cls_num))
            total += len(glob.glob(pattern))
        return total
    
    def _get_class_images(self, folder_path: str, cls_num: int) -> List[str]:
        """Lấy danh sách ảnh của một class cụ thể"""
        pattern = os.path.join(folder_path, self.CROP_PATTERN.format(cls_num))
        return sorted(glob.glob(pattern))
    
    def _process_single_image_file(self, image_path: str) -> Dict[str, Any]:
        """Xử lý OCR cho một file ảnh bằng DeepSeek Vision API"""
        filename = os.path.basename(image_path)
        result = {
            'filename': filename,
            'success': False,
            'text': '',
            'error': None
        }
        
        try:
            # Chuyển ảnh sang base64
            base64_image = self._image_to_base64(image_path)
            
            # Tạo prompt
            prompt = self._create_deepseek_prompt()
            
            # Gọi DeepSeek API với retry
            api_result = self._call_deepseek_vision_api_with_retry(base64_image, prompt)
            
            if api_result:
                result.update({
                    'success': True,
                    'text': api_result
                })
            else:
                result['error'] = "Không nhận được phản hồi từ DeepSeek API sau 3 lần thử"
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _write_ocr_result_to_file(self, file_handle, result: Dict[str, Any]) -> None:
        """Ghi kết quả OCR vào file - chỉ DeepSeek Vision API result"""
        # Header với tên file
        file_handle.write("=" * 30 + "\n")
        file_handle.write(f"FILE: {result['filename']}\n")
        file_handle.write("=" * 30 + "\n\n")
        
        if result['success']:
            # Chỉ có một phần: kết quả từ DeepSeek Vision API
            file_handle.write(result['text'])
            file_handle.write("\n\n")
        else:
            # Ghi lỗi nếu có
            file_handle.write("❌ ERROR:\n")
            file_handle.write("-" * 30 + "\n")
            file_handle.write(f"Lỗi: {result['error']}")
            file_handle.write("\n\n")
    
    def _process_single_folder(self, folder_path: str) -> Dict[str, Any]:
        """OCR tất cả ảnh trong một folder"""
        folder_name = os.path.basename(folder_path)
        result = {
            'folder_name': folder_name,
            'status': 'success',
            'processed_files': 0,
            'total_files': 0,
            'output_file': None,
            'error': None
        }
        
        try:
            output_file = os.path.join(folder_path, self.OUTPUT_FILENAME)
            result['output_file'] = output_file
            result['total_files'] = self._count_images_in_folder(folder_path)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Xử lý từng class
                for cls_num in range(self.NUM_CLASSES):
                    image_files = self._get_class_images(folder_path, cls_num)
                    
                    for image_file in image_files:
                        ocr_result = self._process_single_image_file(image_file)
                        self._write_ocr_result_to_file(f, ocr_result)
                        
                        if ocr_result['success']:
                            result['processed_files'] += 1
            
        except Exception as e:
            result.update({
                'status': 'error',
                'error': str(e)
            })
        
        return result
    
    def process_directories(self, base_path: str, 
                          status_callback: Optional[Callable] = None) -> Tuple[bool, str, Optional[Dict]]:
        """OCR tất cả ảnh cls0-cls2 trong các thư mục image_xxxx"""
        try:
            self._update_status(status_callback, 
                              stage='ocr', 
                              message='Bắt đầu quá trình OCR bằng DeepSeek Vision API...')
            
            # Ensure API is ready
            success, message = self._ensure_reader_loaded(status_callback)
            if not success:
                return False, message, None
            
            # Find image folders
            image_folders = self._find_image_folders(base_path)
            if not image_folders:
                return False, "Không tìm thấy thư mục image_xxxx nào", None
            
            total_folders = len(image_folders)
            self._update_status(status_callback,
                              total_folders=total_folders,
                              current_folder=0,
                              message=f'Tìm thấy {total_folders} folder để OCR')
            
            # Process folders
            ocr_results = []
            processed_folders = 0
            
            for i, folder_path in enumerate(image_folders):
                folder_name = os.path.basename(folder_path)
                
                self._update_status(status_callback,
                                  current_folder=i + 1,
                                  message=f'Đang OCR folder {folder_name} ({i + 1}/{total_folders})')
                
                result = self._process_single_folder(folder_path)
                ocr_results.append(result)
                
                if result['status'] == 'success':
                    processed_folders += 1
            
            return True, f"Đã OCR {processed_folders}/{total_folders} folder thành công", {
                'total_folders': total_folders,
                'processed_folders': processed_folders,
                'results': ocr_results
            }
            
        except Exception as e:
            return self._handle_error('OCR directories', e, status_callback) + (None,)
    
    def process_single_image(self, image_path: str) -> Tuple[bool, Any, Optional[List[float]]]:
        """OCR một ảnh đơn lẻ bằng DeepSeek Vision API"""
        try:
            success, message = self._ensure_reader_loaded()
            if not success:
                return False, message, None
            
            # Chuyển ảnh sang base64
            base64_image = self._image_to_base64(image_path)
            
            # Tạo prompt
            prompt = self._create_deepseek_prompt()
            
            # Gọi DeepSeek API với retry
            api_result = self._call_deepseek_vision_api_with_retry(base64_image, prompt)
            
            if api_result:
                # Tách text thành các dòng và loại bỏ dòng trống
                texts = [line.strip() for line in api_result.split('\n') if line.strip()]
                
                # DeepSeek không trả về confidence score, tạo mock scores
                confidences = [0.95] * len(texts)  # Mock confidence score
                
                return True, texts, confidences
            else:
                return False, "Không nhận được phản hồi từ DeepSeek API sau 3 lần thử", None
                
        except Exception as e:
            return False, f"Lỗi khi OCR ảnh: {str(e)}", None