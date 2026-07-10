"""
智谱OCR客户端
调用智谱AI的OCR服务，支持图片文字识别
"""

import requests
import logging
import time
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class ZhipuOCRClient:
    """智谱OCR客户端"""

    DEFAULT_API_URL = 'https://open.bigmodel.cn/api/paas/v4/files/ocr'
    MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB

    def __init__(self, api_key: str, api_url: str = None, language_type: str = 'CHN_ENG'):
        self.api_key = api_key
        self.api_url = api_url or self.DEFAULT_API_URL
        self.language_type = language_type

    def recognize_image(self, image_path: Path, language_type: str = None, probability: bool = False, timeout: int = 120) -> Dict[str, Any]:
        """
        调用智谱OCR识别图片

        Args:
            image_path: 图片文件路径 (PNG/JPG/JPEG/BMP)
            language_type: 语言类型，默认使用实例配置
            probability: 是否返回置信度
            timeout: 请求超时时间(秒)

        Returns:
            dict: OCR识别结果
        """
        file_size = image_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"图片文件大小 {file_size} 超过限制 {self.MAX_FILE_SIZE} 字节 (8MB)")

        lang = language_type or self.language_type

        with open(image_path, 'rb') as f:
            files = {
                'file': (image_path.name, f, self._get_content_type(image_path))
            }
            data = {
                'tool_type': 'hand_write',
                'language_type': lang,
                'probability': str(probability).lower()
            }
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }

            try:
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=timeout
                )
            except requests.exceptions.Timeout:
                raise TimeoutError(f"智谱OCR请求超时 ({image_path.name})")
            except requests.exceptions.ConnectionError:
                raise ConnectionError(f"无法连接到智谱OCR服务: {self.api_url}")
            except requests.RequestException as exc:
                raise RuntimeError(f"智谱OCR请求失败: {exc}")

        if response.status_code != 200:
            raise RuntimeError(f"智谱OCR返回错误状态 {response.status_code}: {response.text[:300]}")

        result = response.json()

        if result.get('status') != 'succeeded':
            raise RuntimeError(f"智谱OCR识别失败: {result.get('message', '未知错误')}")

        return result

    def recognize_image_bytes(self, image_bytes: bytes, filename: str, language_type: str = None, probability: bool = False, timeout: int = 120) -> Dict[str, Any]:
        """
        调用智谱OCR识别图片字节流

        Args:
            image_bytes: 图片字节数据
            filename: 文件名 (用于确定格式)
            language_type: 语言类型
            probability: 是否返回置信度
            timeout: 请求超时时间(秒)

        Returns:
            dict: OCR识别结果
        """
        if len(image_bytes) > self.MAX_FILE_SIZE:
            raise ValueError(f"图片数据大小 {len(image_bytes)} 超过限制 {self.MAX_FILE_SIZE} 字节 (8MB)")

        lang = language_type or self.language_type
        suffix = Path(filename).suffix.lower() if filename else '.png'

        files = {
            'file': (filename, image_bytes, self._get_content_type_by_suffix(suffix))
        }
        data = {
            'tool_type': 'hand_write',
            'language_type': lang,
            'probability': str(probability).lower()
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        try:
            response = requests.post(
                self.api_url,
                files=files,
                data=data,
                headers=headers,
                timeout=timeout
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(f"智谱OCR请求超时 ({filename})")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"无法连接到智谱OCR服务: {self.api_url}")
        except requests.RequestException as exc:
            raise RuntimeError(f"智谱OCR请求失败: {exc}")

        if response.status_code != 200:
            raise RuntimeError(f"智谱OCR返回错误状态 {response.status_code}: {response.text[:300]}")

        result = response.json()

        if result.get('status') != 'succeeded':
            raise RuntimeError(f"智谱OCR识别失败: {result.get('message', '未知错误')}")

        return result

    @staticmethod
    def extract_text_from_result(result: Dict[str, Any]) -> str:
        """
        从智谱OCR结果中提取纯文本

        Args:
            result: OCR识别结果

        Returns:
            str: 提取的文本内容
        """
        words_result = result.get('words_result', [])
        if not words_result:
            return ''

        lines = []
        for item in words_result:
            words = item.get('words', '')
            if words:
                lines.append(words)

        return '\n'.join(lines)

    @staticmethod
    def _get_content_type(image_path: Path) -> str:
        ext = image_path.suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.bmp': 'image/bmp'
        }
        return content_types.get(ext, 'image/jpeg')

    @staticmethod
    def _get_content_type_by_suffix(suffix: str) -> str:
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.bmp': 'image/bmp'
        }
        return content_types.get(suffix, 'image/jpeg')


