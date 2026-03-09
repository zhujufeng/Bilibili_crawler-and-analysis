# 防风控优化说明

## 🔍 风控风险分析

### 已优化的风险点

| 风险点 | 优化前 | 优化后 | 风险等级 |
|--------|--------|--------|---------|
| 视频详情请求 | 固定 1 秒 | 随机 0.5-2 秒 | 🟢 低 |
| 视频处理间隔 | **无延迟** | 随机 2-5 秒 | 🟢 低 |
| 评论翻页延迟 | 固定 1-2 秒 | 随机 1-3 秒 | 🟢 低 |
| 搜索翻页延迟 | 固定 5 秒 | 固定 5 秒（可调） | 🟡 中 |

---

## ✅ 优化内容

### 1. 新增配置参数（config.py）

```python
# 请求配置（防风控优化）
CRAWLER_MAX_SLEEP_SEC = 5  # 搜索翻页、UP主翻页间隔
VIDEO_DETAIL_SLEEP_MIN = 0.5  # 视频详情请求最小延迟
VIDEO_DETAIL_SLEEP_MAX = 2.0  # 视频详情请求最大延迟
VIDEO_PROCESS_SLEEP_MIN = 2.0  # 视频处理间隔最小延迟
VIDEO_PROCESS_SLEEP_MAX = 5.0  # 视频处理间隔最大延迟
COMMENT_PAGE_SLEEP_MIN = 1.0  # 评论翻页最小延迟
COMMENT_PAGE_SLEEP_MAX = 3.0  # 评论翻页最大延迟
```

### 2. 优化位置

#### 位置 1: 视频详情请求（bili_crawler.py - _get_video_detail）

**优化前**：
```python
time.sleep(1)  # 固定 1 秒
```

**优化后**：
```python
sleep_time = random.uniform(
    getattr(config, 'VIDEO_DETAIL_SLEEP_MIN', 0.5),
    getattr(config, 'VIDEO_DETAIL_SLEEP_MAX', 2.0)
)
logger_info(f"视频详情请求完成，延迟 {sleep_time:.2f} 秒")
time.sleep(sleep_time)
```

#### 位置 2: 视频处理间隔（bili_crawler.py - search & crawl_uploader_videos）

**优化前**：
```python
# 处理完一个视频后，立即处理下一个（无延迟）
```

**优化后**：
```python
# 视频间随机延迟（防风控）
if total_videos < config.CRAWLER_MAX_VIDEOS_COUNT:
    video_sleep = random.uniform(
        getattr(config, 'VIDEO_PROCESS_SLEEP_MIN', 2.0),
        getattr(config, 'VIDEO_PROCESS_SLEEP_MAX', 5.0)
    )
    logger_info(f"等待 {video_sleep:.2f} 秒后处理下一个视频...")
    time.sleep(video_sleep)
```

#### 位置 3: 评论翻页延迟（client.py - get_video_all_comments）

**优化前**：
```python
time.sleep(crawl_interval + random.uniform(0, 1))  # 1-2 秒
```

**优化后**：
```python
sleep_min = getattr(config, 'COMMENT_PAGE_SLEEP_MIN', 1.0)
sleep_max = getattr(config, 'COMMENT_PAGE_SLEEP_MAX', 3.0)
sleep_time = random.uniform(sleep_min, sleep_max)
print(f"评论翻页延迟 {sleep_time:.2f} 秒...")
time.sleep(sleep_time)
```

#### 位置 4: 每日评论任务（bili_crawler.py - crawl_daily_comments）

**优化前**：
```python
time.sleep(config.CRAWLER_MAX_SLEEP_SEC)  # 固定 5 秒
```

**优化后**：
```python
if i < len(bvids) - 1:
    video_sleep = random.uniform(
        getattr(config, 'VIDEO_PROCESS_SLEEP_MIN', 2.0),
        getattr(config, 'VIDEO_PROCESS_SLEEP_MAX', 5.0)
    )
    logger_info(f"等待 {video_sleep:.2f} 秒后处理下一个视频...")
    time.sleep(video_sleep)
```

---

## 🎯 推荐配置

### 低速模式（最安全，适合长期定时任务）

```python
CRAWLER_MAX_SLEEP_SEC = 8  # 搜索翻页 8 秒
VIDEO_DETAIL_SLEEP_MIN = 1.0
VIDEO_DETAIL_SLEEP_MAX = 3.0
VIDEO_PROCESS_SLEEP_MIN = 3.0
VIDEO_PROCESS_SLEEP_MAX = 8.0
COMMENT_PAGE_SLEEP_MIN = 2.0
COMMENT_PAGE_SLEEP_MAX = 4.0
```

