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
        self.all_detections_dir = self.output_dir / "books_detections/30-de-thi"
        # self.valid_detections_dir = self.output_dir / "valid_detections"
        self.cropped_dir = self.output_dir / "books_cropped/30-de-thi"
        
        self.all_detections_dir.mkdir(parents=True, exist_ok=True)
        # self.valid_detections_dir.mkdir(parents=True, exist_ok=True)
        self.cropped_dir.mkdir(parents=True, exist_ok=True)
        
        # === Không sử dụng điều kiện lọc - Lấy tất cả bbox ===
        # Đã bỏ tất cả điều kiện lọc theo yêu cầu
        
        # Định dạng file được hỗ trợ
        self.SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.pdf', '.tiff', '.tif', '.bmp'}
        
        # Thống kê tổng quan
        self.total_images = 0
        self.processed_images = 0
        self.failed_images = 0
        self.total_bboxes = 0
        self.total_valid_bboxes = 0
        
        print(f"🔧 Cấu hình xử lý:")
        print(f"   - Thư mục đầu vào: {self.input_dir}")
        print(f"   - Thư mục đầu ra: {self.output_dir}")
        print(f"   - Thư mục tất cả detections: {self.all_detections_dir}")
        # print(f"   - Thư mục valid detections: {self.valid_detections_dir}")
        print(f"   - Thư mục cropped: {self.cropped_dir}")
        print(f"   - Chế độ: Lấy TẤT CẢ bbox (không lọc)")
        
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
    
    def load_image_with_fitz(self, image_path):
        """
        Load ảnh bằng fitz (giống hệt code đơn) để đảm bảo chất lượng cao
        """
        try:
            # === Dùng fitz để đọc ảnh chất lượng cao (giống code đơn) ===
            doc = fitz.open(str(image_path))
            pix = doc[0].get_pixmap(dpi=300)  # ảnh gốc có thể rất lớn
            fitz_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:  # nếu có alpha
                fitz_img = cv2.cvtColor(fitz_img, cv2.COLOR_RGBA2RGB)
            
            fitz_h, fitz_w = fitz_img.shape[:2]
            doc.close()
            
            # === Dùng OpenCV để lấy kích thước ảnh YOLO resize (giống code đơn) ===
            yolo_input = cv2.imread(str(image_path))
            if yolo_input is None:
                # Fallback: tạo yolo_input từ fitz_img
                yolo_input = cv2.cvtColor(fitz_img, cv2.COLOR_RGB2BGR)
            
            yolo_h, yolo_w = yolo_input.shape[:2]
            
            return {
                "fitz_img": fitz_img,
                "yolo_input": yolo_input,
                "fitz_size": (fitz_w, fitz_h),
                "yolo_size": (yolo_w, yolo_h),
                "success": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_single_image(self, image_path, image_index):
        """Xử lý một ảnh (logic giống hệt code đơn)"""
        try:
            image_name = f"image_{image_index:04d}"
            print(f"\n📸 Đang xử lý: {image_path.name} -> {image_name}")
            
            # Tạo thư mục con cho ảnh crop
            crop_subdir = self.cropped_dir / image_name
            crop_subdir.mkdir(exist_ok=True)
            
            # === Load ảnh bằng fitz (giống code đơn) ===
            image_data = self.load_image_with_fitz(image_path)
            if not image_data["success"]:
                raise ValueError(f"Không thể load ảnh: {image_data['error']}")
            
            fitz_img = image_data["fitz_img"]
            yolo_input = image_data["yolo_input"]
            fitz_w, fitz_h = image_data["fitz_size"]
            yolo_w, yolo_h = image_data["yolo_size"]
            
            # === Tính hệ số scale (giống code đơn) ===
            scale_x = fitz_w / yolo_w
            scale_y = fitz_h / yolo_h
            
            print(f"   📏 Kích thước:")
            print(f"       - YOLO input: {yolo_w}x{yolo_h}")
            print(f"       - Ảnh gốc: {fitz_w}x{fitz_h}")
            print(f"       - Scale: x={scale_x:.3f}, y={scale_y:.3f}")
            
            # === Dự đoán YOLO ===
            det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.2, device="cuda")
            
            if not det_res[0].boxes:
                print(f"⚠️  Không phát hiện bbox nào trong {image_path.name}")
                return self._create_empty_result(image_path, image_name, fitz_w, fitz_h, yolo_w, yolo_h, scale_x, scale_y)
            
            # === Xử lý TẤT CẢ bbox (không lọc) ===
            all_bboxes = []
            
            for i, result in enumerate(det_res[0].boxes):
                bbox_result = self._process_bbox(
                    result, i, scale_x, scale_y, fitz_img, 
                    crop_subdir, i, image_name
                )
                all_bboxes.append(bbox_result["bbox_info"])
            
            # === Tạo ảnh annotated ===
            # 1. Ảnh với tất cả bbox -> all_detections
            annotated_all = det_res[0].plot(pil=True, line_width=5, font_size=20)
            annotated_all_path = self.all_detections_dir / f"{image_name}_all_bboxes.jpg"
            cv2.imwrite(str(annotated_all_path), cv2.cvtColor(np.array(annotated_all), cv2.COLOR_RGB2BGR))
            
            # 2. Ảnh với bbox -> valid_detections (giống all vì không lọc)
            # annotated_path = self.valid_detections_dir / f"{image_name}_annotated.jpg"
            # cv2.imwrite(str(annotated_path), cv2.cvtColor(np.array(annotated_all), cv2.COLOR_RGB2BGR))
            
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
                    "cropped_boxes": len(all_bboxes)
                },
                "all_bboxes": all_bboxes,
                "paths": {
                    "all_detections": str(annotated_all_path),
                    # "annotated": str(annotated_path),
                    "cropped_folder": str(crop_subdir)
                },
                "status": "success"
            }
            
            self.total_bboxes += total_boxes
            self.total_valid_bboxes += len(all_bboxes)
            
            print(f"   ✅ Hoàn thành: Đã crop {len(all_bboxes)}/{total_boxes} bbox")
            return result
            
        except Exception as e:
            error_msg = f"Lỗi xử lý {image_path.name}: {str(e)}"
            print(f"   ❌ {error_msg}")
            self.failed_images += 1
            return {
                "image_info": {
                    "original_path": str(image_path),
                    "image_name": f"image_{image_index:04d}",
                    "original_filename": image_path.name,
                    "error": error_msg
                },
                "status": "failed"
            }
    
    def _process_bbox(self, result, bbox_index, scale_x, scale_y, fitz_img, crop_subdir, crop_count, image_name):
        """Xử lý một bbox - Lấy tất cả không lọc"""
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
            "index": bbox_index,
            "class_id": int(result.cls[0]),
            "confidence": float(result.conf[0]),
            "bbox": [scaled_x1, scaled_y1, scaled_x2, scaled_y2],
            "width": width,
            "height": height,
            "area": area
        }
        
        # === Crop và lưu TẤT CẢ bbox ===
        cropped = fitz_img[scaled_y1:scaled_y2, scaled_x1:scaled_x2]
        
        # Làm nét ảnh bằng kernel sharpen
        sharpen_kernel = np.array([[0, -1, 0],
                                   [-1, 5, -1],
                                   [0, -1, 0]])
        sharpened = cv2.filter2D(cropped, -1, sharpen_kernel)
        
        # Lưu với tên file
        crop_filename = f"crop_{crop_count:03d}_cls{int(result.cls[0])}.png"
        crop_path = crop_subdir / crop_filename
        
        # Chuyển từ RGB sang BGR trước khi lưu (vì cv2.imwrite expect BGR)
        cv2.imwrite(str(crop_path), cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR))
        
        bbox_info["crop_path"] = str(crop_path)
        bbox_info["crop_filename"] = crop_filename
        
        print(f"      ✅ Bbox {bbox_index} -> crop_{crop_count}: [{scaled_x1}, {scaled_y1}, {scaled_x2}, {scaled_y2}] "
              f"(W:{width}, H:{height}, Area:{area:,}) -> {crop_filename}")
        
        return {
            "bbox_info": bbox_info
        }
    

    
    def _create_empty_result(self, image_path, image_name, fitz_w, fitz_h, yolo_w, yolo_h, scale_x, scale_y):
        """Tạo kết quả rỗng cho ảnh không có bbox"""
        return {
            "image_info": {
                "original_path": str(image_path),
                "image_name": image_name,
                "original_filename": image_path.name,
                "image_size": [fitz_w, fitz_h],
                "yolo_size": [yolo_w, yolo_h],
                "scale": [scale_x, scale_y]
            },
            "statistics": {
                "total_boxes": 0,
                "cropped_boxes": 0
            },
            "all_bboxes": [],
            "paths": {
                "all_detections": None,
                "annotated": None,
                "cropped_folder": None
            },
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
        
        # === Lưu kết quả tổng hợp ===
        self._save_batch_results(all_results)
        
        # === Thống kê cuối cùng ===
        self._print_final_statistics()
        
        return True
    
    def _save_batch_results(self, all_results):
        """Lưu kết quả tổng hợp trong thư mục gốc output"""
        batch_result = {
                            "config": {
                "input_directory": str(self.input_dir),
                "output_directory": str(self.output_dir),
                "all_detections_directory": str(self.all_detections_dir),
                # "valid_detections_directory": str(self.valid_detections_dir),
                "cropped_directory": str(self.cropped_dir),
                "filtering": "disabled - take all bboxes",
                "supported_formats": list(self.SUPPORTED_FORMATS),
                "processing_time": datetime.now().isoformat()
            },
            "batch_statistics": {
                "total_images": self.total_images,
                "processed_images": self.processed_images,
                "failed_images": self.failed_images,
                "success_rate": self.processed_images/self.total_images*100 if self.total_images > 0 else 0,
                "total_bboxes": self.total_bboxes,
                "total_cropped_bboxes": self.total_valid_bboxes,
                "crop_rate": 100.0  # 100% vì không lọc
            },
            "results": all_results
        }
        
        # Lưu JSON tổng hợp trong thư mục gốc output
        # batch_json_path = self.output_dir / "batch_results.json"
        # with open(batch_json_path, "w", encoding='utf-8') as f:
        #     json.dump(batch_result, f, ensure_ascii=False, indent=2)
        
        # print(f"\n💾 Đã lưu kết quả tổng hợp: {batch_json_path}")
    
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
        print(f"   - Tổng bbox đã crop: {self.total_valid_bboxes:,}")
        print(f"   - Tỷ lệ crop: 100% (không lọc)")
        
        print(f"\n📁 Kết quả đầu ra:")
        print(f"   - Ảnh tất cả detections: {self.all_detections_dir}")
        # print(f"   - Ảnh valid detections: {self.valid_detections_dir}")
        print(f"   - Ảnh crop: {self.cropped_dir}")
        print(f"   - JSON tổng hợp: {self.output_dir}/batch_results.json")


def main():
    # === Cấu hình đường dẫn ===
    INPUT_DIR = "books_to_images/30-de-thi"  # Thay đổi đường dẫn này
    OUTPUT_DIR = "."  # Thay đổi đường dẫn này
    
    # Tạo processor và chạy
    processor = YOLOBatchProcessor(INPUT_DIR, OUTPUT_DIR)
    processor.process_batch()


if __name__ == "__main__":
    main()