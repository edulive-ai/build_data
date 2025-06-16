import os
import cv2
import json
import fitz  # PyMuPDF
import numpy as np
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

# === Cấu hình ===
IMG_PATH = "/home/batien/Desktop/build_data/toan1_tuduy_1001_images/Toán 1 Chân trời sáng tạo_page_014.png"
CROP_DIR = "crop_images1"
os.makedirs(CROP_DIR, exist_ok=True)

# === Tham số lọc ===
MIN_AREA = 130000  # 629 * 205 = 128,945
MIN_Y = 95
MAX_Y = 7950

print(f"🔧 Cấu hình lọc:")
print(f"   - Diện tích tối thiểu: {MIN_AREA:,} pixels")
print(f"   - Vùng Y hợp lệ: {MIN_Y} <= y <= {MAX_Y}")

# === Load model YOLO ===
filepath = hf_hub_download(
    repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
    filename="doclayout_yolo_docstructbench_imgsz1024.pt"
)
model = YOLOv10(filepath)

# === Dự đoán ===
det_res = model.predict(IMG_PATH, imgsz=1024, conf=0.5, device="cuda")

# === Dùng OpenCV để lấy kích thước ảnh YOLO resize (1024x...)
yolo_input = cv2.imread(IMG_PATH)
yolo_h, yolo_w = yolo_input.shape[:2]

# === Dùng fitz để đọc ảnh chất lượng cao
doc = fitz.open(IMG_PATH)
pix = doc[0].get_pixmap(dpi=300)  # ảnh gốc có thể rất lớn
fitz_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n == 4:  # nếu có alpha
    fitz_img = cv2.cvtColor(fitz_img, cv2.COLOR_RGBA2RGB)
fitz_h, fitz_w = fitz_img.shape[:2]

# === Tính hệ số scale
scale_x = fitz_w / yolo_w
scale_y = fitz_h / yolo_h

print(f"📏 Kích thước ảnh:")
print(f"   - YOLO input: {yolo_w}x{yolo_h}")
print(f"   - Ảnh gốc: {fitz_w}x{fitz_h}")
print(f"   - Scale: x={scale_x:.3f}, y={scale_y:.3f}")

# === Xử lý và lọc bbox
valid_bboxes = []
filtered_bboxes = []
valid_count = 0

for i, result in enumerate(det_res[0].boxes):
    x1, y1, x2, y2 = result.xyxy[0].tolist()
    
    # Scale về tọa độ ảnh gốc
    scaled_x1 = int(x1 * scale_x)
    scaled_y1 = int(y1 * scale_y)
    scaled_x2 = int(x2 * scale_x)
    scaled_y2 = int(y2 * scale_y)
    
    # Tính kích thước
    width = scaled_x2 - scaled_x1
    height = scaled_y2 - scaled_y1
    area = width * height
    
    bbox_info = {
        "original_index": i,
        "class_id": int(result.cls[0]),
        "confidence": float(result.conf[0]),
        "bbox": [scaled_x1, scaled_y1, scaled_x2, scaled_y2],
        "width": width,
        "height": height,
        "area": area
    }
    
    # === Kiểm tra điều kiện lọc ===
    is_valid = True
    reject_reasons = []
    
    # Kiểm tra diện tích
    if area < MIN_AREA:
        is_valid = False
        reject_reasons.append(f"diện tích nhỏ ({area:,} < {MIN_AREA:,})")
    
    # Kiểm tra vị trí Y
    if scaled_y1 < MIN_Y:
        is_valid = False
        reject_reasons.append(f"y1 quá nhỏ ({scaled_y1} < {MIN_Y})")
    
    if scaled_y1 > MAX_Y:
        is_valid = False
        reject_reasons.append(f"y1 quá lớn ({scaled_y1} > {MAX_Y})")
    
    if is_valid:
        # === Crop, làm nét và lưu bbox hợp lệ ===
        cropped = fitz_img[scaled_y1:scaled_y2, scaled_x1:scaled_x2]
        
        # Làm nét ảnh bằng kernel sharpen
        sharpen_kernel = np.array([[0, -1, 0],
                                   [-1, 5, -1],
                                   [0, -1, 0]])
        sharpened = cv2.filter2D(cropped, -1, sharpen_kernel)
        
        # Lưu với chỉ số mới (đánh số lại từ 0)
        out_path = os.path.join(CROP_DIR, f"crop_{valid_count}_cls{int(result.cls[0])}.png")
        cv2.imwrite(out_path, sharpened)
        
        bbox_info["new_index"] = valid_count
        bbox_info["output_path"] = out_path
        valid_bboxes.append(bbox_info)
        
        print(f"✅ Bbox {i} -> crop_{valid_count}: [{scaled_x1}, {scaled_y1}, {scaled_x2}, {scaled_y2}] "
              f"(W:{width}, H:{height}, Area:{area:,}) -> {out_path}")
        valid_count += 1
        
    else:
        # Bbox bị loại bỏ
        bbox_info["reject_reasons"] = reject_reasons
        filtered_bboxes.append(bbox_info)
        
        print(f"❌ Bbox {i} BỊ LOẠI: [{scaled_x1}, {scaled_y1}, {scaled_x2}, {scaled_y2}] "
              f"(W:{width}, H:{height}, Area:{area:,}) - Lý do: {', '.join(reject_reasons)}")

