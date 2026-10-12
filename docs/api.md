# API 参考

Base URL：开发环境 `http://127.0.0.1:5000`，Docker 环境 `http://localhost:8080`（nginx 反代 `/api`）。
除标注外均为 `application/json`；需要登录的接口带 `Authorization: Bearer <token>`。

统一错误体：`{"error": "<code>", "message": "<中文提示>"}`。

## 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 返回数据库连接状态、方言、AI 模型与 key 配置状态 |

```json
{"status":"ok","database":"up","dialect":"mysql",
 "ai":{"embed_model":"Qwen/Qwen3-Embedding-8B","chat_model":"Qwen/Qwen2.5-7B-Instruct",
       "embed_key_configured":true,"chat_key_configured":true}}
```

## 鉴权

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | body `{username, password}`；用户名 3-32 位 `[A-Za-z0-9_-]`，密码 ≥6 位；201 返回 `{token, user}` |
| POST | `/api/auth/login` | body `{username, password}`；返回 `{token, user}`，密码错误 401 |
| GET | `/api/auth/me` | 需登录，返回 `{user}` |
| POST | `/api/auth/logout` | 无状态 JWT，客户端丢弃 token 即可 |

`user` 结构：`{"id":1,"username":"admin","is_admin":true}`；token 默认有效期 `JWT_TTL_HOURS=168` 小时。

## 商品（前台）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/products?keyword=&page=1&page_size=18` | 关键词模糊匹配名称/简介/品牌/类目；**keyword 为空时返回全部原始商品**（100 条） |
| GET | `/api/products/recommend?limit=5` | 随机抽取 N 件（`ORDER BY RAND()`），每次调用结果不同 → 首页“每次打开重新抽 5 个” |
| GET | `/api/products/categories` | 类目及数量，用于筛选/统计 |
| GET | `/api/products/{id}` | 商品详情 |

列表响应（`page_size` 上限 `PAGE_SIZE_MAX=60`，默认 18 = 一行 3 个 × 6 行）：

```json
{"items":[{"id":1,"name":"Essence Mascara Lash Princess","price":9.99,
           "image":"/static/products/1.webp","image_remote":"https://cdn.dummyjson.com/...",
           "description":"…（列表内截断到 90 字）","category":"beauty","brand":"Essence",
           "rating":4.94,"stock":99}],
 "total":100,"page":1,"page_size":18,"pages":6,"has_prev":false,"has_next":true,
 "keyword":""}
```

## 商品（管理后台，需要管理员 token）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/admin/products?keyword=&page=1&page_size=20` | 后台列表，返回完整字段（含简介） |
| POST | `/api/admin/products` | 新增，body 同下；201 |
| PUT | `/api/admin/products/{id}` | 更新（部分字段即可）；改动了名称或简介会清空向量缓存，下次对话自动重新向量化 |
| DELETE | `/api/admin/products/{id}` | 删除 |
| POST | `/api/admin/upload` | `multipart/form-data` 字段名 `file`；返回 `{"url":"/static/uploads/xxx.png"}`，可直接填进 `image` |
| GET | `/api/admin/stats` | `{products, embedded, categories, avg_price}` |
| POST | `/api/admin/embeddings/refresh` | body `{force?:bool}`，用 Qwen3-Embedding-8B 重新向量化，返回 `{embedded, model}` |

可写字段：`name`（必填）、`price`、`image`、`image_remote`、`description`、`category`、`brand`、`stock`、`rating`。

普通用户调用管理接口返回 `403`，未登录返回 `401`。

## AI 客服

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/chat` | body `{product_id, question, history?: [{role, content}]}` |

流程：取当前商品 → 用 Qwen3-Embedding-8B 向量化问题并在 100 件商品中检索最相似的 3 件 → 把
「商品名称 / 售价 / 简介 / 类目 / 品牌 / 相关商品」写进 system prompt → 调 Qwen2.5-7B-Instruct 作答。

```json
{"answer":"这件商品售价是9.99美元。Essence Mascara Lash Princess 是一款……",
 "degraded":false,
 "model":"Qwen/Qwen2.5-7B-Instruct",
 "embedding_model":"Qwen/Qwen3-Embedding-8B",
 "embedding_used":true,
 "embedded_now":0,
 "product":{"id":1,"name":"Essence Mascara Lash Princess","price":9.99,"image":"/static/products/1.webp"},
 "related":[{"id":2,"name":"Eyeshadow Palette with Mirror","price":19.99,"image":"/static/products/2.webp"}],
 "elapsed_ms":3412}
```

- `degraded=true` 表示上游模型不可达，`answer` 是按数据库字段拼的兜底回答（前端会提示“降级回答”）。
- `embedding_used=true` 表示相关商品来自向量检索；否则是同类目兜底。
- 缺 `question` → 400；`product_id` 不存在 → 404。

## 静态资源

| 路径 | 说明 |
| --- | --- |
| `/static/products/{id}.webp` | 100 件商品的本地图片（由种子脚本下载） |
| `/static/products/placeholder.svg` | 缺图占位 |
| `/static/uploads/{uuid}.{ext}` | 管理后台上传的图片 |
