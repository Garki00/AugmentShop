# 架构与需求对照

## 一、技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 前端 | Vue 3 + Vite + vue-router + axios | 单页应用，构建产物由 nginx 托管 |
| 后端 | Flask 3 + Flask-SQLAlchemy + PyJWT + gunicorn | REST API，JWT 鉴权，管理员 RBAC |
| 数据库 | MySQL 8（`mysql+pymysql`） | 通过 SQLAlchemy 访问；未配置 `DATABASE_URL` 时自动回落 SQLite，方便本地跑 |
| AI | SiliconFlow：`Qwen/Qwen3-Embedding-8B` + `Qwen/Qwen2.5-7B-Instruct` | 向量检索 + 对话，OpenAI 兼容接口 |
| 部署 | docker compose（mysql / backend / frontend） | 前端 nginx 反代 `/api`、`/static` |

> 需求原文写的是“springboot数据库”。Spring Boot 不是数据库，这里按“Spring Boot 项目常用的 MySQL”落地：
> Flask 用 SQLAlchemy + PyMySQL 访问 MySQL 8。若确实想要一个 Spring Boot 数据服务，可以在现有
> `/api` 契约不变的前提下替换 `app/routes/products.py`、`app/routes/admin.py` 两个模块。

## 二、数据模型

```
users                          products
─────                          ────────
id            int PK           id            int PK      ← 沿用种子数据的 id（1..100）
username      varchar(64) UQ   name          varchar(200) 索引
password_hash varchar(255)     price         decimal(10,2)
is_admin      bool             image         varchar(500)   ← /static/products/{id}.webp
created_at    datetime         image_remote  varchar(500)   ← 原始外链，作备份
                               description   text
                               category      varchar(64) 索引
                               brand         varchar(64)
                               rating        float
                               stock         int
                               embedding     longtext       ← Qwen3 向量（JSON），懒加载缓存
                               created_at / updated_at
```

- 商品向量在 `prestart.py` / 首次对话时批量生成并写回 `products.embedding`，之后每次对话直接用缓存；
- 管理员改了商品名称或简介会清空该行缓存，下次对话自动重新向量化（无需手工刷新，后台也提供“刷新 AI 向量库”按钮）。

## 三、AI 客服链路

```
用户提问 ──► POST /api/chat {product_id, question, history}
               │
               ├─ 1. 取当前商品（名称 / 价格 / 简介 / 类目 / 品牌）
               │
               ├─ 2. Qwen3-Embedding-8B：问题 → 向量，与 100 条商品向量算余弦相似度
               │        └─► 取最相似的 3 件作为「相关商品」放进提示词（检索增强）
               │
               ├─ 3. 拼 system prompt：当前商品信息 + 相关商品 + 回答约束（价格必须用库里的值、
               │      不要臆造物流/退换货、中文、150 字以内）
               │
               └─ 4. Qwen2.5-7B-Instruct 生成回答 → {answer, related, elapsed_ms, degraded}
```

上游不可达时不抛错，改为按数据库字段拼兜底回答并置 `degraded=true`，前端标注“降级回答”，演示不会空白。

## 四、接口分层

```
/api/health                       健康状况 + AI 配置自检
/api/auth/*                       register · login · me      （JWT）
/api/products/*                   list(搜索/分页) · recommend · categories · detail   （公开）
/api/admin/products*              CRUD + upload + stats + embeddings/refresh          （管理员）
/api/chat                         商品上下文 + 向量检索 + LLM 回答
/static/*                         商品图片、占位图、后台上传图
```

## 五、需求对照表

