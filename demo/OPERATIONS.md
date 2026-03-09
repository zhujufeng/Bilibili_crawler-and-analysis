# Bilibili Demo 运维与发布手册

本文档面向当前项目 `demo/` 目录下的 FastAPI 可视化站点，目标是让你在不熟悉 FastAPI 和 Linux 运维的情况下，也能完成：

- 用服务器公网 IP 访问站点
- 修改代码后重新发布
- 查看日志和排查常见问题
- 备份和恢复关键配置

适用环境：

- 服务器系统：Ubuntu
- 项目目录：`/py_file/bilibili_simple_crawler/demo`
- Python 环境：`/root/miniconda3/envs/crawler/bin/python`
- systemd 服务名：`bilibili-demo`
- Nginx：已安装，用于把 80 端口转发到 `127.0.0.1:8080`

---

## 1. 当前部署结构

当前站点运行结构如下：

1. 浏览器访问服务器公网 IP
2. 请求先到 Nginx 的 80 端口
3. Nginx 反向代理到 FastAPI 服务 `127.0.0.1:8080`
4. FastAPI 进程由 `systemd` 托管，服务名是 `bilibili-demo`

简单理解：

- `app.py` 是你的后端入口
- `static/index.html` 是前端页面
- `systemd` 负责“守护” Python 进程
- `Nginx` 负责“对外提供 HTTP 访问”

---

## 2. 访问方式

你现在不走域名，直接走公网 IP 即可。

访问地址：

```text
http://你的服务器公网IP
```

如果 Nginx 还没配置好，也可以临时直接访问应用端口：

```text
http://你的服务器公网IP:8080
```

但正式建议始终走 80 端口，也就是：

```text
http://你的服务器公网IP
```

原因：

- 用户访问更简单
- 不暴露内部应用端口
- 后续如果切 HTTPS，也更容易

---

## 3. 项目目录说明

服务器上的关键目录：

```text
/py_file/bilibili_simple_crawler/
├── demo/
│   ├── app.py
│   ├── config.py
│   ├── .env
│   ├── requirements.txt
│   ├── static/
│   │   └── index.html
│   └── OPERATIONS.md
```

关键文件作用：

- `app.py`：后端接口、AI 报告逻辑、数据库查询逻辑
- `config.py`：读取 `.env` 配置
- `.env`：数据库、Coze、端口等配置
- `static/index.html`：前端页面和图表逻辑
- `requirements.txt`：依赖清单

---

## 4. 常用运维命令

### 4.1 查看服务状态

```bash
systemctl status bilibili-demo
```

看点：

- `active (running)`：服务正常
- `failed`：服务启动失败
- `activating (auto-restart)`：服务在不停重启，通常说明代码报错或路径错了

### 4.2 查看实时日志

```bash
journalctl -u bilibili-demo -f
```

这个命令非常重要。

遇到站点打不开、接口 500、启动失败，优先看这个。

### 4.3 重启服务

```bash
systemctl restart bilibili-demo
```

每次你修改 `app.py`、`config.py`、`.env` 后，都建议执行一次。

### 4.4 停止服务

```bash
systemctl stop bilibili-demo
```

### 4.5 启动服务

```bash
systemctl start bilibili-demo
```

### 4.6 查看 Nginx 状态

```bash
systemctl status nginx
```

### 4.7 测试 Nginx 配置是否正确

```bash
nginx -t
```

### 4.8 重启 Nginx

```bash
systemctl restart nginx
```

---

## 5. 如何修改代码并发布

这是你以后最常用的流程。

### 5.1 修改后端代码

后端主要改这个文件：

```text
/py_file/bilibili_simple_crawler/demo/app.py
```

比如你要改：

- 新增接口
- 修改 SQL
- 修改 AI 报告逻辑
- 调整缓存策略

改完后执行：

```bash
cd /py_file/bilibili_simple_crawler/demo
/root/miniconda3/envs/crawler/bin/python -m py_compile app.py
```

如果没有报错，再重启服务：

```bash
systemctl restart bilibili-demo
```

然后查看日志：

```bash
journalctl -u bilibili-demo -n 50 --no-pager
```

### 5.2 修改前端页面

前端主要改这个文件：

```text
/py_file/bilibili_simple_crawler/demo/static/index.html
```

比如你要改：

- 图表样式
- 卡片文案
- 表格内容
- AI 报告展示区域

改完通常不需要重启 Nginx，但建议重启 FastAPI 服务，避免缓存和状态不一致：

```bash
systemctl restart bilibili-demo
```

然后浏览器强制刷新：

- Windows：`Ctrl + F5`
- Mac：`Cmd + Shift + R`

### 5.3 修改环境配置

环境配置文件：

```text
/py_file/bilibili_simple_crawler/demo/.env
```

改完后必须重启服务：

```bash
systemctl restart bilibili-demo
```

常见会改的字段：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `COZE_API_TOKEN`
- `COZE_WORKFLOW_ID`
- `COZE_API_BASE_URL`

---

## 6. 推荐的发布流程

以后每次你要发布更新，按这个顺序做。

### 6.1 进入项目目录

```bash
cd /py_file/bilibili_simple_crawler/demo
```

### 6.2 备份关键文件

建议至少备份：

```bash
cp app.py app.py.bak
cp static/index.html static/index.html.bak
cp .env .env.bak
```

如果你改坏了，可以快速恢复。

### 6.3 修改代码

用你熟悉的编辑器：

```bash
vim app.py
```

或者：

```bash
nano app.py
```

前端同理：

