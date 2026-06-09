FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for pyarrow / psycopg build wheels are usually prebuilt; keep slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cache directory for downloaded prices (mounted volume in compose).
ENV PRICE_CACHE_DIR=/app/.price_cache
RUN mkdir -p /app/.price_cache

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
