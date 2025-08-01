"""
PDF处理器
处理PDF文件，支持普通PDF和扫描PDF的OCR识别
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from .base import BaseProcessor, ProcessingResult

# PDF处理相关导入
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import ImageRefMode
    import warnings
    warnings.filterwarnings("ignore", message="'pin_memory' argument is set as true but not supported on MPS")
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# 扫描PDF检测
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# 图像处理（用于扫描PDF）
try:
    from openai import OpenAI
    import base64
    IMAGE_API_AVAILABLE = True
except ImportError:
    IMAGE_API_AVAILABLE = False


class PDFProcessor(BaseProcessor):
    """PDF文档处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化PDF处理器
        
        Args:
            config: 配置字典，包含API密钥等信息
        """
        super().__init__(config)
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling库未安装，无法处理PDF文件")
        
        # 初始化文档转换器
        self._init_converter()
        
        # API配置
        self.api_key = config.get('yunwu_api_key') if config else None
        self.api_base_url = config.get('yunwu_api_base_url', 'https://yunwu.ai/v1')
        self.model = config.get('gemini_model', 'gemini-2.0-flash-thinking-exp-01-21')
        
        # 处理选项
        self.save_intermediate = config.get('save_intermediate', False) if config else False
    
    def _init_converter(self):
        """初始化文档转换器"""
        
                # 导入加速器选项
        from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice
        import torch
        # 检测可用的设备
        if torch.backends.mps.is_available():
            device = AcceleratorDevice.MPS
            self.logger.info("检测到MPS支持，将使用Apple Silicon GPU加速")
        elif torch.cuda.is_available():
            device = AcceleratorDevice.CUDA
            self.logger.info("检测到CUDA支持，将使用NVIDIA GPU加速")
        else:
            device = AcceleratorDevice.CPU
            self.logger.info("使用CPU处理")
        
        # 配置PDF处理选项
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = False
        # 配置加速器选项
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=8,  # 使用8个线程
            device=device   # 使用检测到的最佳设备
        )
        
        # 创建转换器
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        self.pipeline_options = pipeline_options
        self.pipeline_options = pipeline_options
    
    def get_supported_extensions(self) -> list:
        """获取支持的文件扩展名"""
        return ['.pdf']
    
    def is_scanned_pdf(self, file_path: Path) -> bool:
        """
        检测PDF是否为扫描件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 是否为扫描件
        """
        if not PYMUPDF_AVAILABLE:
            self.logger.warning("PyMuPDF未安装，无法检测扫描PDF，默认按普通PDF处理")
            return False
        
        try:
            doc = fitz.open(file_path)
            total_chars = 0
            sample_pages = min(3, len(doc))  # 检查前3页
            
            for page_num in range(sample_pages):
                page = doc[page_num]
                text = page.get_text()
                total_chars += len(text.strip())
            
            doc.close()
            
            # 如果前几页的文本字符数很少，可能是扫描件
            avg_chars_per_page = total_chars / sample_pages if sample_pages > 0 else 0
            is_scanned = avg_chars_per_page < 100
            
            self.logger.info(f"PDF扫描检测: 平均每页字符数={avg_chars_per_page:.1f}, 是否扫描件={is_scanned}")
            return is_scanned
            
        except Exception as e:
            self.logger.error(f"检测扫描PDF时出错: {e}")
            return False
    
    def process_scanned_pdf_with_api(self, pages_dir: Path) -> str:
        """
        使用API处理扫描PDF的页面图像
        
        Args:
            pages_dir: 页面图像目录
            
        Returns:
            str: 合并后的Markdown内容
        """
        if not self.api_key or not IMAGE_API_AVAILABLE:
            self.logger.error("API密钥未设置或OpenAI库未安装，无法处理扫描PDF")
            return ""
        
        # 创建OpenAI客户端
        client = OpenAI(
            base_url=self.api_base_url,
            api_key=self.api_key
        )
        
        # 获取所有页面图像
        page_images = sorted(pages_dir.glob("*.png"))
        if not page_images:
            self.logger.error("未找到页面图像")
            return ""
        
        markdown_content = ""
        
        for i, page_image in enumerate(page_images, 1):
            self.logger.info(f"处理第 {i}/{len(page_images)} 页: {page_image.name}")
            
            try:
                # 编码图像
                with open(page_image, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # 调用API
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "请提取这个图像中的所有文本内容，并以Markdown格式返回。保留原始格式和表格结构，忽略水印和印章。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4000,
                    temperature=0.1
                )
                
                page_content = response.choices[0].message.content
                if page_content:
                    markdown_content += f"\n\n---\n\n{page_content}"
                    self.logger.info(f"成功处理页面 {i}")
                else:
                    self.logger.warning(f"页面 {i} 未提取到内容")
                    
            except Exception as e:
                self.logger.error(f"处理页面 {i} 时出错: {e}")
                continue
        
        return markdown_content.strip()
    
    def remove_images_from_markdown(self, content: str) -> str:
        """
        从Markdown内容中移除图像引用
        
        Args:
            content: 原始Markdown内容
            
        Returns:
            str: 移除图像后的内容
        """
        import re
        # 移除图像引用
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        return content.strip()
    
    def process(self, file_path: Path) -> ProcessingResult:
        """
        处理PDF文件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        try:
            # 检测是否为扫描PDF
            is_scanned = self.is_scanned_pdf(file_path)
            
            # 转换文档
            conv_result = self.doc_converter.convert(str(file_path))
            
            markdown_content = ""
            temp_dirs = []
            
            if not is_scanned:
                # 普通PDF，直接导出Markdown
                markdown_content = conv_result.document.export_to_markdown(
                    image_mode=ImageRefMode.EMBEDDED
                )
                # 移除图像引用
                markdown_content = self.remove_images_from_markdown(markdown_content)
                
            else:
                # 扫描PDF，使用API处理页面图像
                self.logger.info("检测到扫描PDF，使用API处理页面图像")
                
                # 创建临时目录保存页面图像
                with tempfile.TemporaryDirectory() as temp_dir:
                    pages_dir = Path(temp_dir) / "pages"
                    pages_dir.mkdir(exist_ok=True)
                    
                    # 保存页面图像
                    if conv_result.document.pages:
                        for page_no, page in conv_result.document.pages.items():
                            if page.image and page.image.pil_image:
                                page_image_path = pages_dir / f"page-{page.page_no}.png"
                                page.image.pil_image.save(page_image_path, format="PNG")
                    
                    # 使用API处理页面图像
                    if list(pages_dir.glob("*.png")):
                        markdown_content = self.process_scanned_pdf_with_api(pages_dir)
                    else:
                        # 如果没有页面图像，回退到普通处理
                        markdown_content = conv_result.document.export_to_markdown(
                            image_mode=ImageRefMode.EMBEDDED
                        )
                        markdown_content = self.remove_images_from_markdown(markdown_content)
            
            if not markdown_content:
                return ProcessingResult(
                    success=False,
                    error="未能提取到文档内容"
                )
            
            # 构建元数据
            metadata = {
                'file_type': 'pdf',
                'is_scanned': is_scanned,
                'pages_count': len(conv_result.document.pages) if conv_result.document.pages else 0
            }
            
            return ProcessingResult(
                success=True,
                content=markdown_content,
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"处理PDF文件失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ProcessingResult(
                success=False,
                error=error_msg
            )
