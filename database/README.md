# B站数据库使用说明

## 📦 快速开始

### 1. 创建数据库

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE bilibili DEFAULT CHARSET=utf8mb4;

# 执行建表脚本
USE bilibili;
SOURCE schema.sql;
```

### 2. 导入数据

```bash
# 安装依赖
pip install pymysql

# 修改 data_to_db.py 中的数据库密码
# password='your_password'

# 执行导入
python data_to_db.py
```

---

## 📊 表结构

### 3张表通过 bvid 关联

| 表名 | 对应文件 | 说明 | 关联字段 |
|------|---------|------|---------|
| bilibili_videos | bilibili_videos.json | 视频数据（主表） | **bvid** |
| bilibili_comments | bilibili_comments_{bvid}.json | 评论数据 | **bvid** → videos |
| bilibili_danmaku | bilibili_danmaku_{bvid}.json | 弹幕数据 | **bvid** → videos |

**表关系说明**：
- `bilibili_videos` 是主表，存储视频基础信息
- `bilibili_comments` 和 `bilibili_danmaku` 通过 `bvid` 字段关联到视频表
- 可以通过 `bvid` 进行 JOIN 查询，分析视频、评论、弹幕的综合数据

---

## 🔍 常用查询

### 1. 查看最新视频
```sql
SELECT bvid, title, view, like, created_time 
FROM bilibili_videos 
ORDER BY created_time DESC 
LIMIT 10;
```

### 2. 播放量增长趋势
```sql
SELECT created_time, view, like, coin 
FROM bilibili_videos 
WHERE bvid = 'BV1A3cczZEf6' 
ORDER BY created_time;
```

### 3. 热门评论（通过 bvid 关联）
```sql
SELECT c.uname, c.message, c.like, FROM_UNIXTIME(c.ctime) AS time
FROM bilibili_comments c
WHERE c.bvid = 'BV1A3cczZEf6' 
ORDER BY c.like DESC 
LIMIT 20;
```

### 4. 高能时刻（弹幕密集时间段，通过 bvid 关联）
```sql
SELECT 
    FLOOR(d.time / 10) * 10 AS time_segment, 
    COUNT(*) AS count 
FROM bilibili_danmaku d
WHERE d.bvid = 'BV1A3cczZEf6'
GROUP BY time_segment 
ORDER BY count DESC 
LIMIT 10;
```

### 5. 综合分析（JOIN 查询：视频 + 评论 + 弹幕）
```sql
SELECT 
  v.bvid,
  v.title,
  v.view,
  v.like,
  COUNT(DISTINCT c.rpid) AS comment_count,
  COUNT(DISTINCT d.row_id) AS danmaku_count
FROM bilibili_videos v
LEFT JOIN bilibili_comments c ON v.bvid = c.bvid
LEFT JOIN bilibili_danmaku d ON v.bvid = d.bvid
WHERE v.bvid = 'BV1A3cczZEf6'
GROUP BY v.bvid, v.title, v.view, v.like;
```

---

## 📈 数据分析场景

### 场景1: UP主视频表现（影视飓风）
```sql
SELECT 
    v.owner_name,
    COUNT(DISTINCT v.bvid) AS video_count,
    SUM(v.view) AS total_view,
    SUM(v.like) AS total_like,
    AVG(v.view) AS avg_view
FROM bilibili_videos v
WHERE v.owner_mid = 436482484
GROUP BY v.owner_name;
```

### 场景2: 互动率分析
```sql
SELECT 
    bvid, title, view,
    (like + coin + favorite + share) AS engagement,
    ROUND((like + coin + favorite + share) / view * 100, 2) AS engagement_rate
FROM bilibili_videos
WHERE view > 0
ORDER BY engagement_rate DESC
LIMIT 10;
```

### 场景3: 评论活跃时间分布
```sql
SELECT 
    HOUR(FROM_UNIXTIME(ctime)) AS hour,
    COUNT(*) AS comment_count
FROM bilibili_comments
GROUP BY hour
ORDER BY hour;
```

### 场景4: 视频热度综合排名（结合评论和弹幕数据）
```sql
SELECT 
    v.bvid,
    v.title,
    v.view,
    v.like,
    COUNT(DISTINCT c.rpid) AS comment_count,
    COUNT(DISTINCT d.row_id) AS danmaku_count,
    (v.like + v.coin + v.favorite) / v.view * 100 AS engagement_rate
FROM bilibili_videos v
LEFT JOIN bilibili_comments c ON v.bvid = c.bvid
LEFT JOIN bilibili_danmaku d ON v.bvid = d.bvid
WHERE v.view > 1000
GROUP BY v.bvid, v.title, v.view, v.like, v.coin, v.favorite
ORDER BY engagement_rate DESC
LIMIT 20;
```

---

## ⚙️ 数据库配置

```python
# data_to_db.py
importer = BilibiliImporter(
    host='localhost',      # 数据库地址
    port=3306,             # 端口
    user='root',           # 用户名
    password='your_password',  # 密码
    database='bilibili'    # 数据库名
)

# 导入指定目录
importer.import_directory('data/2026/02-13')
```

---

## 📝 表结构详情

### bilibili_videos (视频表 - 主表)
- **主键**: id (自增)
- **唯一键**: (bvid, created_time) - 支持同一视频多次爬取
- **关联键**: bvid (供评论和弹幕表关联)
- **索引**: owner_mid, view, created_time

### bilibili_comments (评论表)
- **主键**: id (自增)
- **唯一键**: rpid (B站评论ID)
- **关联键**: bvid (关联到 bilibili_videos.bvid)
- **索引**: bvid, oid, mid, ctime, like

### bilibili_danmaku (弹幕表)
- **主键**: id (自增)
- **唯一键**: row_id (B站弹幕ID)
- **关联键**: bvid (关联到 bilibili_videos.bvid)
- **索引**: bvid, time, timestamp

---

## ✅ 完成
