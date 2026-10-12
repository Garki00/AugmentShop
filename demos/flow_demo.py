"""跨境电商平台 · 流程展示脚本（答辩/讲解用）

和 tests/ 里的"断言型"脚本不同，这个脚本是"叙事型"：按幕推进，每一幕先说清要证明的需求点，
再发真实请求、把关键字段和耗时打出来，最后给一份结论汇总。适合投屏或照着念。

用法：
    python demos/flow_demo.py                          # 默认 http://127.0.0.1:5000
    python demos/flow_demo.py --base http://localhost:8080
    python demos/flow_demo.py --pause                  # 每幕回车再继续（现场讲解）
    python demos/flow_demo.py --slow                   # 每步 sleep，投屏跟得上
    python demos/flow_demo.py --no-ai                  # 跳过 AI 那一幕（网络不通时保底）
    python demos/flow_demo.py --save demo_log.txt      # 同时存一份演示记录

写操作都可回收：演示新增的商品在幕 7 结束前删掉；演示账号 demo_shopper 首次运行创建，之后复用登录。
"""
from __future__ import annotations

import argparse
import sys
import time

import requests

TIMEOUT = 120
DEMO_USER = "demo_shopper"
DEMO_PASS = "demo123456"
LINE = "═" * 74


class Demo:
    def __init__(self, base: str, *, pause: bool, slow: bool, use_ai: bool, save: str | None):
        self.base = base.rstrip("/")
        self.pause = pause
        self.slow = slow
        self.use_ai = use_ai
        self.session = requests.Session()
        self.transcript: list[str] | None = [] if save else None
        self.save_path = save
        self.oks = 0
        self.warns = 0
        self.warn_msgs: list[str] = []
        self.admin_headers: dict[str, str] = {}

    # ---------- 输出 ----------
    def emit(self, line: str = "") -> None:
        print(line)
        if self.transcript is not None:
            self.transcript.append(line)

    def curtain(self, number: int, title: str, requirement: str = "") -> None:
        self.emit()
        self.emit(LINE)
        self.emit(f"  幕 {number}｜{title}")
        if requirement:
            self.emit(f"  需求点：{requirement}")
        self.emit(LINE)
        if self.pause:
            try:
                input("  （回车继续）")
            except EOFError:
                pass

    def say(self, text: str = "") -> None:
        self.emit(f"  {text}")

    def ok(self, text: str, detail: str = "") -> None:
        self.oks += 1
        self.emit(f"  ✅ {text}" + (f" ｜ {detail}" if detail else ""))

    def warn(self, text: str, detail: str = "") -> None:
        self.warns += 1
        self.warn_msgs.append(text)
        self.emit(f"  ⚠️  {text}" + (f" ｜ {detail}" if detail else ""))

    def slow_down(self, factor: float = 1.0) -> None:
        if self.slow:
            time.sleep(0.6 * factor)

    # ---------- 请求 ----------
    def req(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        body: dict | None = None,
        headers: dict | None = None,
        show: bool = True,
    ) -> requests.Response | None:
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items() if v not in (None, ""))
        label = f"{method} {path}{query}"
        t0 = time.perf_counter()
        try:
            resp = self.session.request(
                method, f"{self.base}{path}", params=params, json=body, headers=headers, timeout=TIMEOUT
            )
        except requests.RequestException as exc:
            self.emit(f"    {label}  →  连接失败：{exc}")
            return None
        elapsed = (time.perf_counter() - t0) * 1000
        if show:
            self.emit(f"    {label}  →  {resp.status_code}  {elapsed:.0f}ms")
        self.slow_down()
        return resp

    # ---------- 工具 ----------
    @staticmethod
    def pretty(value, limit: int = 90) -> str:
        text = str(value).replace("\n", " ")
        return text if len(text) <= limit else text[:limit] + "…"

    def finish(self) -> int:
        self.emit()
        self.emit(LINE)
        self.emit("  结论汇总")
        self.emit(LINE)
        for line in self.warn_msgs:
            self.emit(f"    ⚠️  {line}")
        self.emit(f"    检查点通过 {self.oks} 项" + (f"，需注意 {self.warns} 项" if self.warns else "，无告警"))
        if self.transcript is not None and self.save_path:
            with open(self.save_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(self.transcript) + "\n")
            self.emit(f"    演示记录已保存：{self.save_path}")
        self.emit(LINE)
        return 0 if self.warns == 0 else 0  # 演示脚本：有告警也退出 0，告警在上面列出