| # | 需求 | 落地 | 验证方式 |
| --- | --- | --- | --- |
| 1 | 用户名 + 密码注册登录 | `/login` `/register` 页面 + `/api/auth/*`，Werkzeug 哈希 + JWT | `smoke_test`：注册 201、重复 409、弱口令 400、错密码 401、`/auth/me` 往返 |
| 2 | 商品字段：名称/图片/价格/简介 | `products` 表（另存类目/品牌/评分/库存） | `smoke_test`：详情四字段齐全 |
| 3 | 100 条原始商品数据，图片来自网络 | `seed/fetch_seed.py` 从 DummyJSON 抓 100 条 + 下载 100 张图片到 `static/products/` | 脚本输出 `records 100 / local images 100` |
| 4 | 管理员增删改查 | `/admin` 表格 + 弹窗表单 + 上传；`/api/admin/products*` | `smoke_test` 8 项 + `ui_check` 新建/编辑/删除 5 项 |
| 5 | 首页推荐随机 5 个并轮换，重开页面重抽 | `ORDER BY RAND()` + 轮播（3.5s 自动切换、圆点、换一批） | `ui_check`：5 个圆点、切换生效、换一批结果不同 |
| 6 | 推荐下方搜索框，空值显示原始列表 | `.hero` 之后是 `.searchbar`；`keyword=""` 走全量查询 | `ui_check`：搜索框位置在推荐块之下、`mascara` 命中 1 条、清空恢复 18 条 |
| 7 | 列表一行 3 个、最多 6 行、超出分页 | `.grid` 三列 + `Pagination`（18/页 = 3×6，共 6 页） | `ui_check`：首页 18 张卡片、第 6 页 10 张、上一页可回退 |
| 8 | 点击商品进详情页 | `/product/:id` 路由，展示名称/图片/简介/价格 | `ui_check`：点卡片后 h1/价格/简介齐全 |
| 9 | 右侧 AI 客服，提示词带当前商品信息 | `ChatPanel.vue` + `/api/chat`，system prompt 注入名称/价格/简介 | `ui_check`：回答里出现数据库中的真实价格 6.99 |
| 10 | 用 Embedding 模型调用 AI | 向量检索用 `Qwen3-Embedding-8B`，对话用同一个 key 的 `Qwen2.5-7B-Instruct` | `smoke_test`：100 条商品已向量化、相关商品返回 3 条 |
| 11 | 部署在本地 docker | `docker-compose.yml` 三服务 + nginx 反代 | `docker compose config` 校验通过；见下节说明 |

## 六、验证记录

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| API 端到端（本地 SQLite） | `BASE=http://127.0.0.1:5000 .venv/Scripts/python.exe tests/smoke_test.py` | 37/37 通过 |
| API 端到端（docker + MySQL 8） | `BASE=http://localhost:8080 .venv/Scripts/python.exe tests/smoke_test.py` | 37/37 通过，`dialect=mysql` |
| 真实 UI（无头 Chrome，本地） | `.venv/Scripts/python.exe tests/ui_check.py` | 24/24 通过 |
| 真实 UI（docker 部署） | `UI_BASE=http://localhost:8080 .venv/Scripts/python.exe tests/ui_check.py` | 24/24 通过 |
| 前端构建 | `npm run build` | 成功，104 modules |
| compose 文件 | `docker compose config` | 通过 |
| 整栈启动 | `docker compose up -d --build` | mysql healthy → backend（prestart 灌 100 条 + 向量化 20s）→ healthy → frontend 启动 |

数据库侧核对（docker 内）：

```bash
docker compose exec -T mysql mysql -ukjds -pkjds123456 kjds \
  -e "select count(*) products, sum(embedding is not null) embedded from products;"
# products 100 | embedded 100
```

截图：`01-home.png`（首页推荐 + 搜索 + 3 列列表 + 分页）、`02-search.png`（关键词搜索）、
`03-detail.png`、`04-detail-chat.png`（详情页 + AI 客服对话 + 相关商品）、`05-admin.png`
（后台表格）、`06-admin-created.png`（新增商品）、`07-admin-after-delete.png`。

## 七、演示项目的取舍

- 只做展示：JWT 密钥、MySQL 口令都在 `.env` 明文；未做限流、幂等、订单与支付、图片 CDN；
- 未做购物车/下单（首页与详情页的“加入购物车”按钮是摆设，页面已注明）；
- 向量检索是内存里算余弦（100 条数据毫秒级），生产应换向量库（Milvus / pgvector / Qdrant）；
- 商品图是 400px 缩略图，够展示用。
