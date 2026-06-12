"""Canonical book split definitions for the converted *Super Gene* corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass(frozen=True, slots=True)
class BookSplit:
    """Describe one contiguous chapter range in the planned book split.

    Attributes:
        number: One-based book number in the split plan.
        name: Human-readable book title.
        start_chapter: Inclusive chapter number at which the book starts.
        end_chapter: Inclusive chapter number at which the book ends.
    """

    number: int
    name: str
    start_chapter: int
    end_chapter: int


BOOK_SPLITS: tuple[BookSplit, ...] = (
    BookSplit(1, r"First God's Sanctuary", 1, 424),
    BookSplit(2, "Second God's Sanctuary", 425, 882),
    BookSplit(3, "Third God's Sanctuary", 883, 1338),
    BookSplit(4, "Fourth and Fifth God's Sanctuaries", 1339, 1712),
    BookSplit(5, "Planet Kate and Narrow Moon", 1713, 2209),
    BookSplit(6, "The Extreme King", 2210, 2467),
    BookSplit(7, "The Very High and Outer Sky", 2468, 2719),
    BookSplit(8, "War Against the Gods", 2720, 2969),
    BookSplit(9, "God Spirit Blood-Pulse", 2970, 3217),
    BookSplit(10, "The Thirty-Three Skies", 3218, 3463),
)


def get_super_gene_book_splits() -> list[BookSplit]:
    """Return the canonical *Super Gene* book split plan.

    Returns:
        A new list containing the ten planned book ranges.
    """
    logger.trace("Entering get_super_gene_book_splits")

    # Return a list copy so callers can sort/filter without mutating the
    # canonical tuple used by reports and tests.
    return list(BOOK_SPLITS)


def render_super_gene_book_splits_markdown() -> str:
    """Render the canonical split plan as a Markdown table.

    Returns:
        A Markdown document that can be written to disk or embedded in docs.
    """
    logger.trace("Entering render_super_gene_book_splits_markdown")

    lines = [
        "# Super Gene Book Split Plan",
        "",
        "| Book | Range | Title |",
        "| --- | --- | --- |",
    ]
    for split in BOOK_SPLITS:
        lines.append(
            f"| {split.number} | Chapters {split.start_chapter}-{split.end_chapter} | {split.name} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_super_gene_book_splits_markdown(output_path: Path) -> None:
    """Write the canonical split plan to a Markdown file.

    Args:
        output_path: Destination path for the Markdown document.
    """
    logger.trace("Entering write_super_gene_book_splits_markdown")

    output_path.write_text(render_super_gene_book_splits_markdown() + "\n", encoding="utf-8")