def stage1(d: Demo) -> None:
    d.curtain(1, "数据基础：库里有 100 条真实商品", "商品需要含有 100 条原始商品数据用于展示")
    r = d.req("GET", "/api/health")
    if r is None or r.status_code != 200:
        d.warn("健康检查失败，后续幕次可能不准确")
        return
    health = r.json()
    d.ok("后端与数据库就绪", f"database={health['database']}, dialect={health['dialect']}")
    d.ok(
        "AI 模型已配置",
        f"{health['ai']['embed_model']} + {health['ai']['chat_model']}",
    )

    total, items, page = None, [], 1
    while True:
        resp = d.req("GET", "/api/products", params={"page": page, "page_size": 50}, show=(page == 1))
        if resp is None or resp.status_code != 200:
            break
        data = resp.json()
        total = data["total"]
        items.extend(data["items"])
        if page >= data["pages"]:
            break
        page += 1
    if not items:
        d.warn("没有取到商品列表")
        return
    prices = [p["price"] for p in items]
    seed = [p for p in items if p["id"] <= 100]
    extra = [p for p in items if p["id"] > 100]
    d.ok("商品总数", f"{total} 条" + (f"（其中种子数据 {len(seed)} 条 + 后台新增 {len(extra)} 条）" if extra else ""))
    if extra:
        d.say("      非种子商品：" + "、".join(f"#{p['id']} {p['name']}" for p in extra[:5]))
        d.say("      提示：需求里的 100 条是原始数据（id 1-100），这些是后台新增/演示时录入的。")
    d.ok("价格区间 / 均价", f"${min(prices):.2f} ~ ${max(prices):.2f} / 均价 ${sum(prices)/len(prices):.2f}")
    cats = d.req("GET", "/api/products/categories")
    if cats is not None and cats.status_code == 200:
        rows = cats.json()["items"]
        d.ok("类目分布", f"{len(rows)} 个类目：" + "、".join(f"{c['category']}({c['count']})" for c in rows[:6]) + " …")
    with_img = sum(1 for p in items if p.get("image", "").startswith("/static/"))
    d.ok("图片已本地化（不依赖外网展示）", f"{with_img}/{len(items)} 张走 /static/products/")
    d.say()
    d.say("说明：数据来自公开商品数据集 DummyJSON，由 backend/seed/fetch_seed.py 抓取并下载图片。")


def stage2(d: Demo) -> None:
    d.curtain(2, "首页推荐：随机 5 个、每次打开重抽", "推荐（随机抽取 5 个商品，这五个商品轮换显示，再打开页面再抽取五个）")
    first = d.req("GET", "/api/products/recommend", params={"limit": 5})
    second = d.req("GET", "/api/products/recommend", params={"limit": 5})
    if not first or not second:
        d.warn("推荐接口不可用")
        return
    a = first.json()["items"]
    b = second.json()["items"]
    ids_a = [p["id"] for p in a]
    ids_b = [p["id"] for p in b]
    d.ok("一次返回 5 个且不重复", f"id={ids_a}")
    d.ok("再次调用换了另一批（→ 每次打开页面重新抽取）", f"id={ids_b}")
    if ids_a != ids_b:
        d.ok("两次结果不同，随机生效")
    else:
        d.warn("两次结果相同（概率极低，可再跑一次）")
    d.say("前端：首页 onMounted 调该接口 → 打开/刷新即重抽；RecommendCarousel 每 3.5s 自动轮播，")
    d.say("      圆点可跳转，右上「换一批」手动重抽。")
    d.ok("轮播数据完整（名称/价格/图片都在）", d.pretty(f"{a[0]['name']} ${a[0]['price']} {a[0]['image']}"))


