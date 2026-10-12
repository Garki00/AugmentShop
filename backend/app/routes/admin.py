"""Admin CRUD for products (create / read / update / delete) + image upload."""
from __future__ import annotations

import pathlib
import uuid

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from ..models import Product, db
from ..security import admin_required
from . import paginate

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
PLACEHOLDER = "/static/products/placeholder.svg"
NUM_FIELDS = {"price": float, "stock": int, "rating": float}
TEXT_FIELDS = ("name", "image", "image_remote", "description", "category", "brand")


def _num(value, caster, default):
    try:
        return caster(value)
    except (TypeError, ValueError):
        return default


def _apply(product: Product, data: dict) -> Product:
    """Write a request payload onto a product, clearing the cached embedding if needed."""
    text_changed = False
    for field in TEXT_FIELDS:
        if field in data and data[field] is not None:
            new_value = str(data[field]).strip()
            if field in ("name", "description") and getattr(product, field) != new_value:
                text_changed = True
            setattr(product, field, new_value)
    for field, caster in NUM_FIELDS.items():
        if field in data and data[field] not in ("", None):
            setattr(product, field, _num(data[field], caster, getattr(product, field) or 0))
    if not product.image:
        product.image = product.image_remote or PLACEHOLDER
    if text_changed:
        product.embedding = None  # name/description changed -> re-embed
    return product


@bp.get("/products")
@admin_required
def list_products():
    keyword = (request.args.get("keyword") or "").strip()
    page = max(1, request.args.get("page", type=int) or 1)
    page_size = min(max(1, request.args.get("page_size", type=int) or 20), 100)
    query = Product.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(Product.name.ilike(like) | Product.brand.ilike(like) | Product.category.ilike(like))
    total = query.count()
    rows = query.order_by(Product.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return jsonify(paginate([p.to_dict() for p in rows], total, page, page_size))


@bp.post("/products")
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "bad_request", "message": "商品名不能为空"}), 400
    product = Product(name=name, price=0, image="", image_remote="", description="")
    _apply(product, data)
    db.session.add(product)
    db.session.commit()
    return jsonify({"item": product.to_dict()}), 201


@bp.put("/products/<int:product_id>")
@admin_required
def update_product(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify({"error": "not_found", "message": "商品不存在"}), 404
    _apply(product, request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify({"item": product.to_dict()})


@bp.delete("/products/<int:product_id>")
@admin_required
def delete_product(product_id: int):
    product = db.session.get(Product, product_id)
    if product is None:
        return jsonify({"error": "not_found", "message": "商品不存在"}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({"ok": True, "deleted_id": product_id})


@bp.post("/upload")
@admin_required
def upload_image():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "bad_request", "message": "请选择图片文件"}), 400
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify({"error": "bad_type", "message": f"仅支持 {', '.join(sorted(ALLOWED_IMAGE_EXT))}"}), 400
    target_dir = pathlib.Path(current_app.config["UPLOAD_DIR"])
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(target_dir / filename)
    return jsonify({"url": f"/static/uploads/{filename}"}), 201


@bp.get("/stats")
@admin_required
def stats():
    total = db.session.query(func.count(Product.id)).scalar()
    avg_price = db.session.query(func.avg(Product.price)).scalar() or 0
    embedded = db.session.query(func.count(Product.id)).filter(Product.embedding.isnot(None)).scalar()
    categories = db.session.query(func.count(func.distinct(Product.category))).scalar()
    return jsonify(
        {
            "products": total,
            "embedded": embedded,
            "categories": categories,
            "avg_price": round(float(avg_price), 2),
        }
    )


@bp.post("/embeddings/refresh")
@admin_required
def refresh_embeddings():
    """Re-embed products with Qwen3-Embedding-8B (used by the AI 客服)."""
    from ..services.rag import ensure_embeddings

    client = current_app.extensions["ai_client"]
    count = ensure_embeddings(client, force=bool((request.get_json(silent=True) or {}).get("force")))
    return jsonify({"embedded": count, "model": client.embed_model})
