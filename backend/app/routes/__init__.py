"""Route package. Shared helpers live here."""
from __future__ import annotations

import math


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    pages = max(1, math.ceil(total / page_size)) if total else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
    }


def register_blueprints(app) -> None:
    from . import admin, auth, chat, products

    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(chat.bp)
