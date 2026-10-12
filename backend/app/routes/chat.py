"""AI customer-service endpoint for the product detail page.

Flow per request:
  1. load the product the shopper is looking at;
  2. embed the question with Qwen3-Embedding-8B and pick the most similar products
     (retrieval);
  3. send the product record + retrieved products + the conversation to
     Qwen2.5-7B-Instruct and return the answer.
"""
from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request

from ..models import Product, db
from ..services.ai import AIClient
from ..services.rag import ensure_embeddings, related_products

bp = Blueprint("chat", __name__, url_prefix="/api")

MAX_HISTORY = 8


@bp.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    product_id = data.get("product_id")

    if not question:
        return jsonify({"error": "bad_request", "message": "请输入问题"}), 400
    product = db.session.get(Product, int(product_id)) if product_id else None
    if product is None:
        return jsonify({"error": "not_found", "message": "商品不存在"}), 404

    client: AIClient = current_app.extensions["ai_client"]
    started = time.perf_counter()

    # (2) retrieval with the embedding model
    embedded_now = ensure_embeddings(client)  # no-op once the catalogue is embedded
    related, embedding_used = related_products(client, product, limit=3)

    # (3) grounded answer
    history = [
        {"role": m.get("role"), "content": str(m.get("content", ""))[:1000]}
        for m in (data.get("history") or [])
        if m.get("role") in ("user", "assistant") and m.get("content")
    ][-MAX_HISTORY:]

    messages = [{"role": "system", "content": AIClient.product_system_prompt(product, related)}]
    messages += history
    messages.append({"role": "user", "content": question})

    answer = client.chat(messages)
    degraded = answer is None
    if degraded:
        answer = AIClient.fallback_answer(product, question)

    return jsonify(
        {
            "answer": answer,
            "degraded": degraded,
            "model": client.chat_model,
            "embedding_model": client.embed_model,
            "embedding_used": embedding_used,
            "embedded_now": embedded_now,
            "product": product.to_dict(full=False),
            "related": [p.to_dict(full=False) for p in related],
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
    )
