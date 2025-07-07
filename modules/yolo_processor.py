# modules/yolo_processor.py
import os
import cv2
import numpy as np
import logging
import traceback
import time
from pathlib import Path
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
import multiprocessing as mp
from functools import partial

class YOLOProcessor:
    def __init__(self, debug_mode=False):
        self.model = None
        self.model_loaded = False
        self.debug_mode = debug_mode
        
        # Thiết lập logging cho YOLO
        self.logger = logging.getLogger('YOLOProcessor')
        if debug_mode:
            self.logger.setLevel(logging.DEBUG)
            self.logger.info("YOLOProcessor khởi tạo với DEBUG MODE")
    
    def _debug_log(self, message, level='info'):
        """Helper function để log debug info cho YOLO"""
        if not self.debug_mode:
            return
        
        if level == 'debug':
            self.logger.debug(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def _debug_exception(self, e, context=""):
        """Log chi tiết exception cho YOLO"""
        error_msg = f"YOLO EXCEPTION in {context}: {str(e)}"
        self.logger.error(error_msg)
        
        if self.debug_mode:
            self.logger.error("YOLO Full traceback:")
            self.logger.error(traceback.format_exc())
        
        return error_msg
    
    def load_model(self, status_callback=None):
        """Load YOLO model với debug support"""
        try:
            self._debug_log("=== LOADING YOLO MODEL ===")
            
            if status_callback:
                status_callback({
                    'stage': 'model_loading',
                    'message': 'Đang tải YOLO model...'
                })
            
            model_start_time = time.time()
            self._debug_log("Downloading model từ HuggingFace...")
            
            filepath = hf_hub_download(
                repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
                filename="doclayout_yolo_docstructbench_imgsz1024.pt"
            )
            
            self._debug_log(f"Model downloaded to: {filepath}")
            self._debug_log("Khởi tạo YOLOv10 model...")
            
            self.model = YOLOv10(filepath)
            self.model_loaded = True
            
            load_time = time.time() - model_start_time
            self._debug_log(f"✓ Model loaded successfully trong {load_time:.2f}s")
            
            if status_callback:
                status_callback({
                    'message': 'YOLO model đã được tải thành công!'
                })
            
            return True, "Model đã được tải thành công!"
            
        except Exception as e:
            self.model_loaded = False
            error_msg = self._debug_exception(e, "load_model")
            return False, f"Lỗi khi tải model: {str(e)}"
    
    def process_images(self, input_dir, output_base_dir, book_name, status_callback=None):
        """
        Xử lý tất cả ảnh trong thư mục với YOLO (batch processing + multiprocessing crop) với debug support
        """
        process_start_time = time.time()
        
        try:
            self._debug_log("=== BẮT ĐẦU YOLO PROCESSING ===")
            self._debug_log(f"Input dir: {input_dir}")
            self._debug_log(f"Output base dir: {output_base_dir}")
            self._debug_log(f"Book name: {book_name}")
            
            if status_callback:
                status_callback({
                    'stage': 'yolo_detect',
                    'message': 'Bắt đầu xử lý YOLO detection...'
                })
            
            # Load model nếu chưa load
            if not self.model_loaded:
                self._debug_log("Model chưa được load, đang load...")
                success, message = self.load_model(status_callback)
                if not success:
                    return False, message, None
            
            # Tạo cấu trúc thư mục output
            cropped_dir = Path(output_base_dir) / "books_cropped" / book_name
            detection_dir = Path(output_base_dir) / "books_detections" / book_name
            cropped_dir.mkdir(parents=True, exist_ok=True)
            detection_dir.mkdir(parents=True, exist_ok=True)
            
            self._debug_log(f"Cropped dir: {cropped_dir}")
            self._debug_log(f"Detection dir: {detection_dir}")
            
            # Lấy danh sách ảnh
            image_files = list(Path(input_dir).glob("*.png"))
            total_images = len(image_files)
            
            self._debug_log(f"Tìm thấy {total_images} file .png")
            
            if total_images == 0:
                self._debug_log("❌ Không tìm thấy file ảnh nào", level='error')
                return False, "Không tìm thấy file ảnh nào trong thư mục", None
            
            if status_callback:
                status_callback({
                    'total_images': total_images,
                    'current_image': 0,
                    'message': f'Tìm thấy {total_images} ảnh để xử lý'
                })
            
            # ===== BƯỚC 1: BATCH DETECTION =====
            batch_start_time = time.time()
            self._debug_log("=== BATCH DETECTION START ===")
            
            if status_callback:
                status_callback({
                    'stage': 'batch_detection',
                    'message': f'Đang thực hiện batch detection cho {total_images} ảnh...'
                })
            
            # Predict tất cả ảnh một lần
            self._debug_log(f"Chạy model.predict với source={input_dir}")
            batch_results = self.model.predict(
                source=str(input_dir), 
                imgsz=1024, 
                conf=0.3, 
                device="cuda",
                save=False,
                verbose=False
            )
            
            batch_time = time.time() - batch_start_time
            self._debug_log(f"✓ Batch detection hoàn thành trong {batch_time:.2f}s")
            self._debug_log(f"Số kết quả nhận được: {len(batch_results)}")
            
            if status_callback:
                status_callback({
                    'message': f'Hoàn thành batch detection. Bắt đầu tạo detection images...'
                })
            
            # ===== BƯỚC 2: TẠO DETECTION IMAGES =====
            detection_start_time = time.time()
            self._debug_log("=== CREATING DETECTION IMAGES ===")
            
            detection_data = []
            for i, (image_path, result) in enumerate(zip(sorted(image_files), batch_results)):
                image_name = f"image_{i:04d}"
                
                self._debug_log(f"Processing detection image {i+1}/{total_images}: {image_path.name}")
                
                # Tạo ảnh annotated
                detection_path = None
                if result.boxes is not None and len(result.boxes) > 0:
                    try:
                        annotated_img = result.plot(pil=True, line_width=5, font_size=20)
                        detection_path = detection_dir / f"{image_name}_detections.jpg"
                        
                        # Chuyển PIL sang OpenCV và lưu
                        annotated_cv = cv2.cvtColor(np.array(annotated_img), cv2.COLOR_RGB2BGR)
                        cv2.imwrite(str(detection_path), annotated_cv)
                        
                        self._debug_log(f"  Saved detection image: {detection_path.name}")
                        self._debug_log(f"  Found {len(result.boxes)} boxes")
                    except Exception as e:
                        self._debug_log(f"  ❌ Lỗi tạo detection image: {e}", level='error')
                        detection_path = None
                else:
                    self._debug_log(f"  No boxes detected for {image_path.name}")
                
                # Chuẩn bị data cho multiprocessing crop
                detection_data.append({
                    'image_path': str(image_path),
                    'image_name': image_name,
                    'image_index': i,
                    'result': result,
                    'cropped_dir': str(cropped_dir),
                    'detection_path': str(detection_path) if detection_path else None
                })
            
            detection_time = time.time() - detection_start_time
            self._debug_log(f"✓ Detection images tạo xong trong {detection_time:.2f}s")
            
            # ===== BƯỚC 3: MULTIPROCESSING CROP =====
            crop_start_time = time.time()
            self._debug_log("=== MULTIPROCESSING CROP START ===")
            
            if status_callback:
                status_callback({
                    'stage': 'multiprocessing_crop',
                    'message': 'Bắt đầu crop ảnh với multiprocessing...'
                })
            
            # Xác định số processes
            num_processes = min(mp.cpu_count(), len(detection_data), 8)
            self._debug_log(f"Sử dụng {num_processes} processes cho {len(detection_data)} ảnh")
            
            if status_callback:
                status_callback({
                    'message': f'Sử dụng {num_processes} processes để crop {len(detection_data)} ảnh'
                })
            
            # Tạo progress callback cho multiprocessing
            def update_progress(completed_count):
                if status_callback:
                    progress = int((completed_count / total_images) * 30) + 70  # 70-100%
                    status_callback({
                        'current_image': completed_count,
                        'message': f'Đã crop {completed_count}/{total_images} ảnh'
                    })
                    
                self._debug_log(f"Crop progress: {completed_count}/{total_images}")
            
            # Thực hiện multiprocessing crop
            processed_results = self._multiprocess_crop_images(
                detection_data, 
                num_processes,
                update_progress
            )
            
            crop_time = time.time() - crop_start_time
            self._debug_log(f"✓ Multiprocessing crop hoàn thành trong {crop_time:.2f}s")
            
            # ===== BƯỚC 4: TỔNG HỢP KẾT QUẢ =====
            total_time = time.time() - process_start_time
            
            # Đếm số lượng kết quả
            success_count = len([r for r in processed_results if r.get('status') == 'success'])
            error_count = len([r for r in processed_results if r.get('status') == 'error'])
            no_detection_count = len([r for r in processed_results if r.get('status') == 'no_detection'])
            
            self._debug_log("=== TỔNG KẾT QUẢ YOLO PROCESSING ===")
            self._debug_log(f"Tổng thời gian: {total_time:.2f}s")
            self._debug_log(f"  - Batch detection: {batch_time:.2f}s")
            self._debug_log(f"  - Detection images: {detection_time:.2f}s")
            self._debug_log(f"  - Multiprocessing crop: {crop_time:.2f}s")
            self._debug_log(f"Kết quả:")
            self._debug_log(f"  - Success: {success_count}")
            self._debug_log(f"  - No detection: {no_detection_count}")
            self._debug_log(f"  - Errors: {error_count}")
            
            if status_callback:
                status_callback({
                    'message': f'Hoàn thành xử lý {total_images} ảnh'
                })
            
            return True, f"Đã xử lý {total_images} ảnh thành công", {
                'total_images': total_images,
                'cropped_dir': str(cropped_dir),
                'detection_dir': str(detection_dir),
                'results': processed_results,
                'timing_info': {
                    'total_time': total_time,
                    'batch_detection_time': batch_time,
                    'detection_images_time': detection_time,
                    'crop_time': crop_time
                } if self.debug_mode else None,
                'stats': {
                    'success_count': success_count,
                    'error_count': error_count,
                    'no_detection_count': no_detection_count
                } if self.debug_mode else None
            }
            
        except Exception as e:
            error_msg = self._debug_exception(e, "process_images")
            return False, f"Lỗi khi xử lý YOLO: {str(e)}", None
    
    def _multiprocess_crop_images(self, detection_data, num_processes, progress_callback=None):
        """Xử lý crop ảnh với multiprocessing và debug support"""
        try:
            self._debug_log(f"Bắt đầu multiprocessing crop với {num_processes} processes")
            
            # Tạo shared counter cho progress tracking
            with mp.Manager() as manager:
                completed_counter = manager.Value('i', 0)
                
                # Tạo partial function với shared counter
                crop_func = partial(
                    self._crop_single_image_worker,
                    completed_counter=completed_counter,
                    total_images=len(detection_data),
                    progress_callback=progress_callback,
                    debug_mode=self.debug_mode
                )
                
                # Chạy multiprocessing
                mp_start_time = time.time()
                with mp.Pool(processes=num_processes) as pool:
                    results = pool.map(crop_func, detection_data)
                
                mp_time = time.time() - mp_start_time
                self._debug_log(f"✓ Multiprocessing pool hoàn thành trong {mp_time:.2f}s")
                
                return results
                
        except Exception as e:
            error_msg = self._debug_exception(e, "_multiprocess_crop_images")
            self._debug_log("❌ Multiprocessing failed, fallback to sequential processing", level='warning')
            # Fallback: xử lý tuần tự
            return [self._crop_single_image_worker(data, debug_mode=self.debug_mode) for data in detection_data]
    
    @staticmethod
    def _crop_single_image_worker(detection_item, completed_counter=None, total_images=None, progress_callback=None, debug_mode=False):
        """Worker function cho multiprocessing crop với debug support - STATIC METHOD"""
        worker_start_time = time.time()
        
        try:
            image_path = detection_item['image_path']
            image_name = detection_item['image_name']
            image_index = detection_item['image_index']
            result = detection_item['result']
            cropped_dir = Path(detection_item['cropped_dir'])
            detection_path = detection_item['detection_path']
            
            if debug_mode:
                print(f"[Worker] Processing {image_name} (index {image_index})")
            
            # Tạo thư mục con cho ảnh này
            crop_subdir = cropped_dir / image_name
            crop_subdir.mkdir(exist_ok=True)
            
            # Load ảnh bằng OpenCV
            img_load_start = time.time()
            original_img = cv2.imread(image_path)
            if original_img is None:
                if debug_mode:
                    print(f"[Worker] ❌ Không thể load ảnh: {image_path}")
                
                # Cập nhật progress counter
                if completed_counter is not None:
                    with completed_counter.get_lock():
                        completed_counter.value += 1
                        if progress_callback:
                            progress_callback(completed_counter.value)
                
                return {
                    'image_name': image_name,
                    'status': 'error',
                    'error': 'Không thể load ảnh'
                }
            
            img_load_time = time.time() - img_load_start
            
            # Chuyển từ BGR sang RGB
            original_img_rgb = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
            img_h, img_w = original_img_rgb.shape[:2]
            
            if debug_mode:
                print(f"[Worker] {image_name}: Loaded image {img_w}x{img_h} trong {img_load_time:.3f}s")
            
            # Kiểm tra có bbox không
            if result.boxes is None or len(result.boxes) == 0:
                if debug_mode:
                    print(f"[Worker] {image_name}: No boxes detected")
                
                # Cập nhật progress counter
                if completed_counter is not None:
                    with completed_counter.get_lock():
                        completed_counter.value += 1
                        if progress_callback:
                            progress_callback(completed_counter.value)
                
                return {
                    'image_name': image_name,
                    'status': 'no_detection',
                    'bbox_count': 0,
                    'cropped_folder': str(crop_subdir),
                    'detection_image': detection_path,
                    'processing_time': time.time() - worker_start_time if debug_mode else None
                }
            
            # Xử lý tất cả bbox
            bbox_count = 0
            bbox_results = []
            
            crop_start_time = time.time()
            
            for i, box in enumerate(result.boxes):
                try:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Đảm bảo tọa độ trong phạm vi ảnh
                    x1 = max(0, int(x1))
                    y1 = max(0, int(y1))
                    x2 = min(img_w, int(x2))
                    y2 = min(img_h, int(y2))
                    
                    # Kiểm tra bbox hợp lệ
                    if x2 > x1 and y2 > y1:
                        # Crop ảnh
                        cropped = original_img_rgb[y1:y2, x1:x2]
                        
                        # Làm nét ảnh bằng kernel sharpen
                        sharpen_kernel = np.array([[0, -1, 0],
                                                   [-1, 5, -1],
                                                   [0, -1, 0]])
                        sharpened = cv2.filter2D(cropped, -1, sharpen_kernel)
                        
                        # Tạo tên file crop
                        crop_filename = f"crop_{bbox_count:03d}_cls{int(box.cls[0])}.png"
                        crop_path = crop_subdir / crop_filename
                        
                        # Chuyển về BGR trước khi lưu
                        cv2.imwrite(str(crop_path), cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR))
                        
                        bbox_results.append({
                            'bbox_index': i,
                            'class_id': int(box.cls[0]),
                            'confidence': float(box.conf[0]),
                            'bbox': [x1, y1, x2, y2],
                            'crop_path': str(crop_path),
                            'crop_filename': crop_filename
                        })
                        
                        bbox_count += 1
                        
                except Exception as e:
                    if debug_mode:
                        print(f"[Worker] ❌ Lỗi xử lý bbox {i} của {image_name}: {e}")
                    continue
            
            crop_time = time.time() - crop_start_time
            worker_total_time = time.time() - worker_start_time
            
            if debug_mode:
                print(f"[Worker] ✓ {image_name}: {bbox_count} crops trong {crop_time:.3f}s (total: {worker_total_time:.3f}s)")
            
            # Cập nhật progress counter
            if completed_counter is not None:
                with completed_counter.get_lock():
                    completed_counter.value += 1
                    if progress_callback:
                        progress_callback(completed_counter.value)
            
            return {
                'image_name': image_name,
                'status': 'success',
                'bbox_count': bbox_count,
                'cropped_folder': str(crop_subdir),
                'detection_image': detection_path,
                'bbox_results': bbox_results,
                'processing_time': worker_total_time if debug_mode else None
            }
            
        except Exception as e:
            # Cập nhật progress counter ngay cả khi lỗi
            if completed_counter is not None:
                with completed_counter.get_lock():
                    completed_counter.value += 1
                    if progress_callback:
                        progress_callback(completed_counter.value)
            
            if debug_mode:
                print(f"[Worker] ❌ Exception trong {detection_item.get('image_name', 'unknown')}: {e}")
            
            return {
                'image_name': detection_item.get('image_name', 'unknown'),
                'status': 'error',
                'error': str(e)
            }