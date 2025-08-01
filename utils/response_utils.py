"""
响应处理工具
提供API响应格式化的工具函数
"""

from typing import Any, Dict, Optional
from flask import jsonify


class ResponseUtils:
    """响应处理工具类"""
    
    @staticmethod
    def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            
        Returns:
            Dict: 响应字典
        """
        response = {
            "success": True,
            "message": message
        }
        
        if data is not None:
            response["data"] = data
            
        return response
    
    @staticmethod
    def error_response(error: str, code: int = 400, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            error: 错误信息
            code: 错误代码
            details: 错误详情
            
        Returns:
            Dict: 响应字典
        """
        response = {
            "success": False,
            "error": error,
            "code": code
        }
        
        if details:
            response["details"] = details
            
        return response
    
    @staticmethod
    def processing_response(filename: str, content: str, file_type: str, 
                          processing_time: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建处理成功响应
        
        Args:
            filename: 文件名
            content: 处理后的内容
            file_type: 文件类型
            processing_time: 处理时间
            metadata: 元数据
            
        Returns:
            Dict: 响应字典
        """
        response = {
            "success": True,
            "filename": filename,
            "content": content,
            "file_type": file_type,
            "processing_time": round(processing_time, 2)
        }
        
        if metadata:
            response["metadata"] = metadata
            
        return response
    
    @staticmethod
    def validation_error_response(errors: Dict[str, str]) -> Dict[str, Any]:
        """
        创建验证错误响应
        
        Args:
            errors: 验证错误字典
            
        Returns:
            Dict: 响应字典
        """
        return {
            "success": False,
            "error": "验证失败",
            "validation_errors": errors
        }
    
    @staticmethod
    def file_too_large_response(max_size: str) -> Dict[str, Any]:
        """
        创建文件过大错误响应
        
        Args:
            max_size: 最大文件大小
            
        Returns:
            Dict: 响应字典
        """
        return ResponseUtils.error_response(
            error=f"文件大小超过限制，最大允许 {max_size}",
            code=413
        )
    
    @staticmethod
    def unsupported_file_type_response(file_type: str, supported_types: list) -> Dict[str, Any]:
        """
        创建不支持文件类型错误响应
        
        Args:
            file_type: 文件类型
            supported_types: 支持的文件类型列表
            
        Returns:
            Dict: 响应字典
        """
        return ResponseUtils.error_response(
            error=f"不支持的文件类型: {file_type}",
            code=415,
            details={
                "supported_types": supported_types
            }
        )
    
    @staticmethod
    def no_file_response() -> Dict[str, Any]:
        """
        创建无文件错误响应
        
        Returns:
            Dict: 响应字典
        """
        return ResponseUtils.error_response(
            error="请选择要上传的文件",
            code=400
        )
    
    @staticmethod
    def server_error_response(error: str = "服务器内部错误") -> Dict[str, Any]:
        """
        创建服务器错误响应
        
        Args:
            error: 错误信息
            
        Returns:
            Dict: 响应字典
        """
        return ResponseUtils.error_response(
            error=error,
            code=500
        )
    
    @staticmethod
    def make_json_response(data: Dict[str, Any], status_code: int = 200):
        """
        创建JSON响应
        
        Args:
            data: 响应数据
            status_code: HTTP状态码
            
        Returns:
            Flask Response对象
        """
        response = jsonify(data)
        response.status_code = status_code
        return response
