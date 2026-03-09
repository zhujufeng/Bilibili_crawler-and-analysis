# -*- coding: utf-8 -*-
"""
bilibili_crawler/client.py - B站 API 客户端 (同步版 + WBI签名)
"""
import random
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import httpx
import time
from typing import Dict, List, Optional, Tuple
from playwright.sync_api import Page
from .wbi_helper import enc_wbi


class BilibiliClient:
    def __init__(self, playwright_page: Page, headers: Dict):
        self.page = playwright_page
        self.headers = headers
        self.base_url = "https://api.bilibili.com"

        # 使用 httpx Client 管理会话
        self.client = httpx.Client(
            headers=headers,
            timeout=30.0,
            http2=True  # 尽量开启 HTTP2 模拟浏览器行为
        )

        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        })

        self.client = httpx.Client(
            headers=self.headers,
            timeout=30.0,
            http2=True,
            follow_redirects=True
        )


    def update_cookies(self, cookie_dict: Dict):
        """更新 Client 的 cookies (主要是 Header 里的 Cookie 字符串)"""
        self.headers.update(cookie_dict)
        self.client.headers.update(cookie_dict)

    def _get_wbi_keys(self) -> Tuple[str, str]:
        """
        从浏览器 LocalStorage 中获取 img_key 和 sub_key
        这是最安全的方法，因为浏览器访问 B 站首页时会自动生成这些 Key
        """
        try:
            # 执行 JS 获取 localStorage
            local_storage = self.page.evaluate("() => window.localStorage")
            wbi_img_urls = local_storage.get("wbi_img_urls", "")

            if not wbi_img_urls:
                # 尝试访问 nav 接口获取
                resp = self.client.get(f"{self.base_url}/x/web-interface/nav")
                wbi_img = resp.json().get('data', {}).get('wbi_img', {})
                img_url = wbi_img.get('img_url', '')
                sub_url = wbi_img.get('sub_url', '')
            else:
                img_url, sub_url = wbi_img_urls.split("-")

            img_key = img_url.rsplit('/', 1)[1].split('.')[0]
            sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
            return img_key, sub_key
        except Exception as e:
            print(f"[Warning] 获取 WBI Keys 失败，使用硬编码默认值: {e}")
            return "7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45"

    def _request(self, method, url, params=None, **kwargs):
        """
        核心请求方法：手动构建 URL 以保护签名
        """
        if params:
            # 手动 urlencode，防止 httpx 自动排序导致签名失效
            query_string = urlencode(params)
            url = f"{url}?{query_string}"

        # 发送请求时，params 设为 None，因为我们已经拼接到 URL 里了
        response = self.client.request(method, url, params=None, **kwargs)
        return response

    def search_videos(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict:
        """
        搜索视频 (带 WBI 签名)
        """
        url = "/x/web-interface/wbi/search/type"

        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": "totalrank"
        }

        # 1. 获取 Key
        img_key, sub_key = self._get_wbi_keys()

        # 2. 计算签名 (这一步会给 params 增加 w_rid 和 wts)
        signed_params = enc_wbi(params, img_key, sub_key)

        # 3. 发送请求
        try:
            resp = self.client.get(f"{self.base_url}{url}", params=signed_params)
            resp.raise_for_status()
            data = resp.json()
            if data['code'] == 0:
                return data['data']
            else:
                print(f"搜索接口返回错误: {data.get('message')}")
                return {}
        except Exception as e:
            print(f"搜索请求异常: {e}")
            return {}

    def get_user_videos(self, mid: str, page: int = 1, page_size: int = 30, order: str = "pubdate") -> Dict:
        """
        获取UP主投稿视频列表 (带 WBI 签名)
        :param mid: UP主的UID
        :param page: 页码
        :param page_size: 每页数量
        :param order: 排序方式 pubdate(时间) click(播放) stow(收藏)
        :return: 包含视频列表的字典
        """
        url = "/x/space/wbi/arc/search"

        params = {
            "mid": mid,
            "pn": page,
            "ps": page_size,
            "tid": 0,  # 0表示全部分类
            "order": order,
            "keyword": ""
        }

        # 1. 获取 Key
        img_key, sub_key = self._get_wbi_keys()

        # 2. 计算签名
        signed_params = enc_wbi(params, img_key, sub_key)

        # 3. 发送请求
        try:
            resp = self.client.get(f"{self.base_url}{url}", params=signed_params)
            resp.raise_for_status()
            data = resp.json()
            if data['code'] == 0:
                return data['data']
            else:
                print(f"获取UP主视频列表接口返回错误: {data.get('message')}")
                return {}
        except Exception as e:
            print(f"获取UP主视频列表请求异常: {e}")
            return {}


    def get_video_detail(self, bvid: str) -> Dict:
        """
        获取视频详情 (View 接口通常不需要 WBI，但带上也不影响)
        """
        url = "/x/web-interface/view"
        params = {"bvid": bvid}

        try:
            resp = self.client.get(f"{self.base_url}{url}", params=params)
            data = resp.json()
            if data['code'] == 0:
                return data['data']
            return {}
        except Exception as e:
            print(f"详情请求异常: {e}")
            return {}

    def get_video_all_comments(self, oid: str, crawl_interval: float = 1.0, callback=None, max_count=20):
        """
        获取评论 (新版评论接口 /x/v2/reply/wbi/main 也需要签名)
        """
        all_comments = []
        page = 1
        next_page_offset = 0  # B站评论翻页游标，初始为 0
        is_end = False
        url = f"{self.base_url}/x/v2/reply/wbi/main"

        # 获取一次 Key 即可
        img_key, sub_key = self._get_wbi_keys()
        
        # 导入 config 获取随机延迟参数
        import config

        while not is_end and len(all_comments) < max_count:
            # 构造参数
            params = {
                "oid": oid,
                "type": 1,  # 1=视频
                "mode": 3,  # 3=热度排序 (默认)，2=时间排序
                "ps": 20,  # 每页条数
                "next": next_page_offset  # 关键翻页参数
            }

            # 签名
            signed_params = enc_wbi(params, img_key, sub_key)

            try:
                # 请求
                resp = self._request("GET", url, params=signed_params)

                # 容错处理
                if resp.status_code != 200:
                    print(f"请求状态码异常: {resp.status_code}")
                    break

                data = resp.json()
                if data['code'] != 0:
                    print(f"API 返回错误: {data.get('message')}")
                    # 遇到反爬或错误时，停止翻页
                    break

                # 解析数据
                data_body = data.get('data', {})
                if not data_body:
                    break

                replies = data_body.get('replies', [])
                if not replies:
                    replies = []  # 确保是列表

                # 收集评论
                all_comments.extend(replies)
                if callback:
                    callback(oid, replies)  # 如果有回调，触发回调

                # 检查翻页游标
                cursor = data_body.get('cursor', {})
                is_end = cursor.get('is_end', True)
                next_page_offset = cursor.get('next', 0)

                print(f"已获取视频 {oid} 的第 {page} 页评论，本页 {len(replies)} 条，累计 {len(all_comments)} 条")

                if is_end:
                    break

                # 随机休眠防止封控（使用配置的随机范围）
                sleep_min = getattr(config, 'COMMENT_PAGE_SLEEP_MIN', 1.0)
                sleep_max = getattr(config, 'COMMENT_PAGE_SLEEP_MAX', 3.0)
                sleep_time = random.uniform(sleep_min, sleep_max)
                print(f"评论翻页延迟 {sleep_time:.2f} 秒...")
                time.sleep(sleep_time)
                page += 1

            except Exception as e:
                print(f"获取评论异常: {e}")
                break

        return all_comments

    def get_video_danmaku(self, cid: str) -> List[Dict]:
        """
        获取弹幕 (XML 格式)
        """
        url = f"https://comment.bilibili.com/{cid}.xml"
        try:
            resp = self.client.get(url)
            if resp.status_code != 200:
                print(f"获取弹幕失败，状态码: {resp.status_code}")
                return []
            
            # 解决编码问题，B站弹幕通常是 UTF-8
            content = resp.content.decode('utf-8', errors='replace')
            root = ET.fromstring(content)
            
            danmaku_list = []
            for d in root.findall('d'):
                p = d.get('p', '').split(',')
                if len(p) < 8:
                    continue
                
                item = {
                    "time": float(p[0]),      # 弹幕在视频中的时间 (秒)
                    "mode": int(p[1]),       # 模式
                    "size": int(p[2]),       # 字号
                    "color": int(p[3]),      # 颜色
                    "timestamp": int(p[4]),  # 发布时间戳
                    "pool": int(p[5]),       # 弹幕池
                    "user_id": p[6],         # 用户ID哈希
                    "row_id": p[7],          # 弹幕数据库ID
                    "text": d.text           # 弹幕内容
                }
                danmaku_list.append(item)
            
            return danmaku_list
        except Exception as e:
            print(f"解析弹幕 XML 异常: {e}")
            return []

    def pong(self) -> bool:
        """检查登录状态"""
        try:
            resp = self.client.get(f"{self.base_url}/x/web-interface/nav")
            data = resp.json()
            return data.get('data', {}).get('isLogin', False)
        except:
            return False