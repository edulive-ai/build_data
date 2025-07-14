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
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_crop_for_box(image_path: str, box: Dict, image_output_dir: str, image_index: int) -> str:
    """Save crop for box with fixed directory structure - image_0001 format"""
    try:
        from modules_auto_mapping.utils import ImageUtils
        
        # Generate crop filename
        crop_filename = f"bbox_{box['id']:03d}_{box['label']}_cls{box['cls']}.png"
        crop_path = os.path.join(image_output_dir, crop_filename)
        
        # Crop and save
        ImageUtils.crop_bbox(image_path, box['bbox'], crop_path)
        
        # Return relative path: image_0001/crop_filename (fixed format)
        relative_path = f"image_{image_index:04d}/{crop_filename}"
        
        logger.info(f"   Saved crop: {relative_path}")
        return relative_path
        
    except Exception as e:
        logger.error(f"   Failed to crop box {box['id']}: {e}")
        return None

def process_single_image(image_path: str, output_dir: str, image_index: int = 1) -> Dict:
    """Process single image with fixed directory structure"""
    try:
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        # Fixed directory structure: image_0001, image_0002, etc.
        image_dir_name = f"image_{image_index:04d}"
        
        print(f"\n{'='*60}")
        print(f"Processing: {image_name} → {image_dir_name}")
        print(f"{'='*60}")
        
        # Setup directories with fixed structure
        image_output_dir = os.path.join(output_dir, image_dir_name)
        os.makedirs(image_output_dir, exist_ok=True)
        
        # Initialize pipeline
        from pipeline import DocumentProcessingPipeline
        config_override = {
            'TARGET_CLASSES': None,  # Detect all classes
            'OCR_CLASSES': [0, 1, 2]  # Only OCR these classes
        }
        pipeline = DocumentProcessingPipeline(config_override)
        
        start_time = time.time()
        
        # Step 1: Detection
        print("🔍 Step 1: Document detection...")
        boxes, detection_metadata = pipeline.detector.detect_and_deduplicate(image_path)
        
        if not boxes:
            print("❌ No boxes detected")
            return create_empty_result(image_path, "No boxes detected")
        
        print(f"   Detected {len(boxes)} boxes")
        
        # Separate classes
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
        
        # Step 2: Process non-OCR classes with fixed directory structure
        processed_boxes = []
        
        if crop_classes:
            print("✂️ Step 2: Cropping non-OCR classes...")
            for box in crop_classes:
                box_copy = box.copy()
                relative_crop_path = save_crop_for_box(image_path, box_copy, image_output_dir, image_index)
                box_copy['crop_path'] = relative_crop_path
                box_copy['ocr_text'] = None
                box_copy['is_question'] = False
                processed_boxes.append(box_copy)
        else:
            print("⏭️ Step 2: No non-OCR classes to crop")
        
        # Step 3-4: OCR and classification
        if ocr_classes:
            print("🔤 Step 3: OCR processing...")
            ocr_processed = pipeline.ocr_service.process_boxes_batch(image_path, ocr_classes)
            
            print("❓ Step 4: Question classification...")
            classified_boxes = pipeline.question_classifier.process_boxes(ocr_processed)
            
            processed_boxes.extend(classified_boxes)
        else:
            print("⏭️ Step 3-4: No OCR classes to process")
        
        # Step 5: Document structure processing
        print("🏗️ Step 5: Document structure processing...")
        processed_data = pipeline.bbox_processor.process_document_structure(processed_boxes)
        
        # Step 6: Generate mapping
        print("📋 Step 6: Generating mapping format...")
        from modules_auto_mapping.mapping_generator import MappingGenerator
        mapping_generator = MappingGenerator()
        
        preliminary_result = {
            "status": "success",
            "processed_data": processed_data,
            "raw_data": {"boxes": processed_boxes}
        }
        
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
            "image_dir": image_dir_name,
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
        
        # Print summary
        print("✅ Processing completed successfully!")
        print(f"   Directory: {image_dir_name}")
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
    """Process all images in folder with fixed directory structure"""
    try:
        # Find all image files
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif']
        image_files = []
        
        for ext in image_extensions:
            pattern = os.path.join(folder_path, ext)
            image_files.extend(glob.glob(pattern))
            pattern = os.path.join(folder_path, ext.upper())
            image_files.extend(glob.glob(pattern))
        
        image_files = sorted(list(set(image_files)))
        
        if not image_files:
            print(f"❌ No image files found in: {folder_path}")
            return []
        
        print(f"🚀 FOLDER PROCESSING STARTED")
        print(f"📁 Folder: {folder_path}")
        print(f"📊 Found {len(image_files)} images")
        print(f"💾 Output: {output_dir}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Process images with fixed indexing
        results = []
        successful = 0
        failed = 0
        all_mapping_data = []
        current_mapping_index = 1
        start_time = time.time()
        
        for i, image_path in enumerate(image_files):
            image_index = i + 1  # 1-based indexing for directories
            print(f"\n[{i+1}/{len(image_files)}] Processing: {os.path.basename(image_path)} → image_{image_index:04d}")
            
            try:
                result = process_single_image(image_path, output_dir, image_index)
                results.append(result)
                
                if result['status'] == 'success':
                    successful += 1
                    
                    # Update mapping data with correct index
                    mapping_data = result.get('mapping_data', [])
                    for mapping_item in mapping_data:
                        mapping_item['index'] = current_mapping_index
                        all_mapping_data.append(mapping_item)
                        current_mapping_index += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                error_result = create_error_result(image_path, str(e))
                results.append(error_result)
                print(f"❌ Failed: {e}")
            
            if i < len(image_files) - 1:
                time.sleep(0.5)
        
        # Save combined mapping
        print(f"\n📋 Generating combined mapping.json...")
        mapping_path = os.path.join(output_dir, "mapping.json")
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(all_mapping_data, f, ensure_ascii=False, indent=2)
        print(f"📄 Combined mapping saved: {mapping_path}")
        
        # Create summary
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
                    "total_mapping_questions": len(all_mapping_data),
                    "avg_time_per_image": round(total_time / len(image_files), 2) if image_files else 0
                },
                "processed_images": [
                    {
                        "original_name": os.path.basename(img),
                        "directory": f"image_{i+1:04d}"
                    }
                    for i, img in enumerate(image_files)
                ]
            }
        }
        
        summary_path = os.path.join(output_dir, "folder_processing_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"🎉 FOLDER PROCESSING COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Results:")
        print(f"   Total images: {len(image_files)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success rate: {summary['folder_processing_summary']['statistics']['success_rate']:.1f}%")
        print(f"   Total mapping questions: {len(all_mapping_data)}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average per image: {summary['folder_processing_summary']['statistics']['avg_time_per_image']:.2f}s")
        print(f"📄 Summary saved: {summary_path}")
        print(f"📋 Combined mapping: {mapping_path}")
        
        # Print directory mapping
        print(f"\n📁 Directory Structure:")
        for i, img in enumerate(image_files[:5]):  # Show first 5
            print(f"   {os.path.basename(img)} → image_{i+1:04d}/")
        if len(image_files) > 5:
            print(f"   ... and {len(image_files)-5} more")
        
        return results
        
    except Exception as e:
        print(f"❌ Folder processing failed: {e}")
        return []

def process_pdf(pdf_path: str, images_dir: str = "books_to_images", cropped_dir: str = "books_cropped") -> bool:
    """Convert PDF to images then process with fixed directory structure"""
    try:
        from modules_auto_mapping import PDFProcessor
        
        pdf_name = Path(pdf_path).stem
        print(f"🔄 Processing PDF: {pdf_name}")
        
        # Step 1: Convert PDF to images in books_to_images
        print(f"📄 Step 1: Converting PDF to images...")
        processor = PDFProcessor(dpi=300, max_workers=4)
        images_output_dir = os.path.join(images_dir, pdf_name)
        
        result = processor.convert_to_images(pdf_path, images_output_dir)
        
        if result['status'] != 'success':
            print(f"❌ PDF conversion failed: {result.get('error', 'Unknown error')}")
            return False
        
        print(f"✅ PDF converted: {result['successful_pages']}/{result['total_pages']} pages")
        print(f"📁 Images saved to: {images_output_dir}")
        
        # Step 2: Process images with fixed directory structure
        print(f"\n🚀 Step 2: Processing converted images...")
        cropped_output_dir = os.path.join(cropped_dir, pdf_name)
        process_folder(images_output_dir, cropped_output_dir)
        
        print(f"✅ Processing completed for {pdf_name}")
        print(f"📁 Images: {images_output_dir}")
        print(f"📁 Results: {cropped_output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF processing failed: {e}")
        return False

def process_pdf_folder(folder_path: str, images_dir: str = "books_to_images", cropped_dir: str = "books_cropped") -> bool:
    """Convert all PDFs in folder to images then process with fixed directory structure"""
    try:
        from modules_auto_mapping import PDFProcessor
        
        print(f"📚 Processing PDF folder: {folder_path}")
        
        # Find all PDF files
        pdf_files = []
        for ext in ['*.pdf', '*.PDF']:
            pattern = os.path.join(folder_path, ext)
            pdf_files.extend(glob.glob(pattern))
        
        pdf_files = sorted(list(set(pdf_files)))
        
        if not pdf_files:
            print("❌ No PDF files found")
            return False
        
        print(f"📊 Found {len(pdf_files)} PDF files")
        
        # Process each PDF separately
        processor = PDFProcessor(dpi=300, max_workers=4)
        successful_pdfs = 0
        
        for i, pdf_path in enumerate(pdf_files):
            pdf_name = Path(pdf_path).stem
            print(f"\n[{i+1}/{len(pdf_files)}] Processing: {pdf_name}")
            
            try:
                # Step 1: Convert PDF to images
                print(f"📄 Step 1: Converting {pdf_name} to images...")
                images_output_dir = os.path.join(images_dir, pdf_name)
                
                result = processor.convert_to_images(pdf_path, images_output_dir)
                
                if result['status'] != 'success':
                    print(f"❌ PDF conversion failed: {result.get('error', 'Unknown error')}")
                    continue
                
                print(f"✅ PDF converted: {result['successful_pages']}/{result['total_pages']} pages")
                print(f"📁 Images: {images_output_dir}")
                
                # Step 2: Process images with fixed directory structure
                print(f"🚀 Step 2: Processing images for {pdf_name}...")
                cropped_output_dir = os.path.join(cropped_dir, pdf_name)
                process_folder(images_output_dir, cropped_output_dir)
                
                print(f"✅ Completed {pdf_name}")
                print(f"📁 Results: {cropped_output_dir}")
                successful_pdfs += 1
                
                # Small delay between PDFs
                if i < len(pdf_files) - 1:
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Failed to process {pdf_name}: {e}")
                continue
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"🎉 PDF FOLDER PROCESSING COMPLETED")
        print(f"{'='*60}")
        print(f"📊 Results:")
        print(f"   Total PDFs: {len(pdf_files)}")
        print(f"   Successful: {successful_pdfs}")
        print(f"   Failed: {len(pdf_files) - successful_pdfs}")
        print(f"   Success rate: {(successful_pdfs/len(pdf_files)*100):.1f}%")
        print(f"📁 Images directory: {os.path.abspath(images_dir)}")
        print(f"📁 Results directory: {os.path.abspath(cropped_dir)}")
        
        return successful_pdfs > 0
        
    except Exception as e:
        print(f"❌ PDF folder processing failed: {e}")
        return False

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

