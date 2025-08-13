"""
OCR Backend Flask应用
独立的文件上传和OCR处理服务
"""

import os
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# 配置docling使用项目本地模型
def setup_local_models():
    """配置docling使用项目本地模型"""

    project_root = Path(__file__).parent
    local_models = project_root / "docling_models"
    local_cache = project_root / "docling_cache"

    # 检查本地模型是否存在
    if local_models.exists() and any(local_models.iterdir()):
        # docling 的主模型路径应该指向 model_artifacts 目录
        docling_main_models = local_models / "ds4sd--docling-models"
        model_artifacts = docling_main_models / "model_artifacts"

        if model_artifacts.exists():
            # 创建必要的符号链接，让 docling 能找到模型文件
            layout_dir = model_artifacts / "layout"
            tableformer_dir = model_artifacts / "tableformer"

            # 创建 layout 模型的符号链接
            if layout_dir.exists():
                for file_name in ["model.safetensors", "preprocessor_config.json", "config.json"]:
                    src_file = layout_dir / file_name
                    dst_file = model_artifacts / file_name
                    if src_file.exists():
                        # 如果目标文件已存在，先删除
                        if dst_file.exists() or dst_file.is_symlink():
                            dst_file.unlink()
                            print(f"🗑️  删除已存在的文件: {dst_file}")

                        try:
                            dst_file.symlink_to(src_file)
                            print(f"✅ 创建符号链接: {dst_file} -> {src_file}")
                        except OSError:
                            # 如果符号链接失败，复制文件
                            import shutil
                            shutil.copy2(src_file, dst_file)
                            print(f"✅ 复制文件: {src_file} -> {dst_file}")

            # 创建 tableformer 模型的符号链接
            if tableformer_dir.exists():
                for mode in ["accurate", "fast"]:
                    src_dir = tableformer_dir / mode
                    dst_dir = model_artifacts / mode
                    if src_dir.exists():
                        # 如果目标目录已存在，先删除
                        if dst_dir.exists() or dst_dir.is_symlink():
                            if dst_dir.is_symlink():
                                dst_dir.unlink()
                                print(f"🗑️  删除已存在的符号链接: {dst_dir}")
                            else:
                                import shutil
                                shutil.rmtree(dst_dir)
                                print(f"🗑️  删除已存在的目录: {dst_dir}")

                        try:
                            dst_dir.symlink_to(src_dir)
                            print(f"✅ 创建符号链接: {dst_dir} -> {src_dir}")
                        except OSError:
                            # 如果符号链接失败，复制目录
                            import shutil
                            shutil.copytree(src_dir, dst_dir)
                            print(f"✅ 复制目录: {src_dir} -> {dst_dir}")

            # 设置 docling 使用本地模型的环境变量
            os.environ['DOCLING_ARTIFACTS_PATH'] = str(model_artifacts)
            artifacts_path = str(model_artifacts)
        elif docling_main_models.exists():
            os.environ['DOCLING_ARTIFACTS_PATH'] = str(docling_main_models)
            artifacts_path = str(docling_main_models)
        else:
            # 如果没有找到主模型目录，使用整个模型目录
            os.environ['DOCLING_ARTIFACTS_PATH'] = str(local_models)
            artifacts_path = str(local_models)

        # 创建缓存目录
        local_cache.mkdir(exist_ok=True)

        # 创建符号链接或复制模型
        models_link = local_cache / "models"
        # 如果目标已存在，先删除
        if models_link.exists() or models_link.is_symlink():
            if models_link.is_symlink():
                models_link.unlink()
                print(f"🗑️  删除已存在的模型符号链接: {models_link}")
            else:
                import shutil
                shutil.rmtree(models_link)
                print(f"🗑️  删除已存在的模型目录: {models_link}")

        try:
            # 尝试创建符号链接
            models_link.symlink_to(local_models.absolute())
            print(f"✅ 创建模型符号链接: {models_link} -> {local_models}")
        except OSError:
            # 如果符号链接失败，复制目录
            import shutil
            shutil.copytree(local_models, models_link)
            print(f"✅ 复制模型目录: {models_link}")

        # 设置缓存目录环境变量
        os.environ['DOCLING_CACHE_DIR'] = str(local_cache)

        # 设置离线模式环境变量，防止访问外部网络
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_DATASETS_OFFLINE'] = '1'

        print(f"✅ 配置docling使用本地模型: {artifacts_path}")
        print(f"✅ 设置模型缓存目录: {local_cache}")
        print("✅ 已启用离线模式，禁止访问外部网络")
        return True
    else:
        print(f"⚠️  本地模型目录不存在或为空: {local_models}")
        print("   请先运行模型设置脚本: python setup_models.py")
        print("   或者将使用系统默认缓存，首次运行可能需要下载模型")
        return False

# 在导入processors之前设置模型路径
setup_local_models()

from config import get_config
from processors import PDFProcessor, ImageProcessor, ExcelProcessor, HTMLProcessor
from utils import FileUtils, ResponseUtils


def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    config_class = get_config()
    config_class.init_app(app)
    
    # 启用CORS
    CORS(app, origins="*")
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format=app.config['LOG_FORMAT']
    )
    
    return app


app = create_app()


