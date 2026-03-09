# -*- coding: utf-8 -*-
"""
Demo 后端 - FastAPI
提供统计 API、可视化页面和 Coze Workflow 代理接口。

启动方式:
    cd demo
    uvicorn app:app --host 0.0.0.0 --port 8080 --reload
"""

import asyncio
import json
import os
from contextlib import contextmanager
from typing import Optional

import httpx
import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import config as cfg

app = FastAPI(title="Bilibili Crawler Demo", version="1.2.0")

LATEST_VIDEO_CTE = """
WITH latest_videos AS (
    SELECT *
    FROM (
        SELECT bvid,
               title,
               `view`,
               `like`,
               coin,
               favorite,
               share,
               danmaku,
               reply,
               owner_name,
               pic,
               pubdate,
               created_time,
               ROW_NUMBER() OVER (
                   PARTITION BY bvid
                   ORDER BY created_time DESC, id DESC
               ) AS rn
        FROM bilibili_videos
    ) ranked
    WHERE rn = 1
)
"""


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _chunk_text(text: str, size: int = 120):
    text = text or ""
    for i in range(0, len(text), size):
        yield text[i : i + size]


def _extract_coze_output(result):
    data = result.get("data", "")
    if isinstance(data, dict):
        for key in ("output", "content", "result", "text"):
            value = data.get(key)
            if value:
                return value
        return json.dumps(data, ensure_ascii=False)
    return data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)


def _format_coze_error(response: httpx.Response) -> str:
    detail = None
    logid = None
    try:
        payload = response.json()
        detail = payload.get("msg") or payload.get("message")
        detail_obj = payload.get("detail") or {}
        if isinstance(detail_obj, dict):
            logid = detail_obj.get("logid")
    except Exception:
        detail = response.text

    if response.status_code == 401:
        base = "Coze 鉴权失败：当前 COZE_API_TOKEN 无效、已过期，或与 COZE_API_BASE_URL 区域不匹配。"
        hint = "请重新生成可用于 Open API 的 Personal Access Token；中国区令牌配合 https://api.coze.cn，国际区令牌配合 https://api.coze.com。"
        if logid:
            hint += f" logid={logid}"
        return f"{base} {hint}"

    detail = detail or response.text or "未知错误"
    if logid:
        detail = f"{detail} (logid={logid})"
    return f"Coze API 错误：HTTP {response.status_code} {detail}"


