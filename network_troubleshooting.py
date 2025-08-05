#!/usr/bin/env python3
"""
网络连接问题诊断和解决方案
用于诊断和解决服务器部署时的网络连接问题
"""

import os
import sys
import socket
import urllib.request
import urllib.error
from pathlib import Path
import subprocess
import time

def check_internet_connection():
    """检查基本的互联网连接"""
    print("=== 网络连接诊断 ===\n")
    
    test_urls = [
        "https://www.google.com",
        "https://www.baidu.com", 
        "https://huggingface.co",
        "https://yunwu.ai"
    ]
    
    for url in test_urls:
        try:
            print(f"测试连接: {url}")
            response = urllib.request.urlopen(url, timeout=10)
            print(f"✅ 连接成功 - 状态码: {response.getcode()}")
        except urllib.error.URLError as e:
            print(f"❌ 连接失败: {e}")
        except Exception as e:
            print(f"❌ 连接错误: {e}")
        print()

def check_dns_resolution():
    """检查DNS解析"""
    print("=== DNS解析检查 ===\n")
    
    domains = [
        "huggingface.co",
        "yunwu.ai", 
        "google.com",
        "github.com"
    ]
    
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"✅ {domain} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ {domain} DNS解析失败: {e}")

def check_proxy_settings():
    """检查代理设置"""
    print("=== 代理设置检查 ===\n")
    
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'no_proxy', 'NO_PROXY']
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"🔧 {var} = {value}")
        else:
            print(f"   {var} = (未设置)")

def check_firewall_ports():
    """检查防火墙和端口"""
    print("=== 端口连接检查 ===\n")
    
    test_connections = [
        ("huggingface.co", 443),
        ("yunwu.ai", 443),
        ("github.com", 443),
        ("38.60.251.79", 7860)  # MonkeyOCR API
    ]
    
    for host, port in test_connections:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {host}:{port} - 连接成功")
            else:
                print(f"❌ {host}:{port} - 连接失败 (错误码: {result})")
        except Exception as e:
            print(f"❌ {host}:{port} - 连接错误: {e}")

def suggest_solutions():
    """提供解决方案建议"""
    print("=== 解决方案建议 ===\n")
    
    solutions = [
        "1. 检查服务器网络连接",
        "   - 确保服务器可以访问外网",
        "   - 检查防火墙设置",
        "",
        "2. 配置离线模式",
        "   - 预先下载模型文件到本地",
        "   - 使用本地模型缓存",
        "",
        "3. 配置代理（如果需要）",
        "   export http_proxy=http://proxy:port",
        "   export https_proxy=http://proxy:port",
        "",
        "4. 使用镜像源",
        "   - 使用国内镜像下载模型",
        "   - 配置pip镜像源",
        "",
        "5. 禁用外部API调用",
        "   - 设置环境变量禁用外部服务",
        "   - 使用纯本地处理模式"
    ]
    
    for solution in solutions:
        print(solution)

def setup_offline_mode():
    """设置离线模式"""
    print("=== 设置离线模式 ===\n")
    
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    
    # 创建或更新.env文件
    env_content = []
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    # 添加离线模式配置
    offline_configs = [
        "# 离线模式配置\n",
        "OFFLINE_MODE=true\n",
        "DISABLE_EXTERNAL_APIS=true\n",
        "USE_LOCAL_MODELS_ONLY=true\n",
        "\n"
    ]
    
    # 检查是否已存在配置
    has_offline_config = any("OFFLINE_MODE" in line for line in env_content)
    
    if not has_offline_config:
        env_content.extend(offline_configs)
        
        with open(env_file, 'w') as f:
            f.writelines(env_content)
        
        print(f"✅ 已更新 {env_file} 添加离线模式配置")
    else:
        print("✅ 离线模式配置已存在")

def check_local_models():
    """检查本地模型"""
    print("=== 本地模型检查 ===\n")
    
    project_root = Path(__file__).parent
    models_dir = project_root / "docling_models"
    cache_dir = project_root / "docling_cache"
    
    if models_dir.exists() and any(models_dir.iterdir()):
        total_size = sum(f.stat().st_size for f in models_dir.rglob('*') if f.is_file())
        print(f"✅ 本地模型存在: {models_dir}")
        print(f"   模型大小: {total_size / 1024 / 1024:.1f} MB")
    else:
        print(f"❌ 本地模型不存在: {models_dir}")
        print("   建议运行: python restore_models.py")
    
    if cache_dir.exists():
        print(f"✅ 缓存目录存在: {cache_dir}")
    else:
        print(f"❌ 缓存目录不存在: {cache_dir}")

def main():
    """主函数"""
    print("OCR Backend 网络问题诊断工具\n")
    
    # 基本信息
    print(f"Python版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")
    print(f"用户: {os.environ.get('USER', 'unknown')}")
    print()
    
    # 运行诊断
    check_internet_connection()
    check_dns_resolution()
    check_proxy_settings()
    check_firewall_ports()
    check_local_models()
    
    # 提供解决方案
    suggest_solutions()
    
    # 询问是否设置离线模式
    print("\n" + "="*50)
    response = input("是否设置离线模式以避免网络问题? (y/n): ").lower()
    if response == 'y':
        setup_offline_mode()
        print("\n💡 建议:")
        print("1. 重启应用: python app.py")
        print("2. 如果仍有问题，运行: python restore_models.py")

if __name__ == "__main__":
    main()