def get_processor(file_type: str, config: dict):
    """
    根据文件类型获取对应的处理器
    
    Args:
        file_type: 文件类型
        config: 配置字典
        
    Returns:
        BaseProcessor: 对应的处理器实例
    """
    processors = {
        'pdf': PDFProcessor,
        'image': ImageProcessor,
        'excel': ExcelProcessor,
        'html': HTMLProcessor
    }
    
    processor_class = processors.get(file_type)
    if not processor_class:
        raise ValueError(f"不支持的文件类型: {file_type}")
    
    return processor_class(config)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return ResponseUtils.make_json_response(
        ResponseUtils.success_response(
            data={
                "status": "healthy",
                "service": "OCR Backend",
                "version": "1.0.0"
            },
            message="服务运行正常"
        )
    )


@app.route('/api/process', methods=['POST'])
def process_file():
    """文件处理接口"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return ResponseUtils.make_json_response(
                ResponseUtils.no_file_response(),
                400
            )
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return ResponseUtils.make_json_response(
                ResponseUtils.error_response("未选择文件"),
                400
            )
        
        # 检查文件类型
        from config import Config
        if not Config.is_allowed_file(file.filename):
            return ResponseUtils.make_json_response(
                ResponseUtils.unsupported_file_type_response(
                    FileUtils.get_file_extension(file.filename) or "unknown",
                    Config.get_all_allowed_extensions()
                ),
                415
            )
        
        # 保存上传的文件
        success, file_path, error = FileUtils.save_uploaded_file(
            file, app.config['UPLOAD_FOLDER']
        )
        
        if not success:
            return ResponseUtils.make_json_response(
                ResponseUtils.error_response(error),
                500
            )
        
        try:
            # 验证文件大小
            valid, size_error = FileUtils.validate_file_size(file_path, 100)
            if not valid:
                FileUtils.cleanup_file(file_path)
                return ResponseUtils.make_json_response(
                    ResponseUtils.file_too_large_response("100MB"),
                    413
                )
            
            # 获取文件类型
            file_type = Config.get_file_type(file.filename)
            
            # 准备处理器配置
            processor_config = {
                'yunwu_api_key': app.config.get('YUNWU_API_KEY'),
                'yunwu_api_base_url': app.config.get('YUNWU_API_BASE_URL'),
                'gemini_model': app.config.get('DEFAULT_GEMINI_MODEL'),
                'save_intermediate': app.config.get('SAVE_INTERMEDIATE_FILES', False)
            }
            
            # 调试信息
            app.logger.info(f"处理器配置: {processor_config}")
            
            # 获取处理器并处理文件
            processor = get_processor(file_type, processor_config)
            result = processor.process_with_timing(Path(file_path))
            
            # 清理临时文件
            if app.config.get('CLEANUP_TEMP_FILES', True):
                FileUtils.cleanup_file(file_path)
            
            # 返回处理结果
            if result.success:
                return ResponseUtils.make_json_response(
                    ResponseUtils.processing_response(
                        filename=file.filename,
                        content=result.content,
                        file_type=file_type,
                        processing_time=result.processing_time,
                        metadata=result.metadata
                    )
                )
            else:
                return ResponseUtils.make_json_response(
                    ResponseUtils.error_response(
                        f"文件处理失败: {result.error}"
                    ),
                    500
                )
                
        except ValueError as e:
            # 清理文件
            FileUtils.cleanup_file(file_path)
            return ResponseUtils.make_json_response(
                ResponseUtils.error_response(str(e)),
                400
            )
        
        except Exception as e:
            # 清理文件
            FileUtils.cleanup_file(file_path)
            app.logger.error(f"处理文件时发生异常: {e}", exc_info=True)
            return ResponseUtils.make_json_response(
                ResponseUtils.server_error_response("文件处理过程中发生错误"),
                500
            )
    
    except Exception as e:
        app.logger.error(f"API调用异常: {e}", exc_info=True)
        return ResponseUtils.make_json_response(
            ResponseUtils.server_error_response(),
            500
        )


@app.route('/api/supported-types', methods=['GET'])
def get_supported_types():
    """获取支持的文件类型接口"""
    from config import Config
    return ResponseUtils.make_json_response(
        ResponseUtils.success_response(
            data={
                "supported_extensions": Config.get_all_allowed_extensions(),
                "file_types": {
                    "pdf": "PDF文档",
                    "excel": "Excel表格",
                    "image": "图像文件",
                    "html": "HTML网页"
                }
            },
            message="获取支持的文件类型成功"
        )
    )


@app.errorhandler(413)
def request_entity_too_large(error):
    """文件过大错误处理"""
    return ResponseUtils.make_json_response(
        ResponseUtils.file_too_large_response("100MB"),
        413
    )


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return ResponseUtils.make_json_response(
        ResponseUtils.error_response("接口不存在", 404),
        404
    )


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    app.logger.error(f"服务器内部错误: {error}")
    return ResponseUtils.make_json_response(
        ResponseUtils.server_error_response(),
        500
    )


if __name__ == '__main__':
    # 确保必要的目录存在
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['PROCESSED_FOLDER']).mkdir(parents=True, exist_ok=True)
    
    # 启动应用
    app.logger.info(f"OCR Backend服务启动中...")
    app.logger.info(f"服务地址: http://{app.config['HOST']}:{app.config['PORT']}")
    app.logger.info(f"上传目录: {app.config['UPLOAD_FOLDER']}")
    app.logger.info(f"处理目录: {app.config['PROCESSED_FOLDER']}")
    
    if app.config.get('YUNWU_API_KEY'):
        app.logger.info("云雾AI API密钥已配置")
    else:
        app.logger.warning("云雾AI API密钥未配置，图像和扫描PDF处理功能将不可用")
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
