"""SiliconFlow client.

Two models are used, both over the OpenAI-compatible API exposed by SiliconFlow:

* ``Qwen/Qwen3-Embedding-8B`` (EMBED_MODEL) - embeds the catalogue and the user's
  question, so the answer can be grounded in the *most relevant* products.
* ``Qwen/Qwen2.5-7B-Instruct`` (CHAT_MODEL) - answers the shopper, with the current
  product's name / price / description injected into the system prompt.

Everything degrades gracefully: if the upstream API is unreachable the shop still
answers from the product record itself (``degraded=True`` in the response).
"""
from __future__ import annotations

import logging
import math

import requests

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个跨境电商独立站「环球优选」的 AI 客服助手。

【当前商品信息】
商品名称：{name}
售价：${price:.2f} USD
商品简介：{description}
{extra}

【回答要求】
1. 只围绕当前这件商品回答；价格一律以上面的售价为准，不要编造折扣或更低价格。
2. 结合商品简介说明卖点、材质、适用场景；简介里没有的信息（如具体物流时效、退换货细节）不要臆造，可以提示用户联系人工客服。
3. 用简体中文回答，口语化、亲切，控制在 150 字以内，必要时用短列表。
4. 若用户问的是其它商品，可以简要介绍下面「相关商品」，并说明可以点击查看详情。
5. 不谈论政治、不输出与本商城无关的内容。"""


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class AIClient:
    """Thin wrapper around SiliconFlow's /embeddings and /chat/completions."""

    def __init__(self, config):
        self.embed_base = config["EMBED_BASE_URL"].rstrip("/")
        self.embed_key = config["EMBED_API_KEY"]
        self.embed_model = config["EMBED_MODEL"]
        self.chat_base = config["CHAT_BASE_URL"].rstrip("/")
        self.chat_key = config["CHAT_API_KEY"]
        self.chat_model = config["CHAT_MODEL"]
        self.timeout = config["AI_TIMEOUT"]
        self.max_tokens = config["AI_MAX_TOKENS"]

    # ---------------- embeddings ----------------

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Batch embed. Returns None when the API is unavailable."""
        if not self.embed_key or not texts:
            return None
        try:
            resp = requests.post(
                f"{self.embed_base}/embeddings",
                headers={"Authorization": f"Bearer {self.embed_key}", "Content-Type": "application/json"},
                json={"model": self.embed_model, "input": texts},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data.sort(key=lambda item: item.get("index", 0))
            return [item["embedding"] for item in data]
        except Exception as exc:  # noqa: BLE001
            log.warning("embedding call failed: %s", exc)
            return None

    # ---------------- chat ----------------

    def chat(self, messages: list[dict]) -> str | None:
        if not self.chat_key:
            return None
        try:
            resp = requests.post(
                f"{self.chat_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.chat_key}", "Content-Type": "application/json"},
                json={
                    "model": self.chat_model,
                    "messages": messages,
                    "temperature": 0.6,
                    "top_p": 0.9,
                    "max_tokens": self.max_tokens,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("chat call failed: %s", exc)
            return None

    # ---------------- prompt building ----------------

    @staticmethod
    def product_system_prompt(product, related: list | None = None) -> str:
        extra = ""
        if product.category or product.brand:
            extra = f"类目/品牌：{product.category or '-'} / {product.brand or '-'}\n"
        if related:
            lines = [f"- {p.name}（${float(p.price):.2f}）" for p in related]
            extra += "【相关商品】\n" + "\n".join(lines) + "\n"
        return SYSTEM_PROMPT.format(
            name=product.name,
            price=float(product.price or 0),
            description=(product.description or "（暂无简介）")[:1200],
            extra=extra,
        )

    @staticmethod
    def fallback_answer(product, question: str) -> str:
        """Used when the LLM cannot be reached: answer straight from the DB record."""
        return (
            f"（AI 服务暂时不可用，以下信息来自商品库）\n"
            f"您问的是：{question.strip()[:60]}\n"
            f"商品「{product.name}」当前售价 ${float(product.price or 0):.2f} USD。\n"
            f"简介：{(product.description or '暂无简介')[:220]}\n"
            f"更多细节建议咨询人工客服。"
        )
