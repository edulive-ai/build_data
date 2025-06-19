# modules/pdf_processor.py
import fitz  # PyMuPDF
import os
from pathlib import Path

class PDFProcessor:
    def __init__(self):
        self.dpi = 300
        
    def convert_to_images(self, pdf_file, output_dir, status_callback=None):
        """
        Convert PDF to high quality PNG images
        
        Args:
            pdf_file (str): Path to PDF file
            output_dir (str): Output directory
            status_callback (function): Callback function to update status
        
        Returns:
            tuple: (success, message, info)
        """
        try:
            if status_callback:
                status_callback({
                    'stage': 'pdf_convert',
                    'message': 'Đang chuyển đổi PDF thành ảnh...'
                })
            
            # Tạo thư mục output
            os.makedirs(output_dir, exist_ok=True)
            
            # Lấy tên file để đặt tên ảnh
            pdf_name = Path(pdf_file).stem
            
            # Mở file PDF
            doc = fitz.open(pdf_file)
            
            # Tính zoom factor cho DPI mong muốn
            zoom_factor = self.dpi / 72
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            
            total_pages = len(doc)
            converted_images = []
            
            if status_callback:
                status_callback({
                    'total_pages': total_pages,
                    'current_page': 0
                })
            
            # Convert từng trang
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Render trang thành ảnh với chất lượng cao
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Tạo tên file ảnh
                image_name = f"{pdf_name}_page_{page_num + 1:03d}.png"
                image_path = os.path.join(output_dir, image_name)
                
                # Lưu ảnh
                pix.save(image_path)
                converted_images.append(image_path)
                
                if status_callback:
                    status_callback({
                        'current_page': page_num + 1,
                        'message': f'Đã chuyển đổi {page_num + 1}/{total_pages} trang'
                    })
                
                # Giải phóng bộ nhớ
                pix = None
            
            # Đóng document
            doc.close()
            
            return True, f"Đã chuyển đổi {total_pages} trang thành công", {
                'total_pages': total_pages,
                'output_dir': output_dir,
                'converted_images': converted_images
            }
            
        except Exception as e:
            return False, f"Lỗi khi chuyển đổi PDF: {str(e)}", None
    
    def get_pdf_info(self, pdf_file):
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
                'file_size': os.path.getsize(pdf_file)
            }
            doc.close()
            return info
        except Exception as e:
            return {'error': str(e)}