"""Shared Loguru configuration for Super Gene command-line workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from loguru._logger import Logger
from rich.console import Console

_CONFIGURED = False

PanelPadding = int | tuple[int, int] | tuple[int, int, int, int]


@dataclass(frozen=True)
class RichLoggerConfig:
    """Configuration for Super Gene's Rich-backed Loguru console sink.

    Args:
        level: Minimum Loguru level rendered to the console sink.
        panel_padding: Padding metadata retained for callers that tune Rich panel output.
        panel_expand: Whether Rich panel output should expand to the console width.
        render_width: Optional console width used for rendering terminal output.
        stderr: Whether console output should be written to standard error.
    """

    level: str = "INFO"
    panel_padding: PanelPadding = (0, 1)
    panel_expand: bool = False
    render_width: int | None = 120
    stderr: bool = True


def setup_logger(config: RichLoggerConfig | None = None) -> Logger:
    """Configure Loguru with Super Gene's Rich console sink.

    Args:
        config: Rich console sink configuration. Defaults to ``RichLoggerConfig``.

    Returns:
        The shared Loguru logger with the configured console sink attached.
    """
    logger.trace("Entering setup_logger")
    resolved_config = config or RichLoggerConfig()
    console = Console(
        stderr=resolved_config.stderr,
        width=resolved_config.render_width,
        soft_wrap=True,
    )
    logger.remove()
    logger.add(
        lambda message: console.print(str(message), end=""),
        level=resolved_config.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        colorize=False,
    )
    return logger


def configure_logging(
    log_dir: str | Path = "logs",
    config: RichLoggerConfig | None = None,
) -> None:
    """Configure the shared Loguru sinks once for CLI workflows.

    Args:
        log_dir: Directory where trace and info log files should be written.
        config: Rich console sink configuration. Defaults to ``RichLoggerConfig``.
    """
    logger.trace("Entering configure_logging")
    global _CONFIGURED
    if _CONFIGURED:
        return

    trace_log_path: Path = Path(log_dir) / "trace.log"
    trace_log_path.parent.mkdir(parents=True, exist_ok=True)
    info_log_path: Path = Path(log_dir) / "info.log"
    info_log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure the default Rich console sink while preserving Loguru's sink API.
    configured_logger = setup_logger(
        config
        or RichLoggerConfig(
            level="INFO",
            panel_padding=(0, 1),
            panel_expand=False,
            render_width=120,
        )
    )
    configured_logger.add(
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
    configured_logger.add(
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
