# modules/ocr_processor.py
import os
import easyocr
import glob
import re
from pathlib import Path
import openai
import cv2
from dotenv import load_dotenv
from typing import List, Tuple, Dict, Any, Optional, Callable

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


class OCRProcessor:
    """OCR Processor với khả năng xử lý batch và single image"""
    
    # Constants
    DEFAULT_LANGUAGES = ['vi', 'en']
    Y_THRESHOLD = 15
    NUM_CLASSES = 3  # cls0, cls1, cls2
    IMAGE_FOLDER_PREFIX = 'image_'
    IMAGE_FOLDER_LENGTH = 10
    OUTPUT_FILENAME = 'text.txt'
    CROP_PATTERN = 'crop*_cls{}.png'
    GPT_MODEL = 'gpt-3.5-turbo'
    GPT_TEMPERATURE = 0.01
    
    def __init__(self, languages: List[str] = None):
        self.languages = languages or self.DEFAULT_LANGUAGES
        self.reader = None
        self.reader_loaded = False
    
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
    
    def sort_easyocr_results(self, results: List, y_thresh: int = None) -> str:
        """Sắp xếp kết quả OCR theo vị trí văn bản"""
        if not results:
            return ""
            
        y_thresh = y_thresh or self.Y_THRESHOLD
        lines = []
        
        # Group text by lines based on y-coordinate
        for box, text, conf in results:
            x, y = min(pt[0] for pt in box), min(pt[1] for pt in box)
            
            # Find existing line or create new one
            line_found = False
            for line in lines:
                if abs(line[0][1] - y) < y_thresh:
                    line.append((x, y, text))
                    line_found = True
                    break
            
            if not line_found:
                lines.append([(x, y, text)])
        
        # Sort lines by y-coordinate and text within lines by x-coordinate
        lines.sort(key=lambda line: min(y for _, y, _ in line))
        
        final_lines = []
        for line in lines:
            sorted_line = sorted(line, key=lambda item: item[0])
            line_text = " ".join(item[2] for item in sorted_line)
            final_lines.append(line_text)
        
        return "\n".join(final_lines)
    
    def _create_gpt_prompt(self, ocr_text: str) -> str:
        """Tạo prompt cho GPT để clean OCR text"""
        return f"""
        Văn bản sau được sinh ra từ hệ thống OCR nên có thể mắc lỗi như: sai chính tả, thiếu dấu câu, từ ngữ bị sắp xếp sai thứ tự.

        Yêu cầu của bạn là:
        - **Không** tự suy luận, không tính toán, không bổ sung nội dung.
        - Chỉ **giữ nguyên nội dung gốc** và **sửa các lỗi** như: chính tả, dấu câu, và thứ tự từ để câu trở nên **tự nhiên, đúng ngữ pháp tiếng Việt**.
        - Nếu văn bản có nhiều câu, hãy nối lại thành đoạn văn rõ ràng.

        Dưới đây là văn bản cần xử lý:

        "{ocr_text}"

        Hãy trả về **chỉ văn bản đã được chỉnh sửa**, không giải thích thêm.
        """
    
    def clean_ocr_text_with_gpt(self, ocr_raw_text: str) -> str:
        """Sử dụng GPT để clean và sửa lỗi OCR text"""
        try:
            prompt = self._create_gpt_prompt(ocr_raw_text)
            
            response = openai.ChatCompletion.create(
                model=self.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.GPT_TEMPERATURE,
            )
            
            return response.choices[0].message['content'].strip()
        
        except Exception as e:
            # Fallback to original text if GPT fails
            return ocr_raw_text
    
    def load_reader(self, status_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Khởi tạo EasyOCR reader"""
        try:
            self._update_status(status_callback, 
                              stage='ocr_init', 
                              message='Đang khởi tạo OCR reader...')
            
            self.reader = easyocr.Reader(self.languages)
            self.reader_loaded = True
            
            success_msg = 'OCR reader đã được khởi tạo thành công!'
            self._update_status(status_callback, message=success_msg)
            
            return True, success_msg
            
        except Exception as e:
            self.reader_loaded = False
            return self._handle_error('khởi tạo OCR reader', e, status_callback)
    
    def _ensure_reader_loaded(self, status_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Đảm bảo OCR reader đã được load"""
        if not self.reader_loaded:
            return self.load_reader(status_callback)
        return True, "Reader đã sẵn sàng"
    
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
        """Xử lý OCR cho một file ảnh"""
        filename = os.path.basename(image_path)
        result = {
            'filename': filename,
            'success': False,
            'raw_text': '',
            'cleaned_text': '',
            'error': None
        }
        
        try:
            # Thực hiện OCR
            ocr_result = self.reader.readtext(image_path)
            raw_text = self.sort_easyocr_results(ocr_result)
            cleaned_text = self.clean_ocr_text_with_gpt(raw_text)
            
            result.update({
                'success': True,
                'raw_text': raw_text,
                'cleaned_text': cleaned_text
            })
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _write_ocr_result_to_file(self, file_handle, result: Dict[str, Any]) -> None:
    # Header với tên file
        file_handle.write("=" * 80 + "\n")
        file_handle.write(f"FILE: {result['filename']}\n")
        file_handle.write("=" * 80 + "\n\n")
        
        if result['success']:
            # Phần Raw Text (Sorted)
            file_handle.write("📝 RAW TEXT (SORTED OCR RESULTS):\n")
            file_handle.write("-" * 50 + "\n")
            file_handle.write(result['raw_text'])
            file_handle.write("\n\n")
            
            # Phần Cleaned Text
            file_handle.write("✨ CLEANED TEXT (GPT PROCESSED):\n") 
            file_handle.write("-" * 50 + "\n")
            file_handle.write(result['cleaned_text'])
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
                              message='Bắt đầu quá trình OCR...')
            
            # Ensure reader is loaded
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
        """OCR một ảnh đơn lẻ"""
        try:
            success, message = self._ensure_reader_loaded()
            if not success:
                return False, message, None
            
            result = self.reader.readtext(image_path)
            
            if result:
                texts, confidences = [], []
                
                for detection in result:
                    text = detection[1].strip()
                    confidence = detection[2]
                    
                    if text:  # Chỉ lấy text không rỗng
                        cleaned_text = re.sub(r'\s+', ' ', text)
                        texts.append(cleaned_text)
                        confidences.append(confidence)
                
                return True, texts, confidences
            else:
                return True, [], []
                
        except Exception as e:
            return False, f"Lỗi khi OCR ảnh: {str(e)}", None