def detect_input_type(input_path: str) -> str:
    """Detect input type: image, folder, pdf, or pdf_folder"""
    if not os.path.exists(input_path):
        return "invalid"
    
    if os.path.isfile(input_path):
        ext = Path(input_path).suffix.lower()
        if ext == '.pdf':
            return "pdf"
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']:
            return "image"
        else:
            return "unknown_file"
    
    elif os.path.isdir(input_path):
        # Check if folder contains PDFs or images
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf")) + glob.glob(os.path.join(input_path, "*.PDF"))
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif']:
            image_files.extend(glob.glob(os.path.join(input_path, ext)))
            image_files.extend(glob.glob(os.path.join(input_path, ext.upper())))
        
        if pdf_files and not image_files:
            return "pdf_folder"
        elif image_files and not pdf_files:
            return "image_folder"
        elif pdf_files and image_files:
            return "mixed_folder"
        else:
            return "empty_folder"
    
    return "unknown"

def main():
    """Main function with fixed directory structure"""
    parser = argparse.ArgumentParser(description='Document Processing Pipeline - FIXED DIRECTORY STRUCTURE (image_0001)')
    
    parser.add_argument('input_path', help='Path to file or folder (PDF, image, or folder containing PDFs/images)')
    parser.add_argument('-o', '--output', default='books_cropped', help='Output directory for processed results (default: books_cropped)')
    parser.add_argument('--images-dir', default='books_to_images', help='Directory for PDF converted images (default: books_to_images)')
    parser.add_argument('--dpi', type=int, default=300, help='PDF conversion DPI (default: 300)')
    parser.add_argument('--workers', type=int, default=4, help='Max worker threads for PDF conversion (default: 4)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input
    if not os.path.exists(args.input_path):
        print(f"❌ Error: Input path does not exist: {args.input_path}")
        sys.exit(1)
    
    # Detect input type
    input_type = detect_input_type(args.input_path)
    print(f"🔍 Detected input type: {input_type}")
    print(f"📁 Directory structure: image_0001, image_0002, ...")
    
    try:
        if input_type == "pdf":
            # Single PDF processing
            print("📄 SINGLE PDF PROCESSING")
            print(f"📁 Images will be saved to: {args.images_dir}")
            print(f"📁 Results will be saved to: {args.output}")
            success = process_pdf(args.input_path, args.images_dir, args.output)
            if not success:
                print("❌ PDF processing failed")
                sys.exit(1)
                
        elif input_type == "pdf_folder":
            # PDF folder processing
            print("📚 PDF FOLDER PROCESSING")
            print(f"📁 Images will be saved to: {args.images_dir}")
            print(f"📁 Results will be saved to: {args.output}")
            success = process_pdf_folder(args.input_path, args.images_dir, args.output)
            if not success:
                print("❌ PDF folder processing failed")
                sys.exit(1)
                
        elif input_type == "image":
            # Single image processing
            print("🖼️ SINGLE IMAGE PROCESSING")
            result = process_single_image(args.input_path, args.output, 1)
            
            if result['status'] == 'success':
                print(f"\n🎉 Processing completed successfully!")
                
                # Save mapping for single image
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
                
        elif input_type == "image_folder":
            # Image folder processing
            print("🖼️ IMAGE FOLDER PROCESSING")
            results = process_folder(args.input_path, args.output)
            
        elif input_type == "mixed_folder":
            print("📁 MIXED FOLDER DETECTED")
            print("⚠️ Folder contains both PDFs and images.")
            print("📄 Processing PDFs first...")
            success = process_pdf_folder(args.input_path, args.images_dir, args.output)
            if success:
                print("✅ PDF processing completed.")
                print("🖼️ Now processing existing images...")
                process_folder(args.input_path, args.output)
            
        elif input_type == "empty_folder":
            print("❌ Error: Folder contains no PDF or image files")
            sys.exit(1)
            
        elif input_type == "unknown_file":
            print(f"❌ Error: Unsupported file type. Supported: PDF, PNG, JPG, JPEG, BMP, TIFF")
            sys.exit(1)
            
        else:
            print(f"❌ Error: Cannot process input type: {input_type}")
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