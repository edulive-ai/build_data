# modules/processing_manager.py
import os
import time
from pathlib import Path
from .pdf_processor import PDFProcessor
from .yolo_processor import YOLOProcessor
from .ocr_processor import OCRProcessor

class ProcessingManager:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.yolo_processor = YOLOProcessor()
        self.ocr_processor = OCRProcessor()
        self.status_data = {}
    
    def process_pdf_complete(self, pdf_path, book_name, status_id):
        """
        Xử lý hoàn chỉnh một file PDF qua tất cả các bước:
        1. Convert PDF to images
        2. YOLO detection và crop
        3. OCR
        
        Args:
            pdf_path (str): Đường dẫn tới file PDF
            book_name (str): Tên sách (dùng làm tên thư mục)
            status_id (str): ID để theo dõi trạng thái
            
        Returns:
            dict: Kết quả xử lý
        """
        try:
            # Khởi tạo trạng thái
            self.status_data[status_id] = {
                'stage': 'starting',
                'message': 'Bắt đầu xử lý PDF...',
                'progress': 0,
                'status': 'processing',
                'start_time': time.time()
            }
            
            # Tạo callback function để cập nhật trạng thái
            def update_status(data):
                if status_id in self.status_data:
                    self.status_data[status_id].update(data)
            
            # STEP 1: Convert PDF to images
            self._update_progress(status_id, 10, 'Bắt đầu chuyển đổi PDF...')
            
            images_dir = f"books_to_images/{book_name}"
            success, message, pdf_info = self.pdf_processor.convert_to_images(
                pdf_path, images_dir, update_status
            )
            
            if not success:
                self._set_error(status_id, f"Lỗi convert PDF: {message}")
                return self.status_data[status_id]
            
            self._update_progress(status_id, 30, f"Đã convert {pdf_info['total_pages']} trang thành ảnh")
            
            # STEP 2: YOLO processing
            self._update_progress(status_id, 35, 'Bắt đầu YOLO detection...')
            
            success, message, yolo_info = self.yolo_processor.process_images(
                images_dir, ".", book_name, update_status
            )
            
            if not success:
                self._set_error(status_id, f"Lỗi YOLO processing: {message}")
                return self.status_data[status_id]
            
            self._update_progress(status_id, 70, f"Đã xử lý {yolo_info['total_images']} ảnh với YOLO")
            
            # STEP 3: OCR processing
            self._update_progress(status_id, 75, 'Bắt đầu OCR...')
            
            cropped_path = f"books_cropped/{book_name}"
            success, message, ocr_info = self.ocr_processor.process_directories(
                cropped_path, update_status
            )
            
            if not success:
                self._set_error(status_id, f"Lỗi OCR: {message}")
                return self.status_data[status_id]
            
            # STEP 4: Hoàn thành
            self._update_progress(status_id, 100, 'Hoàn thành tất cả các bước!')
            
            self.status_data[status_id].update({
                'status': 'completed',
                'message': 'Hoàn thành xử lý PDF!',
                'book_name': book_name,
                'end_time': time.time(),
                'results': {
                    'pdf_info': pdf_info,
                    'yolo_info': yolo_info,
                    'ocr_info': ocr_info
                }
            })
            
            return self.status_data[status_id]
            
        except Exception as e:
            self._set_error(status_id, f"Lỗi không xác định: {str(e)}")
            return self.status_data[status_id]
    
    def process_pdf_step_by_step(self, pdf_path, book_name, status_id, steps_to_run=None):
        """
        Xử lý PDF theo từng bước riêng biệt
        
        Args:
            pdf_path (str): Đường dẫn tới file PDF
            book_name (str): Tên sách
            status_id (str): ID theo dõi trạng thái
            steps_to_run (list): Danh sách bước cần chạy ['pdf', 'yolo', 'ocr']
        """
        if steps_to_run is None:
            steps_to_run = ['pdf', 'yolo', 'ocr']
        
        try:
            self.status_data[status_id] = {
                'stage': 'starting',
                'message': 'Bắt đầu xử lý theo bước...',
                'progress': 0,
                'status': 'processing',
                'start_time': time.time(),
                'steps_to_run': steps_to_run,
                'completed_steps': []
            }
            
            def update_status(data):
                if status_id in self.status_data:
                    self.status_data[status_id].update(data)
            
            results = {}
            
            # Step 1: PDF to Images
            if 'pdf' in steps_to_run:
                self._update_progress(status_id, 10, 'Đang chuyển đổi PDF thành ảnh...')
                
                images_dir = f"books_to_images/{book_name}"
                success, message, pdf_info = self.pdf_processor.convert_to_images(
                    pdf_path, images_dir, update_status
                )
                
                if not success:
                    self._set_error(status_id, f"Lỗi convert PDF: {message}")
                    return self.status_data[status_id]
                
                results['pdf'] = pdf_info
                self.status_data[status_id]['completed_steps'].append('pdf')
                self._update_progress(status_id, 33, 'Hoàn thành chuyển đổi PDF')
            
            # Step 2: YOLO Processing
            if 'yolo' in steps_to_run:
                self._update_progress(status_id, 35, 'Đang xử lý YOLO detection...')
                
                images_dir = f"books_to_images/{book_name}"
                success, message, yolo_info = self.yolo_processor.process_images(
                    images_dir, ".", book_name, update_status
                )
                
                if not success:
                    self._set_error(status_id, f"Lỗi YOLO processing: {message}")
                    return self.status_data[status_id]
                
                results['yolo'] = yolo_info
                self.status_data[status_id]['completed_steps'].append('yolo')
                self._update_progress(status_id, 66, 'Hoàn thành YOLO detection')
            
            # Step 3: OCR Processing
            if 'ocr' in steps_to_run:
                self._update_progress(status_id, 70, 'Đang thực hiện OCR...')
                
                cropped_path = f"books_cropped/{book_name}"
                success, message, ocr_info = self.ocr_processor.process_directories(
                    cropped_path, update_status
                )
                
                if not success:
                    self._set_error(status_id, f"Lỗi OCR: {message}")
                    return self.status_data[status_id]
                
                results['ocr'] = ocr_info
                self.status_data[status_id]['completed_steps'].append('ocr')
                self._update_progress(status_id, 100, 'Hoàn thành OCR')
            
            # Hoàn thành
            self.status_data[status_id].update({
                'status': 'completed',
                'message': f'Hoàn thành các bước: {", ".join(steps_to_run)}',
                'book_name': book_name,
                'end_time': time.time(),
                'results': results
            })
            
            return self.status_data[status_id]
            
        except Exception as e:
            self._set_error(status_id, f"Lỗi không xác định: {str(e)}")
            return self.status_data[status_id]
    
    def get_status(self, status_id):
        """Lấy trạng thái xử lý"""
        return self.status_data.get(status_id, {
            'status': 'not_found',
            'message': 'Không tìm thấy tiến trình xử lý'
        })
    
    def cleanup_status(self, status_id):
        """Xóa trạng thái sau khi hoàn thành"""
        if status_id in self.status_data:
            del self.status_data[status_id]
    
    def get_all_statuses(self):
        """Lấy tất cả trạng thái đang xử lý"""
        return self.status_data
    
    def _update_progress(self, status_id, progress, message):
        """Cập nhật tiến trình"""
        if status_id in self.status_data:
            self.status_data[status_id].update({
                'progress': progress,
                'message': message
            })
    
    def _set_error(self, status_id, error_message):
        """Đặt trạng thái lỗi"""
        if status_id in self.status_data:
            self.status_data[status_id].update({
                'status': 'error',
                'message': error_message,
                'end_time': time.time()
            })
    
    def validate_inputs(self, pdf_path, book_name):
        """
        Kiểm tra tính hợp lệ của inputs
        
        Args:
            pdf_path (str): Đường dẫn file PDF
            book_name (str): Tên sách
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Kiểm tra file PDF tồn tại
        if not os.path.exists(pdf_path):
            return False, "File PDF không tồn tại"
        
        # Kiểm tra extension
        if not pdf_path.lower().endswith('.pdf'):
            return False, "File không phải định dạng PDF"
        
        # Kiểm tra tên sách
        if not book_name or not book_name.strip():
            return False, "Tên sách không được để trống"
        
        # Kiểm tra tên sách có ký tự đặc biệt
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', book_name):
            return False, "Tên sách chỉ được chứa chữ cái, số, dấu gạch dưới và gạch ngang"
        
        # Kiểm tra kích thước file
        file_size = os.path.getsize(pdf_path)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return False, f"File PDF quá lớn (tối đa 100MB), file hiện tại: {file_size / 1024 / 1024:.1f}MB"
        
        return True, "OK"
    
    def get_processing_summary(self, status_id):
        """
        Lấy tóm tắt kết quả xử lý
        
        Args:
            status_id (str): ID trạng thái
            
        Returns:
            dict: Tóm tắt kết quả
        """
        if status_id not in self.status_data:
            return None
        
        status = self.status_data[status_id]
        
        if status['status'] != 'completed':
            return {
                'status': status['status'],
                'message': status.get('message', ''),
                'progress': status.get('progress', 0)
            }
        
        summary = {
            'status': 'completed',
            'book_name': status.get('book_name'),
            'processing_time': status.get('end_time', 0) - status.get('start_time', 0),
            'results': {}
        }
        
        results = status.get('results', {})
        
        # PDF processing summary
        if 'pdf_info' in results:
            pdf_info = results['pdf_info']
            summary['results']['pdf'] = {
                'total_pages': pdf_info.get('total_pages', 0),
                'output_dir': pdf_info.get('output_dir', ''),
                'status': 'success'
            }
        
        # YOLO processing summary
        if 'yolo_info' in results:
            yolo_info = results['yolo_info']
            summary['results']['yolo'] = {
                'total_images': yolo_info.get('total_images', 0),
                'output_dir': yolo_info.get('output_dir', ''),
                'status': 'success'
            }
        
        # OCR processing summary
        if 'ocr_info' in results:
            ocr_info = results['ocr_info']
            summary['results']['ocr'] = {
                'total_folders': ocr_info.get('total_folders', 0),
                'processed_folders': ocr_info.get('processed_folders', 0),
                'status': 'success'
            }
        
        return summary