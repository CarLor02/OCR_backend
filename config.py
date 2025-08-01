"""
配置管理模块
集中管理所有配置项，支持环境变量和默认值
"""

import os
from pathlib import Path

class Config:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ocr-backend-secret-key-2024')
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    # 服务器配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5050))
    
    # 文件存储配置
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    PROCESSED_FOLDER = os.environ.get('PROCESSED_FOLDER', str(BASE_DIR / 'processed'))
    
    # 文件大小限制 (100MB)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))
    
    # 支持的文件类型
    ALLOWED_EXTENSIONS = {
        'pdf': ['.pdf'],
        'excel': ['.xls', '.xlsx'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'],
        'html': ['.html', '.htm']
    }
    
    # API配置
    YUNWU_API_KEY = os.environ.get('YUNWU_API_KEY')
    YUNWU_API_BASE_URL = os.environ.get('YUNWU_API_BASE_URL', 'https://yunwu.ai/v1')
    
    # 处理器配置
    DEFAULT_GEMINI_MODEL = os.environ.get('DEFAULT_GEMINI_MODEL', 'gemini-2.0-flash-thinking-exp-01-21')
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 处理选项
    SAVE_INTERMEDIATE_FILES = os.environ.get('SAVE_INTERMEDIATE_FILES', 'false').lower() == 'true'
    CLEANUP_TEMP_FILES = os.environ.get('CLEANUP_TEMP_FILES', 'true').lower() == 'true'
    
    @classmethod
    def init_app(cls, app):
        """初始化应用配置"""
        # 创建必要的目录
        Path(cls.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(cls.PROCESSED_FOLDER).mkdir(parents=True, exist_ok=True)
        
        # 设置Flask配置
        app.config.from_object(cls)
        
        # 验证必要的配置
        if not cls.YUNWU_API_KEY:
            app.logger.warning("YUNWU_API_KEY未设置，图像和扫描PDF处理功能将不可用")
    
    @classmethod
    def get_all_allowed_extensions(cls):
        """获取所有支持的文件扩展名"""
        extensions = []
        for file_type, exts in cls.ALLOWED_EXTENSIONS.items():
            extensions.extend(exts)
        return extensions
    
    @classmethod
    def get_file_type(cls, filename):
        """根据文件名获取文件类型"""
        if not filename or '.' not in filename:
            return None
            
        ext = '.' + filename.rsplit('.', 1)[1].lower()
        
        for file_type, extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        
        return None
    
    @classmethod
    def is_allowed_file(cls, filename):
        """检查文件是否被允许"""
        return cls.get_file_type(filename) is not None


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}


def get_config():
    """获取当前配置"""
    env = os.environ.get('FLASK_ENV', 'production')
    return config.get(env, config['default'])
