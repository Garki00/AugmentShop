"""WSGI entrypoint used by gunicorn in docker: `gunicorn wsgi:app`."""
from app import create_app

app = create_app()
