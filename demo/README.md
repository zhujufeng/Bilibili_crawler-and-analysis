# Bilibili Crawler Demo

基于 FastAPI + ECharts 的数据可视化展示页面，支持汇总 B 站采集数据，并可选接入 Coze Workflow 生成 AI 分析报告。

## 目录结构

```
demo/
├── app.py            # FastAPI 后端
├── config.py         # 从 .env 读取配置
├── .env.example      # 环境变量示例
├── requirements.txt  # Python 依赖
├── static/
│   └── index.html    # 单页前端
└── README.md
```

## 快速启动

### 1. 安装依赖

```bash
cd bilibili_simple_crawler/demo
pip install -r requirements.txt
```

### 2. 配置环境变量

先复制示例文件：

```bash
cp .env.example .env
```

然后编辑 `demo/.env`：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=data_big

COZE_API_TOKEN=pat_xxxx...
COZE_WORKFLOW_ID=7xxx...
COZE_API_BASE_URL=https://api.coze.cn
# 海外可改为 https://api.coze.com
```

说明：
- `COZE_API_TOKEN` 和 `COZE_WORKFLOW_ID` 不填时，页面仍可正常展示图表，只是 AI 分析按钮会提示未配置。
- `COZE_API_BASE_URL` 只填写基础域名，不要附带 `/v1/workflow/run` 之类的路径。

### 3. 启动服务

```bash
# 开发模式（含热重载）
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

# 生产模式
uvicorn app:app --host 0.0.0.0 --port 8080
```

浏览器访问：`http://127.0.0.1:8080`

## 功能说明

| 模块 | 说明 |
|------|------|
| 数据总览 | 视频数、评论数、弹幕数、数据时间跨度 |
| TOP 10 播放量 | 横向柱状图，展示最新快照下的高热视频 |
| 每日采集趋势 | 折线图，展示每日采集到的视频数量 |
| 互动率排行 | `(点赞+投币+收藏+分享)/播放量` |
| 评论时间分布 | 24 小时评论活跃度分析 |
| 视频列表 | 展示最新快照数据，可跳转 B 站原视频 |
| AI 分析报告 | 调用 Coze Workflow，流式返回 Markdown 报告 |

## API 接口

| 路由 | 说明 |
|------|------|
| `GET /api/overview` | 数据总览统计 |
| `GET /api/top_videos` | 播放量 TOP 视频 |
| `GET /api/view_trend` | 每日采集趋势 |
| `GET /api/engagement` | 互动率排行 |
| `GET /api/comment_hour_dist` | 评论时间分布 |
| `GET /api/videos` | 视频列表（分页） |
| `POST /api/analyze` | 触发 Coze AI 分析（SSE 流式） |

## 实现说明

- 榜单和视频列表统一按 `bvid` 的最新快照统计，避免同一视频改标题后被重复计数。
- AI 报告输出在前端做了基础 HTML 净化，降低富文本注入风险。
- 当前前端仍依赖 CDN 加载 `ECharts` 和 `marked`，如果你要做离线演示，建议将这两个前端依赖改为本地静态资源。

## Coze Workflow 接入说明

工作流会收到一个 `data_summary` 参数，包含：
- 数据时间范围
- 采集视频数、总播放量、总点赞数、总投币数、总收藏数
- TOP 5 播放量视频
- TOP 5 热门评论

你的工作流可以基于这些内容生成 Markdown 格式的数据分析报告。
