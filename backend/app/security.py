"""JWT auth helpers and route guards."""
from __future__ import annotations

import functools
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, g, jsonify, request

from .models import User, db


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": bool(user.is_admin),
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_TTL_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm=current_app.config["JWT_ALGORITHM"])


def _decode(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, current_app.config["JWT_SECRET"], algorithms=[current_app.config["JWT_ALGORITHM"]]
        )
    except jwt.PyJWTError:
        return None


def _current_user() -> User | None:
    if "current_user" in g:
        return g.current_user
    header = request.headers.get("Authorization", "")
    user = None
    if header.startswith("Bearer "):
        payload = _decode(header[7:].strip())
        if payload and payload.get("sub"):
            user = db.session.get(User, int(payload["sub"]))
    g.current_user = user
    return user


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if _current_user() is None:
            return jsonify({"error": "unauthorized", "message": "请先登录"}), 401
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if user is None:
            return jsonify({"error": "unauthorized", "message": "请先登录"}), 401
        if not user.is_admin:
            return jsonify({"error": "forbidden", "message": "需要管理员权限"}), 403
        return view(*args, **kwargs)

    return wrapper
