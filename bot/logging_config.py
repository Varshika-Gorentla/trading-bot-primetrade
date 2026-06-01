"""
bot/logging_config.py
~~~~~~~~~~~~~~~~~~~~~
Centralised logging setup for the trading bot.

Design decisions:
  • Two handlers: rotating file (JSON) + console (human-readable coloured text)
  • JSON file logs let you grep/parse with tools like jq in production
  • RotatingFileHandler caps disk usage — logs never fill the drive
  • A custom JSONFormatter emits one JSON object per line (structured logging)

Interviewer talking point:
  "I separated the logging config into its own module so every layer calls
   `get_logger(__name__)` and gets consistent formatting. The file handler
   writes newline-delimited JSON so logs can be ingested by any log
   aggregation system (Datadog, CloudWatch, etc.) without extra parsing."
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


# ── JSON formatter ───────────────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName",
            }:
                log_obj[key] = value

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


# ── Coloured console formatter ───────────────────────────────────────────────

LEVEL_COLOURS = {
    "DEBUG":    "\033[36m",
    "INFO":     "\033[32m",
    "WARNING":  "\033[33m",
    "ERROR":    "\033[31m",
    "CRITICAL": "\033[35m",
}
RESET = "\033[0m"


class ConsoleFormatter(logging.Formatter):
    """Human-readable coloured formatter for the terminal."""

    FMT = "{colour}[{level}]{reset} {ts} {logger} — {msg}"

    def format(self, record: logging.LogRecord) -> str:
        colour = LEVEL_COLOURS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        line = self.FMT.format(
            colour=colour,
            reset=RESET,
            level=record.levelname[0],
            ts=ts,
            logger=record.name.split(".")[-1],
            msg=record.getMessage(),
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


# ── Setup function ───────────────────────────────────────────────────────────

_configured = False


def setup_logging(level: str = "DEBUG") -> None:
    """Initialise both file and console handlers."""
    global _configured
    if _configured:
        return
    _configured = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # File handler (JSON, rotating)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JSONFormatter())

    # Console handler (coloured text)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(getattr(logging, level.upper(), logging.INFO))
    ch.setFormatter(ConsoleFormatter())

    root.addHandler(fh)
    root.addHandler(ch)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call as: logger = get_logger(__name__)"""
    return logging.getLogger(name)