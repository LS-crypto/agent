FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765 \
    UVICORN_RELOAD=0

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY core/ core/
COPY server/ server/
COPY apps/cli/ apps/cli/
COPY apps/__init__.py apps/__init__.py
COPY scripts/ scripts/

RUN mkdir -p runtime

EXPOSE 8765

# 直接用 sync 后的 venv，避免容器首次启动时 uv run 再拉依赖
CMD [".venv/bin/python", "-m", "server"]
