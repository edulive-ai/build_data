import fitz  # PyMuPDF
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Tuple

# Thread lock để đảm bảo thread-safe printing
print_lock = threading.Lock()

def safe_print(message):
    """Thread-safe printing"""
    with print_lock:
        print(message)

def process_single_page(args) -> Tuple[bool, str, int]:
    """
    Xử lý một trang PDF thành PNG
    
    Args:
        args: tuple chứa (pdf_file, page_num, output_dir, pdf_name, zoom_factor)
    
    Returns:
        tuple: (success, message, page_num)
    """
    pdf_file, page_num, output_dir, pdf_name, zoom_factor = args
    
    try:
        # Mở document trong thread riêng (PyMuPDF là thread-safe cho read operations)
        doc = fitz.open(pdf_file)
        page = doc[page_num]
        
        # Tạo matrix cho zoom
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        
        # Render trang thành ảnh
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Tạo tên file ảnh
        image_name = f"{pdf_name}_page_{page_num + 1:03d}.png"
        image_path = os.path.join(output_dir, image_name)
        
        # Lưu ảnh
        pix.save(image_path)
        
        # Cleanup
        pix = None
        doc.close()
        
        return True, f"✓ Đã lưu: {image_name}", page_num + 1
        
    except Exception as e:
        return False, f"❌ Lỗi trang {page_num + 1}: {str(e)}", page_num + 1

def pdf_to_png_high_quality_threaded(pdf_file, output_dir=None, max_workers=4, batch_size=10):
    """
    Convert PDF to high quality PNG images (300 DPI) using multi-threading
    
    Args:
        pdf_file (str): Path to PDF file
        output_dir (str): Output directory (default: same as PDF file)
        max_workers (int): Maximum number of worker threads
        batch_size (int): Number of pages to process in each batch
    """
    
    # Kiểm tra file PDF có tồn tại không
    if not os.path.exists(pdf_file):
        print(f"Error: File '{pdf_file}' không tồn tại!")
        return
    
    # Tạo thư mục output nếu không được chỉ định
    if output_dir is None:
        output_dir = os.path.dirname(pdf_file)
        if not output_dir:
            output_dir = "."
    
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Lấy tên file không có extension để đặt tên ảnh
    pdf_name = Path(pdf_file).stem
    
    try:
        # Mở file PDF để lấy thông tin
        doc = fitz.open(pdf_file)
        total_pages = len(doc)
        doc.close()
        
        # Tính toán zoom factor cho 300 DPI
        zoom_factor = 300 / 72
        
        print(f"Bắt đầu convert {total_pages} trang từ '{pdf_file}'...")
        print(f"Sử dụng {max_workers} threads, batch size: {batch_size}")
        
        processed_pages = 0
        successful_pages = 0
        
        # Xử lý theo batch để tránh tạo quá nhiều thread cùng lúc
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            batch_pages = list(range(batch_start, batch_end))
            
            print(f"\n📦 Xử lý batch {batch_start//batch_size + 1}: trang {batch_start + 1}-{batch_end}")
            
            # Chuẩn bị arguments cho batch hiện tại
            batch_args = [
                (pdf_file, page_num, output_dir, pdf_name, zoom_factor)
                for page_num in batch_pages
            ]
            
            # Xử lý batch với ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit tất cả tasks trong batch
                future_to_page = {
                    executor.submit(process_single_page, args): args[1] 
                    for args in batch_args
                }
                
                # Xử lý kết quả khi hoàn thành
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        success, message, page_number = future.result()
                        processed_pages += 1
                        
                        if success:
                            successful_pages += 1
                            safe_print(message)
                        else:
                            safe_print(message)
                        
                        # Hiển thị tiến độ
                        safe_print(f"📊 Tiến độ: {processed_pages}/{total_pages} trang ({(processed_pages/total_pages)*100:.1f}%)")
                        
                    except Exception as e:
                        safe_print(f"❌ Lỗi không mong muốn trang {page_num + 1}: {str(e)}")
                        processed_pages += 1
        
        print(f"\n🎉 Hoàn thành!")
        print(f"✅ Thành công: {successful_pages}/{total_pages} trang")
        print(f"📁 Ảnh được lưu tại: {os.path.abspath(output_dir)}")
        
        if successful_pages < total_pages:
            print(f"⚠️  Có {total_pages - successful_pages} trang bị lỗi")
        
    except Exception as e:
        print(f"❌ Lỗi khi convert PDF: {str(e)}")

