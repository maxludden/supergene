#!/usr/bin/env python3
"""Console script wrapper for rendering table candidate reports to HTML."""

from __future__ import annotations

from supergene.render_table_candidates import main
from loguru import logger


if __name__ == "__main__":
    raise SystemExit(main())
