FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && git config --system http.receivepack true \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /data/repos /data/uploads

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD curl -sf http://127.0.0.1:5000/api/health || exit 1

CMD ["sh", "-c", "python run.py --init-only && gunicorn --config gunicorn.conf.py 'app:create_app()'"]