@contextmanager
def get_db():
    """获取数据库连接（上下文管理器）"""
    conn = pymysql.connect(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
        database=cfg.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()



def query_one(sql: str, args=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()



def query_all(sql: str, args=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()


def execute_write(sql: str, args=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            rows = cur.execute(sql, args)
        conn.commit()
        return rows


def get_today_daily_report():
    return query_one(
        """
        SELECT id, content, created_at, updated_at
        FROM bilibili_daily_report
        WHERE DATE(created_at) = CURDATE()
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """
    )


def save_today_daily_report(content: str):
    execute_write(
        "INSERT INTO bilibili_daily_report (content) VALUES (%s)",
        (content,),
    )


def get_latest_daily_report():
    return query_one(
        """
        SELECT id, content, created_at, updated_at
        FROM bilibili_daily_report
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """
    )


def normalize_markdown_text(markdown_text: str) -> str:
    text = (markdown_text or "").strip()
    if not text:
        return ""

    if text.startswith(chr(34)) and text.endswith(chr(34)):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, str):
                text = parsed
        except Exception:
            pass

    if r"\n" in text or r"\t" in text or r"\r" in text:
        text = (
            text.replace(r"\r\n", chr(10))
            .replace(r"\n", chr(10))
            .replace(r"\t", chr(9))
            .replace(r'\"', '"')
        )

    text = text.replace(chr(13) + chr(10), chr(10)).strip()

    heading_markers = (
        f"{chr(10)}# ",
        f"{chr(10)}## ",
        f"{chr(10)}### ",
        "# ",
        "## ",
        "### ",
    )
    positions = []
    for marker in heading_markers:
        pos = text.find(marker)
        if pos != -1:
            positions.append(pos + (1 if marker.startswith(chr(10)) else 0))

    if positions:
        text = text[min(positions):].lstrip()

    return text


async def stream_markdown_text(markdown_text: str):
    normalized = normalize_markdown_text(markdown_text)
    for chunk in _chunk_text(normalized):
        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)
    yield "data: [DONE]\n\n"


@app.get("/api/overview")
def get_overview():
    try:
        total_records = query_one("SELECT COUNT(*) AS cnt FROM bilibili_videos")["cnt"]
        unique_videos = query_one("SELECT COUNT(DISTINCT bvid) AS cnt FROM bilibili_videos")["cnt"]
        total_comments = query_one("SELECT COUNT(*) AS cnt FROM bilibili_comments")["cnt"]
        total_danmaku = query_one("SELECT COUNT(*) AS cnt FROM bilibili_danmaku")["cnt"]
        active_commenters = query_one("SELECT COUNT(DISTINCT mid) AS cnt FROM bilibili_comments")["cnt"]
        active_danmaku_users = query_one("SELECT COUNT(DISTINCT user_id) AS cnt FROM bilibili_danmaku")["cnt"]
        date_range = query_one(
            "SELECT MIN(created_time) AS start_date, MAX(created_time) AS end_date FROM bilibili_videos"
        )
        return {
            "total_records": total_records,
            "unique_videos": unique_videos,
            "total_comments": total_comments,
            "total_danmaku": total_danmaku,
            "active_commenters": active_commenters,
            "active_danmaku_users": active_danmaku_users,
            "start_date": str(date_range["start_date"]) if date_range and date_range["start_date"] else None,
            "end_date": str(date_range["end_date"]) if date_range and date_range["end_date"] else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {e}")


@app.get("/api/top_videos")
def get_top_videos(limit: int = 10):
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT bvid, title, `view`, `like` AS like_count, coin, favorite, share,
                   danmaku, reply, owner_name, pic, pubdate
            FROM latest_videos
            ORDER BY `view` DESC
            LIMIT %s
            """
        )
        return query_all(sql, (limit,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/view_trend")
def get_view_trend(bvid: Optional[str] = None):
    try:
        if bvid:
            sql = """
                SELECT DATE(created_time) AS date,
                       MAX(`view`) AS view,
                       MAX(`like`) AS likes,
                       MAX(coin) AS coin
                FROM bilibili_videos
                WHERE bvid = %s
                GROUP BY DATE(created_time)
                ORDER BY date
            """
            rows = query_all(sql, (bvid,))
        else:
            sql = """
                WITH daily_latest AS (
                    SELECT DATE(created_time) AS date,
                           bvid,
                           `view`,
                           ROW_NUMBER() OVER (
                               PARTITION BY bvid, DATE(created_time)
                               ORDER BY created_time DESC, id DESC
                           ) AS rn
                    FROM bilibili_videos
                )
                SELECT date,
                       COUNT(*) AS video_count,
                       COALESCE(SUM(`view`), 0) AS total_view
                FROM daily_latest
                WHERE rn = 1
                GROUP BY date
                ORDER BY date
            """
            rows = query_all(sql)

        for row in rows:
            if row.get("date"):
                row["date"] = str(row["date"])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/engagement")
def get_engagement(limit: int = 20):
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT bvid, title, `view`,
                   `like` AS likes, coin, favorite, share,
                   ROUND((`like` + coin + favorite + share) / NULLIF(`view`, 0) * 100, 2) AS engagement_rate,
                   pic, pubdate
            FROM latest_videos
            WHERE `view` > 1000
            ORDER BY engagement_rate DESC, `view` DESC
            LIMIT %s
            """
        )
        return query_all(sql, (limit,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/channel_compare")
def get_channel_compare():
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   COUNT(*) AS video_count,
                   COALESCE(SUM(`view`), 0) AS total_view,
                   ROUND(COALESCE(AVG(`view`), 0), 0) AS avg_view,
                   COALESCE(SUM(`like`), 0) AS total_likes,
                   COALESCE(SUM(reply), 0) AS total_reply,
                   COALESCE(SUM(danmaku), 0) AS total_danmaku,
                   ROUND(
                       COALESCE(AVG((`like` + coin + favorite + share) / NULLIF(`view`, 0) * 100), 0),
                       2
                   ) AS avg_engagement
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY total_view DESC, avg_engagement DESC, video_count DESC
            """
        )
        rows = query_all(sql)
        for row in rows:
            row["avg_engagement"] = float(row.get("avg_engagement") or 0)
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/recent_growth")
def get_recent_growth(days: int = 7):
    days = max(3, min(days, 30))
    try:
        sql = """
            SELECT DATE(created_time) AS date,
                   COALESCE(SUM(GREATEST(view_delta_1h, 0)), 0) AS view_delta,
                   COALESCE(SUM(GREATEST(like_delta_1h, 0)), 0) AS like_delta,
                   COALESCE(SUM(GREATEST(reply_delta_1h, 0)), 0) AS reply_delta
            FROM mart_video_hourly_delta
            WHERE created_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(created_time)
            ORDER BY date
        """
        rows = query_all(sql, (days,))
        for row in rows:
            if row.get("date"):
                row["date"] = str(row["date"])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/dashboard_highlights")
def get_dashboard_highlights():
    try:
        top_channel = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   COUNT(*) AS video_count,
                   COALESCE(SUM(`view`), 0) AS total_view
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY total_view DESC, video_count DESC
            LIMIT 1
            """
        )
        best_publish_hour = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT HOUR(FROM_UNIXTIME(pubdate)) AS pub_hour,
                   COUNT(*) AS video_count,
                   ROUND(COALESCE(AVG(`view`), 0), 0) AS avg_view
            FROM latest_videos
            GROUP BY HOUR(FROM_UNIXTIME(pubdate))
            HAVING COUNT(*) >= 2
            ORDER BY avg_view DESC, video_count DESC, pub_hour ASC
            LIMIT 1
            """
        )
        growth_champion = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT lv.bvid,
                   lv.title,
                   lv.owner_name,
                   m.view_delta_1h,
                   m.like_delta_1h,
                   m.favorite_delta_1h,
                   m.created_time
            FROM mart_video_hourly_delta m
            INNER JOIN latest_videos lv ON lv.bvid = m.bvid
            WHERE m.created_time >= DATE_SUB((SELECT MAX(created_time) FROM mart_video_hourly_delta), INTERVAL 2 HOUR)
            ORDER BY m.created_time DESC, m.view_delta_1h DESC, m.like_delta_1h DESC
            LIMIT 1
            """
        )
        latest_report = get_latest_daily_report()
        return {
            "top_channel": top_channel,
            "best_publish_hour": best_publish_hour,
            "growth_champion": growth_champion,
            "latest_report": {
                "id": latest_report["id"],
                "created_at": str(latest_report["created_at"]),
            }
            if latest_report
            else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/video_matrix")
def get_video_matrix(limit: int = 30):
    limit = max(10, min(limit, 100))
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT bvid,
                   title,
                   owner_name,
                   `view`,
                   `like` AS likes,
                   coin,
                   favorite,
                   share,
                   reply,
                   danmaku,
                   ROUND((`like` + coin + favorite + share) / NULLIF(`view`, 0) * 100, 2) AS engagement_rate,
                   ROUND(reply / NULLIF(`view`, 0) * 10000, 2) AS reply_rate,
                   ROUND(danmaku / NULLIF(`view`, 0) * 10000, 2) AS danmaku_rate,
                   ROUND((coin + favorite) / NULLIF(`view`, 0) * 10000, 2) AS deep_engagement_rate,
                   FROM_UNIXTIME(pubdate) AS pub_time
            FROM latest_videos
            WHERE `view` > 50000
            ORDER BY `view` DESC, engagement_rate DESC
            LIMIT %s
            """
        )
        rows = query_all(sql, (limit,))
        for row in rows:
            row["engagement_rate"] = float(row.get("engagement_rate") or 0)
            row["reply_rate"] = float(row.get("reply_rate") or 0)
            row["danmaku_rate"] = float(row.get("danmaku_rate") or 0)
            row["deep_engagement_rate"] = float(row.get("deep_engagement_rate") or 0)
            if row.get("pub_time"):
                row["pub_time"] = str(row["pub_time"])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/interaction_structure")
def get_interaction_structure():
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   COUNT(*) AS video_count,
                   ROUND(COALESCE(AVG(`like` / NULLIF(`view`, 0) * 10000), 0), 1) AS likes_per_w,
                   ROUND(COALESCE(AVG(coin / NULLIF(`view`, 0) * 10000), 0), 1) AS coins_per_w,
                   ROUND(COALESCE(AVG(favorite / NULLIF(`view`, 0) * 10000), 0), 1) AS favorites_per_w,
                   ROUND(COALESCE(AVG(share / NULLIF(`view`, 0) * 10000), 0), 1) AS shares_per_w,
                   ROUND(COALESCE(AVG(reply / NULLIF(`view`, 0) * 10000), 0), 1) AS replies_per_w,
                   ROUND(COALESCE(AVG(danmaku / NULLIF(`view`, 0) * 10000), 0), 1) AS danmaku_per_w
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY COUNT(*) DESC, owner_name ASC
            """
        )
        rows = query_all(sql)
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/strategy_insights")
def get_strategy_insights():
    try:
        scale_leader = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   COUNT(*) AS video_count,
                   ROUND(COALESCE(AVG(`view`), 0), 0) AS avg_view
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY avg_view DESC, video_count DESC
            LIMIT 1
            """
        )
        discussion_leader = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   ROUND(COALESCE(AVG(reply / NULLIF(`view`, 0) * 10000), 0), 1) AS reply_rate
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY reply_rate DESC
            LIMIT 1
            """
        )
        conversion_leader = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   ROUND(COALESCE(AVG((coin + favorite) / NULLIF(`view`, 0) * 10000), 0), 1) AS deep_rate
            FROM latest_videos
            GROUP BY owner_name
            ORDER BY deep_rate DESC
            LIMIT 1
            """
        )
        best_slot = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   HOUR(FROM_UNIXTIME(pubdate)) AS pub_hour,
                   COUNT(*) AS video_count,
                   ROUND(COALESCE(AVG(`view`), 0), 0) AS avg_view,
                   ROUND(
                       COALESCE(AVG((`like` + coin + favorite + share) / NULLIF(`view`, 0) * 100), 0),
                       2
                   ) AS avg_engagement
            FROM latest_videos
            GROUP BY owner_name, HOUR(FROM_UNIXTIME(pubdate))
            HAVING COUNT(*) >= 2
            ORDER BY avg_view DESC, avg_engagement DESC, video_count DESC
            LIMIT 1
            """
        )
        double_high_sample = query_one(
            LATEST_VIDEO_CTE
            + """
            SELECT owner_name,
                   title,
                   `view`,
                   ROUND((`like` + coin + favorite + share) / NULLIF(`view`, 0) * 100, 2) AS engagement_rate
            FROM latest_videos
            WHERE `view` >= (SELECT AVG(`view`) FROM latest_videos)
            ORDER BY engagement_rate DESC, `view` DESC
            LIMIT 1
            """
        )

        items = []
        if scale_leader:
            items.append(
                {
                    "title": "规模效率领先",
                    "metric": f"{scale_leader['owner_name']} · {int(scale_leader['avg_view'] or 0):,} 平均播放",
                    "detail": f"按最新视频快照计算，该账号单条视频平均播放最高，当前样本量 {int(scale_leader['video_count'] or 0)} 条。",
                }
            )
        if discussion_leader:
            items.append(
                {
                    "title": "讨论密度最高",
                    "metric": f"{discussion_leader['owner_name']} · {float(discussion_leader['reply_rate'] or 0):.1f} 评论/万播放",
                    "detail": "该账号更容易把播放转成评论讨论，适合承接观点型、争议型或解释型内容。",
                }
            )
        if conversion_leader:
            items.append(
                {
                    "title": "深度转化最强",
                    "metric": f"{conversion_leader['owner_name']} · {float(conversion_leader['deep_rate'] or 0):.1f} 收藏投币/万播放",
                    "detail": "投币和收藏密度更高，说明内容更容易形成价值感知和长期留存。",
                }
            )
        if best_slot:
            items.append(
                {
                    "title": "最佳发布时间窗",
                    "metric": f"{best_slot['owner_name']} · {int(best_slot['pub_hour'] or 0):02d}:00 档",
                    "detail": f"该时段样本 {int(best_slot['video_count'] or 0)} 条，平均播放 {int(best_slot['avg_view'] or 0):,}，平均互动率 {float(best_slot['avg_engagement'] or 0):.2f}%。",
                }
            )
        if double_high_sample:
            items.append(
                {
                    "title": "双高样本",
                    "metric": f"{double_high_sample['owner_name']} · {double_high_sample['title']}",
                    "detail": f"在播放量高于整体均值的视频里，这条内容互动率达到 {float(double_high_sample['engagement_rate'] or 0):.2f}%，适合拿来拆选题和表达结构。",
                }
            )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/comment_hour_dist")
