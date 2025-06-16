import os
import easyocr
from pathlib import Path
import glob
import re

def ocr_images_in_directories():
    """
    OCR tất cả ảnh cls0-cls2 trong các thư mục image_xxxx
    và lưu kết quả vào file text.txt trong mỗi thư mục
    """
    # Khởi tạo EasyOCR reader
    reader = easyocr.Reader(['vi', 'en'])

    # Đường dẫn gốc
    base_path = "/home/batien/Desktop/build_data/output/cropped"

    # Duyệt các thư mục image_xxxx
    folder_index = 5
    consecutive_missing = 0  # Đếm số thư mục liền nhau không tồn tại
    max_consecutive_missing = 5  # Dừng khi không tìm thấy 5 thư mục liền nhau

    while consecutive_missing < max_consecutive_missing:
        # Tạo tên thư mục với format image_xxxx (4 chữ số, có dấu gạch dưới)
        folder_name = f"image_{folder_index:04d}"
        folder_path = os.path.join(base_path, folder_name)

        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(folder_path):
            consecutive_missing += 1
            print(f"Không tìm thấy thư mục {folder_name}. ({consecutive_missing}/{max_consecutive_missing})")
            folder_index += 1
            continue

        # Reset đếm khi tìm thấy thư mục
        consecutive_missing = 0

        print(f"Đang xử lý thư mục: {folder_name}")

        # Tạo file output
        output_file = os.path.join(folder_path, "text.txt")

        # Mở file để ghi (ghi đè nếu đã tồn tại)
        with open(output_file, 'w', encoding='utf-8') as f:
            # Duyệt qua từng class (cls0, cls1, cls2)
            for cls_num in range(3):  # cls0, cls1, cls2
                cls_name = f"cls{cls_num}"

                # Tìm tất cả file của class này
                pattern = os.path.join(folder_path, f"crop*_{cls_name}.png")
                image_files = sorted(glob.glob(pattern))

                if not image_files:
                    print(f"  Không tìm thấy file nào cho {cls_name} trong {folder_name}")
                    continue

                print(f"  Tìm thấy {len(image_files)} file cho {cls_name}")

                # OCR từng file của class này
                for image_file in image_files:
                    filename = os.path.basename(image_file)
                    print(f"    Đang OCR: {filename}")

                    try:
                        # Thực hiện OCR
                        result = reader.readtext(image_file)

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

                    except Exception as e:
                        print(f"    Lỗi khi OCR {filename}: {str(e)}")
                        f.write(f"=== {filename} ===\n")
                        f.write(f"LỖI: {str(e)}\n\n")
                        continue

        print(f"  Đã lưu kết quả vào: {output_file}")
        folder_index += 1

    print(f"Kết thúc quá trình sau khi không tìm thấy {max_consecutive_missing} thư mục liền nhau.")
    print("Hoàn thành quá trình OCR!")

if __name__ == "__main__":
    ocr_images_in_directories()