```bash
nano static/index.html
```

### 6.4 做最基本的语法检查

```bash
/root/miniconda3/envs/crawler/bin/python -m py_compile app.py
```

如果报错，先修，再继续。

### 6.5 重启服务

```bash
systemctl restart bilibili-demo
```

### 6.6 看服务状态

```bash
systemctl status bilibili-demo
```

### 6.7 看日志

```bash
journalctl -u bilibili-demo -n 100 --no-pager
```

### 6.8 测试本机接口

```bash
curl http://127.0.0.1:8080
curl http://127.0.0.1:8080/api/overview
```

### 6.9 测试外网访问

```bash
curl http://你的公网IP
```

---

## 7. 修改代码时的建议

### 7.1 改后端时先小改，再重启

不要一次改很多逻辑再重启。建议：

1. 改一小块
2. `py_compile`
3. `systemctl restart bilibili-demo`
4. 看日志

### 7.2 SQL 改动优先在日志里验证

你这个项目里很多接口是 SQL 查询。

如果接口 500，通常是：

- 字段名写错
- `GROUP BY` 不兼容
- 表里没有数据
- 某张表今天没有记录

出现 500 时，先看：

```bash
journalctl -u bilibili-demo -f
```

### 7.3 前端问题和后端问题怎么区分

- 页面打不开：优先看 Nginx 或 systemd
- 页面打开但某个图表“加载失败”：优先看接口日志
- AI 报告显示不对：先看 `/api/analyze` 返回内容，再看前端渲染

---

## 8. 常见问题排查

### 8.1 服务起不来

先看：

```bash
systemctl status bilibili-demo
journalctl -u bilibili-demo -n 100 --no-pager
```

常见原因：

- Python 路径错
- 依赖没装
- `.env` 配置错
- `app.py` 语法错误

### 8.2 页面能开，但接口 500

先看日志：

```bash
journalctl -u bilibili-demo -f
```

如果是数据库问题，再测试数据库连通性。

### 8.3 本机能访问，外网不能访问

检查三件事：

1. Nginx 是否正常

```bash
systemctl status nginx
nginx -t
```

2. 腾讯云安全组是否开放 `80`

3. Ubuntu 防火墙是否拦截

如果你启用了 UFW：

```bash
ufw status
```

需要时放行：

```bash
ufw allow 80
ufw allow 443
```

### 8.4 AI 报告有问题

你现在已经做了“今日日报优先走数据库缓存”。

所以优先检查：

- `bilibili_daily_report` 今天是否有数据
- 数据内容是不是 Markdown
- `/api/analyze` 是不是命中了缓存逻辑

如果今天没有缓存，才会继续走 Coze。

---

## 9. 数据库相关说明

你现在依赖的关键表包括：

- `bilibili_videos`
- `bilibili_comments`
- `bilibili_danmaku`
- `bilibili_daily_report`

如果图表没数据，先看数据库表是否有内容。

例如：

```sql
SELECT COUNT(*) FROM bilibili_videos;
SELECT COUNT(*) FROM bilibili_comments;
SELECT COUNT(*) FROM bilibili_danmaku;
SELECT id, created_at FROM bilibili_daily_report ORDER BY id DESC LIMIT 5;
```

---

## 10. 回滚方法

如果你改坏了代码，最快恢复方法是把备份文件拷回去。

例如：

```bash
cp app.py.bak app.py
cp static/index.html.bak static/index.html
systemctl restart bilibili-demo
```

如果你已经用了 Git，也可以用 Git 回滚，但前提是你清楚哪些改动要保留。

---

## 11. 建议养成的习惯

建议你以后每次改代码都按这个顺序：

1. 先备份
2. 小步修改
3. 先 `py_compile`
4. 再重启服务
5. 再看日志
6. 最后浏览器验证

这样你会少踩很多坑。

---

## 12. 常用命令速查

### 服务

```bash
systemctl status bilibili-demo
systemctl restart bilibili-demo
systemctl stop bilibili-demo
systemctl start bilibili-demo
journalctl -u bilibili-demo -f
```

### Nginx

```bash
nginx -t
systemctl status nginx
systemctl restart nginx
```

### 本机测试

```bash
curl http://127.0.0.1:8080
curl http://127.0.0.1:8080/api/overview
curl http://你的公网IP
```

### Python 语法检查

```bash
cd /py_file/bilibili_simple_crawler/demo
/root/miniconda3/envs/crawler/bin/python -m py_compile app.py
```

### 备份

```bash
cp app.py app.py.bak
cp static/index.html static/index.html.bak
cp .env .env.bak
```

---

## 13. 你以后最常用的一套操作

如果你只是“改了一点代码并重新上线”，最常用的是这几条：

```bash
cd /py_file/bilibili_simple_crawler/demo
cp app.py app.py.bak
/root/miniconda3/envs/crawler/bin/python -m py_compile app.py
systemctl restart bilibili-demo
journalctl -u bilibili-demo -n 50 --no-pager
curl http://127.0.0.1:8080/api/overview
```

如果你改的是前端：

```bash
cd /py_file/bilibili_simple_crawler/demo
cp static/index.html static/index.html.bak
systemctl restart bilibili-demo
```

---

## 14. 后续建议

等你后面更熟一些，建议再做这几件事：

- 给项目加 Git 发布流程
- 给 `.env` 做正式备份
- 给 MySQL 做定期备份
- 给 Nginx 配 HTTPS
- 把 systemd 服务改成非 root 用户运行

但现在先不用一次全做，先把当前站点稳定跑着最重要。
