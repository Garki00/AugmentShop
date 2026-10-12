"""App factory: extensions, blueprints, error handling, startup seeding."""
from __future__ import annotations

import logging
import os
import time

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from . import config as config_module
from .config import Config
from .models import db
from .services.ai import AIClient

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kjds")


def create_app(config_object: type[Config] = Config) -> Flask:
    static_dir = config_module.BASE_DIR / "static"
    (static_dir / "products").mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")
    app.config.from_object(config_object)
    app.json.ensure_ascii = False

    # DATABASE_URL -> Flask-SQLAlchemy's SQLALCHEMY_DATABASE_URI (+ pool tuning for MySQL)
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["DATABASE_URL"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.setdefault(
        "SQLALCHEMY_ENGINE_OPTIONS",
        {"pool_pre_ping": True, "pool_recycle": 1800},
    )

    origins = app.config["CORS_ORIGINS"]
    CORS(app, resources={r"/api/*": {"origins": origins if origins != "*" else "*"}},
         supports_credentials=False, allow_headers=["Content-Type", "Authorization"])

    db.init_app(app)
    config_module.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config_object.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    app.extensions["ai_client"] = AIClient(app.config)

    from .routes import register_blueprints

    register_blueprints(app)

    # ---------- JSON error handlers ----------
    @app.errorhandler(404)
    def not_found(err):
        if request.path.startswith("/api"):
            return jsonify({"error": "not_found", "message": "接口不存在"}), 404
        return err, 404

    @app.errorhandler(405)
    def bad_method(err):
        if request.path.startswith("/api"):
            return jsonify({"error": "method_not_allowed", "message": "请求方法不允许"}), 405
        return err, 405

    @app.errorhandler(413)
    def too_large(err):
        return jsonify({"error": "payload_too_large", "message": "上传文件过大"}), 413

    @app.errorhandler(Exception)
    def server_error(err):  # noqa: ANN001
        log.exception("unhandled error: %s", err)
        code = getattr(err, "code", 500)
        return jsonify({"error": "server_error", "message": str(err)}), code if isinstance(code, int) else 500

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:  # noqa: BLE001
            log.warning("db health check failed: %s", exc)
            db_ok = False
        client: AIClient = app.extensions["ai_client"]
        return jsonify(
            {
                "status": "ok" if db_ok else "degraded",
                "database": "up" if db_ok else "down",
                "dialect": db.engine.dialect.name if db_ok else None,
                "ai": {
                    "embed_model": client.embed_model,
                    "chat_model": client.chat_model,
                    "embed_key_configured": bool(client.embed_key),
                    "chat_key_configured": bool(client.chat_key),
                },
            }
        )

    # ---------- startup: wait for DB (docker-compose), create tables, seed ----------
    if os.getenv("SKIP_STARTUP_DB", "0") != "1":
        with app.app_context():
            _init_database(app)

    return app


def _init_database(app: Flask) -> None:
    from .services.seed_data import run_startup_seed

    for attempt in range(1, 16):
        try:
            db.create_all()
            break
        except OperationalError as exc:
            log.warning("database not ready (attempt %d/15): %s", attempt, exc)
            db.session.rollback()
            time.sleep(2)
    else:
        log.error("database never became ready; serving without seeding")
        return
    try:
        run_startup_seed(app)
        log.info("startup OK: %d products in catalogue", db.session.execute(text("SELECT COUNT(*) FROM products")).scalar())
    except Exception as exc:  # noqa: BLE001
        log.exception("startup seeding failed: %s", exc)

