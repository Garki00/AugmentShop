FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY . .

EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=10 \
    CMD curl -fsS http://localhost:5000/api/health || exit 1

# Seed the catalogue + warm the embedding cache once, then serve.
CMD ["sh", "-c", "python prestart.py && gunicorn --workers 4 --threads 4 --timeout 120 -b 0.0.0.0:5000 wsgi:app"]
