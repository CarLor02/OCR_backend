#!/usr/bin/env python3
"""
模型设置脚本
首次运行时自动下载和配置docling模型
"""

import os
import sys
from pathlib import Path

def setup_models():
    """设置docling模型"""
    
    print("=== OCR Backend 模型设置 ===\n")
    
    project_root = Path(__file__).parent
    models_dir = project_root / "docling_models"
    cache_dir = project_root / "docling_cache"
    
    # 检查模型是否已存在
    if models_dir.exists() and any(models_dir.iterdir()):
        print("✅ 本地模型已存在")
        print(f"   模型位置: {models_dir}")
        
        # 计算模型大小
        total_size = sum(f.stat().st_size for f in models_dir.rglob('*') if f.is_file())
        print(f"   模型大小: {total_size / 1024 / 1024:.1f} MB")
        
        # 设置缓存目录
        setup_cache_directory(models_dir, cache_dir)
        return True
    
    print("📥 本地模型不存在，开始下载...")
    print("   这可能需要几分钟时间，请耐心等待...")
    
    try:
        # 导入docling并下载模型
        #from docling.utils.model_downloader import download_models
        from docling.datamodel.settings import settings
        
        print(f"   下载位置: {settings.cache_dir}")
        
        # 下载模型
        output_dir = download_models(
            force=False,
            progress=True,
            with_layout=True,
            with_tableformer=True,
            with_code_formula=True,
            with_picture_classifier=True,
            with_easyocr=True,
        )
        
        print(f"✅ 模型下载完成: {output_dir}")
        
        # 复制到项目目录
        copy_models_to_project(output_dir, models_dir)
        
        # 设置缓存目录
        setup_cache_directory(models_dir, cache_dir)
        
        return True
        
    except ImportError:
        print("❌ 无法导入docling，请先安装依赖:")
        print("   pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ 模型下载失败: {e}")
        return False

def copy_models_to_project(source_dir, target_dir):
    """复制模型到项目目录"""
    
    print(f"\n📁 复制模型到项目目录...")
    print(f"   从: {source_dir}")
    print(f"   到: {target_dir}")
    
    try:
        import shutil
        
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        shutil.copytree(source_dir, target_dir)
        
        # 计算复制后的大小
        total_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
        print(f"✅ 模型复制完成，大小: {total_size / 1024 / 1024:.1f} MB")
        
    except Exception as e:
        print(f"❌ 模型复制失败: {e}")
        raise

def setup_cache_directory(models_dir, cache_dir):
    """设置缓存目录"""
    
    print(f"\n🔗 设置模型缓存...")
    
    try:
        # 创建缓存目录
        cache_dir.mkdir(exist_ok=True)
        
        # 创建模型链接
        models_link = cache_dir / "models"
        if models_link.exists():
            if models_link.is_symlink():
                models_link.unlink()
            else:
                import shutil
                shutil.rmtree(models_link)
        
        try:
            # 尝试创建符号链接
            models_link.symlink_to(models_dir.absolute())
            print(f"✅ 创建符号链接: {models_link} -> {models_dir}")
        except OSError:
            # 如果符号链接失败，复制目录
            import shutil
            shutil.copytree(models_dir, models_link)
            print(f"✅ 复制模型目录: {models_link}")
        
        print(f"✅ 缓存目录设置完成: {cache_dir}")
        
    except Exception as e:
        print(f"❌ 缓存目录设置失败: {e}")
        raise

def verify_setup():
    """验证设置"""
    
    print(f"\n🔍 验证模型设置...")
    
    try:
        # 设置环境变量
        project_root = Path(__file__).parent
        cache_dir = project_root / "docling_cache"
        os.environ['DOCLING_CACHE_DIR'] = str(cache_dir)
        
        # 测试docling
        from docling.datamodel.settings import settings
        from docling.document_converter import DocumentConverter
        
        print(f"   docling缓存目录: {settings.cache_dir}")
        print(f"   模型目录存在: {(settings.cache_dir / 'models').exists()}")
        
        # 创建转换器测试
        converter = DocumentConverter()
        print("✅ DocumentConverter创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def main():
    """主函数"""
    
    print("OCR Backend 模型设置工具")
    print("此脚本将下载和配置docling所需的AI模型\n")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 设置模型
    if setup_models():
        # 验证设置
        if verify_setup():
            print("\n🎉 模型设置完成！")
            print("\n📋 接下来的步骤:")
            print("1. 配置环境变量（复制.env.example为.env并编辑）")
            print("2. 启动服务: python app.py")
            print("3. 访问: http://localhost:7860")
        else:
            print("\n❌ 模型验证失败，请检查配置")
            sys.exit(1)
    else:
        print("\n❌ 模型设置失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
