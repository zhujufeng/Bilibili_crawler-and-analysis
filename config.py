# -*- coding: utf-8 -*-
"""
B站爬虫配置文件
"""

# 基础配置
PLATFORM = "bilibili"  # 平台标识
KEYWORDS = "影视飓风"  # 搜索关键词，以英文逗号分隔
LOGIN_TYPE = "qrcode"  # 登录方式：qrcode | cookie
COOKIES = ""  # Cookie登录方式使用的Cookie值

# 爬取类型配置
CRAWLER_TYPE = "uploader"  # 爬取类型：search(关键词搜索) | detail(指定视频) | uploader(UP主视频)

# UP主配置 (当 CRAWLER_TYPE = "uploader" 时使用)
UPLOADER_MIDS = "946974,1780480185,407054668"  # UP主的MID，多个用英文逗号分隔，例如 "436482484,23215368"
UPLOADER_ORDER = "pubdate"  # UP主视频排序方式：pubdate(发布时间) | click(播放量) | stow(收藏数)

# 浏览器配置
# 本地调试设为 False（显示浏览器窗口）
# 服务器部署必须设为 True（无头模式，服务器没有图形界面）
HEADLESS = True

# 数据保存配置
SAVE_DATA_OPTION = "json"  # 数据保存格式：json | csv
ENABLE_INCREMENTAL_MODE = False  # 增量模式：True=跳过已存在的视频, False=允许重复保存(定时任务推荐)

# 爬取限制配置
CRAWLER_MAX_VIDEOS_COUNT =10  # 最大爬取视频数量
MAX_CONCURRENCY_NUM = 1  # 并发数量

# 评论配置
ENABLE_GET_COMMENTS = True  # 是否获取评论
CRAWLER_MAX_COMMENTS_COUNT_SINGLEVIDEO =200  # 单个视频最大评论数量

# 弹幕配置
ENABLE_GET_DANMAKU = True  # 是否获取弹幕
CRAWLER_MAX_DANMAKU_COUNT_SINGLEVIDEO = 1000  # 单个视频最大弹幕数量

# 请求配置（防风控优化）
CRAWLER_MAX_SLEEP_SEC = 8  # 请求间隔时间（秒） - 搜索翻页、UP主翻页
VIDEO_DETAIL_SLEEP_MIN = 1.0 # 视频详情请求最小延迟（秒）
VIDEO_DETAIL_SLEEP_MAX = 3.0 # 视频详情请求最大延迟（秒）
VIDEO_PROCESS_SLEEP_MIN = 3.0  # 视频处理间隔最小延迟（秒）
VIDEO_PROCESS_SLEEP_MAX = 8.0  # 视频处理间隔最大延迟（秒）
COMMENT_PAGE_SLEEP_MIN = 2.0 # 评论翻页最小延迟（秒）
COMMENT_PAGE_SLEEP_MAX = 4.0 # 评论翻页最大延迟（秒）

# 其他配置
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
