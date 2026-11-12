FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV WEB_CONCURRENCY=2
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY inventory-fastapi-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY inventory-fastapi-backend/ .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://localhost:$PORT/api/v1/health/live || exit 1
CMD gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w $WEB_CONCURRENCY -b 0.0.0.0:$PORT --timeout 120
