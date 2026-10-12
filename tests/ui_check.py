"""Headless-Chrome UI check for the Vue storefront.

Drives the real app over the Chrome DevTools Protocol: loads the home page,
searches, paginates, opens a product, talks to the AI 客服 in the chat panel,
logs in as admin, creates a product in the admin table and deletes it again.
Screenshots land in docs/screenshots/.

    python tests/ui_check.py                     # app at http://127.0.0.1:5173
    UI_BASE=http://127.0.0.1:5173 python tests/ui_check.py
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

UI_BASE = os.getenv("UI_BASE", "http://127.0.0.1:5173").rstrip("/")
PORT = int(os.getenv("CDP_PORT", "9333"))
ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

results: list[tuple[bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((bool(ok), name))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -> {detail}" if detail else ""))


def find_browser() -> str:
    env = os.getenv("BROWSER_PATH")
    if env and pathlib.Path(env).exists():
        return env
    for path in CHROME_CANDIDATES:
        if pathlib.Path(path).exists():
            return path
    raise SystemExit("no Chrome/Edge found; set BROWSER_PATH")


class CDP:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.id = 0

    def send(self, method: str, **params):
        self.id += 1
        self.ws.send(json.dumps({"id": self.id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expression: str):
        r = self.send("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        return r.get("result", {}).get("value")

    def wait_for(self, expression: str, *, timeout: float = 20, label: str = "") -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.js(expression):
                    return True
            except Exception:  # noqa: BLE001 - page may still be navigating
                pass
            time.sleep(0.4)
        print(f"    (timeout waiting for {label or expression})")
        return False

    def type_into(self, selector: str, text: str) -> bool:
        ok = self.js(
            f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
            f" if (!el) return false; el.focus(); el.select && el.select(); return true; }})()"
        )
        if not ok:
            return False
        self.send("Input.insertText", text=text)
        return True

    def click(self, selector: str) -> bool:
        return bool(
            self.js(
                f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
                f" if (!el) return false; el.click(); return true; }})()"
            )
        )

    def shot(self, name: str, *, full: bool = True) -> str:
        SHOTS.mkdir(parents=True, exist_ok=True)
        data = self.send("Page.captureScreenshot", format="png", captureBeyondViewport=full)
        path = SHOTS / f"{name}.png"
        path.write_bytes(base64.b64decode(data["data"]))
        print(f"    screenshot: {path}")
        return str(path)

    def goto(self, url: str, ready: str | None = None, timeout: float = 25) -> bool:
        self.send("Page.navigate", url=url)
        self.wait_for("document.readyState === 'complete'", timeout=timeout, label="load")
        if ready:
            return self.wait_for(ready, timeout=timeout, label=ready)
        return True


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    print(f"using browser: {browser}")

    profile = tempfile.mkdtemp(prefix="kjds-ui-")
    proc = subprocess.Popen(
        [
            browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--hide-scrollbars", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
            "--window-size=1440,1200", "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ws_url = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=2) as r:
                    targets = json.loads(r.read())
                pages = [t for t in targets if t.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)
        if not ws_url:
            check("headless browser started", False, "CDP endpoint never came up")
            return 1

        cdp = CDP(ws_url)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")

        # ---------- 商城主页 ----------
        ok = cdp.goto(UI_BASE + "/", ready="document.querySelectorAll('.grid .pcard').length === 18")
        cards = cdp.js("document.querySelectorAll('.grid .pcard').length")
        check("home page renders 18 product cards (3 cols x 6 rows)", ok, f"cards={cards}")

        dots = cdp.js("document.querySelectorAll('.hero .dot').length")
        rec_price = cdp.js("document.querySelector('.hero .price.big')?.textContent?.trim() || ''")
        check("recommend block shows a 5-item rotating carousel", dots == 5 and "$" in rec_price,
              f"dots={dots} price={rec_price}")

        rotated = cdp.js(
            "(() => { const before = document.querySelector('.hero .info h3').textContent;"
            " document.querySelectorAll('.hero .dot')[2].click();"
            " return new Promise(r => setTimeout(() => r(document.querySelector('.hero .info h3').textContent !== before), 400)); })()"
        )
        check("carousel rotates between the 5 drawn products", bool(rotated))

        first_rec = cdp.js("document.querySelector('.hero .info h3').textContent.trim()")
        cdp.click(".reroll")
        time.sleep(2.5)
        cdp.wait_for("document.querySelector('.hero .info h3') !== null")
        second_rec = cdp.js("document.querySelector('.hero .info h3').textContent.trim()")
        check("“换一批” re-draws a different set", bool(second_rec) and second_rec != first_rec,
              f"{first_rec} -> {second_rec}")
        check("search box sits below the recommend block",
              bool(cdp.js("(() => { const s = document.querySelector('.searchbar input');"
                          " const h = document.querySelector('.hero'); return !!s && s.getBoundingClientRect().top > h.getBoundingClientRect().bottom; })()")))
        check("pagination reports the full 100-product catalogue",
              "100" in (cdp.js("document.querySelector('.pager .info')?.textContent || ''") or ""),
              cdp.js("document.querySelector('.pager .info')?.textContent?.trim()"))
        cdp.shot("01-home")

        # ---------- 搜索 ----------
        cdp.type_into(".searchbar input", "mascara")
        cdp.click(".searchbar button[type=submit]")
        cdp.wait_for("document.querySelectorAll('.grid .pcard').length === 1", label="search result")
        hits = cdp.js("document.querySelectorAll('.grid .pcard').length")
        title = cdp.js("document.querySelector('.list-head h3').textContent.trim()")
        check("keyword search filters the grid", hits == 1 and "搜索结果" in title, f"{title} -> {hits} 件")
        cdp.shot("02-search")

        cdp.click(".searchbar button.ghost")
        cdp.wait_for("document.querySelectorAll('.grid .pcard').length === 18", label="reset list")
        check("clearing the keyword restores the full list",
              cdp.js("document.querySelectorAll('.grid .pcard').length") == 18)

        # ---------- 分页 ----------
        cdp.js("[...document.querySelectorAll('.pager .pages button')].find(b => b.textContent.trim() === '6').click()")
        ok = cdp.wait_for(
            "(() => { const i = document.querySelector('.pager .info');"
            " return document.querySelectorAll('.grid .pcard').length === 10 && i && i.textContent.includes('第 6/6 页'); })()",
            timeout=20, label="page 6",
        )
        check("pagination jumps to page 6 and shows the last 10 products", ok,
              cdp.js("document.querySelector('.pager .info')?.textContent?.trim()"))

        cdp.js("(() => { const b = [...document.querySelectorAll('.pager .pages button')]"
               ".find(x => x.textContent.trim() === '上一页'); b.click(); return true; })()")
        ok = cdp.wait_for("document.querySelectorAll('.grid .pcard').length === 18", timeout=20, label="page 5")
        check("“上一页” walks back one page", ok, cdp.js("document.querySelector('.pager .info')?.textContent?.trim()"))

        # ---------- 详情页 + AI 客服 ----------
        cdp.js("document.querySelectorAll('.pager .pages button')[0].click()")  # 回到第 1 页
        cdp.wait_for("document.querySelectorAll('.grid .pcard').length === 18", label="page 1")
        cdp.click(".grid .pcard")
        ok = cdp.wait_for("!!document.querySelector('.detail h1')", timeout=20, label="detail page")
        name = cdp.js("document.querySelector('.detail h1').textContent.trim()")
        price = cdp.js("document.querySelector('.detail .price.big').textContent.trim()")
        desc = cdp.js("document.querySelector('.detail .desc').textContent.trim()")
        check("clicking a card opens the detail page with name/price/description",
              ok and bool(name) and "$" in price and len(desc) > 20, f"{name} / {price}")
        check("AI 客服 panel is rendered next to the product info",
              bool(cdp.js("!!document.querySelector('.chat .composer input')")))
        cdp.shot("03-detail")

        cdp.click(".quick button")
        ok = cdp.wait_for(
            "(() => { const b = document.querySelectorAll('.msg.assistant .bubble');"
            " return b.length > 0 && b[b.length-1].textContent.trim().length > 15; })()",
            timeout=90, label="ai first answer",
        )
        answer1 = cdp.js("[...document.querySelectorAll('.msg.assistant .bubble')].at(-1).textContent.trim()")
        meta1 = cdp.js("[...document.querySelectorAll('.msg.assistant .bubble')].at(-1)?.parentElement?.querySelector('.meta')?.textContent?.trim() || ''")
        check("AI 客服 answers a quick question", ok, answer1[:90])
        price_num = re.search(r"[\d.]+", price).group(0).rstrip(".")
        check("answer is grounded in the real price from the DB",
              f"{float(price_num):.2f}" in answer1.replace(",", ""),
              f"price={price_num} -> answer says: {answer1[:60]}")
        check("answer footer shows the model + retrieval info", "Qwen" in meta1 or "ms" in meta1, meta1)

        cdp.type_into(".composer input", "它适合油性皮肤吗？")
        cdp.click(".composer button[type=submit]")
        ok = cdp.wait_for(
            "document.querySelectorAll('.msg.assistant .bubble').length >= 2",
            timeout=90, label="ai follow-up answer",
        )
        answer2 = cdp.js("[...document.querySelectorAll('.msg.assistant .bubble')].at(-1).textContent.trim()")
        check("a typed follow-up question gets an answer", ok, answer2[:90])
        chips = cdp.js("document.querySelectorAll('.related .chip').length")
        check("retrieved related products are shown as chips", chips >= 1, f"chips={chips}")
        cdp.shot("04-detail-chat")

        # ---------- 登录 + 管理后台 ----------
        cdp.goto(UI_BASE + "/login", ready="!!document.querySelector('.form input')")
        cdp.type_into(".form input", "admin")
        cdp.type_into(".form input[type=password]", "admin123")
        cdp.click(".form button[type=submit]")
        ok = cdp.wait_for("!!document.querySelector('.account .who')", timeout=20, label="logged in")
        check("admin logs in from the UI", ok, cdp.js("document.querySelector('.account .who')?.textContent?.trim()"))

        cdp.goto(UI_BASE + "/admin", ready="document.querySelectorAll('tbody tr').length > 0")
        rows = cdp.js("document.querySelectorAll('tbody tr').length")
        stats = cdp.js("[...document.querySelectorAll('.stat b')].map(e => e.textContent.trim()).join(' / ')")
        check("admin table lists products", rows == 20, f"rows={rows}")
        check("admin stat cards show catalogue numbers", "100" in stats, stats)
        cdp.shot("05-admin")

        # 新增
        cdp.click(".head button:not(.ghost)")
        cdp.wait_for("!!document.querySelector('.modal')", label="modal")
        cdp.type_into(".modal .fields input", "UI 冒烟测试商品")
        cdp.type_into(".modal .fields input[type=number]", "88.88")
        cdp.js("(() => { const t = document.querySelector('.modal .fields textarea');"
               " t.focus(); return true; })()")
        cdp.send("Input.insertText", text="由 UI 自动化测试创建的商品简介")
        cdp.click(".modal footer button:not(.ghost)")
        ok = cdp.wait_for("!document.querySelector('.modal')", timeout=20, label="modal closed")
        check("admin creates a product through the modal", ok)
        cdp.type_into(".toolbar input", "UI 冒烟测试商品")
        cdp.click(".toolbar button[type=submit]")
        ok = cdp.wait_for(
            "document.querySelectorAll('tbody tr').length === 1 && document.querySelector('tbody tr').textContent.includes('UI 冒烟测试商品')",
            timeout=20, label="created row",
        )
        check("created product shows up in the admin table", ok, cdp.js("document.querySelector('tbody tr')?.textContent?.replace(/\\s+/g,' ').trim()[:120]"))
        cdp.shot("06-admin-created")

        # 编辑
        cdp.click("tbody tr button.ghost")
        cdp.wait_for("!!document.querySelector('.modal')", label="edit modal")
        cdp.type_into(".modal .fields input", "UI 冒烟测试商品 v2")
        cdp.click(".modal footer button:not(.ghost)")
        ok = cdp.wait_for("!document.querySelector('.modal')", timeout=20, label="edit saved")
        row_text = cdp.js("document.querySelector('tbody tr')?.textContent || ''")
        check("admin edits the product name", "v2" in row_text, row_text.replace("\n", " ")[:80])

        # 删除
        cdp.js("window.confirm = () => true")
        cdp.click("tbody tr button.danger")
        ok = cdp.wait_for(
            "!document.body.textContent.includes('UI 冒烟测试商品') || document.querySelectorAll('tbody tr').length === 0",
            timeout=20, label="row gone",
        )
        check("admin deletes the product", ok)
        remain = cdp.js("document.querySelectorAll('tbody tr').length")
        print(f"    remaining rows after delete: {remain}")
        cdp.shot("07-admin-after-delete")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)

    failed = [n for ok, n in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} UI checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
