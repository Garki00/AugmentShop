"""Fetch ~100 real product records + their images from DummyJSON.

Source: https://dummyjson.com/products (open API, real product dataset with images).
Output:
  backend/seed/products.json            - 100 product records (id, title, price, description, ...)
  backend/static/products/<id>.webp     - image files, served by Flask at /static/products/<id>.webp

Run:  python fetch_seed.py [--count 100]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request

API = "https://dummyjson.com/products"
UA = "kjds-demo-seed/1.0"
HERE = pathlib.Path(__file__).resolve().parent
IMG_DIR = HERE.parent / "static" / "products"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(url: str, dest: pathlib.Path) -> bool:
    if dest.exists() and dest.stat().st_size > 512:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 512:
            return False
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001 - demo seed script, keep going
        print(f"  ! image failed {url}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100)
    args = ap.parse_args()

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    raw = get_json(f"{API}?limit={args.count}&skip=0")["products"]
    print(f"fetched {len(raw)} products from dummyjson")

    records, local_ok = [], 0
    for p in raw:
        pid = int(p["id"])
        remote = p.get("thumbnail") or (p.get("images") or [""])[0]
        ext = pathlib.Path(remote.split("?")[0]).suffix or ".webp"
        fname = f"{pid}{ext}"
        if download(remote, IMG_DIR / fname):
            local_ok += 1
            image = f"/static/products/{fname}"
        else:
            image = remote
        records.append(
            {
                "id": pid,
                "name": p["title"],
                "price": float(p["price"]),
                "description": p.get("description", ""),
                "image": image,
                "image_remote": remote,
                "category": p.get("category", ""),
                "brand": p.get("brand", "") or "",
                "rating": float(p.get("rating", 0) or 0),
                "stock": int(p.get("stock", 0) or 0),
            }
        )

    out = HERE / "products.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(records)} records), {local_ok} images stored locally in {IMG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
