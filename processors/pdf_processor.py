"""
PDF处理器
处理PDF文件，支持普通PDF和扫描PDF的OCR识别
"""

import os
import json
import tempfile
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from .base import BaseProcessor, ProcessingResult
import re
import pdfplumber
# PDF处理相关导入
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    #from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice #20250802lrr注释，本地报错
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

# 扫描PDF分块
try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


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
        
        # 检查是否有本地模型路径
        artifacts_path = os.environ.get('DOCLING_ARTIFACTS_PATH')
        if artifacts_path and Path(artifacts_path).exists():
            self.logger.info(f"使用本地模型路径: {artifacts_path}")

        # 配置PDF处理选项
        pipeline_options = PdfPipelineOptions(
            artifacts_path=artifacts_path if artifacts_path and Path(artifacts_path).exists() else None
        )
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = False
        
        # 配置表格模型模式 (fast 或 accurate)
        tableformer_mode = self.config.get('docling_tableformer_mode', 'fast') if self.config else 'fast'
        if tableformer_mode.lower() == 'fast':
            from docling.datamodel.pipeline_options import TableFormerMode
            pipeline_options.table_structure_options.mode = TableFormerMode.FAST
            self.logger.info("✅ 使用fast表格模型 (更快但精度稍低)")
        else:
            from docling.datamodel.pipeline_options import TableFormerMode
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
            self.logger.info("✅ 使用accurate表格模型 (更精确但较慢)")
        
        pipeline_options.generate_page_images = False
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
    
    def process_scanned_pdf(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """使用批量OCR接口处理扫描PDF (基于pdf_ocr_processor_v2逻辑)"""

        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2库未安装，无法处理扫描PDF")

        ocr_api_url = (
            self.config.get('scanned_pdf_ocr_api_url')
            or self.config.get('monkey_ocr_api_url')
        )
        if not ocr_api_url:
            raise ValueError("扫描PDF OCR接口地址未配置")

        chunk_size = self._get_int_config('scanned_pdf_chunk_size', 50)
        timeout = self._get_int_config('scanned_pdf_api_timeout', 300)
        delay = self._get_float_config('scanned_pdf_request_delay', 0.0)

        chunk_metadata = {
            'chunk_size': chunk_size,
            'chunks_total': 0,
            'chunks_succeeded': 0,
            'chunks_failed': 0
        }

        sections: List[str] = [f"# {file_path.stem}\n"]

        with tempfile.TemporaryDirectory(prefix="pdf_ocr_chunks_") as temp_dir:
            chunks = self._split_pdf_for_ocr(file_path, chunk_size, Path(temp_dir))
            chunk_metadata['chunks_total'] = len(chunks)

            if not chunks:
                raise RuntimeError("PDF分块失败，未生成任何章节")

            for index, (chunk_path, start_page, end_page) in enumerate(chunks, start=1):
                self.logger.info(
                    f"扫描PDF OCR: 第 {index}/{len(chunks)} 段, 页码 {start_page}-{end_page}, 文件大小 {chunk_path.stat().st_size} 字节"
                )

                try:
                    raw_content = self._call_scanned_pdf_api(chunk_path, ocr_api_url, timeout)
                    formatted_content = self._format_ocr_markdown(raw_content)

                    if formatted_content:
                        chunk_metadata['chunks_succeeded'] += 1
                        sections.append(
                            f"## 第 {index} 部分 (页码: {start_page}-{end_page})\n\n{formatted_content}\n"
                        )
                    else:
                        chunk_metadata['chunks_failed'] += 1
                        sections.append(f"<!-- OCR接口返回空内容: {chunk_path.name} -->\n")

                except Exception as exc:
                    chunk_metadata['chunks_failed'] += 1
                    self.logger.error(
                        f"扫描PDF OCR失败 (段 {index}): {exc}",
                        exc_info=True
                    )
                    sections.append(
                        f"<!-- OCR处理失败: {chunk_path.name} - {exc} -->\n"
                    )

                if delay > 0 and index < len(chunks):
                    time.sleep(delay)

        if chunk_metadata['chunks_succeeded'] == 0:
            raise RuntimeError("OCR接口未返回可用内容，请检查服务状态")

        content = "\n".join(sections).strip()
        return content, chunk_metadata

    def _get_int_config(self, key: str, default: int) -> int:
        value = self.config.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            self.logger.warning(f"配置项 {key}={value} 无效，使用默认值 {default}")
            return default

    def _get_float_config(self, key: str, default: float) -> float:
        value = self.config.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            self.logger.warning(f"配置项 {key}={value} 无效，使用默认值 {default}")
            return default

    def _split_pdf_for_ocr(self, pdf_path: Path, chunk_size: int, temp_dir: Path) -> List[Tuple[Path, int, int]]:
        if chunk_size <= 0:
            self.logger.warning("扫描PDF分块大小配置无效，使用默认值50")
            chunk_size = 50

        try:
            reader = PdfReader(str(pdf_path))
        except Exception as exc:
            self.logger.error(f"读取PDF失败: {exc}")
            raise

        total_pages = len(reader.pages)
        if total_pages == 0:
            self.logger.warning("PDF文件没有可用页面")
            return []

        chunk_files: List[Tuple[Path, int, int]] = []
        temp_dir = Path(temp_dir)

        for start in range(0, total_pages, chunk_size):
            end = min(start + chunk_size, total_pages)
            writer = PdfWriter()
            for page_num in range(start, end):
                writer.add_page(reader.pages[page_num])

            chunk_filename = f"{pdf_path.stem}_pages_{start + 1}-{end}.pdf"
            chunk_path = temp_dir / chunk_filename

            with open(chunk_path, 'wb') as output:
                writer.write(output)

            chunk_files.append((chunk_path, start + 1, end))

        self.logger.info(
            f"扫描PDF分块完成: 总页数={total_pages}, 分块大小={chunk_size}, 分块数量={len(chunk_files)}"
        )

        return chunk_files

    def _call_scanned_pdf_api(self, chunk_path: Path, ocr_api_url: str, timeout: int) -> str:
        try:
            with open(chunk_path, 'rb') as file_handle:
                files = {'file': (chunk_path.name, file_handle, 'application/pdf')}
                response = requests.post(ocr_api_url, files=files, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(f"OCR接口请求超时 ({chunk_path.name})") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"无法连接到OCR接口: {ocr_api_url}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"OCR接口请求失败: {exc}") from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"OCR接口返回错误状态 {response.status_code}: {response.text[:200]}"
            )

        if not response.content:
            return ""

        try:
            payload = response.json()
        except ValueError:
            return response.text

        if isinstance(payload, dict):
            for field in ('markdown', 'text', 'content', 'result', 'data'):
                if field in payload and payload[field]:
                    value = payload[field]
                    if isinstance(value, (list, tuple)):
                        value = "\n".join(str(item) for item in value)
                    return str(value)

            return json.dumps(payload, ensure_ascii=False)

        return str(payload)

    def _format_ocr_markdown(self, content: str) -> str:
        if not content:
            return ""

        content = self._strip_inline_base64_images(content)
        content = self.remove_images_from_markdown(content)
        return self._clean_ocr_markdown(content).strip()

    def _strip_inline_base64_images(self, content: str) -> str:
        return re.sub(r'<img[^>]+src="data:image/[^>]+>', '', content, flags=re.IGNORECASE)

    def _clean_ocr_markdown(self, content: str) -> str:
        content = re.sub(r"\r\n?", "\n", content)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        lines = content.split('\n')
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            stripped_line = line.strip()
            if stripped_line == '':
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(stripped_line)
                prev_empty = False

        return '\n'.join(cleaned_lines)
    
    def remove_images_from_markdown(self, content: str) -> str:
        """
        从Markdown内容中移除图像引用
        
        Args:
            content: 原始Markdown内容
            
        Returns:
            str: 移除图像后的内容
        """
        # 移除图像引用 (Markdown语法和HTML标签)
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        content = re.sub(r'<img[^>]*>', '', content, flags=re.IGNORECASE)
        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        return content.strip()
    
    def clean_text_for_md(self,text: str) -> str:
        """Clean and format extracted text for Markdown."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
    
        # Handle common PDF artifacts
        text = re.sub(r'-\s+(\w)', r'\1', text)  # Fix hyphenated words
        text = re.sub(r'\s+([.,;:!?)])', r'\1', text)  # Fix punctuation spacing
    
        return text

    def extract_tables_from_page(self,page) -> str:
        """Extract tables from a PDF page and format as Markdown tables."""
        md_tables = []
        tables = page.extract_tables()
    
        for table in tables:
            if not table or len(table) < 1:
                continue
            
            # Create Markdown table header
            header = "| " + " | ".join(str(cell) for cell in table[0]) + " |"
            separator = "| " + " | ".join(["---"] * len(table[0])) + " |"
            md_table = [header, separator]
        
            # Add rows
            for row in table[1:]:
                md_table.append("| " + " | ".join(str(cell) for cell in row) + " |")
        
            md_tables.append("\n".join(md_table))
    
        return "\n\n".join(md_tables)

    def convert_pdf_to_md(self,
        pdf_path: str    
        ) -> str:
        """
        Convert a PDF file to Markdown format.
    
        Args:
            pdf_path: Path to the input PDF file
        Returns:
            Path to the generated Markdown file
        """
        if not os.path.exists(pdf_path):
            raise self.logger.error(f"PDF file not found: {pdf_path}")
    
        markdown_content=""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract text
                    text = page.extract_text()
                    cleaned_text = self.clean_text_for_md(text)
                    markdown_content+=cleaned_text + "\n\n"
                
                    # Extract tables if enabled
                    tables_md = self.extract_tables_from_page(page)
                    if tables_md:
                        markdown_content+=tables_md + "\n\n"
                         
            return markdown_content
    
        except Exception as e:
            self.logger.error(f"Failed to convert PDF: {str(e)}")

    def analyze_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        has_text = any(page.get_text() for page in doc)  # 是否包含文本层
        
        # 检测复杂语义：表格、多列布局、复杂格式等
        has_complex_layout = False
        total_text_length = 0
        table_count = 0
        
        for page in doc:
            page_text = page.get_text()
            total_text_length += len(page_text)
            
            # 检测表格特征
            # 1. 多个制表符或大量空格分隔
            if '\t' in page_text or '  ' * 5 in page_text:
                has_complex_layout = True
            
            # 2. 检测表格行模式（连续的|符号或多个连续空格）
            lines = page_text.split('\n')
            table_like_lines = 0
            for line in lines:
                # 检测类似表格的行（包含多个分隔符）
                if line.count('|') >= 2 or line.count('\t') >= 2 or len(line.split('  ')) >= 3:
                    table_like_lines += 1
        
            # 如果有较多类似表格的行，认为有表格
            if table_like_lines >= 3:
                table_count += 1
                has_complex_layout = True
            
            # 3. 检测多列布局（文本行长度差异很大）
            line_lengths = [len(line.strip()) for line in lines if line.strip()]
            if len(line_lengths) > 5:
                avg_length = sum(line_lengths) / len(line_lengths)
                variance = sum((l - avg_length) ** 2 for l in line_lengths) / len(line_lengths)
                if variance > 1000:  # 行长度差异很大
                    has_complex_layout = True
                
            # 4. 检测数字密集区域（可能是表格数据）
            digit_ratio = sum(1 for char in page_text if char.isdigit()) / len(page_text) if page_text else 0
            if digit_ratio > 0.15:  # 数字占比超过15%，可能包含大量表格数据
                has_complex_layout = True
        
        doc.close()
        
        # 判断PDF类型
        if not has_text or total_text_length < 100:
            return "scanned"  # 无文本或文本很少，需要OCR
        elif has_complex_layout or table_count >= 2:  # 有复杂布局或多个表格
            return "hybrid"  # 使用docling处理
        else:
            return "text"  # 纯文本，直接提取
    
    def process(self, file_path: Path) -> ProcessingResult:
        """
        处理PDF文件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        try:
            markdown_content=""
            pdf_type = self.analyze_pdf(file_path)
            scanned_details: Dict[str, Any] = {}

           #根据pdf_type实现合适的处理方式，如果是text，就采用
            if pdf_type == "text":
                #markdown_content=self.convert_pdf_to_md(file_path) #LRR：这个版本还能提取表格，正则提取，不过我觉得效果太差，还不如简单版本
                #PyMuPDF直接提取
                doc = fitz.open(file_path)
                markdown_content = ""
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()
                    if page_text.strip():
                        markdown_content += f"\n\n## 第 {page_num + 1} 页\n\n{page_text}"
                doc.close()
            elif pdf_type == "scanned":
                markdown_content, scanned_details = self.process_scanned_pdf(file_path)
            else:  # 混合型
                conv_result = self.doc_converter.convert(str(file_path))
                #直接导出Markdown
                markdown_content = conv_result.document.export_to_markdown(
                    image_mode=ImageRefMode.EMBEDDED
                )
                # 移除图像引用
                markdown_content = self.remove_images_from_markdown(markdown_content)
                
            
            if not markdown_content:
                return ProcessingResult(
                    success=False,
                    error="未能提取到文档内容"
                )
            
            # 构建元数据
            if pdf_type in ["text", "scanned"]:
                # 获取页数
                doc = fitz.open(file_path)
                pages_count = len(doc)
                doc.close()
            else:
                # 混合型，从conv_result获取
                pages_count = len(conv_result.document.pages) if conv_result and conv_result.document.pages else 0
            
            metadata = {
                'file_type': 'pdf',
                'pdf_type': pdf_type,
                'is_scanned': pdf_type == "scanned",
                'pages_count': pages_count
            }

            if scanned_details:
                metadata.update(scanned_details)
            
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
