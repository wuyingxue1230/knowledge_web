from flask import Flask, render_template, jsonify
import requests
from config import Config
import time
import markdown
import json
import re
import math

app = Flask(__name__)
app.config.from_object(Config)

class FeishuAPI:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token = None
        self.token_expire_time = 0

    def get_tenant_access_token(self):
        if self.tenant_access_token and time.time() < self.token_expire_time:
            return self.tenant_access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") == 0:
            self.tenant_access_token = result.get("tenant_access_token")
            self.token_expire_time = time.time() + result.get("expire") - 60
            return self.tenant_access_token
        else:
            raise Exception(f"获取tenant_access_token失败: {result}")

    def get_records(self, base_id, table_id):
        token = self.get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            result = response.json()
            
            if result.get("code") == 0:
                return result.get("data", {}).get("items", [])
            else:
                error_msg = f"获取记录失败: 错误码 {result.get('code')}, 错误信息: {result.get('msg')}"
                print(error_msg)  # 打印错误信息以便调试
                raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"请求飞书API失败: {str(e)}"
            print(error_msg)  # 打印错误信息以便调试
            raise Exception(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"解析飞书API响应失败: {str(e)}"
            print(error_msg)  # 打印错误信息以便调试
            raise Exception(error_msg)

def process_field(field):
    """处理字段值，确保返回格式化的字符串"""
    if field is None:
        return ""
        
    # 如果是列表，将所有项格式化后连接成字符串
    if isinstance(field, list):
        formatted_items = []
        for item in field:
            if isinstance(item, dict):
                # 处理字典类型的列表项
                text = item.get("text", "")
                if text:
                    formatted_items.append(text)
            else:
                formatted_items.append(str(item))
        return "\n".join(formatted_items)
        
    # 如果是字典，优化处理text字段
    if isinstance(field, dict):
        text = field.get("text", "")
        # 处理可能的Markdown格式
        if text:
            # 清理多余的转义字符
            text = text.replace('\\n', '\n').replace('\\r', '\r').strip()
            # 规范化换行符
            text = '\n'.join(line.strip() for line in text.splitlines())
            return text
        return ""
        
    # 如果是字符串，尝试解析JSON并格式化
    if isinstance(field, str):
        try:
            # 尝试解析JSON字符串
            field_dict = json.loads(field)
            if isinstance(field_dict, dict):
                # 处理字典格式
                text = field_dict.get("text", field)
                if text:
                    # 清理并格式化文本
                    text = text.replace('\\n', '\n').replace('\\r', '\r').strip()
                    return '\n'.join(line.strip() for line in text.splitlines())
            elif isinstance(field_dict, list):
                # 处理列表格式
                formatted_items = []
                for item in field_dict:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        if text:
                            formatted_items.append(text)
                    else:
                        formatted_items.append(str(item))
                return '\n'.join(formatted_items)
            return str(field_dict)
        except json.JSONDecodeError:
            # 如果不是JSON格式，清理并格式化原始文本
            text = field.replace('\\n', '\n').replace('\\r', '\r').strip()
            return '\n'.join(line.strip() for line in text.splitlines())
            
    return str(field).strip()

def render_markdown(text):
    """将Markdown文本转换为HTML"""
    return markdown.markdown(text, extensions=['extra'])

def estimate_reading_time(text):
    """估计阅读时间（分钟）"""
    words = len(re.findall(r'\w+', text))
    # 假设中文阅读速度每分钟300字
    return math.ceil(words / 300)

def extract_tags(content):
    """从内容中提取标签"""
    # 简单的标签提取逻辑，可以根据需要调整
    tags = []
    # 查找 #标签# 格式的文本
    tag_matches = re.findall(r'#(.*?)#', content)
    if tag_matches:
        tags.extend(tag_matches)
    return list(set(tags))

feishu_api = FeishuAPI(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET)

@app.route('/')
def index():
    try:
        print("开始获取飞书多维表格数据...")
        print(f"使用的配置：BASE_ID={Config.BASE_ID}, TABLE_ID={Config.TABLE_ID}")
        records = feishu_api.get_records(Config.BASE_ID, Config.TABLE_ID)
        print(f"成功获取到 {len(records)} 条记录")
        articles = []
        for record in records:
            fields = record.get("fields", {})
            content = process_field(fields.get("概要内容输出"))
            tags = extract_tags(content)
            reading_time = estimate_reading_time(content)
            
            article = {
                "id": record.get("record_id"),
                "title": process_field(fields.get("标题")),
                "quote": process_field(fields.get("金句输出")),
                "comment": process_field(fields.get("西瓜点评")),
                "content": content[:200] + "..." if len(content) > 200 else content,
                "tags": tags,
                "reading_time": reading_time
            }
            articles.append(article)
        return render_template('index.html', articles=articles)
    except Exception as e:
        error_message = f"获取数据失败: {str(e)}"
        print(error_message)
        return render_template('error.html', error=error_message), 500

@app.route('/article/<record_id>')
def article_detail(record_id):
    try:
        records = feishu_api.get_records(Config.BASE_ID, Config.TABLE_ID)
        article = None
        for record in records:
            if record.get("record_id") == record_id:
                fields = record.get("fields", {})
                content = process_field(fields.get("概要内容输出"))
                # 确保content是纯文本格式的Markdown
                if isinstance(content, str):
                    content = content.replace('\\n', '\n')  # 处理可能的转义换行符
                
                tags = extract_tags(content)
                reading_time = estimate_reading_time(content)
                
                article = {
                    "id": record_id,
                    "title": process_field(fields.get("标题")),
                    "quote": process_field(fields.get("金句输出")),
                    "comment": process_field(fields.get("西瓜点评")),
                    "content": render_markdown(content),
                    "tags": tags,
                    "reading_time": reading_time
                }
                break
        if article:
            return render_template('detail.html', article=article)
        return "文章未找到", 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 