# === Thống kê kết quả ===
total_boxes = len(det_res[0].boxes)
print(f"\n📊 Thống kê:")
print(f"   - Tổng bbox ban đầu: {total_boxes}")
print(f"   - Bbox hợp lệ: {len(valid_bboxes)}")
print(f"   - Bbox bị loại: {len(filtered_bboxes)}")
print(f"   - Tỷ lệ giữ lại: {len(valid_bboxes)/total_boxes*100:.1f}%")

# === Lưu JSON kết quả ===
result_data = {
    "config": {
        "min_area": MIN_AREA,
        "min_y": MIN_Y,
        "max_y": MAX_Y,
        "scale_x": scale_x,
        "scale_y": scale_y
    },
    "statistics": {
        "total_boxes": total_boxes,
        "valid_boxes": len(valid_bboxes),
        "filtered_boxes": len(filtered_bboxes),
        "retention_rate": len(valid_bboxes)/total_boxes*100
    },
    "valid_bboxes": valid_bboxes,
    "filtered_bboxes": filtered_bboxes
}

with open("bounding_boxes_filtered.json", "w", encoding='utf-8') as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)

print(f"💾 Đã lưu kết quả vào: bounding_boxes_filtered.json")

# === Annotate ảnh (chỉ hiển thị bbox hợp lệ) ===
annotated = det_res[0].plot(pil=True, line_width=5, font_size=20)
cv2.imwrite("result_annotated_all.jpg", cv2.cvtColor(np.array(annotated), cv2.COLOR_RGB2BGR))

# Tạo ảnh annotate chỉ với bbox hợp lệ
yolo_img_copy = yolo_input.copy()
for bbox_info in valid_bboxes:
    # Scale ngược về tọa độ YOLO để vẽ
    x1 = int(bbox_info["bbox"][0] / scale_x)
    y1 = int(bbox_info["bbox"][1] / scale_y)
    x2 = int(bbox_info["bbox"][2] / scale_x)
    y2 = int(bbox_info["bbox"][3] / scale_y)
    
    # Vẽ bbox
    cv2.rectangle(yolo_img_copy, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.putText(yolo_img_copy, f"cls{bbox_info['class_id']}", 
                (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

cv2.imwrite("result_annotated_valid_only.jpg", yolo_img_copy)
print(f"🖼️  Đã lưu ảnh: result_annotated_all.jpg (tất cả bbox)")
print(f"🖼️  Đã lưu ảnh: result_annotated_valid_only.jpg (chỉ bbox hợp lệ)")

print(f"\n🎯 Hoàn thành! Đã lưu {len(valid_bboxes)} ảnh crop vào thư mục '{CROP_DIR}'")