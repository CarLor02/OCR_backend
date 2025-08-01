"""
基础处理器类
定义所有文件处理器的通用接口和基础功能
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProcessingResult:
    """处理结果类"""
    
    def __init__(self, success: bool, content: str = "", error: str = "", 
                 processing_time: float = 0.0, metadata: Dict[str, Any] = None):
        self.success = success
        self.content = content
        self.error = error
        self.processing_time = processing_time
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'success': self.success,
            'content': self.content,
            'error': self.error,
            'processing_time': self.processing_time,
            'metadata': self.metadata
        }


class BaseProcessor(ABC):
    """文档处理器基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化处理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def process(self, file_path: Path) -> ProcessingResult:
        """
        处理文件的抽象方法
        
        Args:
            file_path: 输入文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> list:
        """
        获取支持的文件扩展名
        
        Returns:
            list: 支持的扩展名列表
        """
        pass
    
    def validate_file(self, file_path: Path) -> bool:
        """
        验证文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        if not file_path.exists():
            self.logger.error(f"文件不存在: {file_path}")
            return False
        
        if not file_path.is_file():
            self.logger.error(f"路径不是文件: {file_path}")
            return False
        
        if file_path.stat().st_size == 0:
            self.logger.error(f"文件为空: {file_path}")
            return False
        
        # 检查文件扩展名
        file_ext = file_path.suffix.lower()
        if file_ext not in self.get_supported_extensions():
            self.logger.error(f"不支持的文件类型: {file_ext}")
            return False
        
        return True
    
    def process_with_timing(self, file_path: Path) -> ProcessingResult:
        """
        带计时的处理方法
        
        Args:
            file_path: 输入文件路径
            
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        
        try:
            # 验证文件
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    error="文件验证失败",
                    processing_time=time.time() - start_time
                )
            
            self.logger.info(f"开始处理文件: {file_path.name}")
            
            # 调用具体的处理方法
            result = self.process(file_path)
            
            # 更新处理时间
            result.processing_time = time.time() - start_time
            
            if result.success:
                self.logger.info(f"文件处理成功: {file_path.name}, 耗时: {result.processing_time:.2f}秒")
            else:
                self.logger.error(f"文件处理失败: {file_path.name}, 错误: {result.error}")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"处理文件时发生异常: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ProcessingResult(
                success=False,
                error=error_msg,
                processing_time=processing_time
            )
    
    def cleanup_temp_files(self, *file_paths):
        """
        清理临时文件
        
        Args:
            *file_paths: 要清理的文件路径
        """
        for file_path in file_paths:
            try:
                if isinstance(file_path, (str, Path)):
                    path = Path(file_path)
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                            self.logger.debug(f"已删除临时文件: {path}")
                        elif path.is_dir():
                            import shutil
                            shutil.rmtree(path)
                            self.logger.debug(f"已删除临时目录: {path}")
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """
        获取文件基本信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息
        """
        try:
            stat = file_path.stat()
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'extension': file_path.suffix.lower(),
                'modified_time': stat.st_mtime
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return {}