def get_comment_hour_dist():
    try:
        sql = """
            SELECT HOUR(FROM_UNIXTIME(ctime)) AS hour,
                   COUNT(*) AS comment_count
            FROM bilibili_comments
            GROUP BY hour
            ORDER BY hour
        """
        rows = query_all(sql)
        hour_map = {row["hour"]: row["comment_count"] for row in rows}
        return [{"hour": h, "comment_count": hour_map.get(h, 0)} for h in range(24)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/comment_top_videos")
def get_comment_top_videos(limit: int = 10):
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT lv.bvid,
                   lv.title,
                   lv.pic,
                   COUNT(c.rpid) AS comment_count,
                   COALESCE(SUM(c.`like`), 0) AS total_comment_likes,
                   ROUND(COALESCE(AVG(c.`like`), 0), 2) AS avg_comment_likes
            FROM latest_videos lv
            LEFT JOIN bilibili_comments c ON lv.bvid = c.bvid
            GROUP BY lv.bvid, lv.title, lv.pic
            ORDER BY comment_count DESC, total_comment_likes DESC
            LIMIT %s
            """
        )
        return query_all(sql, (limit,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/danmaku_hotspots")
def get_danmaku_hotspots(limit: int = 12, bucket_size: int = 30):
    bucket_size = max(5, min(bucket_size, 300))
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT lv.bvid,
                   lv.title,
                   FLOOR(d.`time` / %s) AS segment_idx,
                   COUNT(*) AS danmaku_count,
                   MIN(d.`time`) AS first_time,
                   MAX(d.`time`) AS last_time,
                   MAX(lv.`view`) AS latest_view
            FROM bilibili_danmaku d
            INNER JOIN latest_videos lv ON lv.bvid = d.bvid
            GROUP BY lv.bvid, lv.title, FLOOR(d.`time` / %s)
            ORDER BY danmaku_count DESC, latest_view DESC
            LIMIT %s
            """
        )
        rows = query_all(sql, (bucket_size, bucket_size, limit))
        for row in rows:
            row["segment_start"] = float(row.pop("segment_idx", 0) or 0) * bucket_size
            row["first_time"] = float(row["first_time"] or 0)
            row["last_time"] = float(row["last_time"] or 0)
            row["bucket_size"] = bucket_size
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/top_comments")
def get_top_comments(limit: int = 8):
    try:
        sql = (
            LATEST_VIDEO_CTE
            + """
            SELECT c.bvid,
                   lv.title,
                   c.uname,
                   c.message,
                   c.`like` AS likes,
                   c.reply_count,
                   FROM_UNIXTIME(c.ctime) AS comment_time
            FROM bilibili_comments c
            LEFT JOIN latest_videos lv ON lv.bvid = c.bvid
            ORDER BY c.`like` DESC, c.reply_count DESC, c.ctime DESC
            LIMIT %s
            """
        )
        rows = query_all(sql, (limit,))
        for row in rows:
            if row.get("comment_time"):
                row["comment_time"] = str(row["comment_time"])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/top_danmaku")