def pdf_to_png_high_quality_simple_threaded(pdf_file, output_dir=None, max_workers=4):
    """
    Phiên bản đơn giản hơn - xử lý tất cả trang cùng lúc (phù hợp với PDF nhỏ)
    
    Args:
        pdf_file (str): Path to PDF file
        output_dir (str): Output directory
        max_workers (int): Maximum number of worker threads
    """
    
    # Kiểm tra và setup tương tự function trên
    if not os.path.exists(pdf_file):
        print(f"Error: File '{pdf_file}' không tồn tại!")
        return
    
    if output_dir is None:
        output_dir = os.path.dirname(pdf_file)
        if not output_dir:
            output_dir = "."
    
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(pdf_file).stem
    
    try:
        # Lấy thông tin PDF
        doc = fitz.open(pdf_file)
        total_pages = len(doc)
        doc.close()
        
        zoom_factor = 300 / 72
        
        print(f"Bắt đầu convert {total_pages} trang từ '{pdf_file}' với {max_workers} threads...")
        
        # Chuẩn bị arguments cho tất cả trang
        all_args = [
            (pdf_file, page_num, output_dir, pdf_name, zoom_factor)
            for page_num in range(total_pages)
        ]
        
        successful_pages = 0
        
        # Xử lý tất cả trang với ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả tasks
            future_to_page = {
                executor.submit(process_single_page, args): args[1] 
                for args in all_args
            }
            
            # Xử lý kết quả
            for future in as_completed(future_to_page):
                try:
                    success, message, page_number = future.result()
                    if success:
                        successful_pages += 1
                    safe_print(message)
                    
                except Exception as e:
                    page_num = future_to_page[future]
                    safe_print(f"❌ Lỗi trang {page_num + 1}: {str(e)}")
        
        print(f"\n🎉 Hoàn thành! Thành công: {successful_pages}/{total_pages} trang")
        print(f"📁 Ảnh được lưu tại: {os.path.abspath(output_dir)}")
        
    except Exception as e:
        print(f"❌ Lỗi khi convert PDF: {str(e)}")

def get_optimal_workers(total_pages):
    """
    Đề xuất số workers tối ưu dựa trên số trang
    """
    if total_pages <= 10:
        return 2
    elif total_pages <= 50:
        return 4
    elif total_pages <= 100:
        return 6
    else:
        return 8

def main():
    """
    Hàm chính với các tùy chọn xử lý
    """
    
    pdf_file = "pdf_books/test.pdf"
    output_dir = f"books_to_images/test"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(pdf_file):
        print(f"❌ File '{pdf_file}' không tồn tại!")
        return
    
    # Lấy thông tin PDF để đề xuất cài đặt
    try:
        doc = fitz.open(pdf_file)
        total_pages = len(doc)
        doc.close()
        
        print(f"📄 PDF có {total_pages} trang")
        
        # Đề xuất cài đặt tối ưu
        optimal_workers = get_optimal_workers(total_pages)
        print(f"💡 Đề xuất sử dụng {optimal_workers} workers")
        
        # Chọn phương thức xử lý
        if total_pages > 50:
            print("🚀 Sử dụng phương thức xử lý đơn giản...")
            pdf_to_png_high_quality_simple_threaded(pdf_file, output_dir, optimal_workers)
        else:
            print("🚀 Sử dụng phương thức xử lý theo batch...")
            batch_size = max(10, total_pages // optimal_workers)
            pdf_to_png_high_quality_threaded(pdf_file, output_dir, optimal_workers, batch_size)
            
    except Exception as e:
        print(f"❌ Lỗi khi đọc PDF: {str(e)}")

if __name__ == "__main__":
    main()