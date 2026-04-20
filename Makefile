# ═══════════════════════════════════════════════════════
# CrawlForge — Makefile
# ═══════════════════════════════════════════════════════

.PHONY: install dev prod test lint format migrate crawl logs down clean help

SHELL := /bin/bash
COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.prod.yml

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────
install: ## Install deps (poetry + playwright browsers)
	@echo "📦 Installing Python dependencies..."
	poetry install
	@echo "🎭 Installing Playwright browsers..."
	poetry run python -m playwright install chromium
	@echo "✅ Setup complete"

# ── Development ───────────────────────────────────────
dev: ## Start dev environment with hot reload
	@if [ ! -f .env ]; then cp .env.example .env; echo "📋 Created .env from .env.example"; fi
	$(COMPOSE) up --build -d
	@echo "🚀 CrawlForge running at http://localhost:$${APP_PORT:-8000}"
	@echo "📖 Docs at http://localhost:$${APP_PORT:-8000}/docs"

# ── Production ────────────────────────────────────────
prod: ## Start production environment
	$(COMPOSE_PROD) up --build -d
	@echo "🚀 CrawlForge production running"

# ── Testing ───────────────────────────────────────────
test: ## Run tests with coverage (min 80%)
	poetry run pytest tests/ -v --cov=crawlforge --cov-report=term-missing --cov-fail-under=80

# ── Code Quality ──────────────────────────────────────
lint: ## Run ruff linter + mypy type checker
	poetry run ruff check crawlforge/ tests/
	poetry run mypy crawlforge/

format: ## Auto-format code (ruff format + isort)
	poetry run ruff format crawlforge/ tests/
	poetry run ruff check --fix --select I crawlforge/ tests/

# ── Database ──────────────────────────────────────────
migrate: ## Apply SQL migrations to local Supabase/Postgres
	@echo "🗃️  Applying migrations..."
	@for f in migrations/*.sql; do \
		echo "  → $$f"; \
		$(COMPOSE) exec -T db psql -U postgres -d crawlforge -f /docker-entrypoint-initdb.d/$$(basename $$f); \
	done
	@echo "✅ Migrations applied"

# ── Quick Crawl ──────────────────────────────────────
crawl: ## Crawl a single URL: make crawl url=https://example.com
	@if [ -z "$(url)" ]; then echo "❌ Usage: make crawl url=https://example.com"; exit 1; fi
	poetry run python scripts/crawl.py $(url)

# ── Logs ──────────────────────────────────────────────
logs: ## Tail logs from the main container
	$(COMPOSE) logs -f app

# ── Cleanup ───────────────────────────────────────────
down: ## Stop all containers
	$(COMPOSE) down
	$(COMPOSE_PROD) down 2>/dev/null || true

clean: ## Remove volumes, logs, outputs, caches
	$(COMPOSE) down -v 2>/dev/null || true
	$(COMPOSE_PROD) down -v 2>/dev/null || true
	rm -rf logs/ output/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "🧹 Clean complete"
