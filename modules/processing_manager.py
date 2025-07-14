# modules/processing_manager.py
import os
import time
import logging
import traceback
import sys
from pathlib import Path
from datetime import datetime
from .pdf_processor import PDFProcessor
from .yolo_processor import YOLOProcessor
from .ocr_deepseak import OCRProcessor
# from .ocr_processor import OCRProcessor

class ProcessingManager:
    def __init__(self, debug_mode=False, log_file=None):
        """
        Khởi tạo ProcessingManager
        
        Args:
            debug_mode (bool): Bật/tắt debug mode (mặc định False để tương thích)
            log_file (str): Đường dẫn file log (optional)
        """
        
        # Thiết lập logging
        self._setup_logging(debug_mode, log_file)
        self.debug_mode = debug_mode
        
        try:
            self.logger.info("=== KHỞI TẠO PROCESSING MANAGER ===")
            
            # Khởi tạo PDFProcessor
            self.logger.info("Khởi tạo PDFProcessor...")
            self.pdf_processor = PDFProcessor()
            self.logger.info("✓ PDFProcessor OK")
            
            # Khởi tạo YOLOProcessor với fallback cho tương thích
            self.logger.info("Khởi tạo YOLOProcessor...")
            try:
                # Thử với debug_mode parameter
                self.yolo_processor = YOLOProcessor(debug_mode=debug_mode)
                self.logger.info("✓ YOLOProcessor OK (với debug support)")
            except TypeError:
                # Fallback cho version cũ
                self.yolo_processor = YOLOProcessor()
                self.logger.info("✓ YOLOProcessor OK (legacy mode)")
            
            # Khởi tạo OCRProcessor  
            self.logger.info("Khởi tạo OCRProcessor...")
            self.ocr_processor = OCRProcessor()
            self.logger.info("✓ OCRProcessor OK")
            
            self.status_data = {}
            
            self.logger.info("=== PROCESSING MANAGER KHỞI TẠO THÀNH CÔNG ===")
            
        except Exception as e:
            self.logger.error("❌ LỖI KHỞI TẠO PROCESSING MANAGER")
            self.logger.error(f"Exception: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise e
    
    def _setup_logging(self, debug_mode, log_file=None):
        """Thiết lập logging"""
        self.logger = logging.getLogger('ProcessingManager')
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (nếu có)
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.info(f"Log file: {log_file}")
            except Exception as e:
                self.logger.warning(f"Không thể tạo log file: {e}")
        
        self.logger.propagate = False
    
    def _log_exception(self, e, context=""):
        """Log exception với traceback"""
        self.logger.error(f"❌ LỖI tại {context}: {str(e)}")
        self.logger.error(f"Exception type: {type(e).__name__}")
        if self.debug_mode:
            self.logger.error("Full traceback:")
            self.logger.error(traceback.format_exc())
    
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
        start_time = time.time()
        
        try:
            self.logger.info(f"=== BẮT ĐẦU XỬ LÝ PDF: {book_name} ===")
            
            # Khởi tạo trạng thái
            self.status_data[status_id] = {
                'stage': 'starting',
                'message': 'Bắt đầu xử lý PDF...',
                'progress': 0,
                'status': 'processing',
                'start_time': start_time
            }
            
            # Tạo callback function để cập nhật trạng thái
            def update_status(data):
                try:
                    if status_id in self.status_data:
                        self.status_data[status_id].update(data)
                        if self.debug_mode and 'message' in data:
                            self.logger.debug(f"Update: {data['message']}")
                except Exception as e:
                    self.logger.error(f"Lỗi update_status: {e}")
            
            # STEP 1: Convert PDF to images
            self.logger.info("STEP 1: Convert PDF to images")
            try:
                self._update_progress(status_id, 10, 'Bắt đầu chuyển đổi PDF...')
                
                images_dir = f"books_to_images/{book_name}"
                success, message, pdf_info = self.pdf_processor.convert_to_images(
                    pdf_path, images_dir, update_status
                )
                
                if not success:
                    error_msg = f"Lỗi convert PDF: {message}"
                    self.logger.error(error_msg)
                    self._set_error(status_id, error_msg)
                    return self.status_data[status_id]
                
                self.logger.info(f"✓ PDF converted: {pdf_info.get('total_pages', 0)} pages")
                self._update_progress(status_id, 30, f"Đã convert {pdf_info.get('total_pages', 0)} trang thành ảnh")
                
            except Exception as e:
                self._log_exception(e, "PDF conversion")
                self._set_error(status_id, f"Lỗi convert PDF: {str(e)}")
                return self.status_data[status_id]
            
            # STEP 2: YOLO processing
            self.logger.info("STEP 2: YOLO processing")
            try:
                self._update_progress(status_id, 35, 'Bắt đầu YOLO detection...')
                
                success, message, yolo_info = self.yolo_processor.process_images(
                    images_dir, ".", book_name, update_status
                )
                
                if not success:
                    error_msg = f"Lỗi YOLO processing: {message}"
                    self.logger.error(error_msg)
                    self._set_error(status_id, error_msg)
                    return self.status_data[status_id]
                
                self.logger.info(f"✓ YOLO processed: {yolo_info.get('total_images', 0)} images")
                self._update_progress(status_id, 70, f"Đã xử lý {yolo_info.get('total_images', 0)} ảnh với YOLO")
                
            except Exception as e:
                self._log_exception(e, "YOLO processing")
                self._set_error(status_id, f"Lỗi YOLO processing: {str(e)}")
                return self.status_data[status_id]
            
            # STEP 3: OCR processing
            self.logger.info("STEP 3: OCR processing")
            try:
                self._update_progress(status_id, 75, 'Bắt đầu OCR...')
                
                cropped_path = f"books_cropped/{book_name}"
                success, message, ocr_info = self.ocr_processor.process_directories(
                    cropped_path, update_status
                )
                
                if not success:
                    error_msg = f"Lỗi OCR: {message}"
                    self.logger.error(error_msg)
                    self._set_error(status_id, error_msg)
                    return self.status_data[status_id]
                
                self.logger.info("✓ OCR completed")
                
            except Exception as e:
                self._log_exception(e, "OCR processing")
                self._set_error(status_id, f"Lỗi OCR: {str(e)}")
                return self.status_data[status_id]
            
            # STEP 4: Hoàn thành
            total_time = time.time() - start_time
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
            
            self.logger.info(f"=== HOÀN THÀNH: {book_name} ({total_time:.2f}s) ===")
            return self.status_data[status_id]
            
        except Exception as e:
            self._log_exception(e, "process_pdf_complete")
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
        
        start_time = time.time()
        
        try:
            self.logger.info(f"=== XỬ LÝ STEP BY STEP: {book_name} ===")
            self.logger.info(f"Steps: {steps_to_run}")
            
            self.status_data[status_id] = {
                'stage': 'starting',
                'message': 'Bắt đầu xử lý theo bước...',
                'progress': 0,
                'status': 'processing',
                'start_time': start_time,
                'steps_to_run': steps_to_run,
                'completed_steps': []
            }
            
            def update_status(data):
                try:
                    if status_id in self.status_data:
                        self.status_data[status_id].update(data)
                        if self.debug_mode and 'message' in data:
                            self.logger.debug(f"Update: {data['message']}")
                except Exception as e:
                    self.logger.error(f"Lỗi update_status: {e}")
            
            results = {}
            
            # Step 1: PDF to Images
            if 'pdf' in steps_to_run:
                self.logger.info("Executing STEP: PDF")
                try:
                    self._update_progress(status_id, 10, 'Đang chuyển đổi PDF thành ảnh...')
                    
                    images_dir = f"books_to_images/{book_name}"
                    success, message, pdf_info = self.pdf_processor.convert_to_images(
                        pdf_path, images_dir, update_status
                    )
                    
                    if not success:
                        error_msg = f"Lỗi convert PDF: {message}"
                        self.logger.error(error_msg)
                        self._set_error(status_id, error_msg)
                        return self.status_data[status_id]
                    
                    results['pdf'] = pdf_info
                    self.status_data[status_id]['completed_steps'].append('pdf')
                    self.logger.info("✓ PDF step completed")
                    self._update_progress(status_id, 33, 'Hoàn thành chuyển đổi PDF')
                    
                except Exception as e:
                    self._log_exception(e, "PDF step")
                    self._set_error(status_id, f"Lỗi PDF step: {str(e)}")
                    return self.status_data[status_id]
            
            # Step 2: YOLO Processing
            if 'yolo' in steps_to_run:
                self.logger.info("Executing STEP: YOLO")
                try:
                    self._update_progress(status_id, 35, 'Đang xử lý YOLO detection...')
                    
                    images_dir = f"books_to_images/{book_name}"
                    success, message, yolo_info = self.yolo_processor.process_images(
                        images_dir, ".", book_name, update_status
                    )
                    
                    if not success:
                        error_msg = f"Lỗi YOLO processing: {message}"
                        self.logger.error(error_msg)
                        self._set_error(status_id, error_msg)
                        return self.status_data[status_id]
                    
                    results['yolo'] = yolo_info
                    self.status_data[status_id]['completed_steps'].append('yolo')
                    self.logger.info("✓ YOLO step completed")
                    self._update_progress(status_id, 66, 'Hoàn thành YOLO detection')
                    
                except Exception as e:
                    self._log_exception(e, "YOLO step")
                    self._set_error(status_id, f"Lỗi YOLO step: {str(e)}")
                    return self.status_data[status_id]
            
            # Step 3: OCR Processing
            if 'ocr' in steps_to_run:
                self.logger.info("Executing STEP: OCR")
                try:
                    self._update_progress(status_id, 70, 'Đang thực hiện OCR...')
                    
                    cropped_path = f"books_cropped/{book_name}"
                    success, message, ocr_info = self.ocr_processor.process_directories(
                        cropped_path, update_status
                    )
                    
                    if not success:
                        error_msg = f"Lỗi OCR: {message}"
                        self.logger.error(error_msg)
                        self._set_error(status_id, error_msg)
                        return self.status_data[status_id]
                    
                    results['ocr'] = ocr_info
                    self.status_data[status_id]['completed_steps'].append('ocr')
                    self.logger.info("✓ OCR step completed")
                    self._update_progress(status_id, 100, 'Hoàn thành OCR')
                    
                except Exception as e:
                    self._log_exception(e, "OCR step")
                    self._set_error(status_id, f"Lỗi OCR step: {str(e)}")
                    return self.status_data[status_id]
            
            # Hoàn thành
            total_time = time.time() - start_time
            self.status_data[status_id].update({
                'status': 'completed',
                'message': f'Hoàn thành các bước: {", ".join(steps_to_run)}',
                'book_name': book_name,
                'end_time': time.time(),
                'results': results
            })
            
            self.logger.info(f"=== HOÀN THÀNH STEP BY STEP: {book_name} ({total_time:.2f}s) ===")
            return self.status_data[status_id]
            
        except Exception as e:
            self._log_exception(e, "process_pdf_step_by_step")
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
        try:
            self.logger.debug(f"Validating: PDF='{pdf_path}', Book='{book_name}'")
            
            # Kiểm tra file PDF tồn tại
            if not os.path.exists(pdf_path):
                self.logger.error(f"File không tồn tại: {pdf_path}")
                return False, "File PDF không tồn tại"
            
            # Kiểm tra extension
            if not pdf_path.lower().endswith('.pdf'):
                self.logger.error(f"File không phải PDF: {pdf_path}")
                return False, "File không phải định dạng PDF"
            
            # Kiểm tra tên sách
            if not book_name or not book_name.strip():
                self.logger.error("Tên sách trống")
                return False, "Tên sách không được để trống"
            
            # Kiểm tra tên sách có ký tự đặc biệt
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', book_name):
                self.logger.error(f"Tên sách có ký tự không hợp lệ: {book_name}")
                return False, "Tên sách chỉ được chứa chữ cái, số, dấu gạch dưới và gạch ngang"
            
            # Kiểm tra kích thước file
            file_size = os.path.getsize(pdf_path)
            max_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_size:
                self.logger.error(f"File quá lớn: {file_size / 1024 / 1024:.1f}MB")
                return False, f"File PDF quá lớn (tối đa 100MB), file hiện tại: {file_size / 1024 / 1024:.1f}MB"
            
            self.logger.debug(f"✓ Validation passed - Size: {file_size / 1024 / 1024:.1f}MB")
            return True, "OK"
            
        except Exception as e:
            self.logger.error(f"Lỗi trong validate_inputs: {e}")
            return False, f"Lỗi kiểm tra inputs: {str(e)}"
    
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
        
        return summary
    
    def enable_debug_mode(self, log_file=None):
        """Bật debug mode"""
        self.debug_mode = True
        self.logger.setLevel(logging.DEBUG)
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                formatter = logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                    datefmt='%H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.info(f"Debug mode enabled. Log file: {log_file}")
            except Exception as e:
                self.logger.warning(f"Không thể tạo debug log file: {e}")
        else:
            self.logger.info("Debug mode enabled (console only)")
    
    def disable_debug_mode(self):
        """Tắt debug mode"""
        self.debug_mode = False
        self.logger.setLevel(logging.INFO)
        self.logger.info("Debug mode disabled")