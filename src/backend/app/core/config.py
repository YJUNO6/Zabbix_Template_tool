"""
全局配置
项目路径、数据库、上传限制等
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 上传目录
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 数据目录 (SQLite数据库、翻译配置等)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# SQLite数据库路径
DB_PATH = DATA_DIR / "tasks.db"

# 上传文件限制
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".mib", ".txt", ".my"}

# MIB搜索路径 (pysmi编译器用)
MIB_SEARCH_PATHS = [
    str(UPLOAD_DIR),
    str(DATA_DIR / "mibs"),
    os.path.expanduser("~/.pysnmp/mibs"),
]

# Zabbix模板默认值
DEFAULTS = {
    "template_prefix": "LW_Template",
    "snmp_community": "public",
    "status_delay": "1m",
    "performance_delay": "5m",
    "info_delay": "1d",
    "history_days": "7d",
    "trends_days": "30d",
    "discovery_delay_normal": "10m",
    "discovery_delay_fan_power": "5m",
}

# 固定主机组 (不可修改)
FIXED_GROUPS = ["服务器模板", "监控模板"]

# CORS配置
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

# FastAPI配置
API_HOST = "0.0.0.0"
API_PORT = 8000
