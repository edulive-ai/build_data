import os
import cv2
import json
import fitz  # PyMuPDF
import numpy as np
from pathlib import Path
from datetime import datetime
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

class YOLOBatchProcessor:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # Tạo cấu trúc thư mục đầu ra
        self.validated_dir = self.output_dir / "validated"
        self.cropped_dir = self.output_dir / "cropped"
        
        self.validated_dir.mkdir(parents=True, exist_ok=True)
        self.cropped_dir.mkdir(parents=True, exist_ok=True)
        
        # === Tham số lọc ===
        self.REFERENCE_BBOX = [2700, 4968, 3270, 5173]
        self.MIN_AREA = (self.REFERENCE_BBOX[2] - self.REFERENCE_BBOX[0]) * (self.REFERENCE_BBOX[3] - self.REFERENCE_BBOX[1])
        self.MIN_Y = 80
        self.MAX_Y = 7225
        
        # Định dạng file được hỗ trợ
        self.SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.tif', '.bmp'}
        
        # Thống kê tổng quan
        self.total_images = 0
        self.processed_images = 0
        self.failed_images = 0
        self.total_bboxes = 0
        self.total_valid_bboxes = 0
        self.processing_log = []
        
        print(f"🔧 Cấu hình xử lý:")
        print(f"   - Thư mục đầu vào: {self.input_dir}")
        print(f"   - Thư mục đầu ra: {self.output_dir}")
        print(f"   - Diện tích tối thiểu: {self.MIN_AREA:,} pixels")
        print(f"   - Vùng Y hợp lệ: {self.MIN_Y} <= y <= {self.MAX_Y}")
        print(f"   - Bbox tham chiếu: {self.REFERENCE_BBOX}")
        
    def load_model(self):
        """Load YOLO model"""
        try:
            print("🤖 Đang tải model YOLO...")
            filepath = hf_hub_download(
                repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
                filename="doclayout_yolo_docstructbench_imgsz1024.pt"
            )
            self.model = YOLOv10(filepath)
            print("✅ Model đã được tải thành công!")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi tải model: {e}")
            return False
    
    def get_image_files(self):
        """Lấy danh sách file ảnh trong thư mục"""
        image_files = []
        for file_path in self.input_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                image_files.append(file_path)
        return sorted(image_files)
    
    def process_single_image(self, image_path, image_index):
        """Xử lý một ảnh"""
        try:
            image_name = f"image_{image_index:04d}"
            print(f"\n📸 Đang xử lý: {image_path.name} -> {image_name}")
            
            # Tạo thư mục con cho ảnh crop
            crop_subdir = self.cropped_dir / image_name
            crop_subdir.mkdir(exist_ok=True)
            
            # === Dự đoán YOLO ===
            det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.5, device="cuda")
            
            if not det_res[0].boxes:
                print(f"⚠️  Không phát hiện bbox nào trong {image_path.name}")
                return self._create_empty_result(image_path, image_name)
            
            # === Xử lý ảnh gốc ===
            if image_path.suffix.lower() == '.pdf':
                doc = fitz.open(str(image_path))
                pix = doc[0].get_pixmap(dpi=300)
                fitz_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    fitz_img = cv2.cvtColor(fitz_img, cv2.COLOR_RGBA2RGB)
                doc.close()
            else:
                fitz_img = cv2.imread(str(image_path))
                if fitz_img is None:
                    raise ValueError(f"Không thể đọc ảnh: {image_path}")
                fitz_img = cv2.cvtColor(fitz_img, cv2.COLOR_BGR2RGB)
            
            fitz_h, fitz_w = fitz_img.shape[:2]
            
            # === Ảnh YOLO input để tính scale ===
            yolo_input = cv2.imread(str(image_path))
            if yolo_input is None:
                # Fallback cho PDF
                yolo_input = cv2.cvtColor(fitz_img, cv2.COLOR_RGB2BGR)
            
            yolo_h, yolo_w = yolo_input.shape[:2]
            scale_x = fitz_w / yolo_w
            scale_y = fitz_h / yolo_h
            
            print(f"   📏 Kích thước: YOLO {yolo_w}x{yolo_h} -> Gốc {fitz_w}x{fitz_h} (scale: {scale_x:.3f}, {scale_y:.3f})")
            
            # === Xử lý và lọc bbox ===
            valid_bboxes = []
            filtered_bboxes = []
            valid_count = 0
            
            for i, result in enumerate(det_res[0].boxes):
                bbox_result = self._process_bbox(
                    result, i, scale_x, scale_y, fitz_img, 
                    crop_subdir, valid_count, image_name
                )
                
                if bbox_result["is_valid"]:
                    valid_bboxes.append(bbox_result["bbox_info"])
                    valid_count += 1
                else:
                    filtered_bboxes.append(bbox_result["bbox_info"])
            
            # === Tạo ảnh annotated ===
            annotated_all = det_res[0].plot(pil=True, line_width=5, font_size=20)
            annotated_all_path = self.validated_dir / f"{image_name}_all_bboxes.jpg"
            cv2.imwrite(str(annotated_all_path), cv2.cvtColor(np.array(annotated_all), cv2.COLOR_RGB2BGR))
            
            # Ảnh chỉ có bbox hợp lệ
            if valid_bboxes:
                valid_annotated = self._create_valid_annotated(yolo_input, valid_bboxes, scale_x, scale_y)
                valid_annotated_path = self.validated_dir / f"{image_name}_valid_bboxes.jpg"
                cv2.imwrite(str(valid_annotated_path), valid_annotated)
            
            # === Thống kê ảnh ===
            total_boxes = len(det_res[0].boxes)
            result = {
                "image_info": {
                    "original_path": str(image_path),
                    "image_name": image_name,
                    "original_filename": image_path.name,
                    "image_size": [fitz_w, fitz_h],
                    "yolo_size": [yolo_w, yolo_h],
                    "scale": [scale_x, scale_y]
                },
                "statistics": {
                    "total_boxes": total_boxes,
                    "valid_boxes": len(valid_bboxes),
                    "filtered_boxes": len(filtered_bboxes),
                    "retention_rate": len(valid_bboxes)/total_boxes*100 if total_boxes > 0 else 0
                },
                "valid_bboxes": valid_bboxes,
                "filtered_bboxes": filtered_bboxes,
                "status": "success"
            }
            
            self.total_bboxes += total_boxes
            self.total_valid_bboxes += len(valid_bboxes)
            
            print(f"   ✅ Hoàn thành: {len(valid_bboxes)}/{total_boxes} bbox hợp lệ ({len(valid_bboxes)/total_boxes*100:.1f}%)")
            return result
            
        except Exception as e:
            error_msg = f"Lỗi xử lý {image_path.name}: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "image_info": {
                    "original_path": str(image_path),
                    "image_name": f"image_{image_index:04d}",
                    "original_filename": image_path.name,
                    "error": error_msg
                },
                "status": "failed"
            }
    
    def _process_bbox(self, result, bbox_index, scale_x, scale_y, fitz_img, crop_subdir, valid_count, image_name):
        """Xử lý một bbox"""
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
            "original_index": bbox_index,
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
        
        if area < self.MIN_AREA:
            is_valid = False
            reject_reasons.append(f"diện tích nhỏ ({area:,} < {self.MIN_AREA:,})")
        
        if scaled_y1 < self.MIN_Y:
            is_valid = False
            reject_reasons.append(f"y1 quá nhỏ ({scaled_y1} < {self.MIN_Y})")
        
        if scaled_y1 > self.MAX_Y:
            is_valid = False
            reject_reasons.append(f"y1 quá lớn ({scaled_y1} > {self.MAX_Y})")
        
        if is_valid:
            # Crop và làm nét ảnh
            cropped = fitz_img[scaled_y1:scaled_y2, scaled_x1:scaled_x2]
            
            sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharpened = cv2.filter2D(cropped, -1, sharpen_kernel)
            
            # Lưu với tên file mới
            crop_filename = f"crop_{valid_count:03d}_cls{int(result.cls[0])}.png"
            crop_path = crop_subdir / crop_filename
            cv2.imwrite(str(crop_path), cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR))
            
            bbox_info["new_index"] = valid_count
            bbox_info["crop_path"] = str(crop_path)
            bbox_info["crop_filename"] = crop_filename
            
            print(f"      ✅ Bbox {bbox_index} -> {crop_filename}: [{scaled_x1}, {scaled_y1}, {scaled_x2}, {scaled_y2}] (Area: {area:,})")
        else:
            bbox_info["reject_reasons"] = reject_reasons
            print(f"      ❌ Bbox {bbox_index} BỊ LOẠI: {', '.join(reject_reasons)}")
        
        return {
            "is_valid": is_valid,
            "bbox_info": bbox_info
        }
    
    def _create_valid_annotated(self, yolo_img, valid_bboxes, scale_x, scale_y):
        """Tạo ảnh annotated chỉ với bbox hợp lệ"""
        img_copy = yolo_img.copy()
        
        for bbox_info in valid_bboxes:
            # Scale ngược về tọa độ YOLO
            x1 = int(bbox_info["bbox"][0] / scale_x)
            y1 = int(bbox_info["bbox"][1] / scale_y)
            x2 = int(bbox_info["bbox"][2] / scale_x)
            y2 = int(bbox_info["bbox"][3] / scale_y)
            
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(img_copy, f"cls{bbox_info['class_id']}", 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return img_copy
    
    def _create_empty_result(self, image_path, image_name):
        """Tạo kết quả rỗng cho ảnh không có bbox"""
        return {
            "image_info": {
                "original_path": str(image_path),
                "image_name": image_name,
                "original_filename": image_path.name
            },
            "statistics": {
                "total_boxes": 0,
                "valid_boxes": 0,
                "filtered_boxes": 0,
                "retention_rate": 0
            },
            "valid_bboxes": [],
            "filtered_bboxes": [],
            "status": "no_detection"
        }
    
    def process_batch(self):
        """Xử lý tất cả ảnh trong thư mục"""
        # Load model
        if not self.load_model():
            return False
        
        # Lấy danh sách file ảnh
        image_files = self.get_image_files()
        self.total_images = len(image_files)
        
        if self.total_images == 0:
            print("❌ Không tìm thấy file ảnh nào trong thư mục!")
            return False
        
        print(f"\n🚀 Bắt đầu xử lý {self.total_images} ảnh...")
        
        # Xử lý từng ảnh
        all_results = []
        
        for i, image_path in enumerate(image_files):
            result = self.process_single_image(image_path, i)
            all_results.append(result)
            
            if result["status"] == "success":
                self.processed_images += 1
            else:
                self.failed_images += 1
        
        # === Lưu kết quả tổng hợp ===
        self._save_batch_results(all_results)
        
        # === Thống kê cuối cùng ===
        self._print_final_statistics()
        
        return True
    
    def _save_batch_results(self, all_results):
        """Lưu kết quả tổng hợp"""
        batch_result = {
            "config": {
                "input_directory": str(self.input_dir),
                "output_directory": str(self.output_dir),
                "reference_bbox": self.REFERENCE_BBOX,
                "min_area": self.MIN_AREA,
                "min_y": self.MIN_Y,
                "max_y": self.MAX_Y,
                "supported_formats": list(self.SUPPORTED_FORMATS),
                "processing_time": datetime.now().isoformat()
            },
            "batch_statistics": {
                "total_images": self.total_images,
                "processed_images": self.processed_images,
                "failed_images": self.failed_images,
                "success_rate": self.processed_images/self.total_images*100 if self.total_images > 0 else 0,
                "total_bboxes": self.total_bboxes,
                "total_valid_bboxes": self.total_valid_bboxes,
                "overall_retention_rate": self.total_valid_bboxes/self.total_bboxes*100 if self.total_bboxes > 0 else 0
            },
            "results": all_results
        }
        
        # Lưu JSON tổng hợp
        batch_json_path = self.validated_dir / "batch_results.json"
        with open(batch_json_path, "w", encoding='utf-8') as f:
            json.dump(batch_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Đã lưu kết quả tổng hợp: {batch_json_path}")
    
    def _print_final_statistics(self):
        """In thống kê cuối cùng"""
        print(f"\n" + "="*60)
        print(f"🎯 HOÀN THÀNH XỬ LÝ BATCH")
        print(f"="*60)
        print(f"📊 Thống kê tổng quan:")
        print(f"   - Tổng số ảnh: {self.total_images}")
        print(f"   - Ảnh xử lý thành công: {self.processed_images}")
        print(f"   - Ảnh bị lỗi: {self.failed_images}")
        print(f"   - Tỷ lệ thành công: {self.processed_images/self.total_images*100:.1f}%")
        print(f"   - Tổng bbox phát hiện: {self.total_bboxes:,}")
        print(f"   - Tổng bbox hợp lệ: {self.total_valid_bboxes:,}")
        if self.total_bboxes > 0:
            print(f"   - Tỷ lệ bbox giữ lại: {self.total_valid_bboxes/self.total_bboxes*100:.1f}%")
        
        print(f"\n📁 Kết quả đầu ra:")
        print(f"   - Ảnh annotated: {self.validated_dir}")
        print(f"   - Ảnh crop: {self.cropped_dir}")
        print(f"   - JSON tổng hợp: {self.validated_dir}/batch_results.json")


def main():
    # === Cấu hình đường dẫn ===
    INPUT_DIR = "/home/batien/Desktop/build_data/images"  # Thay đổi đường dẫn này
    OUTPUT_DIR = "/home/batien/Desktop/1001_qa_toan1"  # Thay đổi đường dẫn này
    
    # Tạo processor và chạy
    processor = YOLOBatchProcessor(INPUT_DIR, OUTPUT_DIR)
    processor.process_batch()


if __name__ == "__main__":
    main()