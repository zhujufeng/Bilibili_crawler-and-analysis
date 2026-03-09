# -*- coding: utf-8 -*-
"""
bilibili_crawler/bili_crawler.py - B站爬虫核心类 (同步版本)
支持三种任务模式:
  - video:   仅爬取视频详细信息 (每小时执行)
  - comment: 仅爬取评论和弹幕   (每天执行)
  - all:     全部爬取           (默认)
"""
import datetime
import json
import os
import time
import random
from typing import Dict, List
from playwright.sync_api import sync_playwright, BrowserContext, Page
from .helper import logger_info, logger_error, get_current_timestamp
from .client import BilibiliClient
from .login import BilibiliLogin
from .storage import BilibiliDataStorage


class BilibiliCrawler:
    def __init__(self):
        self.browser_context: BrowserContext = None
        self.context_page: Page = None
        self.bili_client: BilibiliClient = None
        self.storage = BilibiliDataStorage()
        self.crawled_bvids_in_session = set()  # 本次运行中已爬取的bvid集合

    def start(self, config, task="all"):
        """
        启动爬虫
        :param config: 配置模块
        :param task: 任务模式
            - "video":   仅爬取视频详情（适合每小时定时任务）
            - "comment": 仅爬取评论和弹幕（适合每天定时任务）
            - "all":     全部爬取（默认，兼容旧行为）
        """
        logger_info(f"开始启动B站爬虫，任务模式: {task}")

        # 设置存储选项（自动按日期创建目录）
        self.storage = BilibiliDataStorage(save_option=config.SAVE_DATA_OPTION)
        logger_info(f"数据存储目录: {self.storage.data_dir}")

        with sync_playwright() as playwright:
            # 启动浏览器
            browser = playwright.chromium.launch(
                headless=config.HEADLESS
            )

            # 创建浏览器上下文
            user_data_dir = os.path.join(os.getcwd(), "browser_data", "bilibili_user_data_dir")
            os.makedirs(user_data_dir, exist_ok=True)

            self.browser_context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=config.USER_AGENT,
            )

            # 尝试加载已保存的cookies
            cookies_file = os.path.join(user_data_dir, "cookies.json")
            saved_cookies = self._load_cookies(cookies_file)
            if saved_cookies:
                self.browser_context.add_cookies(saved_cookies)

            # 创建页面
            self.context_page = self.browser_context.new_page()
            self.context_page.goto("https://www.bilibili.com")
            self.context_page.wait_for_timeout(3000)

            # 创建客户端
            initial_cookies = self.browser_context.cookies()
            cookie_str, cookie_dict = self._convert_cookies(initial_cookies)

            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
                "cache-control": "no-cache",
                "Referer": "https://www.bilibili.com/",
                "pragma": "no-cache",
                "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": config.USER_AGENT,
                "Cookie": cookie_str,
            }

            self.bili_client = BilibiliClient(
                playwright_page=self.context_page,
                headers=headers
            )

            # 检查登录状态，如果未登录则执行登录
            if not self.bili_client.pong():
                logger_info("检测到B站未登录，开始执行登录流程...")
                login_obj = BilibiliLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                login_obj.begin()

                # 更新客户端的cookies
                updated_cookies = self.browser_context.cookies()
                updated_cookie_str, _ = self._convert_cookies(updated_cookies)
                self.bili_client.update_cookies({"Cookie": updated_cookie_str})

                # 保存cookies到文件
                self._save_cookies(cookies_file)
            else:
                logger_info("检测到B站已登录状态")

            # ========== 任务调度 ==========

            if task == "video" or task == "all":
                # video 模式: 仅搜索并保存视频详情，不爬评论
                # all 模式: 搜索视频同时爬评论
                if config.CRAWLER_TYPE == "search":
                    self.search(config, fetch_comments=(task == "all"))
                elif config.CRAWLER_TYPE == "detail":
                    self.get_specified_videos(config)
                elif config.CRAWLER_TYPE == "uploader":
                    self.crawl_uploader_videos(config, fetch_comments=(task == "all"))

            if task == "comment":
                # comment 模式: 读取今日已存视频列表，补充爬取评论和弹幕
                self.crawl_daily_comments(config)

            logger_info("B站爬虫执行完成")


    def _convert_cookies(self, cookies):
        """转换cookies格式"""
        cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        return cookie_str, cookie_dict

    def _save_cookies(self, cookies_file: str):
        """保存cookies到文件"""
        try:
            cookies = self.browser_context.cookies()
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger_info(f"B站Cookies已保存到 {cookies_file}")
        except Exception as e:
            logger_error(f"B站保存Cookies失败: {e}")

    def _load_cookies(self, cookies_file: str):
        """从文件加载cookies"""
        try:
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                logger_info(f"从 {cookies_file} 加载B站Cookies")
                return cookies
        except Exception as e:
            logger_error(f"B站加载Cookies失败: {e}")
        return []

    def search(self, config, fetch_comments=True):
        """
        搜索模式：根据关键词搜索视频
        :param fetch_comments: 是否同时爬取评论和弹幕
                               video 模式下为 False，all 模式下为 True
        """
        logger_info(f"开始B站搜索模式，关键词: {config.KEYWORDS}")
        if not fetch_comments:
            logger_info("当前为 video 模式，仅爬取视频详情，跳过评论和弹幕")

        bili_limit_count = 20
        if config.CRAWLER_MAX_VIDEOS_COUNT < bili_limit_count:
            config.CRAWLER_MAX_VIDEOS_COUNT = bili_limit_count

        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            logger_info(f"正在搜索B站关键词: {keyword}")
            page = 1
            total_videos = 0

            while total_videos < config.CRAWLER_MAX_VIDEOS_COUNT:
                try:
                    search_res = self.bili_client.search_videos(
                        keyword=keyword,
                        page=page,
                        page_size=min(20, config.CRAWLER_MAX_VIDEOS_COUNT - total_videos)
                    )

                    if not search_res or "result" not in search_res:
                        logger_info("B站搜索结果为空或格式异常")
                        break

                    videos = []
                    for item in search_res.get("result", []):
                        if item.get("typename") == "视频" or item.get("type") == "video":
                            videos.append(item)

                    if not videos:
                        logger_info("当前页没有视频结果")
                        break

                    for video_info in videos:
                        if total_videos >= config.CRAWLER_MAX_VIDEOS_COUNT:
                            break

                        bvid = video_info.get("bvid")
                        if not bvid:
                            continue

                        # 运行时去重：检查本次运行中是否已处理过此视频
                        if bvid in self.crawled_bvids_in_session:
                            logger_info(f"本次运行中已处理过视频 {bvid}，跳过")
                            continue

                        video_detail = self._get_video_detail(bvid)
                        if video_detail:
                            self._save_video_data(video_detail)

                            # 仅在 all 模式下爬取评论和弹幕
                            if fetch_comments:
                                if config.ENABLE_GET_COMMENTS:
                                    self._get_video_comments(video_detail)
                                if config.ENABLE_GET_DANMAKU:
                                    self._get_video_danmaku(video_detail)

                            # 标记为已处理
                            self.crawled_bvids_in_session.add(bvid)
                            total_videos += 1
                            logger_info(f"B站已处理第 {total_videos} 个视频")
                            
                            # 视频间随机延迟（防风控）
                            if total_videos < config.CRAWLER_MAX_VIDEOS_COUNT:
                                video_sleep = random.uniform(
                                    getattr(config, 'VIDEO_PROCESS_SLEEP_MIN', 2.0),
                                    getattr(config, 'VIDEO_PROCESS_SLEEP_MAX', 5.0)
                                )
                                logger_info(f"等待 {video_sleep:.2f} 秒后处理下一个视频...")
                                time.sleep(video_sleep)

                    page += 1
                    time.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                except Exception as e:
                    logger_error(f"B站搜索关键词 {keyword} 出错: {e}")
                    import traceback
                    traceback.print_exc()
                    break

    def crawl_uploader_videos(self, config, fetch_comments=True):
        """
        UP主模式：根据UP主MID爬取其投稿视频
        :param fetch_comments: 是否同时爬取评论和弹幕
        """
        logger_info(f"开始B站UP主模式，UP主MID: {config.UPLOADER_MIDS}")
        if not fetch_comments:
            logger_info("当前为 video 模式，仅爬取视频详情，跳过评论和弹幕")

        if not config.UPLOADER_MIDS:
            logger_error("未配置UP主MID，请在config.py中设置UPLOADER_MIDS")
            return

        for mid in config.UPLOADER_MIDS.split(","):
            mid = mid.strip()
            if not mid:
                continue

            logger_info(f"正在爬取UP主 MID={mid} 的视频")
            page = 1
            total_videos = 0

            while total_videos < config.CRAWLER_MAX_VIDEOS_COUNT:
                try:
                    # 获取UP主视频列表
                    result = self.bili_client.get_user_videos(
                        mid=mid,
                        page=page,
                        page_size=min(30, config.CRAWLER_MAX_VIDEOS_COUNT - total_videos),
                        order=getattr(config, "UPLOADER_ORDER", "pubdate")
                    )

                    if not result or "list" not in result:
                        logger_info(f"UP主 {mid} 的视频列表为空或格式异常")
                        break

                    # 获取视频列表
                    vlist = result.get("list", {}).get("vlist", [])
                    if not vlist:
                        logger_info(f"UP主 {mid} 第 {page} 页没有视频")
                        break

                    logger_info(f"获取到UP主 {mid} 第 {page} 页 {len(vlist)} 个视频")

                    for video_info in vlist:
                        if total_videos >= config.CRAWLER_MAX_VIDEOS_COUNT:
                            break

                        bvid = video_info.get("bvid")
                        if not bvid:
                            continue

                        # 运行时去重：检查本次运行中是否已处理过此视频
                        if bvid in self.crawled_bvids_in_session:
                            logger_info(f"本次运行中已处理过视频 {bvid}，跳过")
                            continue

                        # 获取视频详情
                        video_detail = self._get_video_detail(bvid)
                        if video_detail:
                            self._save_video_data(video_detail)

                            # 仅在 all 模式下爬取评论和弹幕
                            if fetch_comments:
                                if config.ENABLE_GET_COMMENTS:
                                    self._get_video_comments(video_detail)
                                if config.ENABLE_GET_DANMAKU:
                                    self._get_video_danmaku(video_detail)

                            # 标记为已处理
                            self.crawled_bvids_in_session.add(bvid)
                            total_videos += 1
                            logger_info(f"UP主 {mid} 已处理第 {total_videos} 个视频")
                            
                            # 视频间随机延迟（防风控）
                            if total_videos < config.CRAWLER_MAX_VIDEOS_COUNT:
                                video_sleep = random.uniform(
                                    getattr(config, 'VIDEO_PROCESS_SLEEP_MIN', 2.0),
                                    getattr(config, 'VIDEO_PROCESS_SLEEP_MAX', 5.0)
                                )
                                logger_info(f"等待 {video_sleep:.2f} 秒后处理下一个视频...")
                                time.sleep(video_sleep)

                    page += 1
                    time.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                except Exception as e:
                    logger_error(f"爬取UP主 {mid} 视频出错: {e}")
                    import traceback
                    traceback.print_exc()
                    break

            logger_info(f"UP主 {mid} 爬取完成，共处理 {total_videos} 个视频")

    def crawl_daily_comments(self, config):

        """
        每日评论/弹幕任务:
        读取今日已存的视频列表，逐个爬取评论和弹幕
        """
        logger_info("=" * 50)
        logger_info("开始执行每日评论/弹幕抓取任务")
        logger_info(f"数据目录: {self.storage.data_dir}")
        logger_info("=" * 50)

        bvids = self.storage.get_today_video_bvids()

        if not bvids:
            logger_info("今日暂无视频数据，请确认 video 任务已执行过")
            return

        logger_info(f"今日共发现 {len(bvids)} 个视频待处理")

        for i, bvid in enumerate(bvids):
            logger_info(f"正在处理第 {i + 1}/{len(bvids)} 个视频: {bvid}")

            try:
                video_detail = self._get_video_detail(bvid)

                if video_detail:
                    if config.ENABLE_GET_COMMENTS:
                        self._get_video_comments(video_detail)
                    if config.ENABLE_GET_DANMAKU:
                        self._get_video_danmaku(video_detail)
                else:
                    logger_error(f"无法获取视频 {bvid} 的详情，跳过")

                # 视频间随机延迟（防风控）
                if i < len(bvids) - 1:
                    video_sleep = random.uniform(
                        getattr(config, 'VIDEO_PROCESS_SLEEP_MIN', 2.0),
                        getattr(config, 'VIDEO_PROCESS_SLEEP_MAX', 5.0)
                    )
                    logger_info(f"等待 {video_sleep:.2f} 秒后处理下一个视频...")
                    time.sleep(video_sleep)

            except Exception as e:
                logger_error(f"处理视频 {bvid} 评论/弹幕失败: {e}")

        logger_info("每日评论/弹幕抓取任务完成!")

    def _get_video_detail(self, bvid: str) -> Dict:
        """获取视频详细信息"""
        try:
            detail = self.bili_client.get_video_detail(bvid)
            if detail:
                detail["bvid"] = bvid
            
            # 随机延迟，模拟人工浏览
            import config
            sleep_time = random.uniform(
                getattr(config, 'VIDEO_DETAIL_SLEEP_MIN', 0.5),
                getattr(config, 'VIDEO_DETAIL_SLEEP_MAX', 2.0)
            )
            logger_info(f"视频详情请求完成，延迟 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)
            
            return detail
        except Exception as e:
            logger_error(f"获取B站视频详情失败 (bvid: {bvid}): {e}")
            return {}

    def _get_video_comments(self, video_detail: Dict):
        """获取视频评论"""
        try:
            oid = str(video_detail.get("aid") or video_detail.get("id"))
            bvid = video_detail.get("bvid", "")

            if not oid:
                return

            import config
            max_count = getattr(config, "CRAWLER_MAX_COMMENTS_COUNT_SINGLEVIDEO", 10)

            comments = self.bili_client.get_video_all_comments(
                oid=oid,
                crawl_interval=1.0,
                callback=None,
                max_count=max_count
            )

            if comments:
                self._save_comment_data(bvid, comments)

        except Exception as e:
            logger_error(f"获取B站视频评论失败: {e}")

    def _get_video_danmaku(self, video_detail: Dict):
        """获取视频弹幕"""
        try:
            cid = str(video_detail.get("cid", ""))
            bvid = video_detail.get("bvid", "")

            if not cid:
                pages = video_detail.get("pages", [])
                if pages:
                    cid = str(pages[0].get("cid", ""))

            if not cid:
                return

            import config
            danmaku_list = self.bili_client.get_video_danmaku(cid)

            if danmaku_list:
                max_count = getattr(config, "CRAWLER_MAX_DANMAKU_COUNT_SINGLEVIDEO", 100)
                self._save_danmaku_data(bvid, danmaku_list[:max_count])

        except Exception as e:
            logger_error(f"获取B站视频弹幕失败: {e}")

    def _save_video_data(self, video_detail: Dict):
        """保存视频数据"""
        try:
            stat = video_detail.get("stat", {})
            owner = video_detail.get("owner", {})

            local_db_item = {
                "created_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "aid": video_detail.get("aid"),
                "bvid": video_detail.get("bvid"),
                "title": video_detail.get("title", ""),
                "desc": video_detail.get("desc", ""),
                "duration": video_detail.get("duration", 0),
                "view": stat.get("view", 0),
                "danmaku": stat.get("danmaku", 0),
                "reply": stat.get("reply", 0),
                "favorite": stat.get("favorite", 0),
                "coin": stat.get("coin", 0),
                "share": stat.get("share", 0),
                "like": stat.get("like", 0),
                "pubdate": video_detail.get("pubdate", 0),
                "ctime": video_detail.get("ctime", 0),
                "owner_mid": owner.get("mid", ""),
                "owner_name": owner.get("name", ""),
                "owner_face": owner.get("face", ""),
                "pic": video_detail.get("pic", ""),
                "stat_view": stat.get("view", 0),
                "stat_danmaku": stat.get("danmaku", 0),
                "stat_reply": stat.get("reply", 0),
                "stat_favorite": stat.get("favorite", 0),
                "stat_coin": stat.get("coin", 0),
                "stat_share": stat.get("share", 0),
                "stat_like": stat.get("like", 0),
                "last_modify_ts": get_current_timestamp(),
            }

            self.storage.save_video(local_db_item)

        except Exception as e:
            logger_error(f"保存B站视频数据失败: {e}")

    def _save_comment_data(self, video_bvid: str, comments: List[Dict]):
        """保存评论数据"""
        try:
            processed_comments = []
            for comment in comments:
                local_db_item = {
                    "rpid": comment.get("rpid", ""),
                    "oid": comment.get("oid", ""),
                    "type": comment.get("type", 0),
                    "mid": comment.get("mid", ""),
                    "uname": comment.get("member", {}).get("uname", "") if "member" in comment else comment.get("uname", ""),
                    "message": comment.get("content", {}).get("message", "") if "content" in comment else "",
                    "like": comment.get("like", 0),
                    "ctime": comment.get("ctime", 0),
                    "reply_count": comment.get("reply_count", 0),
                    "last_modify_ts": get_current_timestamp(),
                }
                processed_comments.append(local_db_item)

            self.storage.save_comment(video_bvid, processed_comments)

        except Exception as e:
            logger_error(f"保存B站评论数据失败: {e}")

    def _save_danmaku_data(self, video_bvid: str, danmaku_list: List[Dict]):
        """保存弹幕数据"""
        try:
            self.storage.save_danmaku(video_bvid, danmaku_list)
        except Exception as e:
            logger_error(f"保存B站弹幕数据失败: {e}")

    def get_specified_videos(self, config):
        """详情模式：获取指定视频"""
        logger_info("B站详情模式暂未实现")
        pass
