"""
数据库模块
使用SQLite存储任务历史、翻译配置
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from .config import DB_PATH


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 任务历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            config_json TEXT NOT NULL,
            parse_result_json TEXT,
            xml_content TEXT,
            status TEXT DEFAULT 'pending',
            message TEXT DEFAULT ''
        )
    """)

    # 自定义翻译表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            english TEXT PRIMARY KEY,
            chinese TEXT NOT NULL,
            category TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 指标分类规则表 (支持用户自定义覆盖)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classify_rules (
            keyword TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            delay TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_task(task_id: str, filename: str, config_json: str,
              parse_result_json: str = "", xml_content: str = "",
              status: str = "pending", message: str = ""):
    """保存任务记录"""
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO tasks
           (task_id, created_at, filename, config_json, parse_result_json, xml_content, status, message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (task_id, datetime.utcnow().isoformat(), filename, config_json,
         parse_result_json, xml_content, status, message)
    )
    conn.commit()
    conn.close()


def get_task(task_id: str) -> Optional[Dict]:
    """获取单个任务"""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def list_tasks(limit: int = 50) -> List[Dict]:
    """列出历史任务"""
    conn = get_db()
    rows = conn.execute(
        "SELECT task_id, created_at, filename, status, message FROM tasks ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_task(task_id: str) -> bool:
    """删除任务"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# 翻译管理
def save_translation(english: str, chinese: str, category: str = ""):
    """保存翻译词条"""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO translations (english, chinese, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (english.lower().strip(), chinese, category, now, now)
    )
    conn.commit()
    conn.close()


def list_translations() -> List[Dict]:
    """列出所有自定义翻译"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM translations ORDER BY english").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_translation(english: str) -> bool:
    """删除翻译词条"""
    conn = get_db()
    cursor = conn.execute("DELETE FROM translations WHERE english = ?", (english.lower().strip(),))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# 分类规则管理
def save_classify_rule(keyword: str, category: str, delay: str):
    """保存分类规则"""
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO classify_rules (keyword, category, delay, created_at)
           VALUES (?, ?, ?, ?)""",
        (keyword.lower().strip(), category, delay, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def list_classify_rules() -> List[Dict]:
    """列出所有自定义分类规则"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM classify_rules ORDER BY keyword").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def init_app():
    """应用初始化"""
    init_db()
