import requests

def parse_pdf(file_path):
    """
    调用PDF解析API接口
    :param file_path: 要解析的PDF文件路径
    :return: 解析后的markdown内容
    """
    url = "http://38.60.251.79:7860/api/parse"  
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.split('/')[-1], f, 'application/pdf')}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        return response.json()['markdown']
    else:
        raise Exception(f"API调用失败，状态码: {response.status_code}, 错误: {response.text}")

# 使用示例
if __name__ == "__main__":
    try:
        markdown_content = parse_pdf("/Users/liruirui/Documents/code/OCR_backend/OCR_backend/uploads/1.pdf")  # 替换为你的PDF文件路径
        print("解析结果:")
        print(markdown_content)
    except Exception as e:
        print(f"发生错误: {e}")
        
        
