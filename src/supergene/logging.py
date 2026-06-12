"""Shared Loguru configuration for Super Gene command-line workflows."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_CONFIGURED = False


def configure_logging(log_dir: str | Path = "logs") -> None:
    """Configure the shared Loguru sinks once for CLI workflows.

    Args:
        log_dir: Directory where trace and info log files should be written.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    trace_log_path: Path = Path(log_dir) / "trace.log"
    trace_log_path.parent.mkdir(parents=True, exist_ok=True)
    info_log_path: Path = Path(log_dir) / "info.log"
    info_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Replace Loguru's default stderr sink so CLI output and file logs share the
    # same formatting and level policy.
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        colorize=False,
    )
    logger.add(
        trace_log_path,
        level="TRACE",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        ),
        encoding="utf-8",
        enqueue=False,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        info_log_path,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        ),
        encoding="utf-8",
        enqueue=False,
        backtrace=True,
        diagnose=True,
    )
    _CONFIGURED = True
