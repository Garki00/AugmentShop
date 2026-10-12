"""Load the 100-product seed catalogue and the demo admin account."""
from __future__ import annotations

import json
import logging
import pathlib

from ..models import Product, User, db

log = logging.getLogger(__name__)

# Demo admin account, created on first boot.
ADMIN = ("admin", "admin123")


def seed_admin() -> bool:
    username, password = ADMIN
    if User.query.filter_by(username=username).first():
        return False
    user = User(username=username, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log.info("seeded admin user %s", username)
    return True


def seed_products(seed_file: str, *, reset: bool = False) -> int:
    """Insert products from the JSON dump; skips ids that already exist."""
    path = pathlib.Path(seed_file)
    if not path.exists():
        log.warning("seed file missing: %s", path)
        return 0
    records = json.loads(path.read_text(encoding="utf-8"))
    if reset:
        Product.query.delete()
        db.session.commit()

    existing = {pid for (pid,) in db.session.query(Product.id).all()}
    added = 0
    for rec in records:
        if rec["id"] in existing:
            continue
        db.session.add(
            Product(
                id=rec["id"],
                name=rec["name"],
                price=rec["price"],
                image=rec.get("image", ""),
                image_remote=rec.get("image_remote", ""),
                description=rec.get("description", ""),
                category=rec.get("category", ""),
                brand=rec.get("brand", ""),
                rating=rec.get("rating", 0),
                stock=rec.get("stock", 0),
            )
        )
        added += 1
    if added:
        db.session.commit()
        log.info("seeded %d products", added)
    return added


def run_startup_seed(app) -> None:
    seed_admin()
    if app.config.get("SEED_ON_START", "1") in ("1", 1, True, "true", "True"):
        total = db.session.query(Product.id).count()
        if total < 100:
            seed_products(app.config["SEED_FILE"])