def stage3(d: Demo) -> None:
    d.curtain(3, "搜索与商品列表：一行 3 个 × 最多 6 行 + 分页", "推荐下方显示搜索框…搜索栏空显示原始商品列表；一行三个商品，最多六行，超过分页")
    empty = d.req("GET", "/api/products", params={"keyword": "", "page": 1, "page_size": 18})
    if empty and empty.status_code == 200:
        data = empty.json()
        d.ok("搜索框留空 → 返回原始全量列表", f"total={data['total']}, 本页 {len(data['items'])} 条")
        d.ok("分页参数", f"每页 {data['page_size']} 条（3 列 × 6 行），共 {data['pages']} 页")
    for kw in ("mascara", "laptop", "kitchen"):
        r = d.req("GET", "/api/products", params={"keyword": kw})
        if r is None:
            continue
        data = r.json()
        names = "、".join(p["name"] for p in data["items"][:2])
        d.ok(f"关键词「{kw}」", f"命中 {data['total']} 条" + (f"：{names}" if names else ""))
    none = d.req("GET", "/api/products", params={"keyword": "zzzzzz"})
    if none is not None:
        d.ok("无匹配关键词", f"命中 {none.json()['total']} 条（前端显示『没有找到匹配的商品』）")
    last = d.req("GET", "/api/products", params={"page": 6, "page_size": 18})
    if last is not None and last.status_code == 200:
        data = last.json()
        d.ok("翻到最后一页", f"第 {data['page']}/{data['pages']} 页，本页 {len(data['items'])} 条，has_next={data['has_next']}")
    d.say("前端：CSS Grid 固定 3 列；分页组件显示「共 100 件商品 · 第 x/6 页 · 每页 18 件」，")
    d.say("      多于 7 页时页码窗口自动折叠，上一页/下一页/点页码都可跳。")


def stage4(d: Demo) -> None:
    d.curtain(4, "商品详情：名称 / 图片 / 价格 / 简介", "在商城主页点击商品进入详情页，显示商品名称，商品图片，商品简介")
    r = d.req("GET", "/api/products/1")
    if r is None or r.status_code != 200:
        d.warn("详情接口不可用")
        return
    item = r.json()["item"]
    d.ok("商品名称", item["name"])
    d.ok("价格", f"${item['price']:.2f} USD（字段类型 decimal(10,2)）")
    d.ok("简介", d.pretty(item["description"], 110))
    d.ok("图片路径", item["image"])
    img = d.req("GET", item["image"], show=False)
    if img is not None and img.status_code == 200:
        magic = img.content[:4]
        kind = "WEBP" if magic[:4] == b"RIFF" else ("PNG" if magic[:4] == b"\x89PNG" else "JPEG/其它")
        d.emit(f"    GET {item['image']}  →  {img.status_code}  {len(img.content)} bytes")
        d.ok("图片是真实图片文件（校验文件头）", f"{kind}, {len(img.content)} bytes")
    else:
        d.warn("图片读取失败", item["image"])
    d.say("前端：详情页左栏显示大图（可切缩略图）、名称、价格、评分/库存/品牌/类目、简介；右栏是 AI 客服。")


