# -*- coding: utf-8 -*-
"""
utils/helper.py - B站工具函数
"""
import json
import base64
from typing import Dict, List
from playwright.async_api import Page


def convert_cookies(cookies: List[Dict]) -> tuple[str, Dict[str, str]]:
    """
    将浏览器cookies转换为请求头格式和字典格式
    """
    cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    return cookie_str, cookie_dict


def convert_str_cookie_to_dict(cookie_str: str) -> Dict[str, str]:
    """
    将字符串格式的cookie转换为字典格式
    """
    cookie_dict = {}
    if not cookie_str:
        return cookie_dict
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key] = value
    return cookie_dict


def get_current_timestamp() -> int:
    """
    获取当前时间戳
    """
    import time
    return int(time.time() * 1000)


def find_login_qrcode(page: Page, selector: str) -> str:
    """
    查找登录二维码
    """
    import asyncio
    
    async def get_qrcode():
        img_element = await page.wait_for_selector(selector, timeout=10000)
        if img_element:
            img_src = await img_element.get_attribute("src")
            if img_src and img_src.startswith("data:image"):
                return img_src
        return None
    
    # 由于需要在同步环境中运行异步函数，我们返回一个任务
    return asyncio.run(get_qrcode()) if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() else None


def show_qrcode(qr_code: str):
    """
    显示二维码
    """
    import io
    from PIL import Image
    
    # 去除data:image前缀，并解码
    if qr_code.startswith("data:image"):
        base64_data = qr_code.split(",")[1]
        qr_image = Image.open(io.BytesIO(base64.b64decode(base64_data)))
        qr_image.show()


def logger_info(msg: str):
    """
    简单的日志记录函数
    """
    import datetime
    print(f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")


def logger_error(msg: str):
    """
    简单的错误日志记录函数
    """
    import datetime
    print(f"[ERROR] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")