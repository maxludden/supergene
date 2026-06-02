"""Core helpers for reviewing Voice of the World candidate lines."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from supergene.find_voice_lines import clean_display_text, normalize_text


class ReviewAction(StrEnum):
    """Available decisions for a reviewed Voice of the World candidate."""

    ACCEPT = "accept"
    REJECT = "reject"
    SKIP = "skip"


@dataclass(frozen=True)
class ReviewCandidate:
    """A candidate line loaded from a Voice of the World review report.

    Attributes:
        candidate_id: Stable identifier used to resume review progress.
        chapter_file: Path to the source chapter file.
        chapter_index: Parsed chapter index when available.
        title: Chapter title when available.
        line_number: One-based source line number.
        raw_text: Candidate line as displayed to the reviewer.
        normalized_text: Normalized candidate text used for deduplication.
        context_before: Previous source line when present in the report.
        context_after: Following source line when present in the report.
        final_score: Hybrid match score from the search report.
        tfidf_similarity: TF-IDF similarity against the closest seed.
        fuzzy_similarity: Fuzzy similarity against the closest seed.
        keyword_score: Rule-based keyword score.
        matched_seed: Closest known seed line.
        category: Candidate category assigned by the search report.
    """

    candidate_id: str
    chapter_file: str
    chapter_index: int | None
    title: str | None
    line_number: int
    raw_text: str
    normalized_text: str
    context_before: str
    context_after: str
    final_score: float
    tfidf_similarity: float
    fuzzy_similarity: float
    keyword_score: float
    matched_seed: str
    category: str


@dataclass(frozen=True)
class ReviewDecision:
    """A persisted review decision for a Voice of the World candidate.

    Attributes:
        candidate_id: Stable candidate identifier.
        action: Review decision selected by the user.
        raw_text: Candidate line shown to the user.
        chapter_file: Path to the chapter containing the candidate.
        line_number: One-based source line number.
        note: Optional reviewer note.
    """

    candidate_id: str
    action: ReviewAction
    raw_text: str
    chapter_file: str
    line_number: int
    note: str = ""


def default_decisions_path(review_path: Path) -> Path:
    """Return the default JSONL decision path beside a review report.

    Args:
        review_path: Path to a review report CSV.

    Returns:
        Path for persisted review decisions.
    """

    return review_path.with_name("voice_review_decisions.jsonl")


def load_pending_candidates(review_path: Path, decisions_path: Path | None = None) -> list[ReviewCandidate]:
    """Load review candidates that do not already have a saved decision.

    Args:
        review_path: CSV file produced by the Voice of the World search.
        decisions_path: Optional JSONL file containing prior decisions.

    Returns:
        Review candidates still awaiting a decision.
    """

    resolved_decisions_path = decisions_path or default_decisions_path(review_path)
    decided_ids = load_decided_candidate_ids(resolved_decisions_path)
    candidates: list[ReviewCandidate] = []

    with review_path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            candidate = candidate_from_row(row)
            if candidate.candidate_id not in decided_ids:
                candidates.append(candidate)

    return candidates


def load_decided_candidate_ids(decisions_path: Path) -> set[str]:
    """Load candidate IDs that already have persisted decisions.

    Args:
        decisions_path: JSONL decision file.

    Returns:
        Set of candidate IDs with saved decisions.
    """

    if not decisions_path.exists():
        return set()

    decided_ids: set[str] = set()
    for line in decisions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id:
            decided_ids.add(candidate_id)
    return decided_ids


def candidate_from_row(row: dict[str, str]) -> ReviewCandidate:
    """Convert a CSV report row into a typed review candidate.

    Args:
        row: CSV row from `review_needed.csv`.

    Returns:
        Typed candidate with parsed numeric fields and a stable ID.
    """

    chapter_file = row.get("chapter_file", "")
    line_number = _parse_int(row.get("line_number")) or 0
    raw_text = clean_display_text(row.get("raw_text", ""))
    normalized = row.get("normalized_text") or normalize_text(raw_text)

    return ReviewCandidate(
        candidate_id=build_candidate_id(chapter_file, line_number, normalized),
        chapter_file=chapter_file,
        chapter_index=_parse_int(row.get("chapter_index")),
        title=row.get("title") or None,
        line_number=line_number,
        raw_text=raw_text,
        normalized_text=normalized,
        context_before=clean_display_text(row.get("context_before", "")),
        context_after=clean_display_text(row.get("context_after", "")),
        final_score=_parse_float(row.get("final_score")),
        tfidf_similarity=_parse_float(row.get("tfidf_similarity")),
        fuzzy_similarity=_parse_float(row.get("fuzzy_similarity")),
        keyword_score=_parse_float(row.get("keyword_score")),
        matched_seed=clean_display_text(row.get("matched_seed", "")),
        category=row.get("category") or "unknown_voice",
    )


def build_candidate_id(chapter_file: str, line_number: int, normalized_text: str) -> str:
    """Build a stable ID for a candidate row.

    Args:
        chapter_file: Source chapter path.
        line_number: One-based source line number.
        normalized_text: Normalized candidate text.

    Returns:
        Stable candidate identifier.
    """

    return f"{chapter_file}:{line_number}:{normalized_text}"


def append_accepted_seed(seed_path: Path, raw_text: str) -> bool:
    """Append a reviewed Voice line to the seed file if it is new.

    Args:
        seed_path: Path to `voice_of_the_world.txt`.
        raw_text: Accepted candidate text.

    Returns:
        True when the seed file was changed, otherwise False.
    """

    candidate = clean_display_text(raw_text)
    candidate_key = normalize_text(candidate)
    existing_keys = {
        normalize_text(clean_display_text(line))
        for line in seed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if candidate_key in existing_keys:
        return False

    current_text = seed_path.read_text(encoding="utf-8") if seed_path.exists() else ""
    needs_leading_newline = bool(current_text) and not current_text.endswith("\n")
    with seed_path.open("a", encoding="utf-8") as file:
        if needs_leading_newline:
            file.write("\n")
        file.write(f'"{candidate}"\n')
    return True


def record_decision(decisions_path: Path, decision: ReviewDecision) -> None:
    """Append a review decision to a JSONL audit log.

    Args:
        decisions_path: JSONL path to write.
        decision: Decision to append.
    """

    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    row = asdict(decision)
    row["action"] = decision.action.value
    with decisions_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _parse_int(value: str | None) -> int | None:
    """Parse an optional integer field from a CSV row."""

    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_float(value: str | None) -> float:
    """Parse an optional float field from a CSV row."""

    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0
