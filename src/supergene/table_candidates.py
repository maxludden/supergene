"""Detect chapter lines that may render more clearly as structured HTML tables."""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from loguru import logger


@dataclass(frozen=True)
class TableCandidate:
    """Potential table or structured block found in a chapter.

        Attributes:
            kind: Candidate category used by reports.
            chapter_path: Markdown chapter containing the candidate.
            start_line: One-based starting line number.
            end_line: One-based ending line number.
            original_text: Source text from the chapter.
            proposed_html: Suggested HTML replacement.
            confidence: Heuristic confidence score between zero and one.
        """

    kind: str
    chapter_path: Path
    start_line: int
    end_line: int
    original_text: str
    proposed_html: str
    confidence: float


STAT_KEYS = {
    "status",
    "life span",
    "lifespan",
    "required for evolution",
    "requirements for evolution",
    "geno points gained",
    "beast soul gained",
    "beast souls gained",
    "next evolution requirement",
    "owned geno points",
    "level",
    "progress",
    "gene potential",
    "gene level",
    "gene class",
    "compatibility",
    "overall",
    "skills",
    "target",
}

# The table detector is intentionally heuristic: converted webnovel chapters do
# not contain reliable source markup, so each candidate carries a confidence and
# the report remains review-oriented rather than auto-rewriting chapters.

def find_table_candidates(chapters_dir: str | Path) -> list[TableCandidate]:
    """Find table candidates."""
    logger.trace("Entering find_table_candidates")
    root = Path(chapters_dir)
    candidates: list[TableCandidate] = []
    for chapter_path in sorted(root.glob("*.md")):
        lines = chapter_path.read_text(encoding="utf-8").splitlines()
        candidates.extend(_stat_block_candidates(chapter_path, lines))
        # Later passes receive existing candidates so a line already claimed by
        # a stat block is not duplicated as a single-line notification/entity.
        candidates.extend(_voice_of_world_candidates(chapter_path, lines, candidates))
        candidates.extend(_entity_line_candidates(chapter_path, lines, candidates))
    return sorted(candidates, key=lambda candidate: (str(candidate.chapter_path), candidate.start_line, candidate.kind))


