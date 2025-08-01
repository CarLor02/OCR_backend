"""
HTML处理器
处理HTML文件，将HTML内容转换为Markdown格式
"""

from pathlib import Path
from typing import Dict, Any

from .base import BaseProcessor, ProcessingResult

# HTML处理相关导入
try:
    from bs4 import BeautifulSoup, Comment
    import html2text
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False


class HTMLProcessor(BaseProcessor):
    """HTML文档处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化HTML处理器
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        
        if not HTML_AVAILABLE:
            raise ImportError("HTML处理相关库未安装，无法处理HTML文件")
        
        # 配置html2text转换器
        self.h = html2text.HTML2Text()
        self.h.ignore_links = False
        self.h.ignore_images = False
        self.h.body_width = 0  # 不限制行宽
        self.h.unicode_snob = True
        self.h.escape_snob = True
    
    def get_supported_extensions(self) -> list:
        """获取支持的文件扩展名"""
        return ['.html', '.htm']
    
    def clean_html(self, html_content: str) -> str:
        """
        清理HTML内容，移除不必要的元素
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            str: 清理后的HTML内容
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除脚本和样式
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 移除注释
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        
        # 移除一些不必要的标签
        for tag in soup(["nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # 移除空的段落和div
        for tag in soup.find_all(['p', 'div']):
            if not tag.get_text(strip=True):
                tag.decompose()
        
        return str(soup)
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        提取HTML元数据
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            Dict: 元数据字典
        """
        metadata = {}
        
        # 提取标题
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # 提取meta信息
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        # 提取语言
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')
        
        return metadata
    
    def convert_to_markdown(self, html_content: str) -> tuple[str, Dict[str, Any]]:
        """
        将HTML内容转换为Markdown
        
        Args:
            html_content: HTML内容
            
        Returns:
            tuple: (Markdown内容, 元数据)
        """
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取元数据
        metadata = self.extract_metadata(soup)
        
        # 清理HTML
        cleaned_html = self.clean_html(html_content)
        
        # 转换为Markdown
        markdown_content = self.h.handle(cleaned_html)
        
        # 清理Markdown内容
        lines = markdown_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # 跳过空行和只包含空格的行
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1]:  # 保留段落间的空行
                cleaned_lines.append('')
        
        # 移除连续的空行
        final_lines = []
        prev_empty = False
        for line in cleaned_lines:
            if not line:
                if not prev_empty:
                    final_lines.append(line)
                prev_empty = True
            else:
                final_lines.append(line)
                prev_empty = False
        
        return '\n'.join(final_lines).strip(), metadata
    
    def process(self, file_path: Path) -> ProcessingResult:
        """
        处理HTML文件
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        try:
            self.logger.info(f"开始处理HTML文件: {file_path.name}")
            
            # 读取HTML文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            if not html_content.strip():
                return ProcessingResult(
                    success=False,
                    error="HTML文件为空"
                )
            
            # 转换为Markdown
            markdown_content, html_metadata = self.convert_to_markdown(html_content)
            
            if not markdown_content:
                return ProcessingResult(
                    success=False,
                    error="未能从HTML文件中提取到有效内容"
                )
            
            # 构建元数据
            file_info = self.get_file_info(file_path)
            metadata = {
                'file_type': 'html',
                'file_size': file_info.get('size', 0),
                'html_metadata': html_metadata
            }
            
            return ProcessingResult(
                success=True,
                content=markdown_content,
                metadata=metadata
            )
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                    html_content = f.read()
                
                markdown_content, html_metadata = self.convert_to_markdown(html_content)
                
                file_info = self.get_file_info(file_path)
                metadata = {
                    'file_type': 'html',
                    'file_size': file_info.get('size', 0),
                    'encoding': 'gbk',
                    'html_metadata': html_metadata
                }
                
                return ProcessingResult(
                    success=True,
                    content=markdown_content,
                    metadata=metadata
                )
                
            except Exception as e:
                error_msg = f"处理HTML文件编码失败: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                return ProcessingResult(
                    success=False,
                    error=error_msg
                )
        
        except Exception as e:
            error_msg = f"处理HTML文件失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ProcessingResult(
                success=False,
                error=error_msg
            )
