#!/usr/bin/env python3
import argparse
import os
import sys
import json
import glob
import time
import logging
from datetime import datetime
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_crop_for_box(image_path: str, box: Dict, image_output_dir: str, image_name: str) -> str:
    """Save crop for box directly in image output directory and return relative path"""
    try:
        from modules_auto_mapping.utils import ImageUtils
        
        # Generate crop filename
        crop_filename = f"bbox_{box['id']:03d}_{box['label']}_cls{box['cls']}.png"
        crop_path = os.path.join(image_output_dir, crop_filename)
        
        # Crop and save
        ImageUtils.crop_bbox(image_path, box['bbox'], crop_path)
        
        # Return relative path: {image_name}/crop_filename
        relative_path = f"{image_name}/{crop_filename}"
        
        logger.info(f"   Saved crop: {relative_path}")
        return relative_path
        
    except Exception as e:
        logger.error(f"   Failed to crop box {box['id']}: {e}")
        return None

def process_single_image(image_path: str, output_dir: str) -> Dict:
    """Process single image with complete pipeline"""
    try:
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        print(f"\n{'='*60}")
        print(f"Processing: {image_name}")
        print(f"{'='*60}")
        
        # Setup directories - no crops subfolder
        image_output_dir = os.path.join(output_dir, image_name)
        os.makedirs(image_output_dir, exist_ok=True)
        
        # Initialize pipeline with config for all classes
        from pipeline import DocumentProcessingPipeline
        config_override = {
            'TARGET_CLASSES': None,  # Detect all classes
            'OCR_CLASSES': [0, 1, 2]  # Only OCR these classes
        }
        pipeline = DocumentProcessingPipeline(config_override)
        
        start_time = time.time()
        
        # Step 1: Detection (all classes)
        print("🔍 Step 1: Document detection...")
        boxes, detection_metadata = pipeline.detector.detect_and_deduplicate(image_path)
        
        if not boxes:
            print("❌ No boxes detected")
            return create_empty_result(image_path, "No boxes detected")
        
        print(f"   Detected {len(boxes)} boxes")
        
        # Count classes
        class_counts = {}
        ocr_classes = []
        crop_classes = []
        
        for box in boxes:
            label = f"{box['label']}(cls{box['cls']})"
            class_counts[label] = class_counts.get(label, 0) + 1
            
            if box['cls'] in [0, 1, 2]:
                ocr_classes.append(box)
            else:
                crop_classes.append(box)
        
        print(f"   Classes: {class_counts}")
        print(f"   OCR classes (0,1,2): {len(ocr_classes)} boxes")
        print(f"   Crop classes (others): {len(crop_classes)} boxes")
        
        # Step 2: Process non-OCR classes (crop and save directly in subfolder)
        processed_boxes = []
        
        if crop_classes:
            print("✂️ Step 2: Cropping non-OCR classes...")
            for box in crop_classes:
                box_copy = box.copy()
                relative_crop_path = save_crop_for_box(image_path, box_copy, image_output_dir, image_name)
                box_copy['crop_path'] = relative_crop_path
                box_copy['ocr_text'] = None
                box_copy['is_question'] = False  # Non-OCR classes are not questions
                processed_boxes.append(box_copy)
        else:
            print("⏭️ Step 2: No non-OCR classes to crop")
        
        # Step 3: OCR for classes 0,1,2
        if ocr_classes:
            print("🔤 Step 3: OCR processing...")
            ocr_processed = pipeline.ocr_service.process_boxes_batch(image_path, ocr_classes)
            
            # Step 4: Question classification for OCR boxes
            print("❓ Step 4: Question classification...")
            classified_boxes = pipeline.question_classifier.process_boxes(ocr_processed)
            
            processed_boxes.extend(classified_boxes)
        else:
            print("⏭️ Step 3-4: No OCR classes to process")
        
        # Step 5: Document structure processing
        print("🏗️ Step 5: Document structure processing...")
        processed_data = pipeline.bbox_processor.process_document_structure(processed_boxes)
        
        # Step 6: Generate mapping format
        print("📋 Step 6: Generating mapping format...")
        from modules_auto_mapping.mapping_generator import MappingGenerator
        mapping_generator = MappingGenerator()
        
        # Create preliminary result for mapping generation
        preliminary_result = {
            "status": "success",
            "processed_data": processed_data,
            "raw_data": {
                "boxes": processed_boxes
            }
        }
        
        # Generate mapping for this image
        mapping_data = mapping_generator.process_single_image_questions(
            preliminary_result, 
            mapping_generator.extract_book_name(os.path.dirname(image_path)), 
            1
        )
        
        # Create final result
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "processing_time": round(time.time() - start_time, 2),
            "image_name": image_name,
            "output_directory": image_output_dir,
            "raw_data": {
                "total_boxes": len(processed_boxes),
                "image_path": image_path,
                "detection_params": detection_metadata["detection_params"],
                "boxes": processed_boxes
            },
            "processed_data": processed_data,
            "statistics": {
                "class_distribution": class_counts,
                "ocr_boxes": len(ocr_classes),
                "crop_boxes": len(crop_classes),
                "questions_found": processed_data["questions_found"],
                "crops_saved": len([b for b in crop_classes if b.get('crop_path')]),
                "mapping_questions": len(mapping_data)
            },
            "mapping_data": mapping_data
        }
        
        # NO LONGER SAVE INDIVIDUAL JSONs - only keep for processing
        
        # Print summary
        print("✅ Processing completed successfully!")
        print(f"   Total boxes: {len(processed_boxes)}")
        print(f"   OCR boxes: {len(ocr_classes)}")
        print(f"   Crop boxes: {len(crop_classes)}")
        print(f"   Questions found: {processed_data['questions_found']}")
        print(f"   Mapping questions: {len(mapping_data)}")
        print(f"   Processing time: {result['processing_time']:.2f}s")
        
        if crop_classes:
            successful_crops = len([b for b in processed_boxes if b.get('crop_path')])
            print(f"   Crops saved: {successful_crops}/{len(crop_classes)} in {image_output_dir}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error processing {os.path.basename(image_path)}: {e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return create_error_result(image_path, str(e))

def process_folder(folder_path: str, output_dir: str) -> List[Dict]:
    """Process all images in folder"""
    try:
        # Find all image files
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif']
        image_files = []
        
        for ext in image_extensions:
            pattern = os.path.join(folder_path, ext)
            image_files.extend(glob.glob(pattern))
            # Also check uppercase
            pattern = os.path.join(folder_path, ext.upper())
            image_files.extend(glob.glob(pattern))
        
        # Remove duplicates and sort
        image_files = sorted(list(set(image_files)))
        
        if not image_files:
            print(f"❌ No image files found in: {folder_path}")
            return []
        
        print(f"🚀 FOLDER PROCESSING STARTED")
        print(f"📁 Folder: {folder_path}")
        print(f"📊 Found {len(image_files)} images")
        print(f"💾 Output: {output_dir}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each image
        results = []
        successful = 0
        failed = 0
        total_boxes = 0
        total_questions = 0
        total_crops = 0
        total_mapping_questions = 0
        
        # For tracking combined mapping
        all_mapping_data = []
        current_index = 1
        
        start_time = time.time()
        
        for i, image_path in enumerate(image_files):
            print(f"\n[{i+1}/{len(image_files)}] Processing: {os.path.basename(image_path)}")
            
            try:
                result = process_single_image(image_path, output_dir)
                results.append(result)
                
                if result['status'] == 'success':
                    successful += 1
                    total_boxes += result['raw_data']['total_boxes']
                    total_questions += result['processed_data']['questions_found']
                    total_crops += result['statistics'].get('crops_saved', 0)
                    total_mapping_questions += result['statistics'].get('mapping_questions', 0)
                    
                    # Update mapping data with correct index
                    mapping_data = result.get('mapping_data', [])
                    for mapping_item in mapping_data:
                        mapping_item['index'] = current_index
                        all_mapping_data.append(mapping_item)
                        current_index += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                error_result = create_error_result(image_path, str(e))
                results.append(error_result)
                print(f"❌ Failed: {e}")
            
            # Add small delay between images
            if i < len(image_files) - 1:
                time.sleep(0.5)
        
        # Save combined mapping.json ONLY
        print(f"\n📋 Generating combined mapping.json...")
        mapping_path = os.path.join(output_dir, "mapping.json")
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(all_mapping_data, f, ensure_ascii=False, indent=2)
        print(f"📄 Combined mapping saved: {mapping_path}")
        print(f"📊 Total mapping questions: {len(all_mapping_data)}")
        
        # Create folder summary
        total_time = time.time() - start_time
        summary = {
            "folder_processing_summary": {
                "folder_path": folder_path,
                "output_directory": output_dir,
                "timestamp": datetime.now().isoformat(),
                "processing_time": round(total_time, 2),
                "statistics": {
                    "total_images": len(image_files),
                    "successful_images": successful,
                    "failed_images": failed,
                    "success_rate": round((successful / len(image_files) * 100), 2) if image_files else 0,
                    "total_boxes_detected": total_boxes,
                    "total_questions_found": total_questions,
                    "total_crops_saved": total_crops,
                    "total_mapping_questions": len(all_mapping_data),
                    "avg_time_per_image": round(total_time / len(image_files), 2) if image_files else 0
                },
                "processed_images": [os.path.basename(img) for img in image_files]
            }
        }
        
        # Save summary
        summary_path = os.path.join(output_dir, "folder_processing_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"🎉 FOLDER PROCESSING COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Results:")
        print(f"   Total images: {len(image_files)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {summary['folder_processing_summary']['statistics']['success_rate']:.1f}%")
        print(f"   Total boxes: {total_boxes}")
        print(f"   Total questions: {total_questions}")
        print(f"   Total mapping questions: {len(all_mapping_data)}")
        print(f"   Total crops saved: {total_crops}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average per image: {summary['folder_processing_summary']['statistics']['avg_time_per_image']:.2f}s")
        print(f"📄 Summary saved: {summary_path}")
        print(f"📋 Combined mapping: {mapping_path}")
        
        return results
        
    except Exception as e:
        print(f"❌ Folder processing failed: {e}")
        return []

def create_empty_result(image_path: str, reason: str) -> Dict:
    """Create empty result structure"""
    return {
        "status": "empty",
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "image_path": image_path,
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

def create_error_result(image_path: str, error_message: str) -> Dict:
    """Create error result structure"""
    return {
        "status": "error",
        "timestamp": datetime.now().isoformat(),
        "error": error_message,
        "image_path": image_path,
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

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Document Processing Pipeline - UPDATED FINAL VERSION')
    
    # Arguments
    parser.add_argument('input_path', help='Path to image file or folder')
    parser.add_argument('-o', '--output', default='output', help='Output directory (default: output)')
    parser.add_argument('--folder', action='store_true', help='Process entire folder (auto-detected if path is directory)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input
    if not os.path.exists(args.input_path):
        print(f"❌ Error: Input path does not exist: {args.input_path}")
        sys.exit(1)
    
    # Auto-detect if input is folder
    is_folder = os.path.isdir(args.input_path)
    if is_folder and not args.folder:
        print("📁 Auto-detected folder input, enabling folder mode...")
        args.folder = True
    
    try:
        if args.folder or is_folder:
            # Folder processing
            if not os.path.isdir(args.input_path):
                print(f"❌ Error: Folder mode requires directory input")
                sys.exit(1)
            
            results = process_folder(args.input_path, args.output)
            
        else:
            # Single image processing
            if not os.path.isfile(args.input_path):
                print(f"❌ Error: Single image mode requires file input")
                sys.exit(1)
            
            print("🚀 SINGLE IMAGE PROCESSING")
            result = process_single_image(args.input_path, args.output)
            
            if result['status'] == 'success':
                print(f"\n🎉 Processing completed successfully!")
                
                # For single image, save mapping.json
                mapping_data = result.get('mapping_data', [])
                if mapping_data:
                    mapping_path = os.path.join(args.output, "mapping.json")
                    with open(mapping_path, 'w', encoding='utf-8') as f:
                        json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                    print(f"📋 Mapping saved: {mapping_path}")
                
                # Print question details
                for i, group in enumerate(result['processed_data']['question_groups']):
                    question_text = group['question_bbox'].get('ocr_text', '')[:50]
                    related_count = len(group['related_boxes'])
                    print(f"   Question {i+1}: '{question_text}...' ({related_count} related boxes)")
                
            elif result['status'] == 'empty':
                print(f"\n⚠️ No content detected: {result['reason']}")
            else:
                print(f"\n❌ Processing failed: {result['error']}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Critical error: {e}")
        logger.exception("Critical error details:")
        sys.exit(1)

if __name__ == "__main__":
    main()