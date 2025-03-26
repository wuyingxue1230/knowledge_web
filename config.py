import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 飞书应用配置
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "xxxx")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "xxxx")
    
    # 多维表格配置
    BASE_ID = os.getenv("BASE_ID", "xxxx")
    TABLE_ID = os.getenv("TABLE_ID", "xxxx")

    # Flask配置
    SECRET_KEY = os.urandom(24)
    DEBUG = True 
