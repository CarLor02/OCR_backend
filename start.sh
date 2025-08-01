#!/bin/bash

# OCR Backend 启动脚本 - 端口管理版本

PORT=5050

echo "=== OCR Backend 启动脚本 ==="

# 检测端口是否被占用
echo "检查端口 $PORT 是否被占用..."
PID=$(lsof -ti:$PORT)

if [ ! -z "$PID" ]; then
    echo "发现端口 $PORT 被进程 $PID 占用，正在终止..."
    kill -9 $PID
    sleep 2

    # 再次检查是否成功终止
    NEW_PID=$(lsof -ti:$PORT)
    if [ ! -z "$NEW_PID" ]; then
        echo "警告: 无法终止进程，请手动处理"
        exit 1
    else
        echo "端口 $PORT 已释放"
    fi
else
    echo "端口 $PORT 可用"
fi

# 创建必要的目录
mkdir -p uploads
mkdir -p processed

# 启动服务
echo "启动OCR Backend服务..."
echo "服务地址: http://localhost:$PORT"
echo "按 Ctrl+C 停止服务"
echo ""

# 激活虚拟环境并启动
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python app.py