def get_top_danmaku(limit: int = 12):
    try:
        sql = """
            SELECT text,
                   COUNT(*) AS freq,
                   COUNT(DISTINCT bvid) AS video_count,
                   MIN(FROM_UNIXTIME(timestamp)) AS first_seen,
                   MAX(FROM_UNIXTIME(timestamp)) AS last_seen
            FROM bilibili_danmaku
            WHERE CHAR_LENGTH(TRIM(text)) BETWEEN 2 AND 20
            GROUP BY text
            HAVING COUNT(*) >= 2
            ORDER BY freq DESC, video_count DESC, last_seen DESC
            LIMIT %s
        """
        rows = query_all(sql, (limit,))
        for row in rows:
            if row.get("first_seen"):
                row["first_seen"] = str(row["first_seen"])
            if row.get("last_seen"):
                row["last_seen"] = str(row["last_seen"])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/videos")
def get_videos(page: int = 1, page_size: int = 20, order_by: str = "view"):
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    page_size = min(page_size, 100)

    order_map = {
        "view": "`view`",
        "likes": "likes",
        "coin": "coin",
        "favorite": "favorite",
        "pubdate": "pubdate",
    }
    order_expr = order_map.get(order_by, "`view`")
    offset = (page - 1) * page_size

    try:
        total = query_one("SELECT COUNT(DISTINCT bvid) AS cnt FROM bilibili_videos")["cnt"]
        sql = (
            LATEST_VIDEO_CTE
            + f"""
            SELECT bvid, title, `view`,
                   `like` AS likes, coin, favorite, share,
                   danmaku, reply, owner_name, pic, pubdate
            FROM latest_videos
            ORDER BY {order_expr} DESC
            LIMIT %s OFFSET %s
            """
        )
        rows = query_all(sql, (page_size, offset))
        return {"total": total, "page": page, "page_size": page_size, "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")


@app.get("/api/analyze")
async def get_analysis_report():
    try:
        report = get_latest_daily_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告失败: {e}")

    if not report or not report.get("content"):
        raise HTTPException(status_code=404, detail="数据库中暂无 AI 数据分析报告")

    return StreamingResponse(
        stream_markdown_text(report["content"]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_file = os.path.join(static_dir, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>前端文件未找到</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=cfg.DEMO_HOST,
        port=cfg.DEMO_PORT,
        reload=False,
    )
