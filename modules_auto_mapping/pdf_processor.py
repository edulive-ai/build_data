import fitz  # PyMuPDF
import os
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Tuple, List, Dict, Optional, Callable
import time
import glob

logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF to PNG converter with multi-threading support - OPTIMIZED VERSION"""
    
    def __init__(self, dpi: int = 300, max_workers: int = 4, batch_size: int = 10):
        """
        Initialize PDF processor
        
        Args:
            dpi: Output image DPI (default: 300)
            max_workers: Maximum number of worker threads
            batch_size: Number of pages to process in each batch
        """
        self.dpi = dpi
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.zoom_factor = dpi / 72
        self.print_lock = threading.Lock()
        
        logger.info(f"PDFProcessor initialized: DPI={dpi}, Workers={max_workers}, Batch={batch_size}")
    
    def _safe_print(self, message: str):
        """Thread-safe printing"""
        with self.print_lock:
            print(message)
    
    def _process_single_page(self, args: Tuple) -> Tuple[bool, str, int]:
        """
        Process single PDF page to PNG
        
        Args:
            args: (pdf_file, page_num, output_dir, pdf_name, zoom_factor)
        
        Returns:
            (success, message, page_number)
        """
        pdf_file, page_num, output_dir, pdf_name, zoom_factor = args
        
        try:
            doc = fitz.open(pdf_file)
            page = doc[page_num]
            
            # Create transformation matrix
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            
            # Render page to image
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Generate image filename
            image_name = f"{pdf_name}_page_{page_num + 1:03d}.png"
            image_path = os.path.join(output_dir, image_name)
            
            # Save image
            pix.save(image_path)
            
            # Cleanup
            pix = None
            doc.close()
            
            return True, f"✓ {image_name}", page_num + 1
            
        except Exception as e:
            return False, f"❌ Page {page_num + 1}: {str(e)}", page_num + 1
    
    def _get_optimal_workers(self, total_pages: int) -> int:
        """Calculate optimal workers based on page count"""
        if total_pages <= 10:
            return min(2, self.max_workers)
        elif total_pages <= 50:
            return min(4, self.max_workers)
        elif total_pages <= 100:
            return min(6, self.max_workers)
        else:
            return self.max_workers
    
    def convert_to_images(self, pdf_path: str, output_dir: str, 
                         progress_callback: Optional[Callable] = None) -> Dict:
        """
        Convert PDF to PNG images
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for images
            progress_callback: Optional callback for progress updates
        
        Returns:
            Conversion result dictionary
        """
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Get PDF info
            pdf_name = Path(pdf_path).stem
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            # Calculate optimal settings
            optimal_workers = self._get_optimal_workers(total_pages)
            use_batch = total_pages > 50
            
            logger.info(f"Converting {total_pages} pages from '{pdf_name}'")
            logger.info(f"Using {optimal_workers} workers, batch mode: {use_batch}")
            
            start_time = time.time()
            successful_pages = 0
            processed_pages = 0
            
            if use_batch:
                # Batch processing for large PDFs
                for batch_start in range(0, total_pages, self.batch_size):
                    batch_end = min(batch_start + self.batch_size, total_pages)
                    batch_pages = list(range(batch_start, batch_end))
                    
                    self._safe_print(f"📦 Batch {batch_start//self.batch_size + 1}: pages {batch_start + 1}-{batch_end}")
                    
                    batch_args = [
                        (pdf_path, page_num, output_dir, pdf_name, self.zoom_factor)
                        for page_num in batch_pages
                    ]
                    
                    with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
                        future_to_page = {
                            executor.submit(self._process_single_page, args): args[1] 
                            for args in batch_args
                        }
                        
                        for future in as_completed(future_to_page):
                            try:
                                success, message, page_number = future.result()
                                processed_pages += 1
                                
                                if success:
                                    successful_pages += 1
                                
                                # Progress callback
                                if progress_callback:
                                    progress_callback(processed_pages, total_pages, message)
                                
                                # Progress display
                                progress = (processed_pages / total_pages) * 100
                                self._safe_print(f"{message} ({processed_pages}/{total_pages} - {progress:.1f}%)")
                                
                            except Exception as e:
                                self._safe_print(f"❌ Unexpected error: {str(e)}")
                                processed_pages += 1
            else:
                # Simple processing for small PDFs
                all_args = [
                    (pdf_path, page_num, output_dir, pdf_name, self.zoom_factor)
                    for page_num in range(total_pages)
                ]
                
                with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
                    future_to_page = {
                        executor.submit(self._process_single_page, args): args[1] 
                        for args in all_args
                    }
                    
                    for future in as_completed(future_to_page):
                        try:
                            success, message, page_number = future.result()
                            processed_pages += 1
                            
                            if success:
                                successful_pages += 1
                            
                            # Progress callback
                            if progress_callback:
                                progress_callback(processed_pages, total_pages, message)
                            
                            self._safe_print(message)
                            
                        except Exception as e:
                            self._safe_print(f"❌ Error: {str(e)}")
                            processed_pages += 1
            
            # Create result
            total_time = time.time() - start_time
            result = {
                "status": "success",
                "pdf_file": pdf_path,
                "pdf_name": pdf_name,
                "output_directory": output_dir,
                "total_pages": total_pages,
                "successful_pages": successful_pages,
                "failed_pages": total_pages - successful_pages,
                "success_rate": round((successful_pages / total_pages) * 100, 2),
                "processing_time": round(total_time, 2),
                "avg_time_per_page": round(total_time / total_pages, 2),
                "settings": {
                    "dpi": self.dpi,
                    "workers": optimal_workers,
                    "batch_mode": use_batch
                }
            }
            
            logger.info(f"Conversion completed: {successful_pages}/{total_pages} pages ({result['success_rate']}%)")
            logger.info(f"Time: {total_time:.2f}s, Avg: {result['avg_time_per_page']:.2f}s/page")
            
            return result
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pdf_file": pdf_path
            }
    
    def convert_folder(self, folder_path: str, output_base_dir: str = "books_cropped", 
                      progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Convert all PDFs in folder to images
        
        Args:
            folder_path: Path to folder containing PDF files
            output_base_dir: Base output directory
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of conversion results
        """
        try:
            # Find all PDF files
            pdf_files = []
            for ext in ['*.pdf', '*.PDF']:
                pattern = os.path.join(folder_path, ext)
                pdf_files.extend(glob.glob(pattern))
            
            pdf_files = sorted(list(set(pdf_files)))
            
            if not pdf_files:
                logger.warning(f"No PDF files found in: {folder_path}")
                return []
            
            logger.info(f"Found {len(pdf_files)} PDF files to convert")
            
            results = []
            successful_pdfs = 0
            total_pages = 0
            total_successful_pages = 0
            
            start_time = time.time()
            
            for i, pdf_path in enumerate(pdf_files):
                pdf_name = Path(pdf_path).stem
                output_dir = os.path.join(output_base_dir, pdf_name)
                
                print(f"\n[{i+1}/{len(pdf_files)}] Converting: {pdf_name}")
                
                try:
                    result = self.convert_to_images(pdf_path, output_dir, progress_callback)
                    results.append(result)
                    
                    if result['status'] == 'success':
                        successful_pdfs += 1
                        total_pages += result['total_pages']
                        total_successful_pages += result['successful_pages']
                    
                    # Small delay between PDFs
                    if i < len(pdf_files) - 1:
                        time.sleep(0.5)
                        
                except Exception as e:
                    error_result = {
                        "status": "error",
                        "error": str(e),
                        "pdf_file": pdf_path
                    }
                    results.append(error_result)
                    logger.error(f"Failed to convert {pdf_name}: {e}")
            
            # Summary
            total_time = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"🎉 FOLDER CONVERSION COMPLETED")
            print(f"{'='*60}")
            print(f"📊 Results:")
            print(f"   PDFs processed: {len(pdf_files)}")
            print(f"   Successful PDFs: {successful_pdfs}")
            print(f"   Failed PDFs: {len(pdf_files) - successful_pdfs}")
            print(f"   Total pages: {total_pages}")
            print(f"   Successful pages: {total_successful_pages}")
            print(f"   Overall success rate: {(total_successful_pages/total_pages*100):.1f}%" if total_pages > 0 else "0%")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Output directory: {os.path.abspath(output_base_dir)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Folder conversion failed: {e}")
            return []
    
    def validate_pdf(self, pdf_path: str) -> Dict:
        """
        Validate PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Validation result
        """
        try:
            if not os.path.exists(pdf_path):
                return {"valid": False, "error": "File not found"}
            
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            if page_count == 0:
                return {"valid": False, "error": "PDF has no pages"}
            
            return {
                "valid": True,
                "pages": page_count,
                "file_size": os.path.getsize(pdf_path)
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get PDF metadata
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            PDF information
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = len(doc)
            doc.close()
            
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "pages": page_count,
                "file_size": os.path.getsize(pdf_path),
                "file_name": Path(pdf_path).name
            }
            
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {"error": str(e)}