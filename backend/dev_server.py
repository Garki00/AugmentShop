"""Local dev server (no docker):

    cd backend
    DATABASE_URL=sqlite:///D:/AAAAGarki/Sonnet/kjds/backend/data/kjds.db \
      ../.venv/Scripts/python.exe dev_server.py

Without DATABASE_URL it falls back to backend/data/kjds.db automatically.
"""
from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
        use_reloader=False,
    )
