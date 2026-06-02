from __future__ import annotations

import json
from pathlib import Path

import pytest
from textual.widgets import Input

from supergene.voice_review import (
    ReviewAction,
    ReviewDecision,
    append_accepted_seed,
    load_pending_candidates,
    record_decision,
)
from supergene.voice_review_tui import VoiceReviewApp


def test_load_pending_candidates_skips_previously_decided_rows(tmp_path: Path) -> None:
    """Load only review candidates without a recorded decision."""
    review_csv = tmp_path / "review_needed.csv"
    review_csv.write_text(
        "\n".join(
            [
                "chapter_file,chapter_index,title,line_number,raw_text,normalized_text,final_score,matched_seed,decision",
                "chapters/001.md,1,Chapter 1,12,Black beetle flesh eaten.,black beetle flesh eaten.,0.61,Seed one,review",
                "chapters/002.md,2,Chapter 2,24,Mutant creature killed.,mutant creature killed.,0.52,Seed two,review",
            ]
        ),
        encoding="utf-8",
    )
    decisions_path = tmp_path / "voice_review_decisions.jsonl"
    record_decision(
        decisions_path,
        ReviewDecision(
            candidate_id="chapters/001.md:12:black beetle flesh eaten.",
            action=ReviewAction.ACCEPT,
            raw_text="Black beetle flesh eaten.",
            chapter_file="chapters/001.md",
            line_number=12,
        ),
    )

    pending = load_pending_candidates(review_csv, decisions_path)

    assert [candidate.raw_text for candidate in pending] == ["Mutant creature killed."]


def test_append_accepted_seed_uses_normalized_dedupe(tmp_path: Path) -> None:
    """Append accepted seed lines only when they are not already present."""
    seed_path = tmp_path / "voice_of_the_world.txt"
    seed_path.write_text('"Black beetle flesh eaten."\n', encoding="utf-8")

    first = append_accepted_seed(seed_path, "  Black beetle flesh eaten.  ")
    second = append_accepted_seed(seed_path, "Mutant creature killed.")

    assert first is False
    assert second is True
    assert seed_path.read_text(encoding="utf-8").splitlines() == [
        '"Black beetle flesh eaten."',
        '"Mutant creature killed."',
    ]


def test_record_decision_writes_jsonl(tmp_path: Path) -> None:
    """Persist a review decision as an append-only JSONL record."""
    decisions_path = tmp_path / "voice_review_decisions.jsonl"
    decision = ReviewDecision(
        candidate_id="chapters/002.md:24:mutant creature killed.",
        action=ReviewAction.REJECT,
        raw_text="Mutant creature killed.",
        chapter_file="chapters/002.md",
        line_number=24,
        note="not the voice",
    )

    record_decision(decisions_path, decision)

    rows = [json.loads(line) for line in decisions_path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "candidate_id": "chapters/002.md:24:mutant creature killed.",
            "action": "reject",
            "raw_text": "Mutant creature killed.",
            "chapter_file": "chapters/002.md",
            "line_number": 24,
            "note": "not the voice",
        }
    ]


@pytest.mark.anyio
async def test_textual_app_accepts_current_candidate(tmp_path: Path) -> None:
    """Accept the current candidate through the Textual key binding."""
    review_csv = tmp_path / "review_needed.csv"
    review_csv.write_text(
        "\n".join(
            [
                "chapter_file,chapter_index,title,line_number,raw_text,normalized_text,final_score,tfidf_similarity,fuzzy_similarity,keyword_score,matched_seed,category,decision",
                "chapters/001.md,1,Chapter 1,12,Black beetle flesh eaten.,black beetle flesh eaten.,0.61,0.5,0.8,0.7,Seed one,geno_point_gain,review",
            ]
        ),
        encoding="utf-8",
    )
    seed_path = tmp_path / "voice_of_the_world.txt"
    seed_path.write_text("", encoding="utf-8")
    decisions_path = tmp_path / "voice_review_decisions.jsonl"
    app = VoiceReviewApp(review_csv, seed_path, decisions_path)

    async with app.run_test() as pilot:
        await pilot.press("a")
        await pilot.pause()

    assert seed_path.read_text(encoding="utf-8") == '"Black beetle flesh eaten."\n'
    rows = [json.loads(line) for line in decisions_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["action"] == "accept"


@pytest.mark.anyio
async def test_textual_app_accepts_edited_candidate_text(tmp_path: Path) -> None:
    """Edit the current candidate before accepting it through the TUI."""
    review_csv = tmp_path / "review_needed.csv"
    review_csv.write_text(
        "\n".join(
            [
                "chapter_file,chapter_index,title,line_number,raw_text,normalized_text,final_score,tfidf_similarity,fuzzy_similarity,keyword_score,matched_seed,category,decision",
                "chapters/001.md,1,Chapter 1,12,Overly long black beetle flesh eaten.,overly long black beetle flesh eaten.,0.61,0.5,0.8,0.7,Seed one,geno_point_gain,review",
            ]
        ),
        encoding="utf-8",
    )
    seed_path = tmp_path / "voice_of_the_world.txt"
    seed_path.write_text("", encoding="utf-8")
    decisions_path = tmp_path / "voice_review_decisions.jsonl"
    app = VoiceReviewApp(review_csv, seed_path, decisions_path)

    async with app.run_test() as pilot:
        await pilot.press("e")
        editor = app.query_one("#editor", Input)
        editor.value = "Black beetle flesh eaten."
        await pilot.press("enter")
        await pilot.press("a")
        await pilot.pause()

    assert seed_path.read_text(encoding="utf-8") == '"Black beetle flesh eaten."\n'
    rows = [json.loads(line) for line in decisions_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["raw_text"] == "Black beetle flesh eaten."
