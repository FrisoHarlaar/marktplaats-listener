FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the system python (no venv needed in Docker)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY *.py ./

CMD ["uv", "run", "python", "listener.py"]
