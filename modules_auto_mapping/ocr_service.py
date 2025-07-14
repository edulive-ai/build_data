import requests
import json
import time
import logging
from typing import List, Dict, Optional
from .utils import ImageUtils

logger = logging.getLogger(__name__)

class OCRService:
    """DeepSeek Vision OCR service - COMPLETE VERSION"""
    
    def __init__(self, config):
        """
        Initialize OCR service
        
        Args:
            config: Configuration object with API settings
        """
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.DEEPSEAK_API_KEY}"
        }
    
    def _make_api_call(self, image_base64_url: str, prompt: str) -> Optional[str]:
        """
        Make single API call to DeepSeek Vision
        
        Args:
            image_base64_url: Base64 encoded image
            prompt: OCR prompt
            
        Returns:
            Extracted text or None if failed
        """
        payload = {
            "model": self.config.DEEPSEAK_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_base64_url}
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.config.DEEPSEAK_API_ENDPOINT,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                return content.strip()
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            return None
    
    def ocr_with_retry(self, image_path: str) -> Optional[str]:
        """
        OCR image with retry mechanism
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text or None if all retries failed
        """
        try:
            # Convert image to base64
            image_base64 = ImageUtils.image_to_base64(image_path)
            
            # Retry loop
            for attempt in range(self.config.MAX_RETRIES):
                logger.debug(f"OCR attempt {attempt + 1}/{self.config.MAX_RETRIES} for {image_path}")
                
                result = self._make_api_call(image_base64, self.config.OCR_PROMPT)
                
                if result:
                    logger.debug(f"OCR successful on attempt {attempt + 1}")
                    return result
                
                if attempt < self.config.MAX_RETRIES - 1:
                    logger.debug(f"Retrying in {self.config.RETRY_DELAY} seconds...")
                    time.sleep(self.config.RETRY_DELAY)
            
            logger.error(f"OCR failed after {self.config.MAX_RETRIES} attempts")
            return None
            
        except Exception as e:
            logger.error(f"OCR error for {image_path}: {e}")
            return None
    
    def process_boxes_batch(self, image_path: str, boxes: List[Dict]) -> List[Dict]:
        """
        Process multiple boxes - OCR only for OCR_CLASSES
        
        Args:
            image_path: Path to source image
            boxes: List of box dictionaries
            
        Returns:
            Updated boxes with OCR text (only for OCR classes)
        """
        try:
            # Filter boxes that need OCR
            ocr_boxes = [box for box in boxes if box['cls'] in self.config.OCR_CLASSES]
            
            logger.info(f"Processing {len(ocr_boxes)} OCR boxes (classes {self.config.OCR_CLASSES})")
            
            temp_files = []
            updated_boxes = []
            
            for box in boxes:
                updated_box = box.copy()
                
                if box['cls'] in self.config.OCR_CLASSES:
                    # Process OCR for this box
                    try:
                        # Crop bbox
                        crop_path = ImageUtils.crop_bbox(
                            image_path, 
                            box["bbox"], 
                            f"temp_crop_{box['id']}.png"
                        )
                        temp_files.append(crop_path)
                        
                        # OCR cropped image
                        ocr_text = self.ocr_with_retry(crop_path)
                        updated_box["ocr_text"] = ocr_text
                        
                        logger.info(f"   Box {box['id']} (cls{box['cls']}): OCR {'success' if ocr_text else 'failed'}")
                        
                        # Add delay between requests
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error processing OCR box {box['id']}: {e}")
                        updated_box["ocr_text"] = None
                else:
                    # Non-OCR class, skip OCR
                    updated_box["ocr_text"] = None
                
                updated_boxes.append(updated_box)
            
            # Cleanup temp files
            ImageUtils.cleanup_temp_files(temp_files)
            
            logger.info(f"OCR processing complete: {len(ocr_boxes)} OCR boxes processed")
            return updated_boxes
            
        except Exception as e:
            logger.error(f"Batch OCR processing failed: {e}")
            raise