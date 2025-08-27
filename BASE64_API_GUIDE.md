# Base64 API 接口使用指南

## 概述

新增的 `/api/process-base64` 接口支持通过 Base64 编码的方式处理文件，无需文件上传，适用于以下场景：
- 前端已有 Base64 编码的文件数据
- 避免文件上传的网络开销
- 集成到其他系统中

## 接口信息

- **URL**: `/api/process-base64`
- **方法**: `POST`
- **Content-Type**: `application/json`

## 请求格式

### 请求体 (JSON)

```json
{
  "file_data": "文件的Base64编码数据",
  "filename": "原始文件名（包含扩展名）"
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_data` | string | 是 | Base64编码的文件数据，支持两种格式：<br/>1. 纯Base64字符串<br/>2. Data URL格式（如：`data:application/pdf;base64,iVBORw0KG...`） |
| `filename` | string | 是 | 原始文件名，必须包含正确的文件扩展名用于类型识别 |

## 响应格式

成功响应与原 `/api/process` 接口相同：

```json
{
  "success": true,
  "message": "文件处理成功",
  "data": {
    "filename": "test.pdf",
    "file_type": "pdf",
    "content": "提取的Markdown内容...",
    "processing_time": 2.35,
    "metadata": {
      "file_type": "pdf",
      "pdf_type": "text",
      "is_scanned": false,
      "pages_count": 5
    }
  }
}
```

## 使用示例

### 1. Python 示例

```python
import base64
import requests
import json

# 读取文件并转换为Base64
def file_to_base64(file_path):
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

# 准备请求数据
file_path = "example.pdf"
file_base64 = file_to_base64(file_path)

request_data = {
    "file_data": file_base64,
    "filename": "example.pdf"
}

# 发送请求
response = requests.post(
    "http://localhost:5000/api/process-base64",
    json=request_data,
    headers={"Content-Type": "application/json"}
)

# 处理响应
if response.status_code == 200:
    result = response.json()
    print("处理成功!")
    print(f"内容: {result['data']['content']}")
else:
    print(f"处理失败: {response.json()}")
```

### 2. JavaScript 示例

```javascript
// 文件转Base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

// 使用示例
async function processFile(file) {
    try {
        // 转换文件为Base64 (Data URL格式)
        const dataUrl = await fileToBase64(file);
        
        const requestData = {
            file_data: dataUrl,  // Data URL格式会自动处理
            filename: file.name
        };
        
        const response = await fetch('/api/process-base64', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log('处理成功!', result);
        } else {
            console.error('处理失败:', result);
        }
    } catch (error) {
        console.error('错误:', error);
    }
}
```

### 3. curl 示例

```bash
# 首先将文件转换为Base64
FILE_BASE64=$(base64 -i example.pdf)

# 发送请求
curl -X POST http://localhost:5000/api/process-base64 \
  -H "Content-Type: application/json" \
  -d "{
    \"file_data\": \"$FILE_BASE64\",
    \"filename\": \"example.pdf\"
  }"
```

## 支持的文件格式

与原接口相同，支持以下文件类型：
- **PDF**: `.pdf`
- **图像**: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`
- **Excel**: `.xlsx`, `.xls`
- **HTML**: `.html`, `.htm`

## 错误处理

### 常见错误码

| 状态码 | 错误类型 | 说明 |
|--------|----------|------|
| 400 | 请求格式错误 | 缺少必需字段或Base64解码失败 |
| 413 | 文件过大 | 文件大小超过100MB限制 |
| 415 | 不支持的文件类型 | 文件扩展名不在支持列表中 |
| 500 | 服务器错误 | 文件处理过程中发生错误 |

### 示例错误响应

```json
{
  "success": false,
  "message": "Base64数据解码失败: Invalid base64-encoded string",
  "error_code": "DECODE_ERROR"
}
```

## 性能建议

1. **文件大小限制**: 最大支持100MB文件
2. **Base64编码开销**: Base64编码会增加约33%的数据大小
3. **网络传输**: 对于大文件，建议使用原文件上传接口
4. **超时设置**: 建议设置合理的请求超时时间（如5分钟）

## 测试

使用提供的测试脚本 `test_base64_api.py` 来测试接口：

```bash
# 修改脚本中的测试文件路径
python test_base64_api.py
```

## 与原接口的对比

| 特性 | `/api/process` | `/api/process-base64` |
|------|----------------|----------------------|
| 输入方式 | 文件上传 (multipart/form-data) | JSON + Base64 |
| 数据传输 | 原始文件大小 | Base64编码后大小（+33%） |
| 前端集成 | 需要 FormData | 标准 JSON API |
| 适用场景 | 直接文件上传 | 已有Base64数据、系统集成 |
| 处理逻辑 | 相同 | 相同 |
| 响应格式 | 相同 | 相同 |
