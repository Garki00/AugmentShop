"""Pre-start step for docker: create tables, seed the catalogue, warm the ANN cache.

Runs before gunicorn so every worker starts with embeddings already cached in the
database (otherwise each of the 4 workers would embed the same 100 products).

Usage: python prestart.py [--no-embed]
"""
from __future__ import annotations

import argparse
import logging

from app import create_app
from app.services.rag import ensure_embeddings

logging.basicConfig(level=logging.INFO, format="[prestart] %(levelname)s %(message)s")
log = logging.getLogger("prestart")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-embed", action="store_true", help="skip embedding warm-up")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        client = app.extensions["ai_client"]
        if args.no_embed or not client.embed_key:
            log.info("embedding warm-up skipped (key configured: %s)", bool(client.embed_key))
            return 0
        log.info("embedding products with %s ...", client.embed_model)
        count = ensure_embeddings(client)
        log.info("embedded %d new products", count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
