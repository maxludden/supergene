from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


_CONFIGURED = False


def configure_logging(log_dir: str | Path = "logs") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_path = Path(log_dir) / "trace.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        colorize=False,
    )
    logger.add(
        log_path,
        level="TRACE",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        enqueue=False,
        backtrace=True,
        diagnose=False,
    )
    _CONFIGURED = True
