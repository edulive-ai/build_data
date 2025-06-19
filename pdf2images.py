import fitz  # PyMuPDF
import os
from pathlib import Path

def pdf_to_png_high_quality(pdf_file, output_dir=None):
    """
    Convert PDF to high quality PNG images (300 DPI)
    
    Args:
        pdf_file (str): Path to PDF file
        output_dir (str): Output directory (default: same as PDF file)
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
        # Mở file PDF
        doc = fitz.open(pdf_file)
        
        # Tính toán zoom factor cho 300 DPI
        # Mặc định PDF là 72 DPI, để có 300 DPI cần zoom = 300/72 ≈ 4.17
        zoom_factor = 300 / 72
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        
        # Lưu số trang trước khi bắt đầu convert
        total_pages = len(doc)
        print(f"Bắt đầu convert {total_pages} trang từ '{pdf_file}'...")
        
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
            
            print(f"✓ Đã lưu: {image_name}")
            
            # Giải phóng bộ nhớ
            pix = None
        
        # Đóng document
        doc.close()
        
        print(f"\n🎉 Hoàn thành! Đã convert {total_pages} trang thành công.")
        print(f"📁 Ảnh được lưu tại: {os.path.abspath(output_dir)}")
        
    except Exception as e:
        print(f"❌ Lỗi khi convert PDF: {str(e)}")

def main():
    """
    Hàm chính - tự động tìm file PDF trong thư mục hiện tại
    """
    
    # Tìm tất cả file PDF trong thư mục hiện tại
    pdf_file = "pdf_books/30_de_thi.pdf"
    
    # Tạo thư mục con cho ảnh
    output_dir = f"books_to_images/30-de-thi"
    
    # Convert PDF
    pdf_to_png_high_quality(pdf_file, output_dir)

if __name__ == "__main__":
    main()