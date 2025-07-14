import logging
from typing import List, Dict, Tuple
from .utils import GeometryUtils

logger = logging.getLogger(__name__)

class BBoxProcessor:
    """Process and group bounding boxes - COMPLETE VERSION"""
    
    def __init__(self, config):
        """
        Initialize bbox processor
        
        Args:
            config: Configuration object
        """
        self.config = config
    
    def extract_questions(self, boxes: List[Dict]) -> List[Dict]:
        """
        Extract boxes that are classified as questions
        
        Args:
            boxes: List of all boxes with classification
            
        Returns:
            List of question boxes sorted by position
        """
        try:
            questions = [box for box in boxes if box.get("is_question", False)]
            
            # Sort questions by top position (y1 coordinate)
            questions_sorted = GeometryUtils.sort_boxes_by_position(questions, 'top')
            
            logger.info(f"Found {len(questions_sorted)} questions")
            for i, q in enumerate(questions_sorted):
                logger.info(f"Question {i+1}: y1={q['bbox'][1]:.1f}, text='{q.get('ocr_text', '')[:50]}...'")
            
            return questions_sorted
            
        except Exception as e:
            logger.error(f"Error extracting questions: {e}")
            return []
    
    def extract_non_questions(self, boxes: List[Dict]) -> List[Dict]:
        """
        Extract boxes that are not questions
        
        Args:
            boxes: List of all boxes with classification
            
        Returns:
            List of non-question boxes sorted by position
        """
        try:
            non_questions = [box for box in boxes if not box.get("is_question", False)]
            
            # Sort by top position
            non_questions_sorted = GeometryUtils.sort_boxes_by_position(non_questions, 'top')
            
            logger.info(f"Found {len(non_questions_sorted)} non-question boxes")
            return non_questions_sorted
            
        except Exception as e:
            logger.error(f"Error extracting non-questions: {e}")
            return []
    
    def group_boxes_by_questions(self, questions: List[Dict], non_questions: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Group non-question boxes with their corresponding questions
        
        Args:
            questions: List of question boxes (sorted by position)
            non_questions: List of non-question boxes (sorted by position)
            
        Returns:
            Tuple of (question_groups, orphan_boxes)
        """
        try:
            if not questions:
                logger.warning("No questions found, all boxes will be orphaned")
                return [], {
                    "above_first_question": [],
                    "below_last_question": non_questions
                }
            
            logger.info(f"Grouping {len(non_questions)} boxes with {len(questions)} questions")
            
            question_groups = []
            orphan_boxes = {
                "above_first_question": [],
                "below_last_question": []
            }
            
            # Get question boundaries
            first_question_y = questions[0]["bbox"][1]  # Top of first question
            last_question_y = questions[-1]["bbox"][1]   # Top of last question
            
            # Initialize groups for each question
            for i, question in enumerate(questions):
                position = "top" if i == 0 else "middle" if i < len(questions) - 1 else "bottom"
                
                question_groups.append({
                    "question_id": question["id"],
                    "question_bbox": {
                        **question,
                        "position": position
                    },
                    "related_boxes": []
                })
            
            # Process each non-question box
            for box in non_questions:
                box_y = box["bbox"][1]  # Top of box
                assigned = False
                
                # Check if box is above first question
                if box_y < first_question_y:
                    orphan_boxes["above_first_question"].append({
                        **box,
                        "relation": "above_first_question"
                    })
                    assigned = True
                    continue
                
                # Check if box is below last question
                if box_y > last_question_y:
                    # Find the bottom of the last question
                    last_question_bottom = questions[-1]["bbox"][3]
                    
                    # If box is below the last question, assign to last question
                    if box_y >= last_question_bottom:
                        question_groups[-1]["related_boxes"].append({
                            **box,
                            "relation": "below_question"
                        })
                    else:
                        # Box is between top and bottom of last question
                        orphan_boxes["below_last_question"].append({
                            **box,
                            "relation": "below_last_question"
                        })
                    assigned = True
                    continue
                
                # Find which question this box belongs to
                for i in range(len(questions)):
                    current_question_y = questions[i]["bbox"][1]
                    
                    # If this is the last question, assign remaining boxes to it
                    if i == len(questions) - 1:
                        question_groups[i]["related_boxes"].append({
                            **box,
                            "relation": "below_question"
                        })
                        assigned = True
                        break
                    
                    # Check if box is between current and next question
                    next_question_y = questions[i + 1]["bbox"][1]
                    
                    if current_question_y <= box_y < next_question_y:
                        question_groups[i]["related_boxes"].append({
                            **box,
                            "relation": "below_question"
                        })
                        assigned = True
                        break
                
                # If somehow not assigned, add to orphans
                if not assigned:
                    logger.warning(f"Box {box['id']} could not be assigned to any question")
                    orphan_boxes["below_last_question"].append({
                        **box,
                        "relation": "unassigned"
                    })
            
            # Log grouping results
            for i, group in enumerate(question_groups):
                related_count = len(group["related_boxes"])
                question_text = group["question_bbox"].get("ocr_text", "")[:30]
                logger.info(f"Question {i+1}: '{question_text}...' has {related_count} related boxes")
            
            orphan_above = len(orphan_boxes["above_first_question"])
            orphan_below = len(orphan_boxes["below_last_question"])
            logger.info(f"Orphan boxes: {orphan_above} above first question, {orphan_below} below last question")
            
            return question_groups, orphan_boxes
            
        except Exception as e:
            logger.error(f"Error grouping boxes by questions: {e}")
            return [], {"above_first_question": [], "below_last_question": non_questions}
    
    def process_document_structure(self, boxes: List[Dict]) -> Dict:
        """
        Process complete document structure
        
        Args:
            boxes: List of all boxes with OCR and classification
            
        Returns:
            Processed document structure
        """
        try:
            logger.info("Processing document structure...")
            
            # Extract questions and non-questions
            questions = self.extract_questions(boxes)
            non_questions = self.extract_non_questions(boxes)
            
            # Group boxes by questions
            question_groups, orphan_boxes = self.group_boxes_by_questions(questions, non_questions)
            
            # Create processed structure
            processed_data = {
                "questions_found": len(questions),
                "question_groups": question_groups,
                "orphan_boxes": orphan_boxes
            }
            
            logger.info("Document structure processing complete")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing document structure: {e}")
            raise
    
    def validate_structure(self, processed_data: Dict) -> bool:
        """
        Validate processed document structure
        
        Args:
            processed_data: Processed document structure
            
        Returns:
            True if structure is valid
        """
        try:
            # Check if we have questions
            if processed_data["questions_found"] == 0:
                logger.warning("No questions found in document")
                return False
            
            # Check if all groups have valid structure
            for i, group in enumerate(processed_data["question_groups"]):
                if "question_bbox" not in group:
                    logger.error(f"Question group {i} missing question_bbox")
                    return False
                
                if "related_boxes" not in group:
                    logger.error(f"Question group {i} missing related_boxes")
                    return False
            
            logger.info("Document structure validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Structure validation failed: {e}")
            return False