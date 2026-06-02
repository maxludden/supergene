"""Canonical book split definitions for the converted *Super Gene* corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    BookSplit(1, "First God's Sanctuary", 1, 424),
    BookSplit(2, "Second God's Sanctuary", 425, 882),
    BookSplit(3, "Third God's Sanctuary", 883, 1338),
    BookSplit(4, "Fourth and Fifth God's Sanctuaries", 1339, 1712),
    BookSplit(5, "Planet Kate and Narrow Moon", 1713, 2209),
    BookSplit(6, "Ice Blue Knights", 2210, 2467),
    BookSplit(7, "Fighting God", 2468, 2719),
    BookSplit(8, "Empty God's Decision", 2720, 2969),
    BookSplit(9, "Breaking Point", 2970, 3217),
    BookSplit(10, "The Third Sky", 3218, 3463),
)


def get_super_gene_book_splits() -> list[BookSplit]:
    """Return the canonical *Super Gene* book split plan.

    Returns:
        A new list containing the ten planned book ranges.
    """

    return list(BOOK_SPLITS)


def render_super_gene_book_splits_markdown() -> str:
    """Render the canonical split plan as a Markdown table.

    Returns:
        A Markdown document that can be written to disk or embedded in docs.
    """

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

    output_path.write_text(render_super_gene_book_splits_markdown() + "\n", encoding="utf-8")
