import cv2
import numpy as np
import base64
import os
from typing import List, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageUtils:
    """Utility class for image operations"""
    
    @staticmethod
    def crop_bbox(image_path: str, bbox: List[float], output_path: str = None) -> str:
        """
        Crop bbox from image and save to file
        
        Args:
            image_path: Path to source image
            bbox: [x1, y1, x2, y2] coordinates
            output_path: Optional output path, if None will generate temp name
            
        Returns:
            Path to cropped image
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Extract coordinates
            x1, y1, x2, y2 = map(int, bbox)
            
            # Ensure coordinates are within image bounds
            h, w = image.shape[:2]
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(x1, min(x2, w))
            y2 = max(y1, min(y2, h))
            
            # Crop image
            cropped = image[y1:y2, x1:x2]
            
            # Generate output path if not provided
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = f"temp_crop_{base_name}_{x1}_{y1}_{x2}_{y2}.png"
            
            # Save cropped image
            cv2.imwrite(output_path, cropped)
            logger.debug(f"Cropped bbox saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error cropping bbox {bbox}: {e}")
            raise
    
    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """
        Convert image to base64 string for API calls
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image with data URL prefix
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Determine MIME type
            ext = image_path.lower().split('.')[-1]
            if ext == 'png':
                mime_type = "image/png"
            elif ext in ['jpg', 'jpeg']:
                mime_type = "image/jpeg"
            else:
                raise ValueError(f"Unsupported image format: {ext}")
            
            # Read and encode
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            return f"data:{mime_type};base64,{encoded_string}"
            
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            raise
    
    @staticmethod
    def cleanup_temp_files(file_patterns: List[str]):
        """
        Clean up temporary files
        
        Args:
            file_patterns: List of file patterns to delete
        """
        try:
            for pattern in file_patterns:
                if os.path.exists(pattern):
                    os.remove(pattern)
                    logger.debug(f"Cleaned up temp file: {pattern}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")

class GeometryUtils:
    """Utility class for geometric operations"""
    
    @staticmethod
    def compute_iou(box1: List[float], box2: List[float]) -> float:
        """
        Compute Intersection over Union (IoU) of two bounding boxes
        
        Args:
            box1: [x1, y1, x2, y2]
            box2: [x1, y1, x2, y2]
            
        Returns:
            IoU value between 0 and 1
        """
        try:
            # Calculate intersection coordinates
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            # Calculate intersection area
            inter_area = max(0, x2 - x1) * max(0, y2 - y1)
            
            # Calculate union area
            box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
            box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union_area = box1_area + box2_area - inter_area
            
            return inter_area / union_area if union_area > 0 else 0
            
        except Exception as e:
            logger.error(f"Error computing IoU: {e}")
            return 0
    
    @staticmethod
    def get_bbox_center(bbox: List[float]) -> Tuple[float, float]:
        """
        Get center point of bounding box
        
        Args:
            bbox: [x1, y1, x2, y2]
            
        Returns:
            (center_x, center_y)
        """
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    @staticmethod
    def sort_boxes_by_position(boxes: List[dict], sort_by: str = 'top') -> List[dict]:
        """
        Sort boxes by position
        
        Args:
            boxes: List of box dictionaries with 'bbox' key
            sort_by: 'top' (y1), 'bottom' (y2), 'left' (x1), 'right' (x2)
            
        Returns:
            Sorted list of boxes
        """
        try:
            if sort_by == 'top':
                return sorted(boxes, key=lambda b: b['bbox'][1])
            elif sort_by == 'bottom':
                return sorted(boxes, key=lambda b: b['bbox'][3])
            elif sort_by == 'left':
                return sorted(boxes, key=lambda b: b['bbox'][0])
            elif sort_by == 'right':
                return sorted(boxes, key=lambda b: b['bbox'][2])
            else:
                logger.warning(f"Unknown sort_by parameter: {sort_by}")
                return boxes
                
        except Exception as e:
            logger.error(f"Error sorting boxes: {e}")
            return boxes