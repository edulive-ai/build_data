# modules/pdf_processor.py
import fitz  # PyMuPDF
import os
import multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
from typing import Callable, Optional, Tuple, Dict, List, Any
import time

def process_pdf_page(args):
    """
    Worker function để xử lý một trang PDF
    
    Args:
        args (tuple): (pdf_path, page_num, output_dir, pdf_name, dpi, total_pages)
    
    Returns:
        tuple: (success, page_num, image_path, error_message)
    """
    pdf_path, page_num, output_dir, pdf_name, dpi, total_pages = args
    
    try:
        # Mở document (mỗi process cần mở riêng)
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Tính zoom factor cho DPI mong muốn
        zoom_factor = dpi / 72
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        
        # Render trang thành ảnh với chất lượng cao
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Tạo tên file ảnh
        image_name = f"{pdf_name}_page_{page_num + 1:03d}.png"
        image_path = os.path.join(output_dir, image_name)
        
        # Lưu ảnh
        pix.save(image_path)
        
        # Giải phóng bộ nhớ
        pix = None
        doc.close()
        
        return True, page_num, image_path, None
        
    except Exception as e:
        return False, page_num, None, str(e)

class PDFProcessor:
    def __init__(self, max_workers: int = 8, max_memory_gb: float = 8.0):
        """
        Initialize PDF Processor with multiprocessing support
        
        Args:
            max_workers (int): Số lượng process tối đa (default: 8)
            max_memory_gb (float): Giới hạn RAM sử dụng (GB) (default: 8.0)
        """
        self.dpi = 300
        self.max_workers = max_workers
        self.max_memory_gb = max_memory_gb
        
        # Thiết lập logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _calculate_optimal_workers(self, total_pages: int) -> int:
        """
        Tính số worker tối ưu dựa trên số trang và RAM khả dụng
        
        Args:
            total_pages (int): Tổng số trang PDF
            
        Returns:
            int: Số worker tối ưu
        """
        # Ước tính RAM cần cho mỗi page (MB) - DPI 300 thường cần ~50-100MB/page
        estimated_ram_per_page = 80  # MB
        max_pages_in_memory = int((self.max_memory_gb * 1024) / estimated_ram_per_page)
        
        # Số worker không vượt quá số trang và không vượt quá khả năng RAM
        optimal_workers = min(
            self.max_workers,
            total_pages,
            max_pages_in_memory,
            mp.cpu_count()
        )
        
        return max(1, optimal_workers)
    
    def convert_to_images(self, pdf_file: str, output_dir: str, 
                         status_callback: Optional[Callable] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Convert PDF to high quality PNG images using multiprocessing
        
        Args:
            pdf_file (str): Path to PDF file
            output_dir (str): Output directory
            status_callback (function): Callback function to update status
        
        Returns:
            tuple: (success, message, info)
        """
        start_time = time.time()
        
        try:
            if status_callback:
                status_callback({
                    'stage': 'pdf_convert',
                    'message': 'Đang khởi tạo quá trình chuyển đổi PDF...'
                })
            
            # Tạo thư mục output
            os.makedirs(output_dir, exist_ok=True)
            
            # Lấy tên file để đặt tên ảnh
            pdf_name = Path(pdf_file).stem
            
            # Mở file PDF để lấy thông tin cơ bản
            doc = fitz.open(pdf_file)
            total_pages = len(doc)
            doc.close()  # Đóng ngay để tiết kiệm RAM
            
            if total_pages == 0:
                return False, "PDF không có trang nào", None
            
            # Tính số worker tối ưu
            optimal_workers = self._calculate_optimal_workers(total_pages)
            
            self.logger.info(f"Xử lý {total_pages} trang với {optimal_workers} workers")
            
            if status_callback:
                status_callback({
                    'total_pages': total_pages,
                    'current_page': 0,
                    'workers': optimal_workers,
                    'message': f'Bắt đầu xử lý với {optimal_workers} CPU cores...'
                })
            
            # Chuẩn bị arguments cho các worker
            worker_args = [
                (pdf_file, page_num, output_dir, pdf_name, self.dpi, total_pages)
                for page_num in range(total_pages)
            ]
            
            converted_images = []
            failed_pages = []
            completed_pages = 0
            
            # Sử dụng ProcessPoolExecutor để quản lý multiprocessing
            with ProcessPoolExecutor(max_workers=optimal_workers) as executor:
                # Submit tất cả tasks
                future_to_page = {
                    executor.submit(process_pdf_page, args): args[1] 
                    for args in worker_args
                }
                
                # Thu thập kết quả khi hoàn thành
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    
                    try:
                        success, returned_page_num, image_path, error_msg = future.result()
                        completed_pages += 1
                        
                        if success:
                            converted_images.append(image_path)
                        else:
                            failed_pages.append({
                                'page': returned_page_num + 1,
                                'error': error_msg
                            })
                            self.logger.error(f"Lỗi trang {returned_page_num + 1}: {error_msg}")
                        
                        # Cập nhật tiến độ
                        if status_callback:
                            progress_percent = (completed_pages / total_pages) * 100
                            status_callback({
                                'current_page': completed_pages,
                                'total_pages': total_pages,
                                'progress_percent': progress_percent,
                                'message': f'Đã xử lý {completed_pages}/{total_pages} trang ({progress_percent:.1f}%)'
                            })
                    
                    except Exception as e:
                        failed_pages.append({
                            'page': page_num + 1,
                            'error': str(e)
                        })
                        completed_pages += 1
                        self.logger.error(f"Lỗi xử lý trang {page_num + 1}: {str(e)}")
            
            # Sắp xếp lại danh sách ảnh theo thứ tự trang
            converted_images.sort()
            
            processing_time = time.time() - start_time
            success_count = len(converted_images)
            
            # Tạo thông báo kết quả
            if failed_pages:
                if success_count > 0:
                    message = f"Hoàn thành với một số lỗi: {success_count}/{total_pages} trang thành công"
                else:
                    message = f"Thất bại: Không thể chuyển đổi trang nào"
                    return False, message, {
                        'total_pages': total_pages,
                        'successful_pages': success_count,
                        'failed_pages': failed_pages,
                        'processing_time': processing_time
                    }
            else:
                message = f"Chuyển đổi thành công {total_pages} trang trong {processing_time:.2f} giây"
            
            return True, message, {
                'total_pages': total_pages,
                'successful_pages': success_count,
                'failed_pages': failed_pages,
                'output_dir': output_dir,
                'converted_images': converted_images,
                'processing_time': processing_time,
                'workers_used': optimal_workers
            }
            
        except Exception as e:
            error_msg = f"Lỗi khi chuyển đổi PDF: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def get_pdf_info(self, pdf_file: str) -> Dict[str, Any]:
        """
        Lấy thông tin cơ bản của file PDF
        
        Args:
            pdf_file (str): Path to PDF file
            
        Returns:
            dict: Thông tin PDF
        """
        try:
            doc = fitz.open(pdf_file)
            info = {
                'page_count': len(doc),
                'metadata': doc.metadata,
                'file_size': os.path.getsize(pdf_file),
                'estimated_processing_time': len(doc) * 0.5,  # Ước tính 0.5s/trang với multiprocessing
                'recommended_workers': self._calculate_optimal_workers(len(doc))
            }
            doc.close()
            return info
        except Exception as e:
            return {'error': str(e)}
    
    def set_dpi(self, dpi: int):
        """Thiết lập DPI cho ảnh output"""
        self.dpi = max(72, min(600, dpi))  # Giới hạn DPI từ 72-600
    
    def set_max_workers(self, max_workers: int):
        """Thiết lập số worker tối đa"""
        self.max_workers = max(1, min(mp.cpu_count(), max_workers))
    
    def set_max_memory(self, max_memory_gb: float):
        """Thiết lập giới hạn RAM sử dụng"""
        self.max_memory_gb = max(1.0, max_memory_gb)

# Ví dụ sử dụng
if __name__ == "__main__":
    def progress_callback(info):
        if 'progress_percent' in info:
            print(f"Tiến độ: {info['progress_percent']:.1f}% - {info['message']}")
        else:
            print(f"Trạng thái: {info['message']}")
    
    # Khởi tạo processor với 8 workers và 8GB RAM
    processor = PDFProcessor(max_workers=8, max_memory_gb=8.0)
    
    # Lấy thông tin PDF trước
    pdf_info = processor.get_pdf_info("example.pdf")
    print(f"PDF Info: {pdf_info}")
    
    # Chuyển đổi PDF
    success, message, info = processor.convert_to_images(
        pdf_file="example.pdf",
        output_dir="output_images",
        status_callback=progress_callback
    )
    
    print(f"Kết quả: {message}")
    if info:
        print(f"Chi tiết: {info}")