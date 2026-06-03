FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install shared package first
COPY packages/shared-py/ /app/packages/shared-py/
RUN pip install -e /app/packages/shared-py

# Install service
COPY services/api-gateway/ /app/services/api-gateway/
WORKDIR /app/services/api-gateway
RUN pip install -e "."

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
