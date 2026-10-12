"""Register / login / session endpoints (username + password only)."""
from __future__ import annotations

import re

from flask import Blueprint, g, jsonify, request

from ..models import User, db
from ..security import _current_user, create_token, login_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,32}$")


def _payload() -> tuple[str, str]:
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    return username, password


@bp.post("/register")
def register():
    username, password = _payload()
    if not USERNAME_RE.match(username):
        return jsonify({"error": "bad_username", "message": "用户名需为 3-32 位字母、数字、下划线或短横线"}), 400
    if len(password) < 6:
        return jsonify({"error": "bad_password", "message": "密码至少 6 位"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username_taken", "message": "用户名已存在"}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"token": create_token(user), "user": user.to_dict()}), 201


@bp.post("/login")
def login():
    username, password = _payload()
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "bad_credentials", "message": "用户名或密码错误"}), 401
    return jsonify({"token": create_token(user), "user": user.to_dict()})


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": _current_user().to_dict()})


@bp.post("/logout")
def logout():
    # Stateless JWT: the client simply drops the token.
    return jsonify({"ok": True})
