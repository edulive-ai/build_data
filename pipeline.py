import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from config import Config
from modules_auto_mapping import (
    DocumentDetector,
    OCRService,
    BBoxProcessor,
    ImageUtils
)
from modules_auto_mapping.rule_based_classifier import QuestionClassifier


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentProcessingPipeline:
    """Main pipeline for document processing - COMPLETE VERSION"""
    
    def __init__(self, config_override: Dict = None):
        """
        Initialize pipeline with configuration
        
        Args:
            config_override: Optional config overrides
        """
        self.config = Config()
        
        # Apply config overrides if provided
        if config_override:
            for key, value in config_override.items():
                setattr(self.config, key, value)
        
        # Initialize components
        self.detector = DocumentDetector(self.config)
        self.ocr_service = OCRService(self.config)
        self.question_classifier = QuestionClassifier(self.config)
        self.bbox_processor = BBoxProcessor(self.config)
        
        logger.info("Pipeline initialized successfully")
    
    def process_image(self, image_path: str, output_path: str = None) -> Dict:
        """
        Process single image through complete pipeline
        
        Args:
            image_path: Path to input image
            output_path: Optional path to save results JSON
            
        Returns:
            Complete processing results
        """
        try:
            start_time = time.time()
            logger.info(f"Starting pipeline processing for: {image_path}")
            
            # Step 1: Document Detection
            logger.info("Step 1: Running document detection...")
            boxes, detection_metadata = self.detector.detect_and_deduplicate(image_path)
            
            if not boxes:
                logger.warning("No boxes detected in image")
                return self._create_empty_result(image_path, "No boxes detected")
            
            # Step 2: OCR Processing (only for OCR classes)
            logger.info("Step 2: Running OCR on detected boxes...")
            boxes_with_ocr = self.ocr_service.process_boxes_batch(image_path, boxes)
            
            # Step 3: Question Classification (only for OCR classes with text)
            logger.info("Step 3: Classifying questions...")
            boxes_with_classification = self.question_classifier.process_boxes(boxes_with_ocr)
            
            # Step 4: Document Structure Processing
            logger.info("Step 4: Processing document structure...")
            processed_data = self.bbox_processor.process_document_structure(boxes_with_classification)
            
            # Step 5: Create final result
            result = self._create_final_result(
                image_path,
                boxes_with_classification,
                processed_data,
                detection_metadata,
                start_time
            )
            
            # Validate result
            if self.bbox_processor.validate_structure(processed_data):
                logger.info("Pipeline processing completed successfully")
            else:
                logger.warning("Pipeline completed but structure validation failed")
            
            # Save result if output path provided
            if output_path:
                self._save_result(result, output_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return self._create_error_result(image_path, str(e))
    
    def process_batch(self, image_paths: List[str], output_dir: str = None) -> List[Dict]:
        """
        Process multiple images
        
        Args:
            image_paths: List of image paths
            output_dir: Optional directory to save results
            
        Returns:
            List of processing results
        """
        try:
            logger.info(f"Starting batch processing for {len(image_paths)} images")
            results = []
            
            for i, image_path in enumerate(image_paths):
                logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")
                
                # Create output path if directory provided
                output_path = None
                if output_dir:
                    import os
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    output_path = os.path.join(output_dir, f"{base_name}_result.json")
                
                # Process image
                result = self.process_image(image_path, output_path)
                results.append(result)
                
                # Add delay between images to avoid rate limiting
                if i < len(image_paths) - 1:
                    time.sleep(1)
            
            logger.info(f"Batch processing completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise
    
    def _create_final_result(self, image_path: str, boxes: List[Dict], 
                           processed_data: Dict, detection_metadata: Dict, 
                           start_time: float) -> Dict:
        """Create final result structure"""
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "processing_time": round(time.time() - start_time, 2),
            "raw_data": {
                "total_boxes": len(boxes),
                "image_path": image_path,
                "detection_params": detection_metadata["detection_params"],
                "boxes": boxes
            },
            "processed_data": processed_data
        }
    
    def _create_empty_result(self, image_path: str, reason: str) -> Dict:
        """Create empty result structure"""
        return {
            "status": "empty",
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "raw_data": {
                "total_boxes": 0,
                "image_path": image_path,
                "boxes": []
            },
            "processed_data": {
                "questions_found": 0,
                "question_groups": [],
                "orphan_boxes": {
                    "above_first_question": [],
                    "below_last_question": []
                }
            }
        }
    
    def _create_error_result(self, image_path: str, error_message: str) -> Dict:
        """Create error result structure"""
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "raw_data": {
                "total_boxes": 0,
                "image_path": image_path,
                "boxes": []
            },
            "processed_data": {
                "questions_found": 0,
                "question_groups": [],
                "orphan_boxes": {
                    "above_first_question": [],
                    "below_last_question": []
                }
            }
        }
    
    def _save_result(self, result: Dict, output_path: str):
        """Save result to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"Result saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline configuration and stats"""
        return {
            "config": {
                "yolo_model": self.config.YOLO_REPO_ID,
                "iou_threshold": self.config.IOU_THRESHOLD,
                "conf_threshold": self.config.CONFIDENCE_THRESHOLD,
                "target_classes": self.config.TARGET_CLASSES if self.config.TARGET_CLASSES else "all_classes",
                "ocr_classes": self.config.OCR_CLASSES,
                "max_retries": self.config.MAX_RETRIES,
                "batch_size": self.config.OCR_BATCH_SIZE
            }
        }