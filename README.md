# B站爬虫 - Bilibili Crawler

一个简洁高效的 B站视频数据爬虫，支持视频信息、评论、弹幕的采集和数据库存储。**已优化防风控机制**。

---

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [防风控优化](#防风控优化)
- [数据库部署](#数据库部署)
- [定时任务配置](#定时任务配置-linux)
- [使用示例](#使用示例)
- [常见问题](#常见问题)

---

## ✨ 功能特性

### 核心功能
- ✅ **关键词搜索爬取**：按关键词搜索并采集视频数据
- ✅ **UP主视频爬取**：支持指定 UP主 MID 批量采集
- ✅ **评论弹幕采集**：完整抓取视频评论和弹幕数据
- ✅ **智能去重**：运行时去重 + 可选增量模式
- ✅ **MySQL 存储**：提供完整的数据库 schema 和导入脚本
- ✅ **分离任务模式**：视频/评论/全量 三种任务模式
- ✅ **防风控优化**：随机延迟 + 模拟人工浏览行为

### 数据采集
- 视频基础信息（标题、描述、时长、封面等）
- 视频统计数据（播放量、点赞、投币、收藏、分享、弹幕数、评论数）
- UP主信息（MID、昵称、头像）
- 评论详情（评论者、内容、点赞数、时间戳）
- 弹幕详情（内容、时间点、样式、发送者哈希）

### 去重机制
- **运行时去重**（默认开启）：单次运行内不重复抓取
- **增量模式**（可选）：跳过文件中已存在的视频（适用于手动运行）
- **数据库去重**：导入时自动跳过重复数据

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Ubuntu 20.04+ / Windows 10+
- 内存 ≥ 2GB（Playwright 浏览器需要）

### 2. 安装依赖

```bash
# 克隆或下载项目
cd bilibili_simple_crawler

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux
# venv\Scripts\activate  # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（必需）
playwright install chromium
playwright install-deps chromium  # Linux 需要 sudo
```

### 3. 配置修改

编辑 `config.py`：

```python
# 搜索关键词（搜索模式）
KEYWORDS = ["影视飓风"]

# UP主 MID（UP主模式，可多个，逗号分隔）
UPLOADER_MIDS = "436482484"

# 爬虫类型：search（关键词搜索）或 uploader（UP主）
CRAWLER_TYPE = "search"

# 登录方式（推荐 qrcode）
LOGIN_TYPE = "qrcode"  # qrcode/cookie

# 无头模式（Linux 服务器必须为 True）
HEADLESS = True
```

### 4. 运行测试

```bash
# 测试完整流程（视频 + 评论 + 弹幕）
python main.py --task all

# 仅爬取视频信息
python main.py --task video

# 仅爬取评论和弹幕
python main.py --task comment
```

---

## ⚙️ 配置说明

### config.py 主要参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `CRAWLER_TYPE` | 爬虫类型 | `"search"` (关键词) / `"uploader"` (UP主) |
| `KEYWORDS` | 搜索关键词列表 | `["影视飓风"]` |
| `UPLOADER_MIDS` | UP主 MID（多个用逗号分隔） | `"436482484"` |
| `UPLOADER_ORDER` | UP主视频排序 | `"pubdate"` (发布时间) / `"click"` (播放量) / `"stow"` (收藏) |
| `CRAWLER_MAX_VIDEOS_COUNT` | 最大爬取视频数量 | `10` |
| `ENABLE_INCREMENTAL_MODE` | 增量模式 | `False` (定时任务关闭) |
| `LOGIN_TYPE` | 登录方式 | `"qrcode"` / `"cookie"` |
| `HEADLESS` | 无头模式 | `True` (服务器) / `False` (本地调试) |

### 防风控配置参数（重要）

| 参数 | 说明 | 默认值 | 推荐值（定时任务） |
|------|------|--------|-------------------|
| `CRAWLER_MAX_SLEEP_SEC` | 搜索翻页延迟 | `5` 秒 | `5-8` 秒 |
| `VIDEO_DETAIL_SLEEP_MIN` | 视频详情最小延迟 | `0.5` 秒 | `1.0` 秒 |
| `VIDEO_DETAIL_SLEEP_MAX` | 视频详情最大延迟 | `2.0` 秒 | `3.0` 秒 |
| `VIDEO_PROCESS_SLEEP_MIN` | 视频间隔最小延迟 | `2.0` 秒 | `3.0` 秒 |
| `VIDEO_PROCESS_SLEEP_MAX` | 视频间隔最大延迟 | `5.0` 秒 | `8.0` 秒 |
| `COMMENT_PAGE_SLEEP_MIN` | 评论翻页最小延迟 | `1.0` 秒 | `2.0` 秒 |
| `COMMENT_PAGE_SLEEP_MAX` | 评论翻页最大延迟 | `3.0` 秒 | `4.0` 秒 |

### 去重逻辑说明

**运行时去重**（默认开启，无需配置）：
- 单次运行内，已处理的视频不重复采集
- 适用于定时任务（每天多次运行）

**增量模式**（可选，`ENABLE_INCREMENTAL_MODE = True`）：
- 跳过文件中已存在的视频
- 适用于手动补充爬取历史数据
- **定时任务请关闭**（否则每天第2次运行会跳过所有视频）

---

## 🛡️ 防风控优化

### 已实现的防风控机制

| 机制 | 实现方式 | 效果 |
|------|---------|------|
| **随机延迟** | 所有请求间隔随机化 | 🟢 模拟人工浏览 |
| **真实登录** | 二维码/Cookie 登录 | 🟢 避免游客限制 |
| **WBI 签名** | 搜索和评论带签名 | 🟢 通过官方验证 |
| **User-Agent** | 真实浏览器 UA | 🟢 模拟浏览器 |
| **HTTP/2** | 使用 httpx HTTP/2 | 🟢 现代浏览器特征 |

### 延迟策略

| 位置 | 延迟范围 | 说明 |
|------|---------|------|
| 视频详情请求 | 0.5-2 秒（随机） | 获取视频详细信息后延迟 |
| 视频处理间隔 | 2-5 秒（随机） | **最重要**，模拟人工浏览视频间隔 |
| 评论翻页 | 1-3 秒（随机） | 获取每页评论后延迟 |
| 搜索翻页 | 5 秒（可调） | 搜索结果翻页延迟 |

### 推荐配置

**定时任务（长期运行）**：
```python
# 低速安全模式
CRAWLER_MAX_SLEEP_SEC = 8
VIDEO_DETAIL_SLEEP_MIN = 1.0
VIDEO_DETAIL_SLEEP_MAX = 3.0
VIDEO_PROCESS_SLEEP_MIN = 3.0
VIDEO_PROCESS_SLEEP_MAX = 8.0
COMMENT_PAGE_SLEEP_MIN = 2.0
COMMENT_PAGE_SLEEP_MAX = 4.0
CRAWLER_MAX_VIDEOS_COUNT = 10  # 每小时不超过 10 个
```

**手动采集（一次性）**：
```python
# 中速平衡模式（默认）
CRAWLER_MAX_SLEEP_SEC = 5
VIDEO_DETAIL_SLEEP_MIN = 0.5
VIDEO_DETAIL_SLEEP_MAX = 2.0
VIDEO_PROCESS_SLEEP_MIN = 2.0
VIDEO_PROCESS_SLEEP_MAX = 5.0
COMMENT_PAGE_SLEEP_MIN = 1.0
COMMENT_PAGE_SLEEP_MAX = 3.0
```

### 风控信号

如果遇到以下情况，说明可能触发风控：

| 信号 | 说明 | 解决方案 |
|------|------|---------|
| API 返回 `-412` | 请求被拦截 | 增大延迟，减少爬取量 |
| API 返回 `-352` | 风控验证 | 停止爬取 30 分钟，检查登录状态 |
| "请求过于频繁" | 触发限流 | 增大 `VIDEO_PROCESS_SLEEP_MAX` 到 10 秒 |
| Cookie 频繁失效 | 账号异常 | 更换账号或使用代理 |

**详细说明**：查看 `ANTI_RISK_OPTIMIZATION.md`

---

## 💾 数据库部署

### 1. 创建数据库

```bash
mysql -u root -p

CREATE DATABASE bilibili DEFAULT CHARSET=utf8mb4;
USE bilibili;
SOURCE database/schema.sql;
```

### 2. 配置导入脚本

编辑 `database/import.py`：

```python
importer = BilibiliImporter(
    host='localhost',      # 数据库地址
    port=3306,
    user='root',
    password='your_password',  # 修改密码
    database='bilibili'
)
```

### 3. 导入数据

```bash
# 自动导入今天的数据
python database/data_to_db.py

# 导入指定日期的数据
python database/data_to_db.py data/2026/02-13
```

### 4. 表结构说明

3 张表通过 `bvid` 关联：

| 表名 | 说明 | 关联字段 |
|------|------|---------|
| `bilibili_videos` | 视频数据（主表） | `bvid` |
| `bilibili_comments` | 评论数据 | `bvid` → videos |
| `bilibili_danmaku` | 弹幕数据 | `bvid` → videos |

**常用查询**（详见 `database/README.md`）：

```sql
-- 综合分析：视频 + 评论 + 弹幕
SELECT 
  v.bvid, v.title, v.view, v.like,
  COUNT(DISTINCT c.rpid) AS comment_count,
  COUNT(DISTINCT d.row_id) AS danmaku_count
FROM bilibili_videos v
LEFT JOIN bilibili_comments c ON v.bvid = c.bvid
LEFT JOIN bilibili_danmaku d ON v.bvid = d.bvid
WHERE v.bvid = 'BV1A3cczZEf6'
GROUP BY v.bvid, v.title, v.view, v.like;
```

---

## ⏰ 定时任务配置 (Linux)

### 方式一：自动配置（推荐）

运行自动配置脚本：

```bash
chmod +x setup_crontab.sh
./setup_crontab.sh
```

脚本会自动：
1. 创建日志目录 `logs/`
2. 更新脚本路径
3. 添加执行权限
4. 配置 crontab 定时任务

### 方式二：手动配置

1. **赋予脚本执行权限**：

```bash
chmod +x run_video_task.sh
chmod +x run_comment_task.sh
chmod +x run_import_task.sh
```

2. **修改脚本路径**：

编辑 `run_*.sh` 文件，将 `/path/to/bilibili_simple_crawler` 替换为实际路径，例如：

```bash
cd /home/ubuntu/bilibili_simple_crawler || exit
```

3. **配置 crontab**：

```bash
crontab -e
```

添加以下内容：

```bash
# B站爬虫定时任务

# 视频详情 - 每小时的50分执行
50 * * * * /home/ubuntu/bilibili_simple_crawler/run_video_task.sh

# 评论弹幕 - 每天 23:20 执行
20 23 * * * /home/ubuntu/bilibili_simple_crawler/run_comment_task.sh

# 数据导入 - 每天 23:59 执行
59 23 * * * /home/ubuntu/bilibili_simple_crawler/run_import_task.sh
```

### 定时任务说明

| 任务 | 执行时间 | 说明 |
|------|---------|------|
| 视频详情 | 每小时 XX:50 | 采集视频基础信息和统计数据 |
| 评论弹幕 | 每天 23:20 | 读取当天视频列表，采集评论和弹幕 |
| 数据导入 | 每天 23:59 | 将今天的 JSON 数据导入 MySQL |

### 查看日志

```bash
# 查看今天的视频任务日志
tail -f logs/video_$(date +%Y-%m-%d).log

# 查看今天的评论任务日志
tail -f logs/comment_$(date +%Y-%m-%d).log

# 查看今天的导入日志
tail -f logs/import_$(date +%Y-%m-%d).log
```

---

## 📖 使用示例

### 示例 1: 关键词搜索爬取

```python
# config.py
CRAWLER_TYPE = "search"
KEYWORDS = ["影视飓风", "相机"]
MAX_PAGES = 3
```

```bash
python main.py --task video
```

### 示例 2: UP主视频爬取

```python
# config.py
CRAWLER_TYPE = "uploader"
UPLOADER_MIDS = "436482484,987654321"  # 多个 MID 逗号分隔
UPLOADER_ORDER = "pubdate"  # 按发布时间排序
```

```bash
python main.py --task video
```

### 示例 3: 评论弹幕采集

```bash
# 先运行视频任务
python main.py --task video

# 再运行评论任务
python main.py --task comment
```

### 示例 4: 数据导入数据库

```bash
# 导入今天的数据
python database/data_to_db.py

# 导入历史数据
python database/data_to_db.py data/2026/02-12
```

---

## 📂 项目结构

```
bilibili_simple_crawler/
├── main.py                    # 主程序入口
├── config.py                  # 配置文件
├── requirements.txt           # Python 依赖
├── README.md                  # 本文档
│
├── bilibili_crawler/          # 爬虫核心模块
│   ├── bili_crawler.py        # 爬虫主逻辑
│   ├── client.py              # API 客户端
│   ├── storage.py             # 数据存储
│   └── ...
│
├── database/                  # 数据库相关
│   ├── schema.sql             # 建表语句
│   ├── import.py              # 数据导入脚本
│   └── README.md              # 数据库使用说明
│
├── data/                      # 数据存储目录（自动生成）
│   └── YYYY/
│       └── MM-DD/
│           ├── bilibili_videos.json
│           ├── bilibili_comments_BVxxx.json
│           └── bilibili_danmaku_BVxxx.json
│
├── logs/                      # 日志目录（自动生成）
│   ├── video_YYYY-MM-DD.log
│   ├── comment_YYYY-MM-DD.log
│   └── import_YYYY-MM-DD.log
│
├── run_video_task.sh          # 视频任务脚本
├── run_comment_task.sh        # 评论任务脚本
├── run_import_task.sh         # 导入任务脚本
└── setup_crontab.sh           # 自动配置 crontab 脚本
```

---

## ❓ 常见问题

### Q1: 浏览器启动失败

**报错**: `browser.launch: Executable doesn't exist`

**解决**:
```bash
playwright install chromium
sudo playwright install-deps chromium  # Linux 需要 sudo
```

### Q2: Cookie 过期导致登录失败

**解决**:
1. 使用二维码登录（推荐）：`LOGIN_TYPE = "qrcode"`
2. 或在本地登录后，将 `browser_data/bilibili_user_data_dir/cookies.json` 上传到服务器

### Q3: comment 任务提示"暂无视频数据"

**原因**: 当天还没有执行过 video 任务

**解决**: 确保 comment 任务执行时间晚于 video 任务

### Q4: 定时任务不执行

**排查**:
1. 检查 cron 服务：`systemctl status cron`
2. 查看 cron 日志：`grep CRON /var/log/syslog | tail -20`
3. 确认脚本路径正确（绝对路径）
4. 确认脚本有执行权限：`chmod +x run_*.sh`

### Q5: 数据导入空跑，什么都没干

**原因**: `import.py` 中路径配置错误或数据文件不存在

**解决**:
```bash
# 检查数据目录是否存在
ls -la data/$(date +%Y/%m-%d)/

# 手动指定目录导入
python database/data_to_db.py data/2026/02-13

# 确认脚本中的 base_dir 路径正确
```

### Q6: 增量模式导致后续运行跳过所有视频

**原因**: `ENABLE_INCREMENTAL_MODE = True` 导致定时任务每天第2次运行跳过所有已存在视频

**解决**: 定时任务必须设置 `ENABLE_INCREMENTAL_MODE = False`

---

## 📝 更新日志

### v1.1.1 (2026-02-13)
- ✅ 修复去重逻辑（运行时去重 + 可选增量模式）
- ✅ 数据库 schema 添加 `bvid` 关联字段
- ✅ 导入脚本支持自动查找今天的数据
- ✅ 新增定时任务自动配置脚本
- ✅ 整理项目结构，统一文档

### v1.1.0 (2026-02-12)
- ✅ 新增 UP主爬取功能
- ✅ 支持任务模式分离（video/comment/all）
- ✅ 新增 MySQL 数据库支持

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系方式

如有问题，请提交 Issue 或联系开发者。
