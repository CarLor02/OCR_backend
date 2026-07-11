# OCR Backend

多文档格式解析服务：上传 PDF / 图片 / Excel / Word / HTML 文件，自动转换为 Markdown。

## 功能概述

- **PDF**：先分析 PDF 类型
  - 纯文本 PDF → 用 PyMuPDF 直接提取文字
  - 版式复杂（含表格/多栏）PDF → 用 [docling](https://github.com/DS4SD/docling) 解析并导出 Markdown
  - 扫描件 PDF（无文本层）→ 逐页转图片后调用 **智谱AI(ZhipuAI) OCR** 接口识别；若未配置智谱 Key，则回退到 MonkeyOCR 接口
- **图片**（jpg/jpeg/png/gif/webp/bmp/tiff）→ 调用云雾AI（Gemini 模型）提取文字
- **Excel**（xls/xlsx）→ 保留合并单元格信息，转换为 Markdown 表格
- **Word**（doc/docx）→ 按原文顺序提取段落（含标题样式）和表格，转换为 Markdown；`.doc` 需系统安装 LibreOffice，会先转换为 `.docx` 再解析
- **HTML**（html/htm）→ 清洗后转换为 Markdown

## 项目结构

```
OCR_backend/
├── app.py                 # Flask 应用入口 + 路由
├── config.py               # 配置管理（读取 .env）
├── zhipu_ocr_client.py     # 智谱OCR客户端 + 扫描PDF逐页OCR逻辑
├── processors/             # 各文件类型处理器
│   ├── pdf_processor.py
│   ├── image_processor.py
│   ├── excel_processor.py
│   ├── word_processor.py
│   └── html_processor.py
├── utils/                   # 文件/响应工具函数
├── start.sh                 # 启动脚本（端口清理 + 启动 app.py）
├── requirements.txt
└── .env                      # 环境变量配置（需自行创建/维护，不提交仓库）
```

## 环境准备

### 依赖

需要 Python 3.10+，核心依赖见 `requirements.txt`（Flask、docling、PyMuPDF、pdfplumber、PyPDF2、openpyxl/xlrd、python-docx、beautifulsoup4/html2text、torch 等）。

处理旧版 `.doc` 文件还需要系统安装 **LibreOffice**（用于转换为 `.docx`），macOS 可通过 `brew install --cask libreoffice` 安装。

推荐使用独立虚拟环境安装：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> 本机也可直接复用已配置好依赖的 conda 环境，例如：
> `/opt/miniconda3/envs/docling_mps/bin/python app.py`

### 配置 `.env`

在 `OCR_backend/` 目录下创建 `.env`（参考已有字段）：

```bash
FLASK_ENV=development
SECRET_KEY=xxx
HOST=0.0.0.0
PORT=7860

UPLOAD_FOLDER=./uploads
PROCESSED_FOLDER=./processed
MAX_CONTENT_LENGTH=104857600

# 图片OCR / Gemini（云雾AI）
YUNWU_API_KEY=你的云雾API Key

# 扫描PDF OCR（智谱AI，优先使用）
ZHIPUAI_API_KEY=你的智谱API Key
ZHIPUAI_OCR_API_URL=https://open.bigmodel.cn/api/paas/v4/files/ocr
ZHIPUAI_OCR_LANGUAGE_TYPE=CHN_ENG

# 扫描PDF OCR兜底接口（未配置智谱Key时使用）
MONKEY_OCR_API_URL=http://your-monkeyocr-host:7860/api/process-base64

LOG_LEVEL=INFO
SAVE_INTERMEDIATE_FILES=false
CLEANUP_TEMP_FILES=true
```

`ZHIPUAI_API_KEY` 必须是真实密钥，占位符 `your_zhipuai_api_key_here` 会导致扫描PDF处理失败。

## 启动服务

```bash
cd OCR_backend
./start.sh
```

`start.sh` 会自动清理占用 7860 端口的进程，并激活 `venv`（如存在）后执行 `python app.py`。

也可以直接运行（跳过端口清理）：

```bash
cd OCR_backend
python app.py
```

服务启动后监听 `http://0.0.0.0:7860`（端口可在 `.env` 的 `PORT` 中修改）。

## API 调用方法

### 1. 健康检查

```bash
curl http://localhost:7860/api/health
```

### 2. 获取支持的文件类型

```bash
curl http://localhost:7860/api/supported-types
```

### 3. 文件上传处理（multipart/form-data）

```bash
curl -X POST http://localhost:7860/api/process \
  -F "file=@/path/to/example.pdf"
```

### 4. Base64 方式处理（JSON）

```bash
FILE_BASE64=$(base64 -i example.pdf)
curl -X POST http://localhost:7860/api/process-base64 \
  -H "Content-Type: application/json" \
  -d "{\"file_data\": \"$FILE_BASE64\", \"filename\": \"example.pdf\"}"
```

更详细的 Base64 接口说明见 `BASE64_API_GUIDE.md`。

### 响应格式示例

```json
{
  "success": true,
  "message": "文件处理成功",
  "filename": "example.pdf",
  "content": "# 提取的Markdown内容...",
  "file_type": "pdf",
  "processing_time": 2.35,
  "metadata": {
    "file_type": "pdf",
    "pdf_type": "scanned",
    "is_scanned": true,
    "pages_count": 3,
    "ocr_engine": "zhipu"
  }
}
```

失败响应：

```json
{
  "success": false,
  "error": "错误信息",
  "code": 500
}
```

## Docker 部署（可选）

```bash
./deploy_ocr.sh          # 拉取代码 + 构建镜像 + 启动容器（含GPU）
./deploy_ocr.sh --skip-git # 跳过代码拉取
```

详见 `Dockerfile.ocr` 与 `deploy_ocr.sh`。
