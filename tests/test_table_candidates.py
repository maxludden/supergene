from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from supergene.__main__ import app
from supergene.table_candidates import find_table_candidates, write_table_candidate_report


runner = CliRunner()


def test_find_table_candidates_detects_stat_blocks_and_entity_lines(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    chapter = chapters_dir / "001-chapter-one.md"
    chapter.write_text(
        "\n".join(
            [
                "---",
                "title: Chapter One",
                "---",
                "# Chapter One",
                "",
                "Han Sen: Not evolved.",
                "Status: None.",
                "Life span: 200 years.",
                "Required for evolution: 100 geno points.",
                "Geno points gained: 79.",
                "Beast souls gained: none.",
                "",
                "Sacred-Blood Iron Bug King Beast Soul: Armour Type.",
                "",
                "**“God spirit hunted. Found god spirit gene.”**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    candidates = find_table_candidates(chapters_dir)

    assert [candidate.kind for candidate in candidates] == ["stat_block", "beast_soul", "voice_of_world"]
    assert candidates[0].start_line == 6
    assert candidates[0].end_line == 11
    assert "<table>" in candidates[0].proposed_html
    assert "<th>Field</th>" in candidates[0].proposed_html
    assert "Geno points gained" in candidates[0].proposed_html
    assert candidates[1].original_text.startswith("Sacred-Blood Iron Bug King")
    assert "Iron Bug King" in candidates[1].proposed_html
    assert candidates[2].kind == "voice_of_world"


def test_find_table_candidates_allows_blank_lines_inside_stat_blocks(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "Han Sen: Not evolved.\n\nStatus: None.\n\nLife span: 200 years.\n\nBeast souls gained: none.\n",
        encoding="utf-8",
    )

    candidates = find_table_candidates(chapters_dir)

    assert len(candidates) == 1
    assert candidates[0].kind == "stat_block"
    assert candidates[0].start_line == 1
    assert candidates[0].end_line == 7
    assert "Beast souls gained" in candidates[0].proposed_html


def test_find_table_candidates_ignores_regular_prose_mentions(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "He kept wondering whether a sacred-blood beast soul was even real.\n"
        "The god spirit temple was quiet, and nobody found anything new there.\n",
        encoding="utf-8",
    )

    assert find_table_candidates(chapters_dir) == []


def test_find_table_candidates_requires_colon_for_beast_soul_entities(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "**“Primitive creature copper-toothed beast killed. Primitive beast soul of copper-toothed beast gained.”**\n"
        "Baron Xenogeneic Beast Soul: Violent Ape (Shape-shifting Type)\n",
        encoding="utf-8",
    )

    candidates = find_table_candidates(chapters_dir)

    assert [candidate.kind for candidate in candidates] == ["voice_of_world", "beast_soul"]
    assert candidates[1].original_text == "Baron Xenogeneic Beast Soul: Violent Ape (Shape-shifting Type)"


def test_find_table_candidates_detects_voice_of_the_world_notifications(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "**“Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.”**\n"
        "**“Black beetle flesh eaten. Zero geno points gained.”**\n"
        "**“Why is this black beetle so strange?”** Han Sen stared at the golden black beetle.\n",
        encoding="utf-8",
    )

    candidates = find_table_candidates(chapters_dir)

    assert [candidate.kind for candidate in candidates] == ["voice_of_world", "voice_of_world"]
    assert candidates[0].start_line == 1
    assert "Black beetle killed" in candidates[0].proposed_html
    assert 'class="voice-of-world"' in candidates[0].proposed_html
    assert "<em>Black beetle killed" in candidates[0].proposed_html
    assert "<table>" not in candidates[0].proposed_html


def test_find_table_candidates_ignores_bold_dialogue_about_world_events(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "**“I think it must be a gang of people that killed these swift mantises.”**\n"
        "**“What is that? Is that a Geno core?”**\n"
        "**“Go and find out who owns this geno core.”**\n",
        encoding="utf-8",
    )

    assert find_table_candidates(chapters_dir) == []


def test_find_table_candidates_ignores_prose_colons_before_entity_words(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "Queen thought it was ridiculous, how he had received another super beast soul. "
        "Particularly given the manner he received it: bribing it off another person.\n",
        encoding="utf-8",
    )

    assert find_table_candidates(chapters_dir) == []


def test_write_table_candidate_report_outputs_json(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text("Deified Beast Soul: Purple Eye Butterfly (Spectacles-type)\n", encoding="utf-8")
    report_path = tmp_path / "table_candidates.json"

    candidates = write_table_candidate_report(chapters_dir, report_path)

    assert len(candidates) == 1
    report = json.loads(report_path.read_text())
    assert report["summary"]["total_candidates"] == 1
    assert report["candidates"][0]["kind"] == "beast_soul"
    assert report["candidates"][0]["chapter_path"] == str(chapters_dir / "001.md")


def test_cli_writes_table_candidate_report(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text("Han Sen: Super God Spirit body.\nLevel: Deified.\nProgress: 0 out of 100\n", encoding="utf-8")
    report_path = tmp_path / "report.json"

    completed = subprocess.run(
        [sys.executable, "-m", "supergene", "table-report", str(chapters_dir), str(report_path)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "Wrote 1 table candidates" in completed.stderr
    assert report_path.exists()


def test_typer_cli_writes_table_candidate_report(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text("Han Sen: Super God Spirit body.\nLevel: Deified.\nProgress: 0 out of 100\n", encoding="utf-8")
    report_path = tmp_path / "report.json"

    result = runner.invoke(app, ["table-report", str(chapters_dir), str(report_path)])

    assert result.exit_code == 0
    assert "Wrote 1 table candidates" in result.stderr
    assert report_path.exists()
