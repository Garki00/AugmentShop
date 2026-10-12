# 环球优选 · 跨境电商商城

一个可以直接 `docker compose up` 跑起来的跨境电商演示站：Flask 提供 API，Vue 3 渲染商城前台与管理后台，
MySQL 8 存数据，商品详情页右侧挂一个由 **SiliconFlow Qwen 模型** 驱动的 AI 客服。

```
┌─────────────┐  /api  ┌──────────────┐        ┌──────────────┐
│  Vue 3 SPA  │ ─────► │ Flask (API)  │ ─────► │  MySQL 8     │
│  nginx :80  │        │ gunicorn:5000│        │  kjds 库     │
└─────────────┘        └──────┬───────┘        └──────────────┘
                              │  Qwen3-Embedding-8B（检索）+ Qwen2.5-7B（回答）
                              ▼
                       api.siliconflow.cn
```

## 功能一览

| 需求 | 实现位置 |
| --- | --- |
| 用户登录 / 注册（用户名 + 密码） | `POST /api/auth/register`、`/api/auth/login`，JWT；页面 `/login` `/register` |
| 商品（名称 / 图片 / 价格 / 简介） | `products` 表；种子数据 100 条真实商品（含图片） |
| 100 条原始商品数据 | `backend/seed/products.json` + `backend/static/products/*.webp` |
| 管理员对商品增删改查 | `/api/admin/products*`，页面 `/admin`（表格 + 弹窗表单 + 图片上传） |
| 首页推荐：随机 5 个且轮换、每次打开页面重抽 | `GET /api/products/recommend`（`ORDER BY RAND()`），首页轮播自动播放 3.5s + “换一批” |
| 推荐下方搜索框，空值显示原始列表 | `GET /api/products?keyword=`（空关键词返回全部 100 条） |
| 商品列表：一行 3 个、最多 6 行（18/页）、超出分页 | 首页 `.grid` + `Pagination` 组件，共 6 页 |
| 点击商品进详情页 | `/product/:id`，展示名称 / 图片 / 简介 / 价格 |
| 详情页右侧 AI 客服，提示词带当前商品信息 | `POST /api/chat` → 商品名 + 价格 + 简介写入 system prompt |

## 快速开始（Docker，推荐）

```bash
cd D:/AAAAGarki/Sonnet/kjds
cp .env.example .env        # 仓库里已带一份可用的 .env，按需改 key
docker compose up -d --build
```

| 地址 | 说明 |
| --- | --- |
| http://localhost:8080 | 商城主页（nginx + Vue） |
| http://localhost:5000/api/health | 后端健康检查（含 AI 模型配置状态） |
| http://localhost:3307 | MySQL 8（用户 `kjds` / 密码 `kjds123456`，库 `kjds`） |

管理员账号：**admin / admin123**（首次启动自动创建）。

首次启动顺序：`mysql` 健康检查通过 → `backend` 容器内执行 `python prestart.py`（建表、灌 100 条商品、用
Qwen3-Embedding-8B 预生成商品向量）→ gunicorn 起服务 → `frontend` 构建静态文件并由 nginx 托管。

## 本地开发（不用 Docker）

后端（默认回落 SQLite，改 `DATABASE_URL` 即切 MySQL）：

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe -r backend/requirements.txt
cd backend && DATABASE_URL="sqlite:///D:/AAAAGarki/Sonnet/kjds/backend/data/kjds.db" \
  ../.venv/Scripts/python.exe dev_server.py       # http://127.0.0.1:5000
```

前端（Vite dev server 会把 `/api`、`/static` 代理到 5000 端口）：

```bash
cd frontend && npm install && npm run dev          # http://127.0.0.1:5173
```

## 测试与验证结果

```bash
.venv/Scripts/python.exe tests/smoke_test.py                       # API，默认 http://127.0.0.1:5000
BASE=http://localhost:8080 .venv/Scripts/python.exe tests/smoke_test.py    # 对 docker 部署跑
.venv/Scripts/python.exe tests/ui_check.py                         
UI_BASE=http://localhost:8080 .venv/Scripts/python.exe tests/ui_check.py   # 对 docker 部署跑
```

| 检查 | 结果 |
| --- | --- |
| `tests/smoke_test.py`（37 项：分页/搜索/推荐随机/图片/注册登录/JWT/RBAC/增删改查/上传/AI 对话） | **37/37 通过**（本地 SQLite 与 docker+MySQL 各跑一遍） |
| `tests/ui_check.py`（24 项：真实点击/输入/拖拽分页/AI 客服对话/后台增删改） | **24/24 通过**，截图见 `docs/screenshots/` |
| `npm run build` | 成功（104 modules，dist 约 151 KB gzip 58 KB） |
| `docker compose config` | 校验通过 |
| `docker compose up -d --build` | mysql healthy → backend healthy → frontend 启动，无 502 |

截图（`docs/screenshots/`）：`01-home` 首页推荐 + 搜索框 + 3 列列表 + 分页 · `02-search` 关键词搜索 ·
`03-detail` 详情页 · `04-detail-chat` AI 客服对话 + 相关商品 · `05-admin` 后台表格 · `06-admin-created`
新增商品 · `07-admin-after-delete` 删除后。

## 流程演示脚本


```bash
.venv/Scripts/python.exe demos/flow_demo.py --base http://localhost:8080   # docker 部署
.venv/Scripts/python.exe demos/flow_demo.py --pause --slow                
.venv/Scripts/python.exe demos/flow_demo.py --no-ai                       # 断网兜底
.venv/Scripts/python.exe demos/flow_demo.py --save demo_log.txt           # 存一份演示记录
```

幕次：①数据基础（100 条种子数据/类目/价格区间/图片本地化）②首页推荐随机重抽 ③搜索与分页
④商品详情与图片校验 ⑤AI 客服（打印注入提示词的商品事实 → 提问 → 回答/相关商品/耗时）
⑥注册登录与权限隔离（403 演示）⑦后台增删改查。写操作可回收：演示新增的商品结束时自动删除，
演示账号 `demo_shopper` 首次创建、之后复用登录。

## 目录结构

```
backend/
  app/__init__.py        Flask 应用工厂（建表、重试连库、启动灌数据）
  app/config.py          环境变量集中配置（.env 自动加载）
  app/models.py          User / Product 模型（含向量缓存字段）
  app/security.py        JWT 签发与 login_required / admin_required
  app/routes/            auth · products · admin · chat
  app/services/ai.py     SiliconFlow 客户端（embeddings + chat + 降级回答）
  app/services/rag.py    Qwen3-Embedding 向量缓存与相似商品检索
  app/services/seed_data.py  100 条商品 + 管理员账号初始化
  seed/fetch_seed.py     从 DummyJSON 抓取商品与图片（可重跑）
  prestart.py            容器启动前：建表 + 灌数据 + 预热向量
frontend/
  src/views/             Home / ProductDetail / Login / Register / Admin
  src/components/        ProductCard · RecommendCarousel · Pagination · ChatPanel
  nginx.conf             静态托管 + /api、/static 反代
tests/                   smoke_test.py（API）· ui_check.py（无头浏览器）
docs/                    API 文档、部署说明、架构与需求对照
```


更多细节：[docs/api.md](docs/api.md) · [docs/deploy.md](docs/deploy.md) · [docs/architecture.md](docs/architecture.md)
