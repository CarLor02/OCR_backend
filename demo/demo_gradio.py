import gradio as gr
import os
import base64
from pdf2image import convert_from_path
import re
import zipfile
import subprocess
from pathlib import Path
import tempfile
import uuid
import requests

from PIL import Image
from loguru import logger

# 支持的文件类型
supported_file_types = [
    ".pdf", ".doc", ".docx",
    ".xlsx", ".xls",
    ".html", ".htm",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"
]

if __name__ == '__main__':
    # 后端API配置
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:7860")
    
    def render_latex_table_to_image(latex_content, temp_dir):
        """渲染LaTeX表格为图像"""
        try:
            pattern = r"(\\begin\{tabular\}.*?\\end\{tabular\})"
            matches = re.findall(pattern, latex_content, re.DOTALL)
            
            if matches:
                table_content = matches[0]
            elif '\\begin{tabular}' in latex_content:
                if '\\end{tabular}' not in latex_content:
                    table_content = latex_content + '\n\\end{tabular}'
                else:
                    table_content = latex_content
            else:
                return latex_content
            
            full_latex = r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{booktabs}
\usepackage{array}
\usepackage{amsmath}
\usepackage[active,tightpage]{preview}
\PreviewEnvironment{tabular}
\begin{document}
""" + table_content + r"""
\end{document}
"""
            
            unique_id = str(uuid.uuid4())[:8]
            tex_path = os.path.join(temp_dir, f"table_{unique_id}.tex")
            pdf_path = os.path.join(temp_dir, f"table_{unique_id}.pdf")
            png_path = os.path.join(temp_dir, f"table_{unique_id}.png")
            
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(full_latex)
            
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_path], 
                timeout=20, capture_output=True, text=True
            )
            
            if result.returncode != 0 or not os.path.exists(pdf_path):
                return f"<pre>{latex_content}</pre>"
            
            images = convert_from_path(pdf_path, dpi=300)
            images[0].save(png_path, "PNG")
            
            with open(png_path, "rb") as f:
                img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            
            # 清理临时文件
            for file_path in [tex_path, pdf_path, png_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return f'<img src="data:image/png;base64,{img_base64}" style="max-width:100%;height:auto;">'
            
        except Exception as e:
            return f"<pre>{latex_content}</pre>"

    def parse_document_and_return_results(file_path):
        """解析文档并返回结果"""
        if file_path is None:
            error_msg = "请上传文件"
            return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
        
        # 检查文件大小
        try:
            file_size = os.path.getsize(file_path)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                error_msg = f"❌ 文件大小超过限制，最大允许10MB，当前文件大小：{file_size / 1024 / 1024:.1f}MB"
                return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
        except Exception as e:
            error_msg = f"❌ 检查文件大小失败: {str(e)}"
            return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
        
        try:
            # 调用后端API
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(f"{BACKEND_URL}/api/process", files=files, timeout=300)
            
            if response.status_code != 200:
                error_msg = f"API调用失败: HTTP {response.status_code}"
                return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
            
            result = response.json()
            if not result.get('success'):
                error_msg = f"处理失败: {result.get('error', '未知错误')}"
                return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
            
            md_content_ori = result.get('content', "处理完成，但未生成内容")
            
            # 处理Markdown内容
            temp_dir = tempfile.mkdtemp()
            try:
                # 处理LaTeX表格
                def replace_html_latex_table(match):
                    html_content = match.group(1)
                    if '\\begin{tabular}' in html_content:
                        return render_latex_table_to_image(html_content, temp_dir)
                    return match.group(0)
                
                md_content = re.sub(r'<html>(.*?)</html>', replace_html_latex_table, md_content_ori, flags=re.DOTALL)
                
            finally:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 创建下载文件
            parent_path = os.path.dirname(file_path)
            name = Path(file_path).stem
            zip_path = os.path.join(parent_path, f"{name}_markdown.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(f"{name}.md", md_content_ori.encode('utf-8'))
            
            return (
                md_content_ori,
                md_content,
                gr.update(value=None, visible=True),
                gr.update(value=zip_path, visible=True),
            )
            
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到后端服务，请确保后端服务已启动"
            return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))
        except Exception as e:
            logger.error(f"调用后端API时出错: {e}")
            error_msg = f"处理出错: {str(e)}"
            return (error_msg, error_msg, gr.update(value=None, visible=False), gr.update(value=None, visible=False))

    # PDF缓存
    pdf_cache = {"images": [], "current_page": 0, "total_pages": 0}

    def load_file(file):
        """加载文件预览"""
        file_ext = Path(file).suffix.lower()
        
        if file_ext == '.pdf':
            pages = convert_from_path(file, dpi=150)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            pages = [Image.open(file)]
        else:
            # 创建简单预览
            img = Image.new('RGB', (800, 600), color='lightgray')
            pages = [img]
        
        pdf_cache["images"] = pages
        pdf_cache["current_page"] = 0
        pdf_cache["total_pages"] = len(pages)
        return pages[0], f"<div id='page_info_box'>1 / {len(pages)}</div>"

    def turn_page(direction):
        """翻页"""
        if not pdf_cache["images"]:
            return None, "<div id='page_info_box'>0 / 0</div>"

        if direction == "prev":
            pdf_cache["current_page"] = max(0, pdf_cache["current_page"] - 1)
        elif direction == "next":
            pdf_cache["current_page"] = min(pdf_cache["total_pages"] - 1, pdf_cache["current_page"] + 1)

        index = pdf_cache["current_page"]
        return pdf_cache["images"][index], f"<div id='page_info_box'>{index + 1} / {pdf_cache['total_pages']}</div>"

    def parse_and_update_view(file_path):
        """解析文档并更新视图"""
        if file_path is None:
            return (gr.update(), "请上传文件", "请上传文件", "<div id='page_info_box'>0 / 0</div>",
                   gr.update(value=None, visible=True), gr.update(value=None, visible=True))

        # 在解析前再次检查文件大小
        try:
            file_size = os.path.getsize(file_path)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                raise gr.Error(f"❌ 文件大小超过限制！最大允许10MB，当前文件：{file_size / 1024 / 1024:.1f}MB")
        except OSError as e:
            raise gr.Error(f"❌ 检查文件失败: {str(e)}")

        # 调用解析函数
        md_content_ori, md_content, layout_pdf_update, zip_update = parse_document_and_return_results(file_path)
        
        # 保持当前预览状态，不重新加载
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            # PDF文件：保持当前页面状态
            if pdf_cache["images"]:
                current_page = pdf_cache["current_page"]
                preview_image = pdf_cache["images"][current_page]
                page_info = f"<div id='page_info_box'>{current_page + 1} / {pdf_cache['total_pages']}</div>"
            else:
                # 如果缓存为空，重新加载
                try:
                    pages = convert_from_path(file_path, dpi=150)
                    pdf_cache["images"] = pages
                    pdf_cache["current_page"] = 0
                    pdf_cache["total_pages"] = len(pages)
                    preview_image = pages[0]
                    page_info = f"<div id='page_info_box'>1 / {len(pages)}</div>"
                except:
                    preview_image = None
                    page_info = "<div id='page_info_box'>0 / 0</div>"
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            # 图像文件：保持当前图像显示
            if pdf_cache["images"]:
                preview_image = pdf_cache["images"][0]
                page_info = f"<div id='page_info_box'>1 / 1</div>"
            else:
                # 重新加载图像
                try:
                    image = Image.open(file_path)
                    pdf_cache["images"] = [image]
                    pdf_cache["current_page"] = 0
                    pdf_cache["total_pages"] = 1
                    preview_image = image
                    page_info = f"<div id='page_info_box'>1 / 1</div>"
                except:
                    preview_image = None
                    page_info = "<div id='page_info_box'>0 / 0</div>"
        else:
            # 其他文件类型：保持当前状态
            if pdf_cache["images"]:
                current_page = pdf_cache["current_page"]
                preview_image = pdf_cache["images"][current_page] if current_page < len(pdf_cache["images"]) else None
                page_info = f"<div id='page_info_box'>{current_page + 1} / {pdf_cache['total_pages']}</div>"
            else:
                preview_image = None
                page_info = "<div id='page_info_box'>0 / 0</div>"
        
        return (preview_image, md_content, md_content_ori, page_info, layout_pdf_update, zip_update)

    def clear_all():
        """清除所有内容"""
        pdf_cache["images"] = []
        pdf_cache["current_page"] = 0
        pdf_cache["total_pages"] = 0
        return (None, None, "## 🕐 等待解析结果...", "🕐 等待解析结果...", "<div id='page_info_box'>0 / 0</div>",
               gr.update(value=None, visible=True), gr.update(value=None, visible=True))

    def validate_file_upload(file):
        """验证上传的文件"""
        if file is None:
            return None

        # 检查文件大小
        try:
            file_size = os.path.getsize(file)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                raise gr.Error(f"❌ 文件大小超过限制！最大允许10MB，当前文件：{file_size / 1024 / 1024:.1f}MB")
        except OSError as e:
            raise gr.Error(f"❌ 检查文件失败: {str(e)}")

        return file

    def load_file_with_validation(file):
        """验证并加载文件预览"""
        # 先验证文件
        validated_file = validate_file_upload(file)
        if validated_file is None:
            # 验证失败，返回空状态
            return None, None, "<div id='page_info_box'>0 / 0</div>"

        # 验证通过，加载预览
        preview_image, page_info = load_file(validated_file)
        return validated_file, preview_image, page_info

    css = """
    #page_info_html { display: flex; align-items: center; justify-content: center; height: 100%; margin: 0 12px; }
    #page_info_box { padding: 8px 20px; font-size: 16px; border: 1px solid #bbb; border-radius: 8px; 
                     background-color: #f8f8f8; text-align: center; min-width: 80px; }
    #markdown_output { min-height: 800px; overflow: auto; }
    footer { visibility: hidden; }
    """

    with gr.Blocks(theme="ocean", css=css, title='文档处理工具') as demo:
        gr.HTML("<h1 style='text-align: center;'>文档处理工具</h1>")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📥 上传文件")
                file_input = gr.File(label="选择文件", type="filepath", file_types=supported_file_types)
                parse_button = gr.Button("🔍 解析文档", variant="primary")
                clear_button = gr.Button("🗑️ 清除", variant="secondary")

            with gr.Column(scale=6):
                with gr.Row():
                    with gr.Column(scale=3):
                        gr.Markdown("### 👁️ 文件预览")
                        pdf_view = gr.Image(label="预览", height=800, show_label=False)
                        with gr.Row():
                            prev_btn = gr.Button("⬅ 上一页")
                            page_info = gr.HTML("<div id='page_info_box'>0 / 0</div>", elem_id="page_info_html")
                            next_btn = gr.Button("下一页 ➡")
                    
                    with gr.Column(scale=3):
                        gr.Markdown("### ✔️ 结果展示")
                        with gr.Tabs():
                            with gr.TabItem("Markdown预览"):
                                md_view = gr.Markdown("## 请点击解析按钮...", elem_id="markdown_output")
                            with gr.TabItem("原始文本"):
                                md_raw = gr.Textbox("🕐 等待解析结果...", lines=38, show_copy_button=True)
                
                with gr.Row():
                    pdf_download_button = gr.DownloadButton("⬇️ 下载PDF", visible=True)
                    md_download_button = gr.DownloadButton("⬇️ 下载Markdown", visible=True)

        # 事件绑定
        file_input.upload(
            fn=load_file_with_validation,
            inputs=file_input,
            outputs=[file_input, pdf_view, page_info]
        )
        prev_btn.click(fn=lambda: turn_page("prev"), outputs=[pdf_view, page_info])
        next_btn.click(fn=lambda: turn_page("next"), outputs=[pdf_view, page_info])
        parse_button.click(fn=parse_and_update_view, inputs=file_input, 
                          outputs=[pdf_view, md_view, md_raw, page_info, pdf_download_button, md_download_button])
        clear_button.click(fn=clear_all, 
                          outputs=[file_input, pdf_view, md_view, md_raw, page_info, pdf_download_button, md_download_button])

    demo.launch(server_port=7861, debug=False, share=False, inbrowser=False)