def write_table_candidate_report(chapters_dir: str | Path, output_path: str | Path) -> list[TableCandidate]:
    """Write table candidate report output."""
    logger.trace("Entering write_table_candidate_report")
    candidates = find_table_candidates(chapters_dir)
    payload = {
        "summary": {
            "chapters_dir": str(Path(chapters_dir)),
            "total_candidates": len(candidates),
            "by_kind": _count_by_kind(candidates),
        },
        "candidates": [_candidate_json(candidate) for candidate in candidates],
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return candidates


def _stat_block_candidates(chapter_path: Path, lines: list[str]) -> list[TableCandidate]:
    """Find multi-line stat blocks that can become HTML tables."""
    logger.trace("Entering _stat_block_candidates")
    candidates: list[TableCandidate] = []
    index = 0
    while index < len(lines):
        parsed = _parse_stat_line(lines[index])
        if not parsed:
            index += 1
            continue

        block: list[tuple[int, str, str]] = [(index, parsed[0], parsed[1])]
        cursor = index + 1
        pending_blank_lines = 0
        while cursor < len(lines):
            if not lines[cursor].strip():
                # Allow sparse stat blocks with blank lines between rows; track
                # trailing blanks so the candidate range does not include them.
                pending_blank_lines += 1
                cursor += 1
                continue
            next_parsed = _parse_stat_line(lines[cursor])
            if not next_parsed:
                break
            block.append((cursor, next_parsed[0], next_parsed[1]))
            cursor += 1
            pending_blank_lines = 0

        # Two colon lines appear frequently in prose; requiring three rows keeps
        # false positives down while still catching actual RPG-style stat cards.
        if len(block) >= 3:
            end_index = block[-1][0]
            original = "\n".join(lines[line_index] for line_index in range(block[0][0], end_index + 1))
            candidates.append(
                TableCandidate(
                    kind="stat_block",
                    chapter_path=chapter_path,
                    start_line=block[0][0] + 1,
                    end_line=end_index + 1,
                    original_text=original,
                    proposed_html=_stat_block_html([(field, value) for _line, field, value in block]),
                    confidence=0.9,
                )
            )
            index = cursor - pending_blank_lines
        else:
            index += 1
    return candidates


def _voice_of_world_candidates(
    chapter_path: Path,
    lines: list[str],
    existing: list[TableCandidate],
) -> list[TableCandidate]:
    """Find Voice of the World notification lines not covered by other candidates."""
    logger.trace("Entering _voice_of_world_candidates")
    covered = {
        line_number
        for candidate in existing
        for line_number in range(candidate.start_line, candidate.end_line + 1)
    }
    candidates: list[TableCandidate] = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if line_number in covered or not _looks_like_voice_of_world_line(line):
            continue
        text = _clean_markup(line)
        candidates.append(
            TableCandidate(
                kind="voice_of_world",
                chapter_path=chapter_path,
                start_line=line_number,
                end_line=line_number,
                original_text=line,
                proposed_html=_voice_of_world_html(text),
                confidence=0.8,
            )
        )
    return candidates


def _entity_line_candidates(
    chapter_path: Path,
    lines: list[str],
    existing: list[TableCandidate],
) -> list[TableCandidate]:
    """Find entity description lines that can become HTML tables."""
    logger.trace("Entering _entity_line_candidates")
    covered = {
        line_number
        for candidate in existing
        for line_number in range(candidate.start_line, candidate.end_line + 1)
    }
    candidates: list[TableCandidate] = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if line_number in covered:
            continue
        if not _looks_like_entity_line(line):
            continue
        text = _clean_markup(line)
        kind = _entity_kind(text)
        if not kind:
            continue
        candidates.append(
            TableCandidate(
                kind=kind,
                chapter_path=chapter_path,
                start_line=line_number,
                end_line=line_number,
                original_text=line,
                proposed_html=_entity_html(kind, text),
                confidence=0.75,
            )
        )
    return candidates


def _parse_stat_line(line: str) -> tuple[str, str] | None:
    """Parse stat line values."""
    logger.trace("Entering _parse_stat_line")
    text = _clean_markup(line)
    if not text or text.startswith("#") or ":" not in text:
        return None
    field, value = [part.strip(" .") for part in text.split(":", 1)]
    if not field or not value:
        return None
    normalized = field.lower()
    if normalized in STAT_KEYS or normalized.startswith(("han sen", "king spirits", "super creatures")):
        return field, value
    if normalized.startswith("type of ") and any(token in normalized for token in ("beast soul", "geno core", "gene race", "god spirit")):
        return field, value
    return None


def _entity_kind(text: str) -> str | None:
    """Classify a cleaned entity line by table candidate kind."""
    logger.trace("Entering _entity_kind")
    lowered = text.lower()
    if ":" in text:
        field_text = text.split(":", 1)[0].strip()
        if not _looks_like_compact_label(field_text):
            return None
        field = field_text.lower()
        # Explicit labels are the strongest signal because the converted text
        # already resembles a key/value row.
        if "beast soul" in field:
            return "beast_soul"
        if "god spirit" in field:
            return "god_spirit"
        if "gene race" in field:
            return "gene_race"
        if "geno core" in field:
            return "geno_core"
    if "god spirit hunted" in lowered or "found god spirit gene" in lowered:
        return "god_spirit"
    if "god spirit" in lowered and any(word in lowered for word in ("became", "become", "new", "hunted", "found", "blood-pulse")):
        return "god_spirit"
    if "gene race" in lowered and any(word in lowered for word in ("mutant", "god", "ultimate", "juvenile", "became", "evolve")):
        return "gene_race"
    if "geno core" in lowered:
        return "geno_core"
    return None


def _stat_block_html(rows: list[tuple[str, str]]) -> str:
    """Render stat block rows as a two-column HTML table."""
    logger.trace("Entering _stat_block_html")
    body = "\n".join(
        f"    <tr><td>{html.escape(field)}</td><td>{html.escape(value)}</td></tr>" for field, value in rows
    )
    return "<table>\n  <thead><tr><th>Field</th><th>Value</th></tr></thead>\n  <tbody>\n" + body + "\n  </tbody>\n</table>"


def _entity_html(kind: str, text: str) -> str:
    """Render one entity candidate as a two-column HTML table."""
    logger.trace("Entering _entity_html")
    label = kind.replace("_", " ").title()
    return (
        "<table>\n"
        "  <thead><tr><th>Type</th><th>Description</th></tr></thead>\n"
        "  <tbody>\n"
        f"    <tr><td>{html.escape(label)}</td><td>{html.escape(text)}</td></tr>\n"
        "  </tbody>\n"
        "</table>"
    )


def _voice_of_world_html(text: str) -> str:
    """Render a Voice of the World line as emphasized HTML."""
    logger.trace("Entering _voice_of_world_html")
    return f'<div class="voice-of-world"><em>{html.escape(text)}</em></div>'


def _looks_like_entity_line(line: str) -> bool:
    """Return whether text matches the entity line heuristic."""
    logger.trace("Entering _looks_like_entity_line")
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "---")):
        return False
    text = _clean_markup(line)
    if not text:
        return False

    if ":" in text:
        field_text = text.split(":", 1)[0].strip()
        if not _looks_like_compact_label(field_text):
            return False
        field = field_text.lower()
        return any(token in field for token in ("beast soul", "god spirit", "gene race", "geno core"))

    lowered = text.lower()
    notification = stripped.startswith("**") and stripped.endswith("**")
    action_words = ("gained", "obtained", "hunted", "found", "became", "become", "evolved")
    entity_words = ("god spirit", "gene race", "geno core")
    # Bold notification lines without a colon can still be entity events; require
    # both an entity term and an action verb so ordinary bold prose is ignored.
    if notification and any(entity in lowered for entity in entity_words) and any(word in lowered for word in action_words):
        return True

    return False


