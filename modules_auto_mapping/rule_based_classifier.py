import re
import logging
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class RuleBasedQuestionClassifier:
    """Rule-based question classification cho tiếng Việt - COMPLETE VERSION"""
    
    def __init__(self, config=None):
        """
        Initialize rule-based question classifier
        
        Args:
            config: Configuration object (kept for compatibility)
        """
        self.config = config
        
        # Từ nghi vấn tiếng Việt
        self.question_words = {
            'ai', 'cái gì', 'gì', 'khi nào', 'ở đâu', 'vì sao', 'tại sao', 
            'như thế nào', 'bao nhiêu', 'mấy', 'nào', 'đâu', 'sao',
            'có phải', 'phải không', 'hay không', 'có', 'không'
        }
        
        # Từ yêu cầu hành động
        self.action_words = {
            'hãy', 'bạn hãy', 'em hãy', 'các em hãy', 'các bạn hãy',
            'hãy cho biết', 'cho biết', 'dựa vào', 'tìm', 'nêu', 'trình bày', 
            'giải thích', 'tính', 'viết', 'so sánh', 'phân tích', 'đánh giá',
            'nhận xét', 'xác định', 'chứng minh', 'giải', 'làm', 'thực hiện',
            'hoàn thành', 'điền', 'chọn', 'khoanh tròn', 'gạch chân',
            'đọc', 'nghe', 'xem', 'quan sát', 'mô tả', 'kể', 'liệt kê',
            'sắp xếp', 'phân loại', 'nhóm', 'ghép', 'nối', 'tô màu',
            'vẽ', 'thiết kế', 'tạo', 'xây dựng', 'lập', 'soạn',
            'dịch', 'chuyển', 'đổi', 'biến đổi', 'rút gọn', 'thu gọn',
            'tóm tắt', 'tổng hợp', 'kết luận', 'đưa ra', 'đề xuất'
        }
        
        # Patterns cho câu hỏi
        self.question_patterns = [
            # Bắt đầu bằng từ nghi vấn
            r'^(ai|cái gì|gì|khi nào|ở đâu|vì sao|tại sao|như thế nào|bao nhiêu|mấy|nào|đâu|sao)',
            
            # Bắt đầu bằng từ yêu cầu hành động
            r'^(hãy|bạn hãy|em hãy|các em hãy|các bạn hãy)',
            r'^(tìm|nêu|trình bày|giải thích|tính|viết|so sánh|phân tích)',
            r'^(đánh giá|nhận xét|xác định|chứng minh|giải|làm|thực hiện)',
            r'^(hoàn thành|điền|chọn|khoanh tròn|gạch chân|đọc|nghe)',
            r'^(xem|quan sát|mô tả|kể|liệt kê|sắp xếp|phân loại)',
            r'^(dựa vào|theo|từ|căn cứ vào)',
            r'^(cho biết|hãy cho biết)',
            
            # Bắt đầu bằng số thứ tự
            r'^\d+[\.\)]\s*',
            r'^[a-zA-Z][\.\)]\s*',
            r'^[•·▪▫-]\s*',
            
            # Bắt đầu bằng "Bài", "Câu"
            r'^(bài|câu|phần|chương|mục)\s*\d*[\.\):\s]*',
            
            # Có từ "hay không", "phải không"
            r'.*(hay không|phải không|có phải|đúng không)',
            
            # Có cấu trúc so sánh
            r'.*(khác nhau|giống nhau|so với|hơn|kém)',
        ]
        
        # Compile patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.UNICODE) for pattern in self.question_patterns]
        
        logger.info("Rule-based Question Classifier initialized for Vietnamese")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters at the beginning
        text = re.sub(r'^[^\w\s]*', '', text)
        
        return text.lower()
    
    def _check_question_mark(self, text: str) -> bool:
        """Check if text ends with question mark"""
        return text.strip().endswith('?')
    
    def _check_question_words(self, text: str) -> bool:
        """Check if text contains question words"""
        text_lower = text.lower()
        
        # Check for question words
        for word in self.question_words:
            if word in text_lower:
                return True
        
        # Check for action words at the beginning
        words = text_lower.split()
        if words:
            first_word = words[0]
            if first_word in self.action_words:
                return True
            
            # Check first two words combination
            if len(words) > 1:
                first_two = ' '.join(words[:2])
                if first_two in self.action_words:
                    return True
        
        return False
    
    def _check_patterns(self, text: str) -> bool:
        """Check if text matches question patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _check_imperative_structure(self, text: str) -> bool:
        """Check for imperative/command structure"""
        # Check for typical exercise patterns
        exercise_patterns = [
            r'(tính|giải|tìm|viết|đọc|chọn|điền).*[:\.]',
            r'(dựa vào|theo|từ).*(hãy|tìm|nêu|trình bày)',
            r'(hãy|bạn hãy).*(tính|giải|tìm|viết|nêu)',
        ]
        
        for pattern in exercise_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_question_by_rules(self, text: str) -> bool:
        """
        Determine if text is a question using rule-based approach
        
        Args:
            text: Text to classify
            
        Returns:
            True if question, False otherwise
        """
        if not text or not text.strip():
            return False
        
        cleaned_text = self._clean_text(text)
        
        # Rule 1: Ends with question mark - strong indicator
        if self._check_question_mark(text):
            return True
        
        # Rule 2: Contains question words
        if self._check_question_words(cleaned_text):
            return True
        
        # Rule 3: Matches question patterns
        if self._check_patterns(cleaned_text):
            return True
        
        # Rule 4: Has imperative structure
        if self._check_imperative_structure(cleaned_text):
            return True
        
        # Rule 5: Very short text with action words (likely incomplete question)
        if len(cleaned_text.split()) <= 3:
            for word in self.action_words:
                if word in cleaned_text:
                    return True
        
        return False
    
    def classify_with_retry(self, text: str) -> Optional[bool]:
        """
        Classify text as question (compatible with OpenAI version)
        
        Args:
            text: Text to classify
            
        Returns:
            True if question, False if not, None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for classification")
            return False
        
        try:
            # Rule-based classification
            result = self._is_question_by_rules(text)
            
            logger.debug(f"Rule-based classification: {'YES' if result else 'NO'}")
            logger.debug(f"Text: {text[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return None
    
    def _make_classification_call(self, text: str) -> Optional[bool]:
        """
        Make single classification call (compatible with OpenAI version)
        
        Args:
            text: Text to classify
            
        Returns:
            True if question, False if not, None if failed
        """
        return self.classify_with_retry(text)
    
    def process_boxes(self, boxes: List[Dict]) -> List[Dict]:
        """
        Classify boxes as questions - only for OCR classes with text
        
        Args:
            boxes: List of box dictionaries with OCR text
            
        Returns:
            Updated boxes with question classification
        """
        try:
            # Get OCR classes from config or use default
            ocr_classes = getattr(self.config, 'OCR_CLASSES', [0, 1, 2, 3, 4, 5])
            
            # Filter boxes that have OCR text and are OCR classes
            classifiable_boxes = [
                box for box in boxes 
                if box['cls'] in ocr_classes and box.get('ocr_text')
            ]
            
            logger.info(f"Classifying {len(classifiable_boxes)} boxes with OCR text...")
            
            updated_boxes = []
            question_count = 0
            
            for box in boxes:
                updated_box = box.copy()
                
                # Only classify OCR classes with text
                if box['cls'] in ocr_classes and box.get('ocr_text'):
                    try:
                        is_question = self.classify_with_retry(box['ocr_text'])
                        
                        # If classification failed, assume not a question
                        if is_question is None:
                            is_question = False
                        
                        updated_box["is_question"] = is_question
                        
                        if is_question:
                            question_count += 1
                        
                        logger.info(f"   Box {box['id']} (cls{box['cls']}): {'QUESTION' if is_question else 'NOT_QUESTION'}")
                        
                        # Small delay for consistency (not needed for rule-based but kept for compatibility)
                        time.sleep(0.1)
                        
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

# Alias for backward compatibility
QuestionClassifier = RuleBasedQuestionClassifier