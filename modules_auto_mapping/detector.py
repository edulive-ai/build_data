import cv2
import numpy as np
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
from typing import List, Dict, Tuple
import logging
from .utils import GeometryUtils

logger = logging.getLogger(__name__)

class DocumentDetector:
    """Document layout detection using YOLO model - COMPLETE VERSION"""
    
    def __init__(self, config):
        """
        Initialize detector with configuration
        
        Args:
            config: Configuration object with YOLO settings
        """
        self.config = config
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model from HuggingFace"""
        try:
            logger.info("Loading YOLO model...")
            model_path = hf_hub_download(
                repo_id=self.config.YOLO_REPO_ID,
                filename=self.config.YOLO_FILENAME
            )
            self.model = YOLOv10(model_path)
            logger.info("YOLO model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect_boxes(self, image_path: str) -> List[Dict]:
        """
        Detect bounding boxes in image
        
        Args:
            image_path: Path to input image
            
        Returns:
            List of detected boxes with metadata
        """
        try:
            logger.info(f"Running detection on: {image_path}")
            
            # Run YOLO prediction
            results = self.model.predict(
                image_path,
                imgsz=self.config.YOLO_IMAGE_SIZE,
                conf=self.config.CONFIDENCE_THRESHOLD,
                device=self.config.YOLO_DEVICE
            )
            
            # Extract results
            result = results[0]
            class_names = result.names
            boxes = result.boxes
            
            # Process detected boxes
            box_data = []
            for i in range(len(boxes.cls)):
                class_id = int(boxes.cls[i])
                
                # Filter by target classes (None = all classes)
                if self.config.TARGET_CLASSES is not None and class_id not in self.config.TARGET_CLASSES:
                    continue
                
                label = class_names[class_id]
                confidence = float(boxes.conf[i])
                x1, y1, x2, y2 = map(float, boxes.xyxy[i])
                
                box_data.append({
                    "id": len(box_data),
                    "label": label,
                    "cls": class_id,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": confidence,
                    "ocr_text": None,
                    "is_question": None,
                    "crop_path": None
                })
            
            # Log detection results
            if self.config.TARGET_CLASSES is None:
                logger.info(f"Detected {len(box_data)} boxes (all classes)")
            else:
                logger.info(f"Detected {len(box_data)} boxes (filtered classes: {self.config.TARGET_CLASSES})")
            
            # Log class distribution
            class_counts = {}
            for box in box_data:
                label_cls = f"{box['label']}(cls{box['cls']})"
                class_counts[label_cls] = class_counts.get(label_cls, 0) + 1
            
            logger.info(f"Class distribution: {class_counts}")
            
            return box_data
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise
    
    def group_duplicate_boxes(self, boxes: List[Dict]) -> List[List[int]]:
        """
        Group boxes with high IoU overlap
        
        Args:
            boxes: List of box dictionaries
            
        Returns:
            List of groups (each group is list of box indices)
        """
        try:
            n = len(boxes)
            visited = [False] * n
            groups = []
            
            for i in range(n):
                if visited[i]:
                    continue
                    
                group = [i]
                visited[i] = True
                
                for j in range(i + 1, n):
                    if visited[j]:
                        continue
                        
                    iou = GeometryUtils.compute_iou(
                        boxes[i]["bbox"], 
                        boxes[j]["bbox"]
                    )
                    
                    if iou >= self.config.IOU_THRESHOLD:
                        group.append(j)
                        visited[j] = True
                
                groups.append(group)
            
            logger.info(f"Found {len(groups)} groups from {n} boxes")
            return groups
            
        except Exception as e:
            logger.error(f"Error grouping duplicate boxes: {e}")
            return [[i] for i in range(len(boxes))]  # Return individual groups as fallback
    
    def deduplicate_boxes(self, boxes: List[Dict]) -> List[Dict]:
        """
        Remove duplicate boxes by keeping highest confidence box from each group
        
        Args:
            boxes: List of box dictionaries
            
        Returns:
            List of deduplicated boxes
        """
        try:
            groups = self.group_duplicate_boxes(boxes)
            deduplicated = []
            
            logger.info(f"Processing {len(groups)} groups for deduplication...")
            
            for group_idx, group in enumerate(groups):
                # Get best box from group (highest confidence)
                best_box = max([boxes[i] for i in group], key=lambda b: b["confidence"])
                
                # Update ID to maintain sequence
                best_box["id"] = len(deduplicated)
                deduplicated.append(best_box)
                
                # Log if duplicates were found
                if len(group) > 1:
                    logger.info(f"Group {group_idx}: Removed {len(group)-1} duplicates, "
                              f"kept {best_box['label']} (conf={best_box['confidence']:.2f})")
            
            logger.info(f"Deduplication complete: {len(boxes)} -> {len(deduplicated)} boxes")
            return deduplicated
            
        except Exception as e:
            logger.error(f"Error deduplicating boxes: {e}")
            return boxes  # Return original boxes as fallback
    
    def detect_and_deduplicate(self, image_path: str) -> Tuple[List[Dict], Dict]:
        """
        Full detection pipeline with deduplication
        
        Args:
            image_path: Path to input image
            
        Returns:
            Tuple of (deduplicated_boxes, detection_metadata)
        """
        try:
            # Detect boxes
            raw_boxes = self.detect_boxes(image_path)
            
            # Deduplicate
            final_boxes = self.deduplicate_boxes(raw_boxes)
            
            # Create metadata
            metadata = {
                "image_path": image_path,
                "total_raw_boxes": len(raw_boxes),
                "total_final_boxes": len(final_boxes),
                "detection_params": {
                    "iou_threshold": self.config.IOU_THRESHOLD,
                    "conf_threshold": self.config.CONFIDENCE_THRESHOLD,
                    "target_classes": self.config.TARGET_CLASSES if self.config.TARGET_CLASSES else "all_classes"
                }
            }
            
            return final_boxes, metadata
            
        except Exception as e:
            logger.error(f"Detection pipeline failed: {e}")
            raise