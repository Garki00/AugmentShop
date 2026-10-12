"""Public (shopper-facing) product endpoints."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, or_

from ..models import Product, db
from . import paginate

bp = Blueprint("products", __name__, url_prefix="/api/products")

SHORT_DESC = 90


def _short(product: dict) -> dict:
    if len(product.get("description", "")) > SHORT_DESC:
        product["description"] = product["description"][:SHORT_DESC] + "…"
    return product


@bp.get("")
def list_products():
    """GET /api/products?keyword=&page=1&page_size=18 — empty keyword returns the whole catalogue."""
    keyword = (request.args.get("keyword") or "").strip()
    page = max(1, request.args.get("page", type=int) or 1)
    page_size = request.args.get("page_size", type=int) or current_app.config["PAGE_SIZE_DEFAULT"]
    page_size = max(1, min(page_size, current_app.config["PAGE_SIZE_MAX"]))

    query = Product.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
                Product.brand.ilike(like),
                Product.category.ilike(like),
            )
        )
    total = query.count()
    rows = query.order_by(Product.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    payload = paginate([_short(p.to_dict()) for p in rows], total, page, page_size)
    payload["keyword"] = keyword
    return jsonify(payload)


@bp.get("/recommend")
def recommend():
    """GET /api/products/recommend?limit=5 — random 5, re-drawn on every page load."""
    limit = max(1, min(request.args.get("limit", type=int) or current_app.config["RECOMMEND_LIMIT"], 20))
    rows = Product.query.order_by(func.random()).limit(limit).all()
    return jsonify({"items": [p.to_dict(full=False) for p in rows], "count": len(rows)})


@bp.get("/categories")
def categories():
    rows = (
        db.session.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    return jsonify({"items": [{"category": c or "uncategorized", "count": n} for c, n in rows]})


@bp.get("/<int:product_id>")
def detail(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify({"error": "not_found", "message": "商品不存在"}), 404
    return jsonify({"item": product.to_dict()})
