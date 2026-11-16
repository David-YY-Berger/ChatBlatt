FROM python:3.12.16 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app


RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install -r requirements.txt
FROM python:3.12.16-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nginx gettext-base \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv .venv/
COPY . .
CMD ["bash", "/app/deploy/start.sh"]