"""Tests for Super Gene logging configuration."""

from __future__ import annotations

from pathlib import Path


def test_configure_logging_uses_supergene_rich_logger_config(tmp_path: Path) -> None:
    """Configure logging with Super Gene's local Rich logger config object."""
    from loguru import logger

    from supergene import RichLoggerConfig as PackageRichLoggerConfig
    from supergene import logging as logging_module
    from supergene.logging import RichLoggerConfig, configure_logging

    logging_module._CONFIGURED = False

    assert PackageRichLoggerConfig is RichLoggerConfig

    config = RichLoggerConfig(
        level="INFO",
        panel_padding=(0, 1),
        panel_expand=False,
        render_width=100,
    )

    configure_logging(log_dir=tmp_path, config=config)
    logger.info("local rich logger config works")

    assert (tmp_path / "trace.log").exists()
    assert "local rich logger config works" in (tmp_path / "info.log").read_text(encoding="utf-8")