def _looks_like_voice_of_world_line(line: str) -> bool:
    """Return whether text matches the voice of world line heuristic."""
    logger.trace("Entering _looks_like_voice_of_world_line")
    stripped = line.strip()
    if not stripped.startswith("**") or not stripped.endswith("**"):
        return False
    text = _clean_markup(line)
    lowered = text.lower()
    dialogue_starters = ("i ", "what ", "who ", "why ", "how ", "go ", "didn", "can ", "is ", "are ")
    # Voice lines are declarative system notices. Questions/exclamations and
    # common first-person/dialogue starts are usually character speech.
    if lowered.startswith(dialogue_starters) or "?" in text or "!" in text:
        return False

    if lowered.startswith(("killed god spirit", "god spirit hunted")):
        return True
    if re.match(r"^[\w'’\-]+(?: [\w'’\-]+){0,5} (?:killed|hunted)(?:[.:;]|$)", lowered):
        return True
    if re.match(r"^[\w'’\-]+(?: [\w'’\-]+){0,5} (?:flesh|meat) eaten(?:[.:;]|$)", lowered):
        return True
    if re.match(r"^[\w'’\-]+(?: [\w'’\-]+){0,7} beast soul (?:gained|obtained)(?:[.:;]|$)", lowered):
        return True
    if re.match(r"^[\w'’\-]+(?: [\w'’\-]+){0,7} geno core (?:received|obtained|destroyed|shattered|unobtained)(?:[.:;]|$)", lowered):
        return True
    if "xenogeneic gene found" in lowered or "god spirit gene" in lowered:
        return True
    if "geno points gained" in lowered and len(text.split()) <= 12:
        return True
    return False


def _looks_like_compact_label(field: str) -> bool:
    """Return whether text matches the compact label heuristic."""
    logger.trace("Entering _looks_like_compact_label")
    if not field or len(field) > 90:
        return False
    if any(mark in field for mark in ".!?;"):
        return False
    return len(field.split()) <= 10


def _clean_markup(line: str) -> str:
    """Strip lightweight Markdown wrappers from a source line."""
    logger.trace("Entering _clean_markup")
    text = line.strip()
    text = re.sub(r"^#+\s*", "", text)
    text = text.strip("*_` ")
    text = text.strip("“”\"")
    return text.strip()


def _candidate_json(candidate: TableCandidate) -> dict[str, object]:
    """Convert a table candidate into JSON-serializable data."""
    logger.trace("Entering _candidate_json")
    payload = asdict(candidate)
    payload["chapter_path"] = str(candidate.chapter_path)
    return payload


def _count_by_kind(candidates: list[TableCandidate]) -> dict[str, int]:
    """Count table candidates by kind for report summaries."""
    logger.trace("Entering _count_by_kind")
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.kind] = counts.get(candidate.kind, 0) + 1
    return counts
