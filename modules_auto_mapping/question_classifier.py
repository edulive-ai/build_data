import openai
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class QuestionClassifier:
    """OpenAI-based question classification - COMPLETE VERSION"""
    
    def __init__(self, config):
        """
        Initialize question classifier
        
        Args:
            config: Configuration object with OpenAI settings
        """
        self.config = config
        openai.api_key = config.OPENAI_API_KEY
    
    def _make_classification_call(self, text: str) -> Optional[bool]:
        """
        Make single classification API call
        
        Args:
            text: Text to classify
            
        Returns:
            True if question, False if not, None if failed
        """
        try:
            prompt = self.config.QUESTION_PROMPT.format(text=text)
            
            response = openai.ChatCompletion.create(
                model=self.config.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                timeout=30
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer.startswith("YES")
            
        except openai.error.OpenAIError as e:
            logger.warning(f"OpenAI API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in classification: {e}")
            return None
    
    def classify_with_retry(self, text: str) -> Optional[bool]:
        """
        Classify text as question with retry mechanism
        
        Args:
            text: Text to classify
            
        Returns:
            True if question, False if not, None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for classification")
            return False
        
        try:
            for attempt in range(self.config.MAX_RETRIES):
                logger.debug(f"Classification attempt {attempt + 1}/{self.config.MAX_RETRIES}")
                
                result = self._make_classification_call(text)
                
                if result is not None:
                    logger.debug(f"Classification successful: {'YES' if result else 'NO'}")
                    return result
                
                if attempt < self.config.MAX_RETRIES - 1:
                    logger.debug(f"Retrying in {self.config.RETRY_DELAY} seconds...")
                    time.sleep(self.config.RETRY_DELAY)
            
            logger.error(f"Classification failed after {self.config.MAX_RETRIES} attempts")
            return None
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return None
    
    def process_boxes(self, boxes: List[Dict]) -> List[Dict]:
        """
        Classify boxes as questions - only for OCR classes with text
        
        Args:
            boxes: List of box dictionaries with OCR text
            
        Returns:
            Updated boxes with question classification
        """
        try:
            # Filter boxes that have OCR text and are OCR classes
            classifiable_boxes = [
                box for box in boxes 
                if box['cls'] in self.config.OCR_CLASSES and box.get('ocr_text')
            ]
            
            logger.info(f"Classifying {len(classifiable_boxes)} boxes with OCR text...")
            
            updated_boxes = []
            question_count = 0
            
            for box in boxes:
                updated_box = box.copy()
                
                # Only classify OCR classes with text
                if box['cls'] in self.config.OCR_CLASSES and box.get('ocr_text'):
                    try:
                        is_question = self.classify_with_retry(box['ocr_text'])
                        
                        # If classification failed, assume not a question
                        if is_question is None:
                            is_question = False
                        
                        updated_box["is_question"] = is_question
                        
                        if is_question:
                            question_count += 1
                        
                        logger.info(f"   Box {box['id']} (cls{box['cls']}): {'QUESTION' if is_question else 'NOT_QUESTION'}")
                        
                        # Add delay between requests
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error classifying box {box['id']}: {e}")
                        updated_box["is_question"] = False
                else:
                    # Non-OCR class or no text, not a question
                    updated_box["is_question"] = False
                
                updated_boxes.append(updated_box)
            
            logger.info(f"Classification complete: {question_count} questions found")
            return updated_boxes
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            raise