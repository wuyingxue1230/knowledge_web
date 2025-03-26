import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 飞书应用配置
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "cli_a769c6cbe13b101c")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "RMv5qs1evWRblW1bekmn9fUdj2XFZZaq")
    
    # 多维表格配置
    BASE_ID = os.getenv("BASE_ID", "R7VObQxrxaHtLzs6QzGcIFyznZg")
    TABLE_ID = os.getenv("TABLE_ID", "tbltlDw7PngrCo4x")

    # Flask配置
    SECRET_KEY = os.urandom(24)
    DEBUG = True 