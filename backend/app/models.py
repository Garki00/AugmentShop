"""Database models: users and products."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import LONGTEXT
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username, "is_admin": bool(self.is_admin)}


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    image = db.Column(db.String(500), nullable=False, default="")
    image_remote = db.Column(db.String(500), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(64), default="", index=True)
    brand = db.Column(db.String(64), default="")
    rating = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=0)
    # cached Qwen3-Embedding vector of "<name> | <category> | <description>", JSON encoded
    embedding = db.Column(db.Text().with_variant(LONGTEXT, "mysql"), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def embedding_text(self) -> str:
        return " | ".join(
            part for part in (self.name, self.category or "", self.brand or "", self.description or "") if part
        )

    def get_embedding(self) -> list[float] | None:
        if not self.embedding:
            return None
        try:
            value = json.loads(self.embedding)
            return value if isinstance(value, list) and value else None
        except (ValueError, TypeError):
            return None

    def set_embedding(self, vector: list[float]) -> None:
        self.embedding = json.dumps([round(float(x), 6) for x in vector])

    def to_dict(self, *, full: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "price": float(self.price or 0),
            "image": self.image,
            "image_remote": self.image_remote,
            "description": self.description or "",
            "category": self.category or "",
            "brand": self.brand or "",
            "rating": float(self.rating or 0),
            "stock": int(self.stock or 0),
        }
        if not full:
            data.pop("description", None)
        return data
