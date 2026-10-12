"""Retrieval-Augmented generation helpers built on Qwen3-Embedding-8B.

The embedding model is used to (1) cache a vector per product and (2) embed the
shopper's question, so the chat prompt always carries the most relevant products
next to the product currently being viewed.
"""
from __future__ import annotations

import logging

from ..models import Product, db
from .ai import AIClient, cosine

log = logging.getLogger(__name__)

_CACHE: dict[int, int] = {}  # product id -> dimension, only for logging/debug


def ensure_embeddings(client: AIClient, *, force: bool = False) -> int:
    """Batch-embed every product that has no cached vector yet. Returns count embedded."""
    query = Product.query
    if not force:
        query = query.filter(db.or_(Product.embedding.is_(None), Product.embedding == ""))
    pending = query.all()
    if not pending:
        return 0

    batch = 16
    done = 0
    for start in range(0, len(pending), batch):
        chunk = pending[start : start + batch]
        vectors = client.embed([p.embedding_text() for p in chunk])
        if not vectors:
            break  # API unavailable - keep going without vectors
        for product, vector in zip(chunk, vectors):
            product.set_embedding(vector)
            _CACHE[product.id] = len(vector)
            done += 1
        db.session.commit()
    if done:
        log.info("embedded %d products with %s", done, client.embed_model)
    return done


def related_products(client: AIClient, product: Product, limit: int = 3) -> tuple[list[Product], bool]:
    """Top-N most similar *other* products for the current one.

    Returns (products, used_embeddings). Falls back to same-category picks when the
    embedding API is unavailable.
    """
    target = product.get_embedding()
    if target:
        others = Product.query.filter(Product.id != product.id).all()
        scored = []
        for other in others:
            vector = other.get_embedding()
            if vector:
                scored.append((cosine(target, vector), other))
        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in scored[:limit]], True
    # fallback: same category, then anything
    pool = (
        Product.query.filter(Product.id != product.id, Product.category == product.category)
        .limit(limit)
        .all()
    )
    if len(pool) < limit:
        extra = Product.query.filter(Product.id != product.id).limit(limit * 2).all()
        seen = {p.id for p in pool}
        pool.extend([p for p in extra if p.id not in seen][: limit - len(pool)])
    return pool[:limit], False
