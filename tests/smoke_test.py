"""End-to-end smoke test for the kjds backend.

    python tests/smoke_test.py                     # against http://127.0.0.1:5000
    BASE=http://127.0.0.1:5000 python tests/smoke_test.py

Covers: health, pagination, keyword search, recommend randomness, detail, static
images, register/login/me, admin CRUD + upload + RBAC, and the AI 客服 chat
(real SiliconFlow call). Prints PASS/FAIL per case and exits non-zero on failure.
"""
from __future__ import annotations

import os
import sys
import uuid

import requests

BASE = os.getenv("BASE", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = 150
results: list[tuple[bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((bool(condition), name))
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"  -> {detail}" if detail else ""))


def main() -> int:
    s = requests.Session()

    # 1. health
    r = s.get(f"{BASE}/api/health", timeout=TIMEOUT)
    h = r.json()
    check("health 200 + db up", r.status_code == 200 and h["database"] == "up", str(h["dialect"]))
    check("ai models configured", h["ai"]["embed_key_configured"] and h["ai"]["chat_key_configured"],
          f'{h["ai"]["embed_model"]} / {h["ai"]["chat_model"]}')

    # 2. pagination: 100 products, 18 per page
    r = s.get(f"{BASE}/api/products", params={"page": 1, "page_size": 18}, timeout=TIMEOUT).json()
    check("catalogue has 100 products, 18/page, 6 pages",
          r["total"] == 100 and len(r["items"]) == 18 and r["pages"] == 6,
          f'total={r["total"]} pages={r["pages"]}')
    check("all list items carry name+image+price",
          all(p["name"] and p["image"] and isinstance(p["price"], (int, float)) for p in r["items"]))
    last = s.get(f"{BASE}/api/products", params={"page": 6, "page_size": 18}, timeout=TIMEOUT).json()
    check("last page returns remaining 10 items", len(last["items"]) == 10 and last["has_next"] is False)

    # 3. keyword search
    kw = s.get(f"{BASE}/api/products", params={"keyword": "mascara"}, timeout=TIMEOUT).json()
    check("keyword 'mascara' hits", kw["total"] >= 1 and all("mascara" in i["name"].lower() for i in kw["items"]),
          f'total={kw["total"]}')
    kw2 = s.get(f"{BASE}/api/products", params={"keyword": "laptop"}, timeout=TIMEOUT).json()
    check("keyword 'laptop' hits category text", kw2["total"] >= 1, f'total={kw2["total"]}')
    none = s.get(f"{BASE}/api/products", params={"keyword": "zzzzzz"}, timeout=TIMEOUT).json()
    check("unknown keyword -> empty list", none["total"] == 0 and none["items"] == [])

    # 4. recommend: random 5, different across calls
    a = s.get(f"{BASE}/api/products/recommend", params={"limit": 5}, timeout=TIMEOUT).json()["items"]
    b = s.get(f"{BASE}/api/products/recommend", params={"limit": 5}, timeout=TIMEOUT).json()["items"]
    check("recommend returns 5 distinct products", len(a) == 5 and len({p["id"] for p in a}) == 5)
    check("recommend re-draws on each call", [p["id"] for p in a] != [p["id"] for p in b],
          f'{[p["id"] for p in a]} vs {[p["id"] for p in b]}')

    # 5. detail + static image
    one = s.get(f"{BASE}/api/products/1", timeout=TIMEOUT).json()["item"]
    check("detail has name/price/description/image",
          all([one["name"], one["description"], one["image"]]), f'{one["name"]} ${one["price"]}')
    img = s.get(f"{BASE}{one['image']}", timeout=TIMEOUT)
    check("product image served (>1KB)", img.status_code == 200 and len(img.content) > 1024,
          f'{len(img.content)} bytes')
    check("product image is a real image file",
          img.content[:4] in (b"RIFF", b"\xff\xd8\xff\x89", b"\x89PNG") or img.content[:2] == b"\xff\xd8",
          img.content[:12].hex())

    # 6. register / login / me
    username = f"tester_{uuid.uuid4().hex[:8]}"
    reg = s.post(f"{BASE}/api/auth/register", json={"username": username, "password": "secret123"}, timeout=TIMEOUT)
    check("register returns 201 + token", reg.status_code == 201 and reg.json().get("token"), username)
    dup = s.post(f"{BASE}/api/auth/register", json={"username": username, "password": "secret123"}, timeout=TIMEOUT)
    check("duplicate username rejected (409)", dup.status_code == 409)
    bad = s.post(f"{BASE}/api/auth/register", json={"username": "ab", "password": "1"}, timeout=TIMEOUT)
    check("weak username/password rejected (400)", bad.status_code == 400)
    badlogin = s.post(f"{BASE}/api/auth/login", json={"username": username, "password": "wrong"}, timeout=TIMEOUT)
    check("wrong password rejected (401)", badlogin.status_code == 401)

    login = s.post(f"{BASE}/api/auth/login", json={"username": username, "password": "secret123"}, timeout=TIMEOUT).json()
    user_headers = {"Authorization": f"Bearer {login['token']}"}
    me = s.get(f"{BASE}/api/auth/me", headers=user_headers, timeout=TIMEOUT)
    check("login + /auth/me round trip", me.status_code == 200 and me.json()["user"]["username"] == username)
    check("no token -> 401", s.get(f"{BASE}/api/auth/me", timeout=TIMEOUT).status_code == 401)

    # 7. RBAC: normal user cannot touch the admin API
    forbidden = s.post(f"{BASE}/api/admin/products", json={"name": "hack"}, headers=user_headers, timeout=TIMEOUT)
    check("normal user blocked from admin API (403)", forbidden.status_code == 403)

    # 8. admin login + CRUD
    adm = s.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"}, timeout=TIMEOUT)
    check("admin/admin123 logs in", adm.status_code == 200 and adm.json()["user"]["is_admin"] is True)
    admin_headers = {"Authorization": f"Bearer {adm.json()['token']}"}

    stats = s.get(f"{BASE}/api/admin/stats", headers=admin_headers, timeout=TIMEOUT).json()
    check("admin stats reachable", stats["products"] >= 100, str(stats))

    created = s.post(
        f"{BASE}/api/admin/products",
        json={"name": "Smoke Test Widget", "price": 12.34, "description": "created by smoke test",
              "image": "/static/products/placeholder.svg", "category": "test", "brand": "SMOKE", "stock": 7},
        headers=admin_headers, timeout=TIMEOUT,
    )
    check("admin create product (201)", created.status_code == 201)
    new_id = created.json()["item"]["id"]

    updated = s.put(
        f"{BASE}/api/admin/products/{new_id}",
        json={"name": "Smoke Test Widget v2", "price": 99.99, "stock": 3},
        headers=admin_headers, timeout=TIMEOUT,
    ).json()["item"]
    check("admin update product", updated["name"] == "Smoke Test Widget v2" and float(updated["price"]) == 99.99,
          f'${updated["price"]} stock={updated["stock"]}')

    searched = s.get(f"{BASE}/api/products", params={"keyword": "Smoke Test Widget"}, timeout=TIMEOUT).json()
    check("updated product visible in public search", searched["total"] == 1 and searched["items"][0]["id"] == new_id)

    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
           b"\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    up = s.post(f"{BASE}/api/admin/upload", files={"file": ("t.png", png, "image/png")}, headers=admin_headers,
                timeout=TIMEOUT)
    check("admin image upload (201)", up.status_code == 201 and up.json()["url"].startswith("/static/uploads/"),
          up.json().get("url", ""))
    up_url = up.json()["url"]
    check("uploaded image is served back", s.get(f"{BASE}{up_url}", timeout=TIMEOUT).status_code == 200)

    deleted = s.delete(f"{BASE}/api/admin/products/{new_id}", headers=admin_headers, timeout=TIMEOUT)
    after = s.get(f"{BASE}/api/products/{new_id}", timeout=TIMEOUT)
    check("admin delete product -> 404 afterwards",
          deleted.status_code == 200 and after.status_code == 404)

    # 9. AI 客服
    print("\n... calling the AI 客服 (Qwen3-Embedding retrieval + Qwen2.5 chat), this can take ~30s")
    res = s.post(f"{BASE}/api/chat", json={"product_id": 1, "question": "这件商品多少钱？它有什么卖点？"}, timeout=TIMEOUT)
    body = res.json()
    check("chat endpoint 200", res.status_code == 200)
    check("chat answered, not degraded", not body.get("degraded"), f'{body.get("model")} in {body.get("elapsed_ms")}ms')
    check("answer mentions the real price", "9.99" in body.get("answer", ""), body.get("answer", "")[:160])
    check("answer is Chinese prose", len(body.get("answer", "")) > 20)
    check("embedding retrieval produced related products", len(body.get("related", [])) == 3,
          str([p["name"] for p in body.get("related", [])]))
    stats2 = s.get(f"{BASE}/api/admin/stats", headers=admin_headers, timeout=TIMEOUT).json()
    check("catalogue embedded with Qwen3-Embedding-8B", stats2["embedded"] >= 100, f'embedded={stats2["embedded"]}')

    history = [{"role": "user", "content": "这件商品多少钱？"}, {"role": "assistant", "content": body["answer"]}]
    res2 = s.post(f"{BASE}/api/chat", json={"product_id": 1, "question": "那适合油性皮肤吗？", "history": history},
                  timeout=TIMEOUT).json()
    check("follow-up question answered with history", not res2.get("degraded") and len(res2["answer"]) > 10,
          res2["answer"][:120])
    check("chat without question -> 400", s.post(f"{BASE}/api/chat", json={"product_id": 1}, timeout=TIMEOUT).status_code == 400)
    check("chat with bad product -> 404", s.post(f"{BASE}/api/chat", json={"product_id": 99999, "question": "hi"},
                                                 timeout=TIMEOUT).status_code == 404)

    failed = [n for ok, n in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
