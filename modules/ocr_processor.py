# modules/ocr_processor.py
import os
import easyocr
import glob
import re
from pathlib import Path

class OCRProcessor:
    def __init__(self, languages=['vi', 'en']):
        self.languages = languages
        self.reader = None
        self.reader_loaded = False
    
    def load_reader(self, status_callback=None):
        """Khởi tạo EasyOCR reader"""
        try:
            if status_callback:
                status_callback({
                    'stage': 'ocr_init',
                    'message': 'Đang khởi tạo OCR reader...'
                })
            
            self.reader = easyocr.Reader(self.languages)
            self.reader_loaded = True
            
            if status_callback:
                status_callback({
                    'message': 'OCR reader đã được khởi tạo thành công!'
                })
            
            return True, "OCR reader đã được khởi tạo thành công!"
            
        except Exception as e:
            self.reader_loaded = False
            return False, f"Lỗi khi khởi tạo OCR reader: {str(e)}"
    
    def process_directories(self, base_path, status_callback=None):
        """
        OCR tất cả ảnh cls0-cls2 trong các thư mục image_xxxx
        
        Args:
            base_path (str): Đường dẫn tới thư mục chứa các folder image_xxxx
            status_callback (function): Callback function để cập nhật trạng thái
            
        Returns:
            tuple: (success, message, info)
        """
        try:
            if status_callback:
                status_callback({
                    'stage': 'ocr',
                    'message': 'Bắt đầu quá trình OCR...'
                })
            
            # Load reader nếu chưa load
            if not self.reader_loaded:
                success, message = self.load_reader(status_callback)
                if not success:
                    return False, message, None
            
            # Tìm tất cả thư mục image_xxxx
            image_folders = self._find_image_folders(base_path)
            
            if not image_folders:
                return False, "Không tìm thấy thư mục image_xxxx nào", None
            
            total_folders = len(image_folders)
            processed_folders = 0
            
            if status_callback:
                status_callback({
                    'total_folders': total_folders,
                    'current_folder': 0,
                    'message': f'Tìm thấy {total_folders} folder để OCR'
                })
            
            ocr_results = []
            
            # Xử lý từng folder
            for i, folder_path in enumerate(image_folders):
                folder_name = os.path.basename(folder_path)
                
                if status_callback:
                    status_callback({
                        'current_folder': i + 1,
                        'message': f'Đang OCR folder {folder_name} ({i + 1}/{total_folders})'
                    })
                
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
            return False, f"Lỗi khi OCR: {str(e)}", None
    
    def _find_image_folders(self, base_path):
        """Tìm tất cả thư mục image_xxxx"""
        image_folders = []
        
        if not os.path.exists(base_path):
            return image_folders
        
        # Duyệt tất cả thư mục con
        for item in sorted(os.listdir(base_path)):
            item_path = os.path.join(base_path, item)
            
            # Kiểm tra xem có phải thư mục image_xxxx không
            if (os.path.isdir(item_path) and 
                item.startswith('image_') and 
                len(item) == 10):  # image_xxxx có độ dài 10 ký tự
                image_folders.append(item_path)
        
        return image_folders
    
    def _process_single_folder(self, folder_path):
        """OCR tất cả ảnh trong một folder"""
        try:
            folder_name = os.path.basename(folder_path)
            output_file = os.path.join(folder_path, "text.txt")
            
            processed_files = 0
            total_files = 0
            
            # Đếm tổng số file cần xử lý
            for cls_num in range(3):  # cls0, cls1, cls2
                cls_name = f"cls{cls_num}"
                pattern = os.path.join(folder_path, f"crop*_{cls_name}.png")
                total_files += len(glob.glob(pattern))
            
            # Mở file để ghi kết quả OCR
            with open(output_file, 'w', encoding='utf-8') as f:
                # Duyệt qua từng class (cls0, cls1, cls2)
                for cls_num in range(3):
                    cls_name = f"cls{cls_num}"
                    
                    # Tìm tất cả file của class này
                    pattern = os.path.join(folder_path, f"crop*_{cls_name}.png")
                    image_files = sorted(glob.glob(pattern))
                    
                    if not image_files:
                        continue
                    
                    # OCR từng file của class này
                    for image_file in image_files:
                        filename = os.path.basename(image_file)
                        
                        try:
                            # Thực hiện OCR
                            result = self.reader.readtext(image_file)
                            
                            # Ghi header cho file
                            f.write(f"=== {filename} ===\n")
                            
                            # Ghi kết quả OCR
                            if result:
                                for detection in result:
                                    text = detection[1].strip()
                                    if text:  # Chỉ ghi nếu có text
                                        # Xóa khoảng trắng thừa
                                        cleaned_text = re.sub(r'\s+', ' ', text)
                                        f.write(f"{cleaned_text}\n")
                            else:
                                f.write("(Không phát hiện text)\n")
                            
                            f.write("\n")  # Dòng trống phân cách
                            processed_files += 1
                            
                        except Exception as e:
                            f.write(f"=== {filename} ===\n")
                            f.write(f"LỖI: {str(e)}\n\n")
                            continue
            
            return {
                'folder_name': folder_name,
                'status': 'success',
                'processed_files': processed_files,
                'total_files': total_files,
                'output_file': output_file
            }
            
        except Exception as e:
            return {
                'folder_name': os.path.basename(folder_path),
                'status': 'error',
                'error': str(e)
            }
    
    def process_single_image(self, image_path):
        """
        OCR một ảnh đơn lẻ
        
        Args:
            image_path (str): Đường dẫn tới ảnh
            
        Returns:
            tuple: (success, text_result, confidence_scores)
        """
        try:
            if not self.reader_loaded:
                success, message = self.load_reader()
                if not success:
                    return False, message, None
            
            result = self.reader.readtext(image_path)
            
            if result:
                texts = []
                confidences = []
                
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
    
    def get_supported_languages(self):
        """Lấy danh sách ngôn ngữ được hỗ trợ"""
        return self.languages