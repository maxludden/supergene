"""Tests for Rich-backed Pandoc build progress helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

import pytest
from rich.console import Console

from supergene.pandoc_progress import (
    PandocBuildError,
    build_all_books,
    build_book,
    pandoc_books,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingRunner:
    """Record subprocess commands and return configured exit codes."""

    def __init__(self, returncodes: Sequence[int] | None = None) -> None:
        """Initialize the runner with optional per-call return codes.

        Args:
            returncodes: Optional return codes to consume in call order.
        """
        self.commands: list[tuple[str, ...]] = []
        self.returncodes = list(returncodes or [])

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Record one command and return a completed process."""
        self.commands.append(tuple(command))
        returncode = self.returncodes.pop(0) if self.returncodes else 0
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=returncode,
            stdout="",
            stderr="pandoc failed" if returncode else "",
        )


def quiet_console() -> Console:
    """Return a console suitable for non-interactive progress tests."""
    return Console(file=None, force_terminal=False)


def test_build_book_runs_generator_then_selected_pandoc_defaults() -> None:
    """Building one book regenerates inputs once before invoking Pandoc."""
    runner = RecordingRunner()

    build_book(4, repo_root=PROJECT_ROOT, runner=runner, console=quiet_console())

    assert runner.commands == [
        (sys.executable, "scripts/generate_pandoc_defaults.py"),
        (
            "pandoc",
            "--defaults",
            "converted/Super Gene/defaults/book-04-fourth-and-fifth-gods-sanctuaries.yaml",
        ),
    ]


def test_build_book_removes_existing_output_epub_before_pandoc() -> None:
    """Building a book overwrites the selected EPUB by default."""
    runner = RecordingRunner()
    output_path = PROJECT_ROOT / "converted/Super Gene/books/book-04-fourth-and-fifth-gods-sanctuaries.epub"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("stale epub", encoding="utf-8")

    try:
        build_book(4, repo_root=PROJECT_ROOT, runner=runner, console=quiet_console())

        assert not output_path.exists()
    finally:
        output_path.unlink(missing_ok=True)


def test_build_all_books_runs_generator_once_then_each_book() -> None:
    """Building all books runs Pandoc for every configured defaults file."""
    runner = RecordingRunner()

    build_all_books(repo_root=PROJECT_ROOT, runner=runner, console=quiet_console())

    pandoc_commands = runner.commands[1:]
    assert runner.commands[0] == (sys.executable, "scripts/generate_pandoc_defaults.py")
    assert len(pandoc_commands) == 10
    assert pandoc_commands[0] == (
        "pandoc",
        "--defaults",
        "converted/Super Gene/defaults/book-01-first-gods-sanctuary.yaml",
    )
    assert pandoc_commands[-1] == (
        "pandoc",
        "--defaults",
        "converted/Super Gene/defaults/book-10-the-thirty-three-skies.yaml",
    )


def test_build_book_rejects_unknown_book_number() -> None:
    """Unknown book numbers fail before running subprocess commands."""
    runner = RecordingRunner()

    with pytest.raises(ValueError, match="Unknown Super Gene book number"):
        build_book(99, repo_root=PROJECT_ROOT, runner=runner, console=quiet_console())

    assert runner.commands == []


def test_build_book_raises_on_pandoc_failure() -> None:
    """Pandoc failures include the failing return code and command output."""
    runner = RecordingRunner(returncodes=[0, 42])

    with pytest.raises(PandocBuildError, match="Pandoc exited with status 42"):
        build_book(1, repo_root=PROJECT_ROOT, runner=runner, console=quiet_console())


def test_pandoc_books_loads_expected_catalog() -> None:
    """The generated book catalog exposes stable display labels and paths."""
    books = pandoc_books(PROJECT_ROOT)

    assert books[0].label == "Book 01 - First God's Sanctuary"
    assert books[0].defaults_path == Path(
        "converted/Super Gene/defaults/book-01-first-gods-sanctuary.yaml"
    )
    assert books[0].output_path == Path(
        "converted/Super Gene/books/book-01-first-gods-sanctuary.epub"
    )
