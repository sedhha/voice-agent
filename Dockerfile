FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-cache

# Copy application code
COPY server/ ./server/

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"]
