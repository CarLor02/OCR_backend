"""
图像处理器
使用云雾AI的Gemini模型提取图像中的文本内容
"""

import base64
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import json

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
        try:
            # 编码图像
            base64_image = self.encode_image(file_path)
            mime_type = self.get_mime_type(file_path)
            
            # 默认提示词
            if prompt is None:
                prompt = "请提取这个图像中的所有文本内容，并以Markdown格式返回。保留原始格式和表格结构，忽略水印和印章。"
            
            # 构建请求数据
            request_data = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # 发送请求到Gemini API
            url = "https://yunwu.ai/v1beta/models/gemini-2.0-flash:generateContent" #TODO：硬编码
            headers = {
                "Content-Type": "application/json"
            }
            params = {
                "key": "your_api_key_here"  # TODO去掉硬编码(我取环境变量的一直不对，就这么写死了)
            }
            
            response = requests.post(
                url,
                json=request_data,
                headers=headers,
                params=params,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content
                else:
                    self.logger.error("Gemini API返回格式异常")
                    return ""
            else:
                self.logger.error(f"Gemini API调用失败: {response.status_code}, {response.text}")
                return ""
                
        except Exception as e:
            self.logger.error(f"提取图像文本时出错: {e}")
            return ""
    
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
                'model_used': 'gemini-2.0-flash'
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
