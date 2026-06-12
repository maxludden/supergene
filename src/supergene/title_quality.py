"""Find likely title spelling issues in converted Markdown chapter frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass(frozen=True)
class TitleSpellingIssue:
    """Likely missing terminal letter in a chapter title.

        Attributes:
            path: Markdown chapter file containing the issue.
            title: Existing title read from frontmatter.
            suggestion: Suggested corrected title.
        """

    chapter_path: Path
    title: str
    word: str
    suggestion: str


DEFAULT_TERMINAL_T_LEXICON = {
    "beast",
    "fight",
    "first",
    "ghost",
    "giant",
    "light",
    "night",
    "past",
    "right",
    "secret",
    "spirit",
    "test",
    "thirst",
    "trust",
    "want",
}

# The lexicon is deliberately small. It catches common OCR/conversion losses
# such as "figh" -> "fight" without turning arbitrary title words into guesses.

def find_missing_terminal_t_title_issues(
    chapters_dir: str | Path,
    *,
    lexicon: set[str] | None = None,
) -> list[TitleSpellingIssue]:
    """Find missing terminal t title issues."""
    logger.trace("Entering find_missing_terminal_t_title_issues")
    words = {word.lower() for word in (lexicon or DEFAULT_TERMINAL_T_LEXICON)}
    issues: list[TitleSpellingIssue] = []
    for chapter_path in sorted(Path(chapters_dir).glob("*.md")):
        title = _frontmatter_title(chapter_path.read_text(encoding="utf-8"))
        if not title:
            continue
        for word in _title_words(title):
            candidate = f"{word}t"
            # Only suggest a repair when adding a terminal "t" creates a known
            # word from the curated lexicon.
            if candidate.lower() in words:
                issues.append(
                    TitleSpellingIssue(
                        chapter_path=chapter_path,
                        title=title,
                        word=word,
                        suggestion=_match_case(word, candidate),
                    )
                )
    return issues


def _frontmatter_title(markdown: str) -> str | None:
    """Extract a title value from Markdown YAML frontmatter."""
    logger.trace("Entering _frontmatter_title")
    if not markdown.startswith("---\n"):
        return None
    end = markdown.find("\n---", 4)
    if end == -1:
        return None
    frontmatter = markdown[4:end]
    for line in frontmatter.splitlines():
        if not line.startswith("title:"):
            continue
        value = line.split(":", 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value.strip() or None
    return None


def _title_words(title: str) -> list[str]:
    """Return normalized words from a chapter title."""
    logger.trace("Entering _title_words")
    title_without_chapter_number = re.sub(r"\bChapter\s+\d+\b", " ", title, flags=re.IGNORECASE)
    return re.findall(r"[A-Za-z][A-Za-z'’\-]*", title_without_chapter_number)


def _match_case(source: str, suggestion: str) -> str:
    """Match a spelling suggestion to the casing of the source word."""
    logger.trace("Entering _match_case")
    if source.isupper():
        return suggestion.upper()
    if source[:1].isupper():
        return suggestion.capitalize()
    return suggestion.lower()
