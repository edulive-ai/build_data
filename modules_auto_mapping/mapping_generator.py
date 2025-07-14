import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class MappingGenerator:
    """Generate mapping.json format for questions - FIXED VERSION"""
    
    def __init__(self):
        pass
    
    def extract_book_name(self, folder_path: str) -> str:
        """
        Extract book name from folder path
        
        Args:
            folder_path: Path to the folder being processed
            
        Returns:
            Book name based on folder name
        """
        try:
            folder_name = os.path.basename(os.path.abspath(folder_path))
            return folder_name
        except Exception as e:
            logger.error(f"Error extracting book name: {e}")
            return "unknown"
    
    def process_single_image_questions(self, result: Dict, book_name: str, starting_index: int) -> List[Dict]:
        """
        Process questions from single image result
        UPDATED: No crops folder, images directly in subfolder
        
        Args:
            result: Single image processing result
            book_name: Book name for this image
            starting_index: Starting index for questions
            
        Returns:
            List of question mappings for this image
        """
        try:
            if result.get('status') != 'success':
                logger.warning(f"Skipping non-successful result")
                return []
            
            question_groups = result.get('processed_data', {}).get('question_groups', [])
            questions_mapping = []
            
            logger.debug(f"Processing {len(question_groups)} question groups")
            
            for i, group in enumerate(question_groups):
                try:
                    question_bbox = group.get('question_bbox', {})
                    related_boxes = group.get('related_boxes', [])
                    
                    logger.debug(f"Question group {i}: {len(related_boxes)} related boxes")
                    
                    # Build question text (main question + related OCR texts)
                    question_texts = []
                    
                    # Add main question text
                    main_question_text = question_bbox.get('ocr_text', '').strip()
                    if main_question_text:
                        question_texts.append(main_question_text)
                        logger.debug(f"Main question: '{main_question_text[:30]}...'")
                    
                    # Add related OCR texts (from cls 0,1,2 with OCR text)
                    for j, box in enumerate(related_boxes):
                        if box.get('cls') in [0, 1, 2] and box.get('ocr_text'):
                            related_text = box.get('ocr_text', '').strip()
                            if related_text:
                                question_texts.append(related_text)
                                logger.debug(f"Related OCR {j}: '{related_text[:30]}...'")
                    
                    # Join all texts with newlines
                    full_question_text = '\n'.join(question_texts) if question_texts else ""
                    
                    # Collect image paths (from ALL related boxes that have crop_path)
                    # crop_path format should be: "image_name/bbox_xxx.png" (no crops folder)
                    image_question_paths = []
                    
                    for j, box in enumerate(related_boxes):
                        crop_path = box.get('crop_path')
                        logger.debug(f"Related box {j}: cls={box.get('cls')}, crop_path='{crop_path}'")
                        
                        if crop_path:
                            # crop_path should already be in format: "image_name/bbox_xxx.png"
                            # This is the relative path format we want in JSON
                            image_question_paths.append(crop_path)
                            logger.debug(f"Added image: {crop_path}")
                    
                    # Also check if question bbox itself has crop_path (in case it's not OCR class)
                    question_crop_path = question_bbox.get('crop_path')
                    if question_crop_path:
                        image_question_paths.append(question_crop_path)
                        logger.debug(f"Added question image: {question_crop_path}")
                    
                    logger.info(f"Question {i+1}: Found {len(image_question_paths)} images")
                    logger.info(f"Question {i+1}: Images = {image_question_paths}")
                    
                    # Create question mapping
                    question_mapping = {
                        "index": starting_index + i,
                        "question": full_question_text,
                        "answer": "null",
                        "image_question": image_question_paths,
                        "image_answer": [],
                        "difficulty": "easy",
                        "book": book_name
                    }
                    
                    questions_mapping.append(question_mapping)
                    
                    logger.info(f"Created question {starting_index + i}: '{full_question_text[:50]}...' with {len(image_question_paths)} images")
                
                except Exception as e:
                    logger.error(f"Error processing question group {i}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            logger.info(f"Final result: {len(questions_mapping)} questions created")
            return questions_mapping
            
        except Exception as e:
            logger.error(f"Error processing image questions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def debug_boxes_structure(self, boxes: List[Dict]) -> None:
        """Debug function to examine boxes structure - UPDATED for no crops folder"""
        logger.info("=== DEBUGGING BOXES STRUCTURE ===")
        logger.info(f"Total boxes: {len(boxes)}")
        
        ocr_boxes = [b for b in boxes if b.get('cls') in [0, 1, 2]]
        crop_boxes = [b for b in boxes if b.get('cls') not in [0, 1, 2]]
        question_boxes = [b for b in boxes if b.get('is_question', False)]
        
        logger.info(f"OCR boxes (cls 0,1,2): {len(ocr_boxes)}")
        logger.info(f"Crop boxes (other cls): {len(crop_boxes)}")
        logger.info(f"Question boxes: {len(question_boxes)}")
        
        # Debug crop boxes - should have crop_path in format "image_name/bbox_xxx.png"
        logger.info("=== CROP BOXES DEBUG ===")
        for i, box in enumerate(crop_boxes[:5]):  # Show first 5 crop boxes
            crop_path = box.get('crop_path')
            logger.info(f"Crop box {i}: cls={box.get('cls')}, label={box.get('label')}, crop_path='{crop_path}'")
            if crop_path:
                # Check if crop_path is in correct format: "folder/filename.png"
                if '/' in crop_path and not crop_path.startswith('/'):
                    logger.info(f"  ✓ Correct relative path format")
                else:
                    logger.warning(f"  ❌ Incorrect path format, should be 'folder/filename.png'")
        
        # Debug question boxes
        logger.info("=== QUESTION BOXES DEBUG ===")
        for i, box in enumerate(question_boxes):
            logger.info(f"Question {i}: cls={box.get('cls')}, text='{box.get('ocr_text', '')[:30]}...'")
        
        logger.info("=== END DEBUG ===")
        
        # Summary for easy reading
        crop_with_paths = [b for b in crop_boxes if b.get('crop_path')]
        logger.info(f"📊 SUMMARY: {len(crop_with_paths)}/{len(crop_boxes)} crop boxes have crop_path")
        if crop_with_paths:
            logger.info(f"📊 Sample crop paths: {[b.get('crop_path') for b in crop_with_paths[:3]]}")
        else:
            logger.warning(f"⚠️ NO crop boxes have crop_path! This is why image_question is empty.")
    
    def generate_mapping_for_folder(self, folder_results: List[Dict], folder_path: str, output_path: str) -> str:
        """
        Generate mapping.json for entire folder
        
        Args:
            folder_results: List of all image processing results
            folder_path: Path to source folder
            output_path: Path to save mapping.json
            
        Returns:
            Path to generated mapping file
        """
        try:
            # Extract book name from folder
            book_name = self.extract_book_name(folder_path)
            
            logger.info(f"Generating mapping for book: {book_name}")
            
            # Process all images
            all_questions = []
            current_index = 1
            
            for i, result in enumerate(folder_results):
                if result.get('status') == 'success':
                    logger.info(f"Processing result {i+1} for mapping...")
                    
                    # Debug boxes structure
                    boxes = result.get('raw_data', {}).get('boxes', [])
                    self.debug_boxes_structure(boxes)
                    
                    image_questions = self.process_single_image_questions(
                        result, 
                        book_name, 
                        current_index
                    )
                    all_questions.extend(image_questions)
                    current_index += len(image_questions)
                    
                    logger.info(f"Added {len(image_questions)} questions from image {i+1}")
                else:
                    logger.warning(f"Skipping failed result {i+1}")
            
            # Save mapping file
            mapping_file_path = os.path.join(output_path, "mapping.json")
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_questions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Generated mapping with {len(all_questions)} total questions")
            logger.info(f"Mapping saved to: {mapping_file_path}")
            
            return mapping_file_path
            
        except Exception as e:
            logger.error(f"Error generating folder mapping: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def generate_mapping_for_single_image(self, result: Dict, image_path: str, output_path: str) -> str:
        """
        Generate mapping.json for single image
        
        Args:
            result: Single image processing result
            image_path: Path to source image
            output_path: Path to save mapping.json
            
        Returns:
            Path to generated mapping file
        """
        try:
            # Extract book name from image path (parent folder)
            parent_folder = os.path.dirname(image_path)
            book_name = self.extract_book_name(parent_folder)
            
            logger.info(f"Generating mapping for single image, book: {book_name}")
            
            # Debug boxes structure
            boxes = result.get('raw_data', {}).get('boxes', [])
            self.debug_boxes_structure(boxes)
            
            # Process single image
            questions = self.process_single_image_questions(result, book_name, 1)
            
            # Save mapping file
            mapping_file_path = os.path.join(output_path, "mapping.json")
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Generated mapping with {len(questions)} questions")
            logger.info(f"Mapping saved to: {mapping_file_path}")
            
            return mapping_file_path
            
        except Exception as e:
            logger.error(f"Error generating single image mapping: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def get_mapping_statistics(self, mapping_data: List[Dict]) -> Dict:
        """
        Get statistics for mapping data
        
        Args:
            mapping_data: List of question mappings
            
        Returns:
            Statistics dictionary
        """
        try:
            total_questions = len(mapping_data)
            total_images = sum(len(q.get('image_question', [])) for q in mapping_data)
            
            # Count by book
            books = {}
            for q in mapping_data:
                book = q.get('book', 'unknown')
                books[book] = books.get(book, 0) + 1
            
            # Count empty image_question
            empty_image_questions = sum(1 for q in mapping_data if not q.get('image_question'))
            
            return {
                "total_questions": total_questions,
                "total_question_images": total_images,
                "empty_image_questions": empty_image_questions,
                "books": books,
                "avg_images_per_question": round(total_images / total_questions, 2) if total_questions > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating mapping statistics: {e}")
            return {}