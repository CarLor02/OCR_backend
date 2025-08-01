#!/usr/bin/env python3
"""
恢复模型文件脚本
从系统缓存或重新下载模型
"""

import os
import shutil
from pathlib import Path

def restore_models():
    """恢复模型文件"""
    
    print("=== 恢复OCR模型文件 ===\n")
    
    project_root = Path(__file__).parent
    target_models = project_root / "docling_models"
    target_cache = project_root / "docling_cache"
    
    # 检查是否已存在
    if target_models.exists() and any(target_models.iterdir()):
        print("✅ 模型文件已存在")
        return True
    
    # 方法1: 从系统缓存复制
    system_cache = Path.home() / ".cache" / "docling" / "models"
    if system_cache.exists() and any(system_cache.iterdir()):
        print(f"📁 从系统缓存复制模型: {system_cache}")
        try:
            if target_models.exists():
                shutil.rmtree(target_models)
            shutil.copytree(system_cache, target_models)
            
            # 计算大小
            total_size = sum(f.stat().st_size for f in target_models.rglob('*') if f.is_file())
            print(f"✅ 模型复制完成，大小: {total_size / 1024 / 1024:.1f} MB")
            
            # 设置缓存
            setup_cache(target_models, target_cache)
            return True
            
        except Exception as e:
            print(f"❌ 复制失败: {e}")
    
    # 方法2: 重新下载
    print("📥 重新下载模型...")
    print("   请运行: python setup_models.py")
    print("   或者手动下载后放置在 docling_models/ 目录")
    
    return False

def setup_cache(models_dir, cache_dir):
    """设置缓存目录"""
    
    print(f"🔗 设置缓存目录...")
    
    try:
        # 创建缓存目录
        cache_dir.mkdir(exist_ok=True)
        
        # 创建符号链接
        models_link = cache_dir / "models"
        if models_link.exists():
            if models_link.is_symlink():
                models_link.unlink()
            else:
                shutil.rmtree(models_link)
        
        try:
            models_link.symlink_to(models_dir.absolute())
            print(f"✅ 创建符号链接: {models_link} -> {models_dir}")
        except OSError:
            shutil.copytree(models_dir, models_link)
            print(f"✅ 复制模型目录: {models_link}")
            
    except Exception as e:
        print(f"❌ 缓存设置失败: {e}")

def check_alternatives():
    """检查其他可能的模型位置"""
    
    print("\n🔍 检查可能的模型位置...")
    
    possible_locations = [
        Path.home() / ".cache" / "docling",
        Path("/tmp") / "docling_models",
        Path.cwd().parent / "docling_models",  # 父目录
    ]
    
    for location in possible_locations:
        if location.exists():
            print(f"   找到: {location}")
            if location.is_dir() and any(location.iterdir()):
                models_dir = location / "models" if (location / "models").exists() else location
                if models_dir.exists():
                    total_size = sum(f.stat().st_size for f in models_dir.rglob('*') if f.is_file())
                    print(f"     大小: {total_size / 1024 / 1024:.1f} MB")
                    
                    # 询问是否使用
                    response = input(f"     是否使用此位置的模型? (y/n): ").lower()
                    if response == 'y':
                        return models_dir
        else:
            print(f"   不存在: {location}")
    
    return None

if __name__ == "__main__":
    if not restore_models():
        # 如果恢复失败，检查其他位置
        alt_location = check_alternatives()
        if alt_location:
            project_root = Path(__file__).parent
            target_models = project_root / "docling_models"
            target_cache = project_root / "docling_cache"
            
            try:
                if target_models.exists():
                    shutil.rmtree(target_models)
                shutil.copytree(alt_location, target_models)
                setup_cache(target_models, target_cache)
                print("✅ 模型恢复成功！")
            except Exception as e:
                print(f"❌ 复制失败: {e}")
        else:
            print("\n💡 建议:")
            print("1. 运行 python setup_models.py 重新下载")
            print("2. 或者从其他机器复制 docling_models/ 目录")
            print("3. 确保网络连接正常后重试")