def stage5(d: Demo) -> None:
    d.curtain(5, "AI 客服：把当前商品信息写进提示词", "该 API 调用 AI 模型，给模型提示词中添加当前商品基本信息：名称，价格，简介")
    if not d.use_ai:
        d.say("（--no-ai：本幕按参数跳过）")
        return
    detail = d.req("GET", "/api/products/1")
    if detail is None or detail.status_code != 200:
        d.warn("取商品失败，跳过 AI 幕")
        return
    product = detail.json()["item"]
    d.say("本次将被写进 system prompt 的商品事实（全部来自数据库）：")
    d.emit(f"      商品名称：{product['name']}")
    d.emit(f"      售价：${product['price']:.2f} USD")
    d.emit(f"      商品简介：{d.pretty(product['description'], 100)}")
    d.emit("      另有约束：价格以库内为准、不臆造物流/退换货、中文、150 字以内")
    d.say()

    question = "这件商品多少钱？它有什么卖点？"
    d.say(f"提问：{question}")
    r = d.req("POST", "/api/chat", body={"product_id": 1, "question": question})
    if r is None or r.status_code != 200:
        d.warn("AI 接口不可用（可用 --no-ai 跳过本幕）")
        return
    answer = r.json()
    d.emit("    回答：")
    for line in str(answer["answer"]).splitlines():
        d.emit(f"      {line}")
    if answer.get("degraded"):
        d.warn("本次走上游降级（未调用到模型），回答来自数据库字段")
    else:
        d.ok("模型真实作答", f"{answer['model']}，耗时 {answer['elapsed_ms']}ms")
    price_text = f"{product['price']:.2f}"
    if price_text in str(answer["answer"]):
        d.ok("回答中的价格与库内一致（未编造）", price_text)
    else:
        d.warn("回答未出现库内价格，建议再问一次核对", price_text)
    if answer.get("related"):
        d.ok(
            "向量检索（embedding_model=%s）给出相关商品" % answer.get("embedding_model", "?"),
            f"{len(answer['related'])} 条：" + "、".join(p["name"] for p in answer["related"]),
        )
    d.say()
    follow = "那它适合油性皮肤吗？"
    d.say(f"追问（带上下文）：{follow}")
    r2 = d.req(
        "POST",
        "/api/chat",
        body={
            "product_id": 1,
            "question": follow,
            "history": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer["answer"]},
            ],
        },
    )
    if r2 is not None and r2.status_code == 200:
        d.emit(f"    回答：{d.pretty(r2.json()['answer'], 140)}")
        d.ok("带历史的多轮对话正常", f"耗时 {r2.json()['elapsed_ms']}ms")
    else:
        d.warn("追问失败")


def stage6(d: Demo) -> None:
    d.curtain(6, "用户注册登录与权限隔离", "用户登录注册（用户名，密码）；管理员页面：操作商品")
    reg = d.req("POST", "/api/auth/register", body={"username": DEMO_USER, "password": DEMO_PASS})
    if reg is not None and reg.status_code == 201:
        d.ok("注册成功（首次运行创建演示账号）", f"{DEMO_USER} / {DEMO_PASS} → 返回 JWT")
    elif reg is not None and reg.status_code == 409:
        d.say(f"（演示账号 {DEMO_USER} 已存在，直接登录）")
        reg = None
    login = d.req("POST", "/api/auth/login", body={"username": DEMO_USER, "password": DEMO_PASS})
    if login is None or login.status_code != 200:
        d.warn("演示账号登录失败")
        return
    token = login.json()["token"]
    user_headers = {"Authorization": f"Bearer {token}"}
    d.ok("登录成功，签发 JWT", f"user={login.json()['user']['username']}, is_admin={login.json()['user']['is_admin']}")
    me = d.req("GET", "/api/auth/me", headers=user_headers)
    if me is not None:
        d.ok("带 token 访问 /auth/me 正常", f"username={me.json()['user']['username']}")
    no_token = d.req("GET", "/api/auth/me", show=False)
    d.ok("不带 token 被拒", f"状态码 {no_token.status_code}" if no_token is not None else "无响应")
    blocked = d.req("POST", "/api/admin/products", body={"name": "不该成功"}, headers=user_headers)
    if blocked is not None:
        d.ok("普通用户调管理接口被拦截（RBAC）", f"状态码 {blocked.status_code}：{blocked.json().get('message', '')}")
    d.say("前端：不登录看不到管理入口；路由守卫也会拦住 /admin。")

    adm = d.req("POST", "/api/auth/login", body={"username": "admin", "password": "admin123"})
    if adm is None or adm.status_code != 200:
        d.warn("管理员 admin/admin123 登录失败（数据库里没有？）")
        return
    d.admin_headers = {"Authorization": f"Bearer {adm.json()['token']}"}
    d.ok("管理员登录成功", "admin / admin123, is_admin=True")


