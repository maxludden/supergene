from __future__ import annotations

import csv
from pathlib import Path

from typer.testing import CliRunner

from supergene.__main__ import app
from supergene.find_voice_lines import (
    categorize,
    extract_candidates_from_file,
    load_seed_lines,
    normalize_text,
    run_voice_line_search,
    score_candidates,
    split_possible_voice_segments,
)


runner = CliRunner()


def test_split_possible_voice_segments_prefers_embedded_announcement() -> None:
    line = (
        "For several days, Han Sen had been hunting mutant black stingers. "
        "On the fourth day, he finally heard the voice saying, "
        "**“Mutant black stinger killed. Beast soul of mutant black stinger gained. "
        "Eat its meat to gain zero to ten mutant geno points randomly.”**"
    )

    assert split_possible_voice_segments(line) == [
        "Mutant black stinger killed. Beast soul of mutant black stinger gained. "
        "Eat its meat to gain zero to ten mutant geno points randomly."
    ]


def test_extract_candidates_deduplicates_partial_fragments(tmp_path: Path) -> None:
    chapter = tmp_path / "001.md"
    chapter.write_text(
        "**“Flesh of black beetle eaten. One sacred geno point gained.”**\n",
        encoding="utf-8",
    )

    candidates = extract_candidates_from_file(chapter)

    assert [candidate.raw_text for candidate in candidates] == [
        "Flesh of black beetle eaten. One sacred geno point gained."
    ]


def test_score_candidates_rejects_dialogue_mentions() -> None:
    seeds = [
        "Mutant black stinger killed. Beast soul of mutant black stinger gained. "
        "Eat its meat to gain zero to ten mutant geno points randomly."
    ]
    chapter = Path("001.md")
    chapter.write_text if False else None
    candidates = []

    temp_line = "**“I think it must be a gang of people that killed these swift mantises.”**\n"
    tmp = Path("/private/tmp/supergene-test-dialogue.md")
    tmp.write_text(temp_line, encoding="utf-8")
    try:
        candidates = extract_candidates_from_file(tmp)
        scored = score_candidates(seeds, candidates, likely_threshold=0.65, review_threshold=0.45)
    finally:
        tmp.unlink(missing_ok=True)

    assert [candidate.decision for candidate in scored] == ["reject"]


def test_categorize_prefers_xenogeneic_gene_for_gene_found_notice() -> None:
    normalized = normalize_text("Xenogeneic Baron hunted; xenogeneic gene found. Xenogeneic beast soul obtained.")

    assert categorize(normalized) == "xenogeneic_gene"


def test_run_voice_line_search_writes_expected_outputs(tmp_path: Path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "001.md").write_text(
        "\n".join(
            [
                "---",
                "index: 1",
                'title: "Chapter 1"',
                "---",
                "**“Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.”**",
                "**“Why is this black beetle so strange?”** Han Sen stared at the golden black beetle.",
                "He ate the meat and heard the voice say, **“Flesh of black beetle eaten. One sacred geno point gained.”**",
            ]
        ),
        encoding="utf-8",
    )
    seeds = tmp_path / "voice_of_the_world.txt"
    seeds.write_text(
        '"Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly."\n'
        '"Flesh of black beetle eaten. One sacred geno point gained."\n',
        encoding="utf-8",
    )
    out = tmp_path / "out"

    summary = run_voice_line_search(
        chapters_dir=chapters,
        seed_path=seeds,
        out_dir=out,
        likely_threshold=0.65,
        review_threshold=0.45,
    )

    assert summary.total_candidates == 3
    assert summary.likely_count == 2
    assert summary.review_count == 0
    likely_rows = list(csv.DictReader((out / "likely_voice_lines.csv").open(encoding="utf-8")))
    assert [row["raw_text"] for row in likely_rows] == [
        "Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.",
        "Flesh of black beetle eaten. One sacred geno point gained.",
    ]


def test_package_cli_writes_voice_line_report(tmp_path: Path) -> None:
    chapters = tmp_path / "chapters"
    chapters.mkdir()
    (chapters / "001.md").write_text(
        "**“Black beetle flesh eaten. Zero geno points gained.”**\n",
        encoding="utf-8",
    )
    seeds = tmp_path / "voice_of_the_world.txt"
    seeds.write_text('"Black beetle flesh eaten. Zero geno points gained."\n', encoding="utf-8")
    out = tmp_path / "voice-report"

    result = runner.invoke(app, ["voice-lines", str(chapters), str(seeds), str(out)])

    assert result.exit_code == 0
    assert "Wrote voice line report" in result.stderr
    assert (out / "likely_voice_lines.csv").exists()


def test_load_seed_lines_uses_full_examples_not_sentence_fragments(tmp_path: Path) -> None:
    seed_path = tmp_path / "voice_of_the_world.txt"
    seed_path.write_text(
        '"Flesh of black beetle eaten. One sacred geno point gained."\n',
        encoding="utf-8",
    )

    assert load_seed_lines(seed_path) == [
        "Flesh of black beetle eaten. One sacred geno point gained."
    ]
