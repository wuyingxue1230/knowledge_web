from flask import Flask, render_template, jsonify
import requests
from config import Config
import time

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
    if isinstance(field, list):
        return "\n".join(str(item) for item in field)
    return str(field) if field is not None else ""

feishu_api = FeishuAPI(Config.FEISHU_APP_ID, Config.FEISHU_APP_SECRET)

@app.route('/')
def index():
    try:
        records = feishu_api.get_records(Config.BASE_ID, Config.TABLE_ID)
        articles = []
        for record in records:
            fields = record.get("fields", {})
            article = {
                "id": record.get("record_id"),
                "title": process_field(fields.get("标题")),
                "quote": process_field(fields.get("金句输出")),
                "comment": process_field(fields.get("西瓜点评")),
                "content": process_field(fields.get("概要内容输出"))[:100] + "..." if fields.get("概要内容输出") else ""
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
                article = {
                    "id": record_id,
                    "title": process_field(fields.get("标题")),
                    "quote": process_field(fields.get("金句输出")),
                    "comment": process_field(fields.get("西瓜点评")),
                    "content": process_field(fields.get("概要内容输出"))
                }
                break
        if article:
            return render_template('detail.html', article=article)
        return "文章未找到", 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 