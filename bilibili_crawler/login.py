# -*- coding: utf-8 -*-
"""
bilibili_crawler/login.py - B站登录功能 (同步版本)
"""
import time
from typing import Optional
from playwright.sync_api import BrowserContext, Page
from .helper import logger_info, logger_error, convert_str_cookie_to_dict, show_qrcode


class BilibiliLogin:
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = ""
    ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    def begin(self):
        """
        开始登录
        """
        logger_info(f"开始使用 {self.login_type} 方式登录B站...")

        if self.login_type == "qrcode":
            self.login_by_qrcode()
        elif self.login_type == "cookie":
            self.login_by_cookies()
        else:
            logger_error(f"不支持的登录方式: {self.login_type}")
            raise ValueError(f"不支持的登录方式: {self.login_type}")

    def login_by_qrcode(self):
        """
        二维码登录
        """
        logger_info("开始B站二维码登录...")

        # 导航到登录页面
        self.context_page.goto("https://passport.bilibili.com/login")
        time.sleep(2)

        # 等待二维码出现
        try:
            # B站二维码登录的常见选择器
            qr_code_selectors = [
                "div.login-img-box img",  # 扫码登录二维码
                "div.qrcode-img img",      # 二维码图片
                "img.qrcode-img",          # 二维码
                "#qrlogin div img"         # 二维码区域
            ]

            qr_code_img = None
            for selector in qr_code_selectors:
                try:
                    qr_code_img = self.context_page.wait_for_selector(selector, timeout=5000)
                    if qr_code_img:
                        break
                except:
                    continue

            if qr_code_img:
                qr_src = qr_code_img.get_attribute("src")
                if not qr_src.startswith("http"):
                    # 如果src是base64编码的数据URL
                    if qr_src.startswith("data:image"):
                        logger_info("检测到二维码，正在显示...")
                        # 显示二维码
                        show_qrcode(qr_src)
                    else:
                        logger_error("无法获取有效的二维码")
                        return
                else:
                    # 如果是网络图片，尝试下载
                    logger_info(f"检测到二维码URL: {qr_src}")
                    # 这里可以实现下载功能，但最简单的是直接在浏览器中打开
                    pass
            else:
                # 如果没有找到标准选择器的二维码，尝试点击二维码登录按钮
                try:
                    qr_login_btn = self.context_page.wait_for_selector(
                        "text=扫码登录",
                        timeout=3000
                    )
                    if qr_login_btn:
                        qr_login_btn.click()
                        time.sleep(2)

                        # 再次尝试查找二维码
                        qr_code_img = self.context_page.wait_for_selector(
                            "div.login-img-box img",
                            timeout=5000
                        )
                        if qr_code_img:
                            qr_src = qr_code_img.get_attribute("src")
                            if qr_src and qr_src.startswith("data:image"):
                                logger_info("检测到二维码，正在显示...")
                                show_qrcode(qr_src)
                except:
                    logger_error("未找到二维码登录选项")
                    return

            # 等待登录完成
            login_success_selector = ".nav-user-center,.bili-avatar,.user-name"
            try:
                self.context_page.wait_for_selector(login_success_selector, timeout=120000)  # 最多等待2分钟
                logger_info("B站二维码登录成功")
            except:
                logger_error("B站二维码登录超时，请检查是否已完成登录")

        except Exception as e:
            logger_error(f"B站二维码登录出错: {e}")

    def login_by_cookies(self):
        """
        Cookie登录
        """
        logger_info("开始B站Cookie登录...")

        # 解析Cookie字符串
        cookie_dict = convert_str_cookie_to_dict(self.cookie_str)

        # 设置Cookie
        for name, value in cookie_dict.items():
            self.browser_context.add_cookies([{
                'name': name,
                'value': value,
                'domain': '.bilibili.com',
                'path': '/'
            }])

        logger_info("B站Cookie设置完成")

        # 访问主页验证登录状态
        self.context_page.goto("https://www.bilibili.com")
        time.sleep(3)