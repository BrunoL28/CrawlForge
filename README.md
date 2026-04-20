# 🕷️ CrawlForge

Professional web scraping system powered by [crawl4ai](https://github.com/unclecode/crawl4ai), FastAPI, and async Python.

## Quick Start

```bash
# 1. Install dependencies
make install

# 2. Start dev environment (Docker)
make dev

# 3. Check health
curl http://localhost:8000/health

# 4. Quick crawl test
make crawl url=https://example.com
```

## Architecture

```
crawlforge/
├── core/           # CrawlerEngine, SessionHandler, ContextHandler
├── extractors/     # Protocol + CSS/HTML/FullPage strategies
├── exporters/      # Protocol + MD/HTML/PDF/TXT converters
├── queue/          # Priority queue with retry + exponential backoff
├── middleware/      # Anti-bot, proxy rotation, captcha interfaces
├── logger/         # Singleton loguru (session logs + job metrics)
├── config/         # pydantic-settings from .env
├── models/         # Pydantic v2 schemas (CrawlJob, CrawlResult, enums)
├── api/            # FastAPI app factory + routes
└── utils/          # Shared helpers
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Poetry install + Playwright browsers |
| `make dev` | Docker Compose dev with hot reload |
| `make prod` | Docker Compose production |
| `make test` | Pytest with 80% coverage minimum |
| `make lint` | Ruff + mypy |
| `make format` | Ruff format + isort |
| `make migrate` | Apply SQL migrations |
| `make crawl url=...` | Quick single-URL crawl |
| `make logs` | Tail container logs |
| `make down` | Stop all containers |
| `make clean` | Remove volumes, logs, caches |

## Stack

- **Python 3.11+** · crawl4ai · FastAPI · uvicorn
- **Pydantic v2** · pydantic-settings · loguru
- **PostgreSQL + pgvector** · Redis · Supabase
- **OpenAI** (primary embedding) · **Google GenAI** (fallback)
- **Docker Compose** · Poetry · Makefile

## License

MIT