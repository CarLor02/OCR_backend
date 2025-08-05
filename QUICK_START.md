# OCR Backend - 快速开始指南

## 一键启动流程

### 1. 克隆仓库
```bash
git clone https://github.com/CarLor02/OCR_backend.git
cd OCR_backend
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 设置模型（重要！）
```bash
python setup_models.py
```
这一步会：
- 自动下载所需的AI模型（约1.1GB）
- 配置本地模型缓存
- 验证设置是否正确

### 5. 配置环境变量（可选）
```bash
cp .env.example .env
# 编辑 .env 文件，设置 YUNWU_API_KEY（用于图像处理）
```

### 6. 启动服务
```bash
python app.py
```

服务将在 http://localhost:7860 启动

## 测试服务

### 上传PDF文件
```bash
curl -X POST -F "file=@your_document.pdf" http://localhost:7860/process
```

### 上传图片文件
```bash
curl -X POST -F "file=@your_image.jpg" http://localhost:7860/process
```

## 常见问题

### Q: 模型下载失败怎么办？
A: 确保网络连接正常，重新运行：
```bash
rm -rf docling_models/ docling_cache/
python setup_models.py
```

### Q: 启动时提示模型不存在？
A: 运行模型设置脚本：
```bash
python setup_models.py
```

### Q: 图像处理不工作？
A: 需要设置API密钥：
1. 复制 `.env.example` 为 `.env`
2. 在 `.env` 中设置 `YUNWU_API_KEY`

### Q: 服务占用内存过多？
A: 这是正常的，AI模型需要2-4GB内存

## 支持的文件格式

- **PDF**: `.pdf`
- **图像**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`
- **Excel**: `.xls`, `.xlsx`
- **HTML**: `.html`, `.htm`

## 项目特点

✅ **离线运行**: 模型下载后无需网络连接
✅ **自动配置**: 智能检测和配置本地模型
✅ **多格式支持**: 统一API处理多种文档格式
✅ **高精度**: 使用最新的AI模型进行文档处理
✅ **易部署**: 一键设置，开箱即用
