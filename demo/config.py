# -*- coding: utf-8 -*-
"""
Demo 配置文件
优先从 .env 或系统环境变量读取配置，避免将敏感信息提交到仓库。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Prefer demo/.env over inherited shell or system variables to keep the demo
# configuration stable when local machine env vars were set for another project.
load_dotenv(Path(__file__).with_name(".env"), override=True, encoding="utf-8-sig")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# ============================================================
# MySQL 数据库配置（与爬虫项目共用同一个数据库）
# ============================================================
DB_HOST = _env("DB_HOST", "127.0.0.1")
DB_PORT = _env_int("DB_PORT", 3306)
DB_USER = _env("DB_USER", "root")
DB_PASSWORD = _env("DB_PASSWORD", "")
DB_NAME = _env("DB_NAME", "data_big")

# ============================================================
# Coze Workflow API 配置
# 获取方式：https://www.coze.cn/open/api  或  https://www.coze.com/open/api
# COZE_API_BASE_URL 只填基础域名，不带接口路径
# ============================================================
COZE_API_TOKEN = _env("COZE_API_TOKEN", "your_coze_api_token")
COZE_WORKFLOW_ID = _env("COZE_WORKFLOW_ID", "")
COZE_API_BASE_URL = _env("COZE_API_BASE_URL", "https://api.coze.cn")

# ============================================================
# Demo 服务配置
# ============================================================
DEMO_HOST = _env("DEMO_HOST", "0.0.0.0")
DEMO_PORT = _env_int("DEMO_PORT", 8080)