def pdf_page_to_image(page, dpi: int = 200) -> bytes:
    """
    将PyMuPDF的page对象转为PNG图片字节

    Args:
        page: fitz.Page 对象
        dpi: 渲染DPI

    Returns:
        bytes: PNG图片字节数据
    """
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes('png')


try:
    import fitz
    PYMUPDF_FOR_RENDER = True
except ImportError:
    PYMUPDF_FOR_RENDER = False


def process_scanned_pdf_with_zhipu(
    file_path: Path,
    zhipu_client: ZhipuOCRClient,
    logger_instance=None,
    dpi: int = 200,
    delay: float = 0.0,
    timeout: int = 120
) -> Tuple[str, Dict[str, Any]]:
    """
    使用智谱OCR处理扫描PDF：逐页渲染为图片后调用OCR

    Args:
        file_path: PDF文件路径
        zhipu_client: 智谱OCR客户端实例
        logger_instance: 日志记录器
        dpi: PDF渲染DPI
        delay: 每页请求间隔(秒)
        timeout: OCR请求超时(秒)

    Returns:
        (content, metadata) 元组
    """
    if not PYMUPDF_FOR_RENDER:
        raise ImportError("PyMuPDF未安装，无法将PDF渲染为图片")

    log = logger_instance or logger

    doc = fitz.open(file_path)
    total_pages = len(doc)

    metadata = {
        'ocr_engine': 'zhipu',
        'total_pages': total_pages,
        'pages_succeeded': 0,
        'pages_failed': 0
    }

    sections = [f"# {file_path.stem}\n"]

    for page_num in range(total_pages):
        page = doc[page_num]
        log.info(f"智谱OCR: 处理第 {page_num + 1}/{total_pages} 页")

        try:
            image_bytes = pdf_page_to_image(page, dpi=dpi)

            if len(image_bytes) > ZhipuOCRClient.MAX_FILE_SIZE:
                scaled_dpi = int(dpi * (ZhipuOCRClient.MAX_FILE_SIZE / len(image_bytes)) ** 0.5)
                scaled_dpi = max(scaled_dpi, 72)
                log.warning(f"第 {page_num + 1} 页图片超过8MB，降低DPI至 {scaled_dpi} 重试")
                image_bytes = pdf_page_to_image(page, dpi=scaled_dpi)

            filename = f"page_{page_num + 1}.png"
            result = zhipu_client.recognize_image_bytes(
                image_bytes=image_bytes,
                filename=filename,
                timeout=timeout
            )

            page_text = ZhipuOCRClient.extract_text_from_result(result)

            if page_text:
                metadata['pages_succeeded'] += 1
                sections.append(f"## 第 {page_num + 1} 页\n\n{page_text}\n")
            else:
                metadata['pages_failed'] += 1
                sections.append(f"<!-- 第 {page_num + 1} 页OCR返回空内容 -->\n")

        except Exception as exc:
            metadata['pages_failed'] += 1
            log.error(f"智谱OCR第 {page_num + 1} 页失败: {exc}", exc_info=True)
            sections.append(f"<!-- 第 {page_num + 1} 页OCR失败: {exc} -->\n")

        if delay > 0 and page_num < total_pages - 1:
            time.sleep(delay)

    doc.close()

    if metadata['pages_succeeded'] == 0:
        raise RuntimeError("智谱OCR未返回任何可用内容，请检查API Key和服务状态")

    content = "\n".join(sections).strip()
    return content, metadata
