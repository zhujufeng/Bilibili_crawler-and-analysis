# -*- coding: utf-8 -*-
"""
B站数据导入脚本 - 简洁版
将JSON数据导入MySQL数据库
"""

import json
import os
import glob
from datetime import datetime
import pymysql


class BilibiliImporter:
    """B站数据导入器"""
    
    def __init__(self, host='localhost', port=3306, user='root', password='', database='bilibili'):
        """初始化数据库连接"""
        self.conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        self.cursor = self.conn.cursor()
        print(f"✓ 连接数据库成功: {database}")
    
    def import_videos(self, json_file):
        """导入视频数据"""
        print(f"\n导入视频数据: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        
        sql = """
        INSERT INTO bilibili_videos (
            bvid, aid, title, `desc`, duration,
            view, danmaku, reply, favorite, coin, share, `like`,
            owner_mid, owner_name, owner_face, pic,
            pubdate, ctime, created_time, last_modify_ts
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """
        
        count = 0
        for v in videos:
            try:
                self.cursor.execute(sql, (
                    v['bvid'], v['aid'], v['title'], v['desc'], v['duration'],
                    v['view'], v['danmaku'], v['reply'], v['favorite'], 
                    v['coin'], v['share'], v['like'],
                    v['owner_mid'], v['owner_name'], v['owner_face'], v['pic'],
                    v['pubdate'], v['ctime'], v['created_time'], v['last_modify_ts']
                ))
                count += 1
            except pymysql.IntegrityError:
                pass  # 重复数据跳过
        
        self.conn.commit()
        print(f"✓ 导入 {count}/{len(videos)} 条视频记录")
    
    def import_comments(self, json_file):
        """导入评论数据"""
        print(f"\n导入评论数据: {json_file}")
        
        # 从文件名提取 bvid (格式: bilibili_comments_BV1A3cczZEf6.json)
        filename = os.path.basename(json_file)
        bvid = filename.replace('bilibili_comments_', '').replace('.json', '')
        
        with open(json_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        sql = """
        INSERT INTO bilibili_comments (
            bvid, rpid, oid, type, mid, uname, message,
            `like`, reply_count, ctime, last_modify_ts
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        count = 0
        for c in comments:
            try:
                self.cursor.execute(sql, (
                    bvid,  # 添加 bvid 参数
                    c['rpid'], c['oid'], c['type'], c['mid'], 
                    c['uname'], c['message'], c['like'], c['reply_count'],
                    c['ctime'], c['last_modify_ts']
                ))
                count += 1
            except pymysql.IntegrityError:
                pass
        
        self.conn.commit()
        print(f"✓ 导入 {count}/{len(comments)} 条评论记录 (bvid={bvid})")
    
    def import_danmaku(self, json_file):
        """导入弹幕数据"""
        print(f"\n导入弹幕数据: {json_file}")
        
        # 从文件名提取 bvid (格式: bilibili_danmaku_BV1A3cczZEf6.json)
        filename = os.path.basename(json_file)
        bvid = filename.replace('bilibili_danmaku_', '').replace('.json', '')
        
        with open(json_file, 'r', encoding='utf-8') as f:
            danmakus = json.load(f)
        
        sql = """
        INSERT INTO bilibili_danmaku (
            bvid, row_id, text, time, mode, size, color,
            timestamp, pool, user_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        count = 0
        for d in danmakus:
            try:
                self.cursor.execute(sql, (
                    bvid,  # 添加 bvid 参数
                    d['row_id'], d['text'], d['time'], d['mode'],
                    d['size'], d['color'], d['timestamp'],
                    d['pool'], d['user_id']
                ))
                count += 1
            except pymysql.IntegrityError:
                pass
        
        self.conn.commit()
        print(f"✓ 导入 {count}/{len(danmakus)} 条弹幕记录 (bvid={bvid})")
    
    def import_directory(self, data_dir):
        """导入整个目录的数据"""
        print(f"\n{'='*60}")
        print(f"导入目录: {data_dir}")
        print(f"{'='*60}")
        
        # 检查目录是否存在
        if not os.path.exists(data_dir):
            print(f"✗ 错误: 目录不存在 {data_dir}")
            return
        
        # 1. 导入视频
        video_file = os.path.join(data_dir, 'bilibili_videos.json')
        if os.path.exists(video_file):
            self.import_videos(video_file)
        else:
            print(f"⚠ 警告: 视频文件不存在 {video_file}")
        
        # 2. 导入评论
        comment_files = glob.glob(os.path.join(data_dir, 'bilibili_comments_*.json'))
        if comment_files:
            for file in comment_files:
                self.import_comments(file)
        else:
            print(f"⚠ 警告: 未找到评论文件")
        
        # 3. 导入弹幕
        danmaku_files = glob.glob(os.path.join(data_dir, 'bilibili_danmaku_*.json'))
        if danmaku_files:
            for file in danmaku_files:
                self.import_danmaku(file)
        else:
            print(f"⚠ 警告: 未找到弹幕文件")
        
        print(f"\n{'='*60}")
        print("✓ 导入完成!")
        print(f"{'='*60}")
    
    def import_today(self, base_dir='data'):
        """导入今天的数据（自动查找今天的目录）"""
        today = datetime.now()
        year = today.strftime('%Y')
        date = today.strftime('%m-%d')
        
        # 构建今天的数据目录路径
        data_dir = os.path.join(base_dir, year, date)
        
        print(f"🔍 查找今天的数据目录: {data_dir}")
        self.import_directory(data_dir)
    
    def import_yesterday(self, base_dir='data'):
        """导入昨天的数据（用于第二天凌晨导入前一天完整数据）"""
        from datetime import timedelta
        
        yesterday = datetime.now() - timedelta(days=1)
        year = yesterday.strftime('%Y')
        date = yesterday.strftime('%m-%d')
        
        # 构建昨天的数据目录路径
        data_dir = os.path.join(base_dir, year, date)
        
        print(f"🔍 查找昨天的数据目录: {data_dir}")
        print(f"📅 昨天日期: {yesterday.strftime('%Y-%m-%d')}")
        self.import_directory(data_dir)
    
    def close(self):
        """关闭数据库连接"""
        self.cursor.close()
        self.conn.close()
        print("\n✓ 数据库连接已关闭")


if __name__ == '__main__':
    import sys
    
    # 配置数据库
    importer = BilibiliImporter(
        host='118.89.165.99',
        port=3306,
        user='root',
        password='071199fY',
        database='data_big'
    )
    
    try:
        # 支持三种模式：
        # 1. 无参数：导入今天的数据（默认）
        # 2. --yesterday：导入昨天的数据（用于定时任务凌晨执行）
        # 3. 指定目录：python data_to_db.py data/2026/02-13
        
        # 获取脚本所在目录的上一级（项目根目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        data_base_dir = os.path.join(project_root, 'data')
        
        if len(sys.argv) > 1:
            if sys.argv[1] == '--yesterday':
                print(f"📅 导入昨天的数据（定时任务模式）")
                importer.import_yesterday(base_dir=data_base_dir)
            else:
                data_dir = sys.argv[1]
                print(f"📂 指定目录模式: {data_dir}")
                importer.import_directory(data_dir)
        else:
            print(f"📅 自动导入今天的数据")
            importer.import_today(base_dir=data_base_dir)
    finally:
        importer.close()
