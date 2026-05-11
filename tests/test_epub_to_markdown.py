from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from supergene import convert_epub
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


def test_missing_anchor_writes_warning_manifest(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "out"
    write_epub(epub_path, ("chapters.xhtml#missing", "chapters.xhtml#c2"))

    result = convert_epub(epub_path, output_dir)

    assert [warning.code for warning in result.warnings] == ["missing_anchor"]
    warnings = json.loads((output_dir / "Fixture Book" / "warnings.json").read_text())
    assert warnings[0]["source_href"] == "chapters.xhtml#missing"


def test_cli_refuses_existing_output_without_overwrite(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    output_dir = tmp_path / "cli-out"
    write_epub(epub_path)
    convert_epub(epub_path, output_dir)

    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "epub-to-md", str(epub_path), str(output_dir)],
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
