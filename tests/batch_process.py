"""
批量处理脚本

遍历指定目录下的所有 PDF / Word / Excel 文件，调用 OCR Backend 的
/api/process 接口进行解析，并将返回的 Markdown 内容保存到
tests/outputs/ 目录下（文件名与源文件同名，扩展名改为 .md）。

用法:
    python tests/batch_process.py
    python tests/batch_process.py --source "/path/to/dir" --url http://127.0.0.1:7860
"""

import argparse
import sys
import time
from pathlib import Path

import requests

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}

DEFAULT_SOURCE_DIR = "/Volumes/D/创业/2026-赛迪知识图谱/数据"
DEFAULT_SERVICE_URL = "http://127.0.0.1:7860"
DEFAULT_TIMEOUT = 600  # 秒，扫描PDF/复杂文档处理可能较慢


def find_target_files(source_dir: Path) -> list:
    """递归查找所有支持的文件，按路径排序"""
    files = [
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)


def unique_output_path(output_dir: Path, stem: str) -> Path:
    """生成不冲突的输出文件路径，同名文件加序号后缀"""
    candidate = output_dir / f"{stem}.md"
    if not candidate.exists():
        return candidate
    idx = 2
    while True:
        candidate = output_dir / f"{stem}_{idx}.md"
        if not candidate.exists():
            return candidate
        idx += 1


def process_one_file(service_url: str, file_path: Path, timeout: int) -> tuple:
    """
    调用 /api/process 接口处理单个文件

    Returns:
        (success: bool, content_or_error: str, metadata: dict)
    """
    url = f"{service_url}/api/process"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            resp = requests.post(url, files=files, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return False, f"请求异常: {e}", {}

    try:
        data = resp.json()
    except ValueError:
        return False, f"响应非JSON, HTTP {resp.status_code}: {resp.text[:200]}", {}

    if resp.status_code == 200 and data.get("success"):
        return True, data.get("content", ""), data.get("metadata", {})

    error_msg = data.get("error", f"HTTP {resp.status_code}")
    return False, error_msg, data.get("details", {})


def main():
    parser = argparse.ArgumentParser(description="批量调用OCR Backend处理PDF/Word/Excel文件")
    parser.add_argument("--source", default=DEFAULT_SOURCE_DIR, help="源文件目录")
    parser.add_argument("--url", default=DEFAULT_SERVICE_URL, help="服务地址")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="单个文件请求超时(秒)")
    args = parser.parse_args()

    source_dir = Path(args.source)
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        sys.exit(1)

    # 健康检查
    try:
        health = requests.get(f"{args.url}/api/health", timeout=10)
        if health.status_code != 200:
            print(f"⚠️  服务健康检查异常: HTTP {health.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接服务 {args.url}: {e}")
        sys.exit(1)

    target_files = find_target_files(source_dir)
    print(f"📂 源目录: {source_dir}")
    print(f"🔍 找到 {len(target_files)} 个待处理文件 (pdf/doc/docx/xls/xlsx)")
    print(f"📝 输出目录: {output_dir}\n")

    succeeded, failed = [], []

    for idx, file_path in enumerate(target_files, start=1):
        rel_path = file_path.relative_to(source_dir)
        print(f"[{idx}/{len(target_files)}] 处理: {rel_path}")

        start = time.time()
        success, content_or_error, metadata = process_one_file(args.url, file_path, args.timeout)
        elapsed = time.time() - start

        if success:
            out_path = unique_output_path(output_dir, file_path.stem)
            out_path.write_text(content_or_error, encoding="utf-8")
            print(f"  ✅ 成功 ({elapsed:.1f}s) -> {out_path.name}  metadata={metadata}")
            succeeded.append(str(rel_path))
        else:
            print(f"  ❌ 失败 ({elapsed:.1f}s): {content_or_error}")
            failed.append((str(rel_path), content_or_error))

    print("\n========== 处理完成 ==========")
    print(f"成功: {len(succeeded)}  失败: {len(failed)}  总计: {len(target_files)}")
    if failed:
        print("\n失败列表:")
        for rel_path, err in failed:
            print(f"  - {rel_path}: {err}")


if __name__ == "__main__":
    main()
