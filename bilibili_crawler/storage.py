# -*- coding: utf-8 -*-
"""
bilibili_crawler/storage.py - B站数据存储功能
数据按日期存储到 data/YYYY/MM-DD/ 目录下
"""
import json
import csv
import os
import datetime
from typing import Dict, List
from .helper import get_current_timestamp, logger_info


class BilibiliDataStorage:
    def __init__(self, save_option: str = "json", base_data_dir: str = "data"):
        self.save_option = save_option

        # 按日期构建存储路径: data/YYYY/MM-DD
        now = datetime.datetime.now()
        self.year_str = now.strftime('%Y')
        self.date_str = now.strftime('%m-%d')

        # 最终数据目录，例如: data/2026/02-12
        self.data_dir = os.path.join(base_data_dir, self.year_str, self.date_str)
        os.makedirs(self.data_dir, exist_ok=True)

    def get_today_video_bvids(self) -> List[str]:
        """
        获取今日已爬取的视频BVID列表（供每日评论任务使用）
        从当天目录下的 bilibili_videos.json 中读取所有 bvid
        """
        video_bvids = []
        if self.save_option == "json":
            file_path = os.path.join(self.data_dir, "bilibili_videos.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        videos = json.load(f)
                        if isinstance(videos, list):
                            for v in videos:
                                bvid = v.get("bvid")
                                if bvid:
                                    video_bvids.append(bvid)
                    except Exception:
                        pass
        elif self.save_option == "csv":
            file_path = os.path.join(self.data_dir, "bilibili_videos.csv")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        bvid = row.get("bvid")
                        if bvid:
                            video_bvids.append(bvid)
        return list(set(video_bvids))  # 去重返回

    def save_video(self, video_data: Dict):
        """保存视频数据"""
        if self.save_option == "json":
            self._save_video_json(video_data)
        elif self.save_option == "csv":
            self._save_video_csv(video_data)

    def save_comment(self, video_bvid: str, comment_data: List[Dict]):
        """保存评论数据"""
        if self.save_option == "json":
            self._save_comment_json(video_bvid, comment_data)
        elif self.save_option == "csv":
            self._save_comment_csv(video_bvid, comment_data)

    def save_danmaku(self, video_bvid: str, danmaku_data: List[Dict]):
        """保存弹幕数据"""
        if self.save_option == "json":
            self._save_danmaku_json(video_bvid, danmaku_data)
        elif self.save_option == "csv":
            self._save_danmaku_csv(video_bvid, danmaku_data)

    def _save_video_json(self, video_data: Dict):
        """以JSON格式保存视频"""
        file_path = os.path.join(self.data_dir, "bilibili_videos.json")
        videos = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    videos = json.load(f)
                except Exception:
                    videos = []
        
        # 增量模式：检查文件中是否已存在（可选功能）
        try:
            import config
            if getattr(config, 'ENABLE_INCREMENTAL_MODE', False):
                new_bvid = video_data.get("bvid")
                if new_bvid:
                    existing_bvids = {v.get("bvid") for v in videos if v.get("bvid")}
                    if new_bvid in existing_bvids:
                        logger_info(f"[增量模式] 视频 {new_bvid} 已存在于文件中，跳过保存")
                        return
        except Exception:
            pass  # 配置不存在时忽略，使用默认行为（不去重）
        
        videos.append(video_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        logger_info(f"B站视频数据已保存到 {file_path}")

    def _save_comment_json(self, video_bvid: str, comment_data: List[Dict]):
        """以JSON格式保存评论"""
        file_path = os.path.join(self.data_dir, f"bilibili_comments_{video_bvid}.json")
        comments = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    comments = json.load(f)
                except Exception:
                    comments = []
        comments.extend(comment_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        logger_info(f"B站评论数据已保存到 {file_path}")

    def _save_danmaku_json(self, video_bvid: str, danmaku_data: List[Dict]):
        """以JSON格式保存弹幕"""
        file_path = os.path.join(self.data_dir, f"bilibili_danmaku_{video_bvid}.json")
        danmakus = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    danmakus = json.load(f)
                except Exception:
                    danmakus = []
        danmakus.extend(danmaku_data)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(danmakus, f, ensure_ascii=False, indent=2)
        logger_info(f"B站弹幕数据已保存到 {file_path}")

    def _save_danmaku_csv(self, video_bvid: str, danmaku_data: List[Dict]):
        """以CSV格式保存弹幕"""
        file_path = os.path.join(self.data_dir, f"bilibili_danmaku_{video_bvid}.csv")
        fieldnames = [
            'time', 'mode', 'size', 'color', 'timestamp', 'pool',
            'user_id', 'row_id', 'text'
        ]
        is_first_write = not os.path.exists(file_path)
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if is_first_write:
                writer.writeheader()
            for dm in danmaku_data:
                writer.writerow(dm)
        logger_info(f"B站弹幕数据已保存到 {file_path}")

    def _save_video_csv(self, video_data: Dict):
        """以CSV格式保存视频"""
        file_path = os.path.join(self.data_dir, "bilibili_videos.csv")
        fieldnames = [
            'aid', 'bvid', 'title', 'desc', 'duration', 'view', 'danmaku',
            'reply', 'favorite', 'coin', 'share', 'like', 'pubdate', 'ctime',
            'owner_mid', 'owner_name', 'owner_face', 'pic', 'stat_view',
            'stat_danmaku', 'stat_reply', 'stat_favorite', 'stat_coin',
            'stat_share', 'stat_like', 'last_modify_ts'
        ]
        
        # 增量模式：检查文件中是否已存在（可选功能）
        try:
            import config
            if getattr(config, 'ENABLE_INCREMENTAL_MODE', False):
                new_bvid = video_data.get("bvid")
                if new_bvid and os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        existing_bvids = {row.get("bvid") for row in reader if row.get("bvid")}
                        if new_bvid in existing_bvids:
                            logger_info(f"[增量模式] 视频 {new_bvid} 已存在于文件中，跳过保存")
                            return
        except Exception:
            pass  # 配置不存在时忽略，使用默认行为（不去重）
        
        is_first_write = not os.path.exists(file_path)
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if is_first_write:
                writer.writeheader()
            writer.writerow(video_data)
        logger_info(f"B站视频数据已保存到 {file_path}")

    def _save_comment_csv(self, video_bvid: str, comment_data: List[Dict]):
        """以CSV格式保存评论"""
        file_path = os.path.join(self.data_dir, f"bilibili_comments_{video_bvid}.csv")
        fieldnames = [
            'rpid', 'oid', 'type', 'mid', 'uname', 'message', 'like',
            'ctime', 'reply_count', 'last_modify_ts'
        ]
        is_first_write = not os.path.exists(file_path)
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if is_first_write:
                writer.writeheader()
            for comment in comment_data:
                writer.writerow(comment)
        logger_info(f"B站评论数据已保存到 {file_path}")
