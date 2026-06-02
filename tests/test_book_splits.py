"""Tests for the canonical *Super Gene* book split plan."""

from __future__ import annotations

import re
from pathlib import Path

from supergene.book_splits import BOOK_SPLITS, render_super_gene_book_splits_markdown


def _chapter_word_count(chapter_path: Path) -> int:
    """Count approximate words in a converted chapter body."""

    text = chapter_path.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1]
    return len(re.findall(r"\b\w+[\w’'-]*\b", body))


def test_super_gene_book_splits_match_the_planned_ranges() -> None:
    """Verify the canonical split uses the intended ten ranges and titles."""

    assert [(split.number, split.name, split.start_chapter, split.end_chapter) for split in BOOK_SPLITS] == [
        (1, "First God's Sanctuary", 1, 424),
        (2, "Second God's Sanctuary", 425, 882),
        (3, "Third God's Sanctuary", 883, 1338),
        (4, "Fourth and Fifth God's Sanctuaries", 1339, 1712),
        (5, "Planet Kate and Narrow Moon", 1713, 2209),
        (6, "Ice Blue Knights", 2210, 2467),
        (7, "Fighting God", 2468, 2719),
        (8, "Empty God's Decision", 2720, 2969),
        (9, "Breaking Point", 2970, 3217),
        (10, "The Third Sky", 3218, 3463),
    ]


def test_post_expedition_books_are_balanced_in_the_current_corpus() -> None:
    """Check that the post-expedition books stay nearly equal in size."""

    chapters_dir = Path("converted/Super Gene/chapters")
    ranges = [(2210, 2467), (2468, 2719), (2720, 2969), (2970, 3217), (3218, 3463)]
    word_counts = []
    for start, end in ranges:
        total = 0
        for chapter_path in sorted(chapters_dir.glob("*.md")):
            chapter_index = int(chapter_path.name.split("-", 1)[0])
            if start <= chapter_index <= end:
                total += _chapter_word_count(chapter_path)
        word_counts.append(total)

    assert max(word_counts) - min(word_counts) < 2000


def test_markdown_renderer_lists_every_book() -> None:
    """Ensure the human-readable manifest includes every planned book."""

    markdown = render_super_gene_book_splits_markdown()
    assert markdown.startswith("# Super Gene Book Split Plan")
    for split in BOOK_SPLITS:
        assert split.name in markdown
        assert f"Chapters {split.start_chapter}-{split.end_chapter}" in markdown
