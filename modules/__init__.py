# modules/__init__.py
"""
PDF Processing Modules

This package contains modules for processing PDF files:
- pdf_processor: Convert PDF to high-quality images
- yolo_processor: YOLO detection for document layout analysis
- ocr_processor: OCR text recognition from images
- processing_manager: Orchestrates the entire processing pipeline
- gallery_manager: Manages Gallery display and book listing
"""

from .pdf_processor import PDFProcessor
from .yolo_processor import YOLOProcessor
from .ocr_processor import OCRProcessor
from .processing_manager import ProcessingManager
from .gallery_manager import GalleryManager

__version__ = "1.0.0"
__author__ = "PDF Processing Team"

__all__ = [
    'PDFProcessor',
    'YOLOProcessor', 
    'OCRProcessor',
    'ProcessingManager',
    'GalleryManager'
]