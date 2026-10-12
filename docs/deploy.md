# 部署说明（本地 Docker）

## 一、启动

```bash
cd D:/AAAAGarki/Sonnet/kjds
docker compose up -d --build          # 首次会构建镜像 + 拉 MySQL，视网络 3~15 分钟
docker compose logs -f backend        # 看到 startup OK: 100 products in catalogue 即就绪
```

| 服务 | 容器 | 端口（宿主机） | 说明 |
| --- | --- | --- | --- |
| frontend | kjds-frontend | 8080 → 80 | nginx 托管 Vue 构建产物，并把 `/api`、`/static` 反代到 backend |
| backend | kjds-backend | 5000 → 5000 | gunicorn 4 worker 跑 Flask |
| mysql | kjds-mysql | 3307 → 3306 | MySQL 8.0，库 `kjds`，账号 `kjds / kjds123456` |

访问 http://localhost:8080 。管理员 `admin / admin123`。

```bash
docker compose ps                     # 状态
docker compose restart backend        # 只重启后端
docker compose down                   # 停止（保留数据卷）
docker compose down -v                # 停止并清空 MySQL 数据与向量缓存
```

## 二、启动时序

```
mysql(healthcheck: mysqladmin ping)
      └─► backend: python prestart.py      # 建表 + 灌 100 条商品 + 建管理员
                  │                       # 用 Qwen3-Embedding-8B 预生成 100 条商品向量
                  └─► gunicorn wsgi:app   # 4 worker，端口 5000，healthcheck /api/health
                        └─► frontend: npm build ──► nginx:80
```

`prestart.py` 只跑一次向量预热，避免 4 个 worker 各自重复调用 embedding 接口（100 条商品约 7 次批量请求）。

## 三、环境变量

所有变量集中在根目录 `.env`（`docker compose` 通过 `env_file` 注入 backend）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+pymysql://kjds:kjds123456@mysql:3306/kjds?charset=utf8mb4` | 换成 `sqlite:///...` 可脱离 MySQL 运行 |
| `JWT_SECRET` | `kjds-demo-secret-change-me` | JWT 签名密钥 |
| `JWT_TTL_HOURS` | `168` | token 有效期 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | 首次启动创建的管理员 |
| `EMBED_BASE_URL` / `EMBED_API_KEY` / `EMBED_MODEL` | SiliconFlow / 给定 key / `Qwen/Qwen3-Embedding-8B` | 向量检索 |
| `CHAT_BASE_URL` / `CHAT_API_KEY` / `CHAT_MODEL` | 同上 / `Qwen/Qwen2.5-7B-Instruct` | 对话模型 |
| `AI_TIMEOUT` / `AI_MAX_TOKENS` | `60` / `700` | 上游调用超时与回答长度 |
| `RECOMMEND_LIMIT` / `PAGE_SIZE_DEFAULT` | `5` / `18` | 首页推荐个数、每页商品数 |
| `SEED_ON_START` | `1` | 设为 `0` 则启动时不灌种子数据 |

## 四、数据与持久化

| 卷 / 挂载 | 内容 |
| --- | --- |
| `mysql-data`（命名卷） | MySQL 数据目录，含商品与商品向量 |
| `backend-data`（命名卷） | SQLite 模式下的 `data/kjds.db` |
| `./backend/static`（绑定挂载） | 商品图片 `products/*.webp` 与后台上传的 `uploads/*` |

因为图片是绑定挂载，直接在宿主机替换 `backend/static/` 下的文件即可生效。

## 五、常见问题

**1. `docker compose` 拉镜像很慢/超时（国内网络）**
给 Docker Desktop 配置镜像加速（Settings → Docker Engine），例如：

```json
{ "registry-mirrors": ["https://docker.m.daocloud.io", "https://dockerproxy.net"] }
```
前端镜像构建时 `npm` 已改用 `registry.npmmirror.com`；后端 `pip` 用的是清华源。

**2. backend 一直重启、日志报 database not ready**
MySQL 首次初始化需要 30~60 秒，`app/__init__.py` 会重试 15 次（每次 2 秒）建表；仍失败就看
`docker compose logs mysql`。端口占用则改 `docker-compose.yml` 里的 `3307:3306`。

**3. AI 客服回答变成“（AI 服务暂时不可用…）”**
`/api/health` 里 `chat_key_configured` 为 false 或上游不可达时会走降级回答。检查 `.env` 的
`EMBED_API_KEY`/`CHAT_API_KEY`，以及容器能否访问 `api.siliconflow.cn`：

```bash
docker compose exec backend curl -s -o /dev/null -w '%{http_code}\n' \
  https://api.siliconflow.cn/v1/models -H "Authorization: Bearer $EMBED_API_KEY"
```

**4. 想重置演示数据**
```bash
docker compose down -v && docker compose up -d --build
```

## 六、不用 Docker 的本地跑法

见 README「本地开发」一节：后端 `backend/dev_server.py`（默认 SQLite），前端 `npm run dev`
（Vite 代理 `/api`、`/static` 到 5000 端口）。两个测试脚本都可以直接对着本地服务跑：

```bash
.venv/Scripts/python.exe tests/smoke_test.py     # API（默认 http://127.0.0.1:5000）
.venv/Scripts/python.exe tests/ui_check.py       # UI（默认 http://127.0.0.1:5173）
```