### 中速模式（默认，平衡效率和安全）

```python
CRAWLER_MAX_SLEEP_SEC = 5  # 搜索翻页 5 秒
VIDEO_DETAIL_SLEEP_MIN = 0.5
VIDEO_DETAIL_SLEEP_MAX = 2.0
VIDEO_PROCESS_SLEEP_MIN = 2.0
VIDEO_PROCESS_SLEEP_MAX = 5.0
COMMENT_PAGE_SLEEP_MIN = 1.0
COMMENT_PAGE_SLEEP_MAX = 3.0
```

### 高速模式（快速采集，风险较高）

```python
CRAWLER_MAX_SLEEP_SEC = 3
VIDEO_DETAIL_SLEEP_MIN = 0.3
VIDEO_DETAIL_SLEEP_MAX = 1.0
VIDEO_PROCESS_SLEEP_MIN = 1.0
VIDEO_PROCESS_SLEEP_MAX = 3.0
COMMENT_PAGE_SLEEP_MIN = 0.5
COMMENT_PAGE_SLEEP_MAX = 2.0
```

---

## 📊 性能影响估算

### 爬取 10 个视频的耗时对比

| 模式 | 总耗时估算 | 说明 |
|------|-----------|------|
| **优化前** | ~120 秒 | 视频间无延迟，风险高 |
| **低速模式** | ~240-350 秒 | 最安全，适合定时任务 |
| **中速模式** | ~150-230 秒 | **推荐**，平衡效率和安全 |
| **高速模式** | ~100-150 秒 | 快速采集，有风险 |

---

## 🛡️ 其他防风控措施（已实现）

| 措施 | 状态 | 说明 |
|------|------|------|
| ✅ 真实登录 | 已实现 | 使用二维码或 cookie 登录 |
| ✅ WBI 签名 | 已实现 | 搜索和评论请求带正确签名 |
| ✅ User-Agent | 已实现 | 模拟真实浏览器 |
| ✅ HTTP/2 | 已实现 | 使用 httpx 的 HTTP/2 支持 |
| ✅ Referer | 已实现 | 正确设置 Referer 头 |
| ✅ 随机延迟 | **新增** | 所有请求都有随机延迟 |

---

## ⚠️ 注意事项

1. **定时任务建议使用低速模式**
   - 长期运行，安全性优先
   - 避免频繁触发风控

2. **监控日志**
   ```bash
   tail -f logs/video_$(date +%Y-%m-%d).log
   ```
   如果看到以下日志，说明延迟生效：
   - `视频详情请求完成，延迟 X.XX 秒`
   - `等待 X.XX 秒后处理下一个视频...`
   - `评论翻页延迟 X.XX 秒...`

3. **风控信号**
   - API 返回 `-412` 或 `-352` 错误码
   - 频繁出现 "请求过于频繁" 提示
   - Cookie 失效频率增加

   **解决方案**：
   - 增大延迟时间（调整 config.py 参数）
   - 减少 `CRAWLER_MAX_VIDEOS_COUNT`
   - 更换 IP（如果使用代理）

4. **合理设置爬取数量**
   - 每小时任务：建议 `CRAWLER_MAX_VIDEOS_COUNT = 10-20`
   - 每天任务：建议 `CRAWLER_MAX_COMMENTS_COUNT_SINGLEVIDEO = 100-200`

---

## 🔧 调试建议

### 测试延迟是否生效

```bash
# 运行 video 任务，观察日志
python main.py --task video

# 预期日志输出：
# [INFO] 视频详情请求完成，延迟 1.23 秒
# [INFO] 等待 3.45 秒后处理下一个视频...
```

### 如果遇到风控

1. **立即停止爬虫**
2. **调整配置**：增大延迟参数
3. **等待冷却**：30 分钟后再试
4. **检查 Cookie**：确保登录状态正常

---

## 📝 更新日志

### v1.2.0 (2026-02-13) - 防风控优化

- ✅ 新增视频处理间隔随机延迟（2-5 秒）
- ✅ 优化视频详情请求延迟（0.5-2 秒随机）
- ✅ 优化评论翻页延迟（1-3 秒随机）
- ✅ 新增可配置的延迟参数
- ✅ 添加详细的日志输出

---

**建议**：使用中速模式（默认配置）运行定时任务，如果长期稳定，可考虑适当提高速度。