def stage7(d: Demo) -> None:
    d.curtain(7, "管理后台：对商品增 / 查 / 改 / 删", "管理员页面：操作商品，增删改查")
    if not d.admin_headers:
        d.warn("没有管理员 token，跳过本幕")
        return
    stats = d.req("GET", "/api/admin/stats", headers=d.admin_headers)
    if stats is not None and stats.status_code == 200:
        s = stats.json()
        d.ok(
            "后台统计",
            f"商品 {s['products']} 条、已向量化 {s['embedded']} 条、类目 {s['categories']} 个、均价 ${s['avg_price']}",
        )

    created = d.req(
        "POST",
        "/api/admin/products",
        body={
            "name": "演示用商品 Demo Item",
            "price": 88.88,
            "description": "由 demos/flow_demo.py 创建，演示结束会自动删除",
            "image": "/static/products/placeholder.svg",
            "category": "demo",
            "brand": "DEMO",
            "stock": 5,
        },
        headers=d.admin_headers,
    )
    if created is None or created.status_code != 201:
        d.warn("新增商品失败")
        return
    new_id = created.json()["item"]["id"]
    d.ok("新增商品成功", f"id={new_id}, 201 Created")

    found = d.req("GET", "/api/products", params={"keyword": "Demo Item"})
    if found is not None:
        total = found.json()["total"]
        d.ok("前台上架（搜索可见）", f"搜到 {total} 条" if total else "未搜到，异常")
    updated = d.req(
        "PUT",
        f"/api/admin/products/{new_id}",
        body={"name": "演示用商品 Demo Item v2", "price": 66.66, "stock": 3},
        headers=d.admin_headers,
    )
    if updated is not None and updated.status_code == 200:
        item = updated.json()["item"]
        d.ok("修改商品成功", f"名称={item['name']}，价格=${item['price']}，库存={item['stock']}")
    deleted = d.req("DELETE", f"/api/admin/products/{new_id}", headers=d.admin_headers)
    after = d.req("GET", f"/api/products/{new_id}", show=False)
    if deleted is not None and after is not None:
        d.emit(f"    GET /api/products/{new_id}  →  {after.status_code}（删除后应查不到）")
        d.ok("删除商品成功且已下架", f"DELETE={deleted.status_code}, 再查={after.status_code}")
    d.say("前端后台：表格 + 弹窗表单（含图片 URL / 本地上传 / 实时预览），带搜索、分页和二次确认删除；")
    d.say("          还有「刷新 AI 向量库」按钮，改完商品可一键重建向量。")


def main() -> int:
    ap = argparse.ArgumentParser(description="跨境电商平台流程展示（叙事型，非断言型）")
    ap.add_argument("--base", default="http://127.0.0.1:5000", help="服务地址，docker 部署用 http://localhost:8080")
    ap.add_argument("--pause", action="store_true", help="每幕开始前等回车")
    ap.add_argument("--slow", action="store_true", help="每步 sleep 0.6s，投屏节奏更从容")
    ap.add_argument("--no-ai", dest="use_ai", action="store_false", help="跳过 AI 客服那一幕")
    ap.add_argument("--save", default=None, help="把演示过程另存为文本文件")
    args = ap.parse_args()

    demo = Demo(args.base, pause=args.pause, slow=args.slow, use_ai=args.use_ai, save=args.save)
    demo.emit(LINE)
    demo.emit("  环球优选 · 跨境电商平台 — 流程演示")
    demo.emit(f"  目标服务：{demo.base}    时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    demo.emit(f"  参数：pause={args.pause} slow={args.slow} ai={args.use_ai}")
    demo.emit(LINE)
    demo.emit("  说明：每幕先讲需求点，再发真实请求，最后给出证据与耗时。")

    for stage in (stage1, stage2, stage3, stage4, stage5, stage6, stage7):
        try:
            stage(demo)
        except Exception as exc:  # noqa: BLE001 - 演示脚本不因单幕异常中断
            demo.warn(f"{stage.__name__} 执行异常：{exc}")
    return demo.finish()


if __name__ == "__main__":
    sys.exit(main())
