"""
图像处理器
使用云雾AI的Gemini模型提取图像中的文本内容
"""

import base64
from pathlib import Path
from typing import Dict, Any, Optional

from .base import BaseProcessor, ProcessingResult

# 图像处理相关导入
try:
    from openai import OpenAI
    IMAGE_API_AVAILABLE = True
except ImportError:
    IMAGE_API_AVAILABLE = False


class ImageProcessor(BaseProcessor):
    """图像文档处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化图像处理器
        
        Args:
            config: 配置字典，包含API密钥等信息
        """
        super().__init__(config)
        
        if not IMAGE_API_AVAILABLE:
            raise ImportError("OpenAI库未安装，无法处理图像文件")
        
        # API配置
        self.api_key = config.get('yunwu_api_key') if config else None
        self.api_base_url = config.get('yunwu_api_base_url', 'https://yunwu.ai/v1')
        self.model = config.get('gemini_model', 'gemini-2.0-flash-thinking-exp-01-21')
        
        if not self.api_key:
            raise ValueError("未设置云雾AI API密钥，无法处理图像文件")
    
    def get_supported_extensions(self) -> list:
        """获取支持的文件扩展名"""
        return ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif']
    
    def get_mime_type(self, file_path: Path) -> str:
        """
        根据文件扩展名获取MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MIME类型
        """
        ext = file_path.suffix.lower().lstrip('.')
        
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        
        return mime_types.get(ext, 'image/jpeg')
    
    def encode_image(self, file_path: Path) -> str:
        """
        将图像编码为base64格式
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            str: base64编码的图像数据
        """
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_text_from_image(self, file_path: Path, prompt: Optional[str] = None) -> str:
        """
        从图像中提取文本
        
        Args:
            file_path: 图像文件路径
            prompt: 自定义提示词
            
        Returns:
            str: 提取的文本内容
        """
        # 创建OpenAI客户端
        client = OpenAI(
            base_url=self.api_base_url,
            api_key=self.api_key
        )
        
        # 编码图像
        base64_image = self.encode_image(file_path)
        mime_type = self.get_mime_type(file_path)
        
        # 默认提示词
        if prompt is None:
            prompt = "请提取这个图像中的所有文本内容，并以Markdown格式返回。保留原始格式和表格结构，忽略水印和印章。"
        
        # 调用API
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        return response.choices[0].message.content or ""
    
    def process(self, file_path: Path) -> ProcessingResult:
        """
        处理图像文件
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        try:
            self.logger.info(f"开始提取图像文本: {file_path.name}")
            
            # 提取文本
            content = self.extract_text_from_image(file_path)
            
            if not content:
                return ProcessingResult(
                    success=False,
                    error="未能从图像中提取到文本内容"
                )
            
            # 构建元数据
            file_info = self.get_file_info(file_path)
            metadata = {
                'file_type': 'image',
                'mime_type': self.get_mime_type(file_path),
                'file_size': file_info.get('size', 0),
                'model_used': self.model
            }
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata=metadata
            )
            
        except Exception as e:
            error_msg = f"处理图像文件失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ProcessingResult(
                success=False,
                error=error_msg
            )
