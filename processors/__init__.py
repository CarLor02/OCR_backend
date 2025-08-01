"""
处理器模块
提供各种文件类型的OCR处理功能
"""

from .base import BaseProcessor
from .pdf_processor import PDFProcessor
from .image_processor import ImageProcessor
from .excel_processor import ExcelProcessor
from .html_processor import HTMLProcessor

__all__ = [
    'BaseProcessor',
    'PDFProcessor', 
    'ImageProcessor',
    'ExcelProcessor',
    'HTMLProcessor'
]
