"""
crawlforge.logger.setup
~~~~~~~~~~~~~~~~~~~~~~~~
Singleton loguru logger with:
  - Colorful terminal output (dev)
  - Structured JSON logging (production)
  - Per-session log files in ./logs/{session_id}.log
  - Job-level metric annotations (time, bytes, status)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from crawlforge.config.settings import Settings

_CONFIGURED = False

# ── Log formats ──────────────────────────────────────
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)

_JSON_FORMAT = (
    '{{"ts":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
    '"level":"{level}",'
    '"module":"{name}",'
    '"func":"{function}",'
    '"line":{line},'
    '"msg":"{message}"}}'
)


def setup_logger(settings: Settings) -> None:
    """Configure the global loguru logger (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    # Remove default handler
    logger.remove()

    # ── Console sink ─────────────────────────────────
    if settings.is_production:
        logger.add(
            sys.stderr,
            format=_JSON_FORMAT,
            level=settings.log_level,
            serialize=False,
            colorize=False,
        )
    else:
        logger.add(
            sys.stderr,
            format=_CONSOLE_FORMAT,
            level=settings.log_level,
            colorize=True,
        )

    # ── Rotating file sink (best-effort) ────────────
    # Tries LOG_DIR env var, then ./logs, then /tmp/crawlforge_logs
    # If none are writable, continues with console-only logging.
    import os

    log_dir_candidates = [
        os.environ.get("LOG_DIR", ""),
        "logs",
        "/tmp/crawlforge_logs",
    ]
    file_sink_added = False
    for candidate in log_dir_candidates:
        if not candidate:
            continue
        log_dir = Path(candidate)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(log_dir / "crawlforge_{time:YYYY-MM-DD}.log"),
                rotation="50 MB",
                retention="7 days",
                compression="gz",
                level="DEBUG",
                format=_CONSOLE_FORMAT,
            )
            file_sink_added = True
            break
        except (PermissionError, OSError) as exc:
            # Can't write here — try next candidate
            print(f"[crawlforge] WARNING: cannot write logs to {log_dir}: {exc}", file=sys.stderr)

    if not file_sink_added:
        print("[crawlforge] WARNING: running with console-only logging (no writable log dir found)", file=sys.stderr)

    _CONFIGURED = True
    logger.info("Logger configured — env={} level={}", settings.app_env, settings.log_level)


def get_session_logger(session_id: str) -> logger:  # type: ignore[valid-type]
    """
    Return a logger bound to a specific session that also writes
    to ./logs/{session_id}.log for post-mortem inspection.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    session_log = log_dir / f"{session_id}.log"
    sink_id = logger.add(
        str(session_log),
        format=_CONSOLE_FORMAT,
        level="DEBUG",
        filter=lambda record: record["extra"].get("session_id") == session_id,
    )

    bound = logger.bind(session_id=session_id, _sink_id=sink_id)
    return bound


def log_job_metrics(
    session_id: str,
    url: str,
    *,
    duration_ms: float,
    bytes_received: int,
    status: str,
    error: str | None = None,
) -> None:
    """Structured log entry for job-level metrics."""
    logger.bind(session_id=session_id).info(
        "JOB_METRIC | url={url} | duration_ms={dur:.1f} | "
        "bytes={bytes} | status={status} | error={err}",
        url=url,
        dur=duration_ms,
        bytes=bytes_received,
        status=status,
        err=error or "none",
    )
