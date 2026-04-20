# ═══════════════════════════════════════════════════════
# CrawlForge — Multi-stage Dockerfile
# Stage 1: builder (poetry install)
# Stage 2: runtime (slim + playwright browsers)
# ═══════════════════════════════════════════════════════

# ── Builder ───────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME="/opt/poetry"

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --only main

# Copy source and install project
COPY crawlforge/ crawlforge/
COPY README.md ./
RUN poetry install --only main


# ── Runtime ───────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Install browsers inside /app so the non-root user can find them.
    # Without this, root installs to /root/.cache and crawlforge user
    # looks in /home/crawlforge/.cache — different paths, browser not found.
    PLAYWRIGHT_BROWSERS_PATH="/app/.playwright"

# Install playwright system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libwayland-client0 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 crawlforge && \
    useradd --uid 1000 --gid crawlforge --shell /bin/bash --create-home crawlforge

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/crawlforge /app/crawlforge
COPY scripts/ scripts/

# Install Playwright browsers to /app/.playwright (PLAYWRIGHT_BROWSERS_PATH)
# while still root, then hand ownership of everything to the app user.
RUN /app/.venv/bin/python -m playwright install chromium && \
    mkdir -p /app/logs /app/output && \
    chown -R crawlforge:crawlforge /app

USER crawlforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "crawlforge"]
