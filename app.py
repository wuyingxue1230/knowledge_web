from flask import Flask, render_template, jsonify
import requests
from config import Config
import time
import markdown
import json

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
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("data", {}).get("items", [])
        else:
            raise Exception(f"获取记录失败: {result}")

def process_field(field):
    """处理字段值，确保返回字符串"""
    if field is None:
        return ""
        
    # 如果是列表，将所有项连接成字符串
    if isinstance(field, list):
        return "\n".join(str(item) for item in field)
        
    # 如果是字典，直接查找 text 字段
    if isinstance(field, dict):
        return str(field.get("text", ""))
        
    # 如果是字符串，尝试解析 JSON
    if isinstance(field, str):
        try:
            # 尝试解析 JSON 字符串
            field_dict = json.loads(field)
            if isinstance(field_dict, dict):
                return str(field_dict.get("text", field))
        except json.JSONDecodeError:
            return field
            
    return str(field)

def render_markdown(text):
    """将Markdown文本转换为HTML"""
    return markdown.markdown(text, extensions=['extra'])

feishu_api = FeishuAPI(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET)

@app.route('/')
def index():
    try:
        records = feishu_api.get_records(Config.BASE_ID, Config.TABLE_ID)
        articles = []
        for record in records:
            fields = record.get("fields", {})
            content = process_field(fields.get("概要内容输出"))
            article = {
                "id": record.get("record_id"),
                "title": process_field(fields.get("标题")),
                "quote": process_field(fields.get("金句输出")),
                "comment": process_field(fields.get("西瓜点评")),
                "content": content[:100] + "..." if len(content) > 100 else content
            }
            articles.append(article)
        return render_template('index.html', articles=articles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/article/<record_id>')
def article_detail(record_id):
    try:
        records = feishu_api.get_records(Config.BASE_ID, Config.TABLE_ID)
        article = None
        for record in records:
            if record.get("record_id") == record_id:
                fields = record.get("fields", {})
                content = process_field(fields.get("概要内容输出"))
                article = {
                    "id": record_id,
                    "title": process_field(fields.get("标题")),
                    "quote": process_field(fields.get("金句输出")),
                    "comment": process_field(fields.get("西瓜点评")),
                    "content": render_markdown(content)
                }
                break
        if article:
            return render_template('detail.html', article=article)
        return "文章未找到", 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 