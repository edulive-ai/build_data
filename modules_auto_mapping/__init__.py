# modules_auto_mapping/__init__.py - UPDATED WITH PDF PROCESSOR
from .detector import DocumentDetector
from .ocr_service import OCRService
from .question_classifier import QuestionClassifier
from .bbox_processor import BBoxProcessor
from .mapping_generator import MappingGenerator
from .pdf_processor import PDFProcessor
from .utils import ImageUtils, GeometryUtils

__all__ = [
    'DocumentDetector',
    'OCRService', 
    'QuestionClassifier',
    'BBoxProcessor',
    'MappingGenerator',
    'PDFProcessor',
    'ImageUtils',
    'GeometryUtils'
]