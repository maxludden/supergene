from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from supergene import ConversionProgress, convert_epub
from epub_fixture import PIXEL_PNG, write_epub


def test_convert_epub_splits_toc_anchors_and_preserves_metadata(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path)

    result = convert_epub(epub_path, output_dir)

    assert result.metadata.title == "Fixture Book"
    assert [chapter.title for chapter in result.chapters] == ["Chapter One", "Chapter Two"]
    assert (output_dir / "Fixture Book" / "metadata.json").exists()
    assert (output_dir / "Fixture Book" / "assets" / "images" / "pixel.png").read_bytes() == PIXEL_PNG

    first = (output_dir / "Fixture Book" / "chapters" / "001-chapter-one.md").read_text()
    second = (output_dir / "Fixture Book" / "chapters" / "002-chapter-two.md").read_text()

    assert "title: Chapter One" in first
    assert 'source_href: "chapters.xhtml#c1"' in first
    assert "creators:" in first
    assert "# Chapter One" in first
    assert "Hello *styled* world." in first
    assert "![Pixel](../assets/images/pixel.png)" in first
    assert "<!-- source:" in first
    assert "# Chapter Two" not in first
    assert "# Chapter Two" in second
    assert "| Name | Value |" in second


def test_convert_epub_reports_chapter_progress(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path)
    events: list[ConversionProgress] = []

    result = convert_epub(epub_path, output_dir, progress_callback=events.append)

    assert len(result.chapters) == 2
    assert [(event.completed, event.total, event.title) for event in events] == [
        (1, 2, "Chapter One"),
        (2, 2, "Chapter Two"),
    ]
    assert events[-1].output_path.name == "002-chapter-two.md"


def test_convert_epub_splits_profile_table_geno_points_gained_rows(tmp_path: Path) -> None:
    """Profile table Geno Points Gained rows render as type-specific totals."""
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path, include_profile_table=True)

    convert_epub(epub_path, output_dir)

    chapter = (output_dir / "Fixture Book" / "chapters" / "002-chapter-two.md").read_text()
    assert "Geno Points Gained" in chapter
    assert "| Primitive |<!-- source: td.profile-value.numeric-value --> 79 |" in chapter
    assert "| Ordinary |<!-- source: td.profile-value.numeric-value --> 0 |" in chapter
    assert "| Mutant |<!-- source: td.profile-value.numeric-value --> 0 |" in chapter
    assert "| Sacred-Blood |<!-- source: td.profile-value.numeric-value --> 8 |" in chapter
    assert "79 geno points; 8 sacred geno points" not in chapter


def test_cli_converts_epub_and_reports_warnings(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "cli-out"
    write_epub(epub_path)

    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "epub-to-md", str(epub_path), str(output_dir)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "Wrote 2 chapters" in completed.stderr
    metadata = json.loads((output_dir / "Fixture Book" / "metadata.json").read_text())
    assert metadata["title"] == "Fixture Book"


def test_cli_logs_info_to_console_and_trace_file(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "cli-out"
    write_epub(epub_path)

    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "epub-to-md", str(epub_path), str(output_dir)],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "INFO" in completed.stderr
    assert "Wrote 2 chapters" in completed.stderr
    trace_log = tmp_path / "logs" / "trace.log"
    assert trace_log.exists()
    trace_text = trace_log.read_text()
    assert "TRACE" in trace_text
    assert "Starting EPUB conversion" in trace_text


def test_missing_anchor_writes_warning_manifest(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path, ("chapters.xhtml#missing", "chapters.xhtml#c2"))

    result = convert_epub(epub_path, output_dir)

    assert [warning.code for warning in result.warnings] == ["missing_anchor"]
    warnings = json.loads((output_dir / "Fixture Book" / "warnings.json").read_text())
    assert warnings[0]["source_href"] == "chapters.xhtml#missing"


def test_incomplete_toc_uses_chapter_like_spine_documents(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path, ("chapter2.xhtml",), split_documents=True)

    result = convert_epub(epub_path, output_dir)

    assert [chapter.title for chapter in result.chapters] == ["Chapter 1: Chapter One", "Chapter 2: Chapter Two"]
    assert [warning.code for warning in result.warnings] == ["incomplete_toc"]
    first = (output_dir / "Fixture Book" / "chapters" / "001-chapter-1-chapter-one.md").read_text()
    assert "# Chapter 1: Chapter One" in first


def test_cli_overwrites_existing_output_by_default(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "cli-out"
    write_epub(epub_path)
    convert_epub(epub_path, output_dir)
    stale_file = output_dir / "Fixture Book" / "stale.txt"
    stale_file.write_text("stale", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "epub-to-md", str(epub_path), str(output_dir)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert not stale_file.exists()


def test_cli_can_refuse_existing_output_with_no_overwrite(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "cli-out"
    write_epub(epub_path)
    convert_epub(epub_path, output_dir)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "supergene",
            "epub-to-md",
            "--no-overwrite",
            str(epub_path),
            str(output_dir),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "Output directory already exists" in completed.stderr


def test_cli_rejects_directory_as_epub_path(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "epub-to-md", str(tmp_path), str(tmp_path / "out")],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    assert "epub_path must be an .epub file" in completed.stderr
