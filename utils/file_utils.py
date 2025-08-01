"""
文件处理工具
提供文件操作相关的工具函数
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple
from werkzeug.utils import secure_filename


class FileUtils:
    """文件处理工具类"""
    
    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """
        生成唯一的文件名
        
        Args:
            original_filename: 原始文件名
            
        Returns:
            str: 唯一的文件名
        """
        # 获取文件扩展名
        name, ext = os.path.splitext(original_filename)
        
        # 生成UUID
        unique_id = str(uuid.uuid4())[:8]
        
        # 安全化文件名
        safe_name = secure_filename(name)
        
        return f"{unique_id}_{safe_name}{ext}"
    
    @staticmethod
    def save_uploaded_file(file, upload_folder: str) -> Tuple[bool, str, str]:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            upload_folder: 上传目录
            
        Returns:
            Tuple[bool, str, str]: (是否成功, 文件路径, 错误信息)
        """
        try:
            # 确保上传目录存在
            Path(upload_folder).mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            unique_filename = FileUtils.generate_unique_filename(file.filename)
            
            # 构建文件路径
            file_path = os.path.join(upload_folder, unique_filename)
            
            # 保存文件
            file.save(file_path)
            
            return True, file_path, ""
            
        except Exception as e:
            return False, "", f"保存文件失败: {str(e)}"
    
    @staticmethod
    def get_file_size_str(file_path: str) -> str:
        """
        获取文件大小的字符串表示
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件大小字符串
        """
        try:
            size = os.path.getsize(file_path)
            
            # 转换为合适的单位
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.1f} GB"
                
        except Exception:
            return "Unknown"
    
    @staticmethod
    def cleanup_file(file_path: str) -> bool:
        """
        清理文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功清理
        """
        try:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                return True
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_file_size(file_path: str, max_size_mb: int = 100) -> Tuple[bool, str]:
        """
        验证文件大小
        
        Args:
            file_path: 文件路径
            max_size_mb: 最大文件大小(MB)
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            size = os.path.getsize(file_path)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if size > max_size_bytes:
                return False, f"文件大小超过限制 ({max_size_mb}MB)"
            
            return True, ""
            
        except Exception as e:
            return False, f"检查文件大小失败: {str(e)}"
    
    @staticmethod
    def get_file_extension(filename: str) -> Optional[str]:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            Optional[str]: 文件扩展名（小写，包含点）
        """
        if not filename or '.' not in filename:
            return None
        
        return '.' + filename.rsplit('.', 1)[1].lower()
    
    @staticmethod
    def create_directory(directory: str) -> bool:
        """
        创建目录
        
        Args:
            directory: 目录路径
            
        Returns:
            bool: 是否成功创建
        """
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def is_safe_path(path: str, base_path: str) -> bool:
        """
        检查路径是否安全（防止路径遍历攻击）
        
        Args:
            path: 要检查的路径
            base_path: 基础路径
            
        Returns:
            bool: 路径是否安全
        """
        try:
            # 规范化路径
            abs_path = os.path.abspath(path)
            abs_base = os.path.abspath(base_path)
            
            # 检查是否在基础路径内
            return abs_path.startswith(abs_base)
            
        except Exception:
            return False
