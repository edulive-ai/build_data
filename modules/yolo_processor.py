# modules/yolo_processor.py
import os
import cv2
import fitz
import numpy as np
from pathlib import Path
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

class YOLOProcessor:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        
    def load_model(self, status_callback=None):
        """Load YOLO model"""
        try:
            if status_callback:
                status_callback({
                    'stage': 'model_loading',
                    'message': 'Đang tải YOLO model...'
                })
            
            filepath = hf_hub_download(
                repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
                filename="doclayout_yolo_docstructbench_imgsz1024.pt"
            )
            self.model = YOLOv10(filepath)
            self.model_loaded = True
            
            if status_callback:
                status_callback({
                    'message': 'YOLO model đã được tải thành công!'
                })
            
            return True, "Model đã được tải thành công!"
            
        except Exception as e:
            self.model_loaded = False
            return False, f"Lỗi khi tải model: {str(e)}"
    
    def process_images(self, input_dir, output_base_dir, book_name, status_callback=None):
        """
        Xử lý tất cả ảnh trong thư mục với YOLO
        
        Args:
            input_dir (str): Thư mục chứa ảnh đầu vào
            output_base_dir (str): Thư mục gốc để lưu kết quả
            book_name (str): Tên sách
            status_callback (function): Callback function để cập nhật trạng thái
            
        Returns:
            tuple: (success, message, info)
        """
        try:
            if status_callback:
                status_callback({
                    'stage': 'yolo_detect',
                    'message': 'Bắt đầu xử lý YOLO detection...'
                })
            
            # Load model nếu chưa load
            if not self.model_loaded:
                success, message = self.load_model(status_callback)
                if not success:
                    return False, message, None
            
            # Tạo cấu trúc thư mục output
            cropped_dir = Path(output_base_dir) / "books_cropped" / book_name
            detection_dir = Path(output_base_dir) / "books_detections" / book_name
            cropped_dir.mkdir(parents=True, exist_ok=True)
            detection_dir.mkdir(parents=True, exist_ok=True)
            
            # Lấy danh sách ảnh
            image_files = list(Path(input_dir).glob("*.png"))
            total_images = len(image_files)
            
            if total_images == 0:
                return False, "Không tìm thấy file ảnh nào trong thư mục", None
            
            if status_callback:
                status_callback({
                    'total_images': total_images,
                    'current_image': 0,
                    'message': f'Tìm thấy {total_images} ảnh để xử lý'
                })
            
            processed_results = []
            
            # Xử lý từng ảnh
            for i, image_path in enumerate(sorted(image_files)):
                if status_callback:
                    status_callback({
                        'current_image': i + 1,
                        'message': f'Đang xử lý ảnh {i + 1}/{total_images}: {image_path.name}'
                    })
                
                result = self._process_single_image(image_path, cropped_dir, detection_dir, i)
                processed_results.append(result)
            
            return True, f"Đã xử lý {total_images} ảnh thành công", {
                'total_images': total_images,
                'cropped_dir': str(cropped_dir),
                'detection_dir': str(detection_dir),
                'results': processed_results
            }
            
        except Exception as e:
            return False, f"Lỗi khi xử lý YOLO: {str(e)}", None
    
    def _process_single_image(self, image_path, cropped_output_dir, detection_output_dir, image_index):
        """Xử lý một ảnh đơn lẻ"""
        try:
            image_name = f"image_{image_index:04d}"
            crop_subdir = cropped_output_dir / image_name
            crop_subdir.mkdir(exist_ok=True)
            
            # === Load ảnh bằng fitz để có chất lượng cao ===
            image_data = self._load_image_with_fitz(image_path)
            if not image_data["success"]:
                raise ValueError(f"Không thể load ảnh: {image_data['error']}")
            
            fitz_img = image_data["fitz_img"]
            yolo_input = image_data["yolo_input"]
            fitz_w, fitz_h = image_data["fitz_size"]
            yolo_w, yolo_h = image_data["yolo_size"]
            
            # === Tính hệ số scale ===
            scale_x = fitz_w / yolo_w
            scale_y = fitz_h / yolo_h
            
            # === YOLO detection ===
            det_res = self.model.predict(str(image_path), imgsz=1024, conf=0.2, device="cuda")
            
            if not det_res[0].boxes:
                return {
                    'image_name': image_name,
                    'status': 'no_detection',
                    'bbox_count': 0
                }
            
            # === Tạo ảnh annotated (detection) ===
            annotated_img = det_res[0].plot(pil=True, line_width=5, font_size=20)
            detection_path = detection_output_dir / f"{image_name}_detections.jpg"
            
            # Chuyển PIL Image sang OpenCV format và lưu
            import cv2
            import numpy as np
            annotated_cv = cv2.cvtColor(np.array(annotated_img), cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(detection_path), annotated_cv)
            
            # === Xử lý tất cả bbox ===
            bbox_count = 0
            bbox_results = []
            for i, result in enumerate(det_res[0].boxes):
                bbox_result = self._process_bbox(
                    result, i, scale_x, scale_y, fitz_img, 
                    crop_subdir, bbox_count, image_name
                )
                if bbox_result:
                    bbox_results.append(bbox_result)
                    bbox_count += 1
            
            return {
                'image_name': image_name,
                'status': 'success',
                'bbox_count': bbox_count,
                'cropped_folder': str(crop_subdir),
                'detection_image': str(detection_path),
                'bbox_results': bbox_results
            }
            
        except Exception as e:
            return {
                'image_name': f"image_{image_index:04d}",
                'status': 'error',
                'error': str(e)
            }
    
    def _load_image_with_fitz(self, image_path):
        """Load ảnh bằng fitz để đảm bảo chất lượng cao"""
        try:
            # Dùng fitz để đọc ảnh chất lượng cao
            doc = fitz.open(str(image_path))
            pix = doc[0].get_pixmap(dpi=300)
            fitz_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:  # nếu có alpha channel
                fitz_img = cv2.cvtColor(fitz_img, cv2.COLOR_RGBA2RGB)
            
            fitz_h, fitz_w = fitz_img.shape[:2]
            doc.close()
            
            # Dùng OpenCV để lấy kích thước ảnh YOLO resize
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
    
    def _process_bbox(self, result, bbox_index, scale_x, scale_y, fitz_img, crop_subdir, crop_count, image_name):
        """Xử lý một bbox - crop và lưu"""
        try:
            x1, y1, x2, y2 = result.xyxy[0].tolist()
            
            # Scale về tọa độ ảnh gốc
            scaled_x1 = int(x1 * scale_x)
            scaled_y1 = int(y1 * scale_y)
            scaled_x2 = int(x2 * scale_x)
            scaled_y2 = int(y2 * scale_y)
            
            # Crop ảnh
            cropped = fitz_img[scaled_y1:scaled_y2, scaled_x1:scaled_x2]
            
            # Làm nét ảnh bằng kernel sharpen
            sharpen_kernel = np.array([[0, -1, 0],
                                       [-1, 5, -1],
                                       [0, -1, 0]])
            sharpened = cv2.filter2D(cropped, -1, sharpen_kernel)
            
            # Tạo tên file crop
            crop_filename = f"crop_{crop_count:03d}_cls{int(result.cls[0])}.png"
            crop_path = crop_subdir / crop_filename
            
            # Chuyển từ RGB sang BGR trước khi lưu
            cv2.imwrite(str(crop_path), cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR))
            
            return {
                'bbox_index': bbox_index,
                'class_id': int(result.cls[0]),
                'confidence': float(result.conf[0]),
                'bbox': [scaled_x1, scaled_y1, scaled_x2, scaled_y2],
                'crop_path': str(crop_path),
                'crop_filename': crop_filename
            }
            
        except Exception as e:
            print(f"Lỗi khi xử lý bbox {bbox_index}: {e}")
            return None