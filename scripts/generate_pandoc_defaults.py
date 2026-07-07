"""Generate Pandoc defaults files for the split *Super Gene* books."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re
import shutil
import zipfile
from loguru import logger
from rapidfuzz import fuzz

from supergene.find_voice_lines import clean_display_text, keyword_score, load_seed_lines, normalize_text
from supergene.logging import configure_logging


@dataclass(frozen=True, slots=True)
class BookDefaults:
    """Describe one Pandoc defaults file to generate.

    Attributes:
        number: One-based book number.
        title: Display title for the book.
        start_index: Inclusive numeric chapter-file prefix at which the book starts.
        end_index: Inclusive numeric chapter-file prefix at which the book ends.
        slug: Filesystem-safe slug used for defaults, cover, and output paths.
    """

    number: int
    title: str
    start_index: int
    end_index: int
    slug: str


BOOKS: tuple[BookDefaults, ...] = (
    BookDefaults(1, "First God's Sanctuary", 1, 424, "first-gods-sanctuary"),
    BookDefaults(2, "Second God's Sanctuary", 425, 882, "second-gods-sanctuary"),
    BookDefaults(3, "Third God's Sanctuary", 883, 1338, "third-gods-sanctuary"),
    BookDefaults(
        4,
        "Fourth and Fifth God's Sanctuaries",
        1339,
        1712,
        "fourth-and-fifth-gods-sanctuaries",
    ),
    BookDefaults(5, "Planet Kate and Narrow Moon", 1713, 2209, "planet-kate-and-narrow-moon"),
    BookDefaults(6, "The Extreme King", 2210, 2467, "the-extreme-king"),
    BookDefaults(7, "The Very High and Outer Sky", 2468, 2719, "the-very-high-and-outer-sky"),
    BookDefaults(8, "War Against the Gods", 2720, 2969, "war-against-the-gods"),
    BookDefaults(9, "God Spirit Blood-Pulse", 2970, 3217, "god-spirit-blood-pulse"),
    BookDefaults(10, "The Thirty-Three Skies", 3218, 3463, "the-thirty-three-skies"),
)

COPYRIGHT_NOTICE = (
    "This is a private reading edition of Super Gene prepared for personal use. "
    "Original text by Twelve-Winged Dark Seraphim. "
    "This edition is not for sale or distribution."
)

CHAPTER_HEADING_PATTERN = re.compile(r"^#\s+Chapter\s+\d+.*$", re.MULTILINE)
SOURCE_COMMENT_PATTERN = re.compile(r"^\s*<!--\s*source:[^>]*-->\s*$", re.MULTILINE)
TITLE_METADATA_PATTERN = re.compile(r'^title:\s*["\']?(?P<title>.+?)["\']?\s*$', re.MULTILINE)
CHAPTER_TITLE_PATTERN = re.compile(r"^Chapter\s+\d+\s*:?\s*(?P<title>.+)$", re.IGNORECASE)
STANDALONE_BOLD_QUOTE_PATTERN = re.compile(r"^\s*\*\*(?P<quote>[“\"].+[”\"])\*\*\s*$")
BOLD_QUOTE_PATTERN = re.compile(r"\*\*(?P<quote>[“\"].+?[”\"])\*\*")
INLINE_VOICE_CONTEXT_PATTERN = re.compile(
    r"\b(heard|hearing|hear|hears)\s+the\s+voice\b|\bvoice\s+(say|saying|telling|told)\b",
    re.IGNORECASE,
)
PROFILE_ROW_PATTERN = re.compile(
    r"^(?P<label>Han Sen|Status|Life span|Lifespan|Required for evolution|"
    r"Requirement for next evolution|Requirement for next revolution|"
    r"Requirements for evolution|Geno points needed for evolution|Geno points gained|Geno points owned|"
    r"Beast souls? gained):\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
PROFILE_LABEL_ONLY_PATTERN = re.compile(r"^(?P<label>Han Sen):\s*$", re.IGNORECASE)
MARKDOWN_PROFILE_ROW_PATTERN = re.compile(r"^\|\s*(?P<label>[^|]+?)\s*\|\s*(?P<value>[^|]+?)\s*\|\s*$")
START_READING_LINK = '<a href="{href}" epub:type="bodymatter">Start Reading</a>'
START_READING_REFERENCE = '<reference type="text" title="Start Reading" href="{href}" />'
VOICE_MATCH_KEYWORD_THRESHOLD = 0.25
VOICE_MATCH_FUZZY_THRESHOLD = 0.78
PROFILE_TABLE_MIN_ROWS = 2
GENO_POINT_TYPES = ("Primitive", "Ordinary", "Mutant", "Sacred-Blood")
SUPER_GENO_POINT_TYPES = (*GENO_POINT_TYPES, "Super")
FULL_WIDTH_PROFILE_LABELS = {
    "required for evolution",
    "beast soul gained",
    "beast souls gained",
}
GENO_POINT_ALIASES = {
    "Primitive": ("Primitive", ""),
    "Ordinary": ("Ordinary",),
    "Mutant": ("Mutant",),
    "Sacred-Blood": ("Sacred-Blood", "Sacred Blood", "Sacred"),
    "Super": ("Super",),
}


@dataclass(frozen=True, slots=True)
class VoiceLineMatcher:
    """Match Voice of the World notifications against curated seed examples.

    Attributes:
        seed_lines: Curated Voice of the World examples.
        normalized_seed_lines: Normalized examples used for exact matching.
    """

    seed_lines: tuple[str, ...]
    normalized_seed_lines: frozenset[str]

    @classmethod
    def from_seed_path(cls, seed_path: Path) -> VoiceLineMatcher:
        """Create a matcher from a `voice_of_the_world.txt` seed file.

        Args:
            seed_path: Path to the curated seed examples.

        Returns:
            A seed-aware Voice of the World matcher.
        """
        logger.info(f"Loading Voice of the World seeds from {seed_path}")

        return cls.from_seed_lines(load_seed_lines(seed_path))

    @classmethod
    def from_seed_lines(cls, seed_lines: list[str]) -> VoiceLineMatcher:
        """Create a matcher from seed example strings.

        Args:
            seed_lines: Curated Voice of the World examples.

        Returns:
            A seed-aware Voice of the World matcher.
        """
        logger.trace("Creating Voice of the World matcher from seed lines")

        cleaned_seed_lines = tuple(clean_display_text(line) for line in seed_lines if clean_display_text(line))
        normalized = frozenset(normalize_text(line) for line in cleaned_seed_lines)
        return cls(seed_lines=cleaned_seed_lines, normalized_seed_lines=normalized)

    def is_voice_line(self, text: str) -> bool:
        """Return whether text is likely a Voice of the World notification.

        Args:
            text: Candidate notification text.

        Returns:
            True when the candidate matches curated seeds or a conservative
            keyword-plus-fuzzy threshold.
        """
        logger.trace("Matching candidate Voice of the World text")

        cleaned = clean_display_text(text)
        normalized = normalize_text(cleaned)
        if not normalized:
            return False
        if normalized in self.normalized_seed_lines:
            return True
        if keyword_score(normalized) < VOICE_MATCH_KEYWORD_THRESHOLD:
            return False
        return self.best_fuzzy_similarity(normalized) >= VOICE_MATCH_FUZZY_THRESHOLD

    def best_fuzzy_similarity(self, normalized_text: str) -> float:
        """Return the strongest fuzzy similarity against known seeds.

        Args:
            normalized_text: Normalized candidate text.

        Returns:
            Best token-set similarity in the inclusive range 0.0 to 1.0.
        """
        logger.trace("Calculating best Voice of the World fuzzy similarity")

        if not self.normalized_seed_lines:
            return 0.0
        return max(
            fuzz.token_set_ratio(normalized_text, seed) / 100.0
            for seed in self.normalized_seed_lines
        )


def quote_yaml(value: str) -> str:
    """Return a double-quoted YAML scalar.

    Args:
        value: Text to quote.

    Returns:
        A YAML-safe double-quoted scalar.
    """
    logger.trace("Entering quote_yaml")

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def book_input_dir(book: BookDefaults) -> Path:
    """Return the relative generated input directory for a book.

    Args:
        book: Book split definition.

    Returns:
        Path below ``converted/Super Gene/book-inputs`` for generated inputs.
    """
    logger.trace(f"Resolving generated input directory for book {book.number}")

    return Path(f"book-{book.number:02d}-{book.slug}")


def chapter_index(path: Path) -> int:
    """Extract the numeric chapter-file prefix from a chapter path.

    Args:
        path: Chapter Markdown path.

    Returns:
        The integer prefix before the first hyphen.
    """
    logger.trace("Entering chapter_index")

    return int(path.name.split("-", 1)[0])


def chapter_files(chapters_dir: Path, book: BookDefaults) -> list[Path]:
    """Return sorted chapter files for a book's inclusive numeric prefix range.

    Args:
        chapters_dir: Directory containing converted chapter Markdown files.
        book: Book split definition.

    Returns:
        Chapter files in numeric order.

    Raises:
        RuntimeError: If no chapters match the book range.
    """
    logger.trace("Entering chapter_files")

    chapters = sorted(
        (
        path
        for path in chapters_dir.glob("*.md")
        if book.start_index <= chapter_index(path) <= book.end_index
        ),
        key=chapter_index,
    )
    if not chapters:
        msg = f"No chapters found for book {book.number}: {book.start_index}-{book.end_index}"
        raise RuntimeError(msg)
    return chapters


def split_markdown_metadata(source: str) -> tuple[str, str]:
    """Split a Markdown document into YAML metadata and body text.

    Args:
        source: Markdown source text.

    Returns:
        A tuple containing the metadata block without fences and the body.
    """
    logger.trace("Splitting Markdown metadata")

    if not source.startswith("---\n"):
        return "", source
    _, metadata, body = source.split("---", 2)
    return metadata.strip(), body.lstrip()


def extract_chapter_title(metadata: str, body: str, chapter_number: int) -> str:
    """Extract the display title for a chapter.

    Args:
        metadata: YAML metadata text from a chapter file.
        body: Markdown body text from a chapter file.
        chapter_number: One-based chapter number used as a fallback.

    Returns:
        The chapter title without the leading ``Chapter N`` label.
    """
    logger.trace(f"Extracting title for chapter {chapter_number}")

    metadata_match = TITLE_METADATA_PATTERN.search(metadata)
    raw_title = metadata_match.group("title") if metadata_match else f"Chapter {chapter_number}"
    raw_title = raw_title.replace("<!-- source: span.hidden-title -->", "").strip()
    chapter_match = CHAPTER_TITLE_PATTERN.match(raw_title)
    if chapter_match and chapter_match.group("title").strip():
        return chapter_match.group("title").strip()

    heading_match = CHAPTER_HEADING_PATTERN.search(body)
    if heading_match:
        heading = heading_match.group(0).lstrip("#").strip()
        heading = heading.replace("<!-- source: span.hidden-title -->", "").strip()
        heading_match_title = CHAPTER_TITLE_PATTERN.match(heading)
        if heading_match_title and heading_match_title.group("title").strip():
            return heading_match_title.group("title").strip()
    return raw_title


def strip_source_chapter_markup(body: str) -> str:
    """Remove source-only heading and conversion comments from chapter Markdown.

    Args:
        body: Chapter body Markdown.

    Returns:
        Body text without the original visible heading or source comments.
    """
    logger.trace("Stripping source chapter markup")

    without_heading = CHAPTER_HEADING_PATTERN.sub("", body, count=1)
    without_comments = SOURCE_COMMENT_PATTERN.sub("", without_heading)
    return re.sub(r"\n{3,}", "\n\n", without_comments).strip()


def normalize_profile_label(label: str) -> str:
    """Normalize status/profile labels for consistent table display.

    Args:
        label: Label text captured from a source profile line.

    Returns:
        Canonical label text for the generated table row.
    """
    logger.trace(f"Normalizing profile label {label}")

    label_map = {
        "lifespan": "Life span",
        "requirement for next evolution": "Required for evolution",
        "requirement for next revolution": "Required for evolution",
        "requirements for evolution": "Required for evolution",
        "geno points needed for evolution": "Required for evolution",
        "geno points gained": "Geno Points Gained",
        "geno points owned": "Geno Points Owned",
    }
    return label_map.get(label.strip().lower(), label.strip())


def is_numeric_profile_value(value: str) -> bool:
    """Return whether a profile value should be right-aligned as numeric.

    Args:
        value: Profile value text from the source line.

    Returns:
        True when the value begins with a digit.
    """
    logger.trace(f"Checking whether profile value is numeric: {value}")

    return bool(re.match(r"^\d", value.strip()))


def clean_table_value(value: str) -> str:
    """Return table cell value text without one terminal period.

    Args:
        value: Raw value text captured from source Markdown.

    Returns:
        Value text with surrounding whitespace and one final period removed.
    """
    logger.trace("Cleaning table value")

    cleaned = value.strip()
    if cleaned.endswith("."):
        return cleaned[:-1]
    return cleaned


def parse_geno_point_rows(value: str, include_super_geno_points: bool = False) -> list[tuple[str, str]]:
    """Extract first-sanctuary Geno Points Gained type totals from a value.

    Args:
        value: Raw ``Geno points gained`` table value.
        include_super_geno_points: Whether to include the later-discovered
            Super Geno Point category in the generated rows.

    Returns:
        Ordered ``(type, amount)`` pairs for every first-sanctuary Geno Point
        type when any supported type is detected. Missing types default to
        zero.
    """
    logger.trace("Parsing Geno Points Gained value")

    cleaned = clean_table_value(value)
    parsed_amounts: dict[str, str] = {}
    point_types = SUPER_GENO_POINT_TYPES if include_super_geno_points else GENO_POINT_TYPES
    for point_type in point_types:
        match = _match_geno_point_amount(cleaned, point_type)
        if match:
            parsed_amounts[point_type] = match.group("amount")
    if not parsed_amounts:
        return []
    return [(point_type, parsed_amounts.get(point_type, "0")) for point_type in point_types]


def _match_geno_point_amount(value: str, point_type: str) -> re.Match[str] | None:
    """Return the numeric amount for one Geno Point type.

    Args:
        value: Cleaned source value from a ``Geno points gained`` row.
        point_type: Canonical Geno Point type label.

    Returns:
        Regex match containing the ``amount`` group, or ``None`` when the type
        is not present.
    """
    logger.trace(f"Matching Geno Point amount for {point_type}")

    for alias in GENO_POINT_ALIASES[point_type]:
        if not alias:
            bare_pattern = re.compile(r"\b(?P<amount>\d+)\s+geno\s+points?\b", re.IGNORECASE)
            match = bare_pattern.search(value)
            if match:
                return match
            continue

        type_pattern = re.escape(alias).replace("\\-", "[- ]")
        before_number_pattern = re.compile(
            rf"\b{type_pattern}\s+geno\s+points?\s+(?P<amount>\d+)\b",
            re.IGNORECASE,
        )
        after_number_pattern = re.compile(
            rf"\b(?P<amount>\d+)\s+{type_pattern}\s+geno\s+points?\b",
            re.IGNORECASE,
        )
        match = before_number_pattern.search(value) or after_number_pattern.search(value)
        if match:
            return match
    return None


def render_geno_points_rows(
    label: str,
    value: str,
    include_super_geno_points: bool = False,
) -> list[str]:
    """Render grouped Geno Point rows when point types are present.

    Args:
        label: Source profile label for the grouped Geno Point section.
        value: Raw ``Geno points gained`` table value.
        include_super_geno_points: Whether to include the later-discovered
            Super Geno Point category in the generated rows.

    Returns:
        HTML row strings for a grouped header and type-specific totals, or an
        empty list when no supported point type is mentioned.
    """
    logger.trace("Rendering Geno Points Gained detail rows")

    point_rows = parse_geno_point_rows(value, include_super_geno_points)
    if not point_rows:
        return []

    section_label = normalize_profile_label(label)
    section_class = re.sub(r"[^a-z0-9]+", "-", section_label.lower()).strip("-")
    rendered_rows = [
        f'<tr class="{section_class}"><th colspan="2" style="text-align:center;">{escape(section_label)}</th></tr>'
    ]
    for point_type, amount in point_rows:
        rendered_rows.append(
            "<tr>"
            f"<th>{escape(point_type)}</th>"
            f'<td class="profile-value numeric-value">{escape(amount)}</td>'
            "</tr>"
        )
    return rendered_rows


def is_full_width_profile_label(label: str) -> bool:
    """Return whether a profile row should span both table columns.

    Args:
        label: Source profile label.

    Returns:
        True when the label should render as a centered full-width section
        label followed by a centered full-width value row.
    """
    logger.trace(f"Checking full-width profile label {label}")

    return normalize_profile_label(label).lower() in FULL_WIDTH_PROFILE_LABELS


def render_full_width_profile_rows(label: str, value: str) -> list[str]:
    """Render a full-width profile label row followed by its full-width value.

    Args:
        label: Source profile label.
        value: Source profile value.

    Returns:
        Two raw HTML table row strings for the centered label and value.
    """
    logger.trace("Rendering full-width profile rows")

    section_label = normalize_profile_label(label)
    cleaned_value = clean_table_value(value)
    value_class = "profile-value numeric-value" if is_numeric_profile_value(cleaned_value) else "profile-value"
    return [
        f'<tr><th colspan="2" style="text-align:center;">{escape(section_label)}</th></tr>',
        (
            "<tr>"
            f'<td colspan="2" class="{value_class}" style="text-align:center;">{escape(cleaned_value)}</td>'
            "</tr>"
        ),
    ]


def render_profile_table(
    rows: list[tuple[str, str]],
    include_super_geno_points: bool = False,
) -> str:
    """Render status/profile rows as an Apple Books-safe HTML table.

    Args:
        rows: Profile label/value pairs in source order.
        include_super_geno_points: Whether to include the later-discovered
            Super Geno Point category in grouped Geno Point sections.

    Returns:
        Raw HTML table markup for EPUB output.
    """
    logger.trace(f"Rendering profile table with {len(rows)} rows")

    rendered_rows: list[str] = []
    for label, value in rows:
        if normalize_profile_label(label).lower() in {"geno points gained", "geno points owned"}:
            geno_rows = render_geno_points_rows(label, value, include_super_geno_points)
            if geno_rows:
                rendered_rows.extend(geno_rows)
                continue

        if is_full_width_profile_label(label):
            rendered_rows.extend(render_full_width_profile_rows(label, value))
            continue

        cleaned_value = clean_table_value(value)
        value_class = "profile-value numeric-value" if is_numeric_profile_value(cleaned_value) else "profile-value"
        rendered_rows.append(
            "<tr>"
            f'<th scope="row">{escape(normalize_profile_label(label))}</th>'
            f'<td class="{value_class}">{escape(cleaned_value)}</td>'
            "</tr>"
        )
    return (
        '<section class="profile-table-wrap" role="region" aria-label="Status profile">'
        '<table class="profile-table">'
        "<tbody>"
        f"{''.join(rendered_rows)}"
        "</tbody>"
        "</table>"
        "</section>"
    )


def parse_profile_row(lines: list[str], index: int) -> tuple[str, str, int] | None:
    """Parse a profile row starting at a line index.

    Args:
        lines: Chapter body lines.
        index: Current line index.

    Returns:
        A ``(label, value, next_index)`` tuple, or ``None`` when the line does
        not start a supported profile row.
    """
    logger.trace(f"Parsing profile row at line {index}")

    stripped = lines[index].strip()
    row_match = PROFILE_ROW_PATTERN.match(stripped)
    if row_match is not None:
        return row_match.group("label"), row_match.group("value"), index + 1

    markdown_match = MARKDOWN_PROFILE_ROW_PATTERN.match(stripped)
    if markdown_match is not None and is_profile_label(markdown_match.group("label")):
        return markdown_match.group("label"), markdown_match.group("value"), index + 1

    label_match = PROFILE_LABEL_ONLY_PATTERN.match(stripped)
    if label_match is None:
        return None

    value_index = next_nonblank_index(lines, index + 1)
    if value_index is None:
        return None
    value = lines[value_index].strip()
    if parse_profile_row(lines, value_index) is not None:
        return None
    return label_match.group("label"), value, value_index + 1


def is_profile_label(label: str) -> bool:
    """Return whether a label belongs in a status/profile table.

    Args:
        label: Candidate profile label.

    Returns:
        True when the normalized label is a supported profile table field.
    """
    logger.trace(f"Checking profile label {label}")

    normalized = normalize_profile_label(label).lower()
    return normalized in {
        "han sen",
        "status",
        "life span",
        "required for evolution",
        "geno points gained",
        "geno points owned",
        "beast soul gained",
        "beast souls gained",
    }


def next_nonblank_index(lines: list[str], start_index: int) -> int | None:
    """Return the index of the next nonblank line.

    Args:
        lines: Chapter body lines.
        start_index: Index to begin scanning.

    Returns:
        Index of the next nonblank line, or ``None`` when none exists.
    """
    logger.trace(f"Looking ahead for nonblank line from {start_index}")

    for index, line in enumerate(lines[start_index:], start=start_index):
        if line.strip():
            return index
    return None


def next_nonblank_profile_row(lines: list[str], start_index: int) -> tuple[str, str, int] | None:
    """Find the next nonblank line if it starts a profile row.

    Args:
        lines: Chapter body lines.
        start_index: Index to begin scanning.

    Returns:
        Parsed profile row tuple, or ``None``.
    """
    logger.trace(f"Looking ahead for profile row from line {start_index}")

    index = next_nonblank_index(lines, start_index)
    if index is None:
        return None
    return parse_profile_row(lines, index)


def collect_profile_rows(lines: list[str], start_index: int) -> tuple[list[tuple[str, str]], int]:
    """Collect contiguous profile rows from source lines.

    Args:
        lines: Chapter body lines.
        start_index: Index where a profile row starts.

    Returns:
        Profile ``(label, value)`` rows and the next unconsumed line index.
    """
    logger.trace(f"Collecting profile rows from line {start_index}")

    rows: list[tuple[str, str]] = []
    cursor = start_index
    while cursor < len(lines):
        stripped = lines[cursor].strip()
        if not stripped:
            next_row = next_nonblank_profile_row(lines, cursor + 1)
            if next_row is None:
                break
            cursor = next_nonblank_index(lines, cursor + 1) or cursor + 1
            continue

        row = parse_profile_row(lines, cursor)
        if row is None:
            break

        label, value, next_index = row
        rows.append((label, value))
        cursor = next_index
    return rows, cursor


def style_status_profile_tables(body: str, include_super_geno_points: bool = False) -> str:
    """Convert compact status/profile line groups into HTML tables.

    Args:
        body: Chapter body Markdown.
        include_super_geno_points: Whether to include the later-discovered
            Super Geno Point category in grouped Geno Point sections.

    Returns:
        Body text with known status/profile blocks rendered as raw HTML tables.
    """
    logger.trace("Styling status/profile tables")

    lines = body.splitlines()
    styled_lines: list[str] = []
    index = 0

    while index < len(lines):
        if parse_profile_row(lines, index) is None:
            styled_lines.append(lines[index])
            index += 1
            continue

        rows, cursor = collect_profile_rows(lines, index)
        has_profile_detail = any(label.strip().lower() != "han sen" for label, _value in rows)
        if len(rows) >= PROFILE_TABLE_MIN_ROWS and has_profile_detail:
            styled_lines.append(render_profile_table(rows, include_super_geno_points))
            index = cursor
            continue

        styled_lines.extend(lines[index:cursor])
        index = cursor

    return "\n".join(styled_lines).strip()


def render_dropcap_paragraph(paragraph: str) -> str:
    """Render one paragraph with a HWF-style drop cap.

    Args:
        paragraph: Plain first prose paragraph.

    Returns:
        Raw HTML paragraph with the first alphanumeric character wrapped.
    """
    logger.trace("Rendering first prose paragraph with a drop cap")

    match = re.search(r"[A-Za-z0-9]", paragraph)
    if not match:
        return f'<p class="first2">{escape(paragraph)}</p>'

    index = match.start()
    prefix = escape(paragraph[:index])
    dropcap = escape(paragraph[index])
    suffix = escape(paragraph[index + 1 :])
    return f'<p class="first2">{prefix}<span class="first-letter">{dropcap}</span>{suffix}</p>'


def add_first_paragraph_dropcap(body: str) -> str:
    """Apply drop-cap markup to the first real prose paragraph in a body.

    Args:
        body: Markdown body text after source markup has been stripped.

    Returns:
        Markdown body with the first prose paragraph replaced by raw HTML.
    """
    logger.trace("Adding first paragraph drop cap")

    lines = body.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "<", "|", ">", "```", ":::", "- ", "* ", "1. ")):
            continue
        if stripped.startswith("**"):
            continue
        lines[index] = render_dropcap_paragraph(stripped)
        break
    return "\n".join(lines).strip()


def render_world_voice_card(text: str) -> str:
    """Render a standalone Voice of the World notice as a bordered card.

    Args:
        text: Display text, including quotation marks when present.

    Returns:
        Raw HTML card markup for EPUB output.
    """
    logger.trace("Rendering Voice of the World card")

    display_text = text.strip()
    return (
        '<section class="world-voice-card" role="note">'
        f'<p class="world-voice"><em>{escape(display_text, quote=False)}</em></p>'
        "</section>"
    )


def render_world_voice_inline(text: str) -> str:
    """Render an inline Voice of the World notice.

    Args:
        text: Display text, including quotation marks when present.

    Returns:
        Raw inline HTML markup for EPUB output.
    """
    logger.trace("Rendering inline Voice of the World notice")

    display_text = text.strip()
    return f'<span class="world-voice-inline"><em>{escape(display_text, quote=False)}</em></span>'


def style_voice_of_the_world_lines(body: str, matcher: VoiceLineMatcher | None) -> str:
    """Apply Voice of the World card and inline styling to Markdown body text.

    Args:
        body: Chapter body Markdown.
        matcher: Seed-aware matcher, or None to leave body unchanged.

    Returns:
        Body text with matched Voice of the World notices styled as HTML.
    """
    logger.trace("Styling Voice of the World lines")

    if matcher is None:
        return body

    styled_lines: list[str] = []
    for line in body.splitlines():
        standalone_match = STANDALONE_BOLD_QUOTE_PATTERN.match(line)
        if standalone_match and matcher.is_voice_line(standalone_match.group("quote")):
            styled_lines.append(render_world_voice_card(standalone_match.group("quote")))
            continue

        has_inline_voice_context = INLINE_VOICE_CONTEXT_PATTERN.search(line) is not None

        def replace_inline(match: re.Match[str]) -> str:
            """Replace a matched bold quote if it is a Voice notice."""
            logger.trace("Checking inline Voice of the World quote")

            quote = match.group("quote")
            if has_inline_voice_context and matcher.is_voice_line(quote):
                return render_world_voice_inline(quote)
            return match.group(0)

        styled_lines.append(BOLD_QUOTE_PATTERN.sub(replace_inline, line))

    return "\n".join(styled_lines)


def render_chapter_heading(chapter_number: int, title: str, chapter_id: str) -> str:
    """Render the visible HWF-inspired chapter heading block.

    Args:
        chapter_number: One-based chapter number shown to readers.
        title: Chapter title shown to readers.
        chapter_id: Stable HTML id for the chapter section.

    Returns:
        Raw HTML for the visible chapter heading block.
    """
    logger.trace(f"Rendering heading for chapter {chapter_number}")

    safe_title = escape(title)
    return f"""<section class="heading1" id="{chapter_id}-heading">
<section class="heading-contents1">
<section class="element">
<section class="element-number-block">
<p class="element-number">{chapter_number}</p>
</section>
<section class="element title-block">
<section class="title-subtitle-block">
<h1 class="title">{safe_title}</h1>
</section>
</section>
</section>
</section>
</section>"""


def render_chapter(
    source: str,
    chapter_number: int,
    chapter_id: str,
    voice_matcher: VoiceLineMatcher | None = None,
) -> str:
    """Render one source chapter as a generated book-ready Markdown file.

    Args:
        source: Raw converted chapter Markdown.
        chapter_number: Chapter number to show in the opening block.
        chapter_id: Stable HTML id for the chapter section.
        voice_matcher: Optional matcher for Voice of the World notices.

    Returns:
        Generated Markdown with a hidden split header and visible styled opening.
    """
    logger.trace(f"Rendering generated chapter {chapter_number}")

    metadata, body = split_markdown_metadata(source)
    title = extract_chapter_title(metadata, body, chapter_number)
    cleaned_body = strip_source_chapter_markup(body)
    tabled_body = style_status_profile_tables(
        cleaned_body,
        include_super_geno_points=chapter_number > 270,
    )
    styled_body = style_voice_of_the_world_lines(add_first_paragraph_dropcap(tabled_body), voice_matcher)
    heading = render_chapter_heading(chapter_number, title, chapter_id)
    hidden_heading = f"# Chapter {chapter_number}: {title} {{.hidden-title}}"

    return f"""{hidden_heading}

<section id="{chapter_id}" class="chapter element" role="doc-chapter" epub:type="bodymatter chapter">
{heading}

<section class="element chapter-text" id="{chapter_id}-text" markdown="1">
{styled_body}
</section>

</section>
"""


def render_also_in_series_page(book: BookDefaults, books: tuple[BookDefaults, ...]) -> str:
    """Render the also-in-series front matter page.

    Args:
        book: Current book split definition.
        books: All configured book split definitions.

    Returns:
        Markdown for the also-in-series page.
    """
    logger.trace(f"Rendering also-in-series page for book {book.number}")

    entries = "\n".join(
        f'{item.number}. <span class="{"current-series-book" if item == book else "series-book"}">'
        f"Super Gene: {escape(item.title)}</span>"
        for item in books
    )
    return f"""# Also in Series {{.hidden-title .unlisted}}

<section id="also-in-series-page" class="frontmatter also-in-series" epub:type="frontmatter">
<h1 class="frontmatter-heading">Also in Series</h1>

{entries}

</section>
"""


def render_title_page(book: BookDefaults) -> str:
    """Render the title page for one book.

    Args:
        book: Current book split definition.

    Returns:
        Markdown for the title page.
    """
    logger.trace(f"Rendering title page for book {book.number}")

    return f"""# Title Page {{.hidden-title .unlisted}}

<section class="frontmatter title-page" epub:type="titlepage">
<p class="series-name">Super Gene</p>
<h1 class="book-title">{escape(book.title)}</h1>
<p class="book-subtitle">Book {book.number} of Super Gene</p>
<p class="book-author">Twelve-Winged Dark Seraphim</p>
<section class="producer-credit">
<p>Produced By</p>
<p>Max Ludden</p>
</section>
</section>
"""


def title_page_artwork_filename(book: BookDefaults) -> str:
    """Return the title-page artwork file name for a book.

    Args:
        book: Current book split definition.

    Returns:
        Expected title-page artwork PNG file name.
    """
    logger.trace(f"Rendering title-page artwork file name for book {book.number}")

    return f"book-{book.number:02d}-{book.slug}-title-page-artwork.png"


def render_title_page_artwork(book: BookDefaults) -> str:
    """Render the artwork page that appears before the title page.

    Args:
        book: Current book split definition.

    Returns:
        Markdown for a full-page title artwork frontmatter page.
    """
    logger.trace(f"Rendering title-page artwork for book {book.number}")

    artwork_filename = title_page_artwork_filename(book)
    alt_text = escape(f"Title page artwork for Super Gene: {book.title}")
    return f"""# Title Page Artwork {{.hidden-title .unlisted}}

<section class="frontmatter title-page-artwork" epub:type="frontmatter">
<figure class="title-page-artwork-frame">
<img class="title-page-artwork-image" src="{artwork_filename}" alt="{alt_text}" />
</figure>
</section>
"""


def render_copyright_page() -> str:
    """Render the neutral private-edition copyright page.

    Returns:
        Markdown for the copyright page.
    """
    logger.trace("Rendering copyright page")

    return f"""# Copyright {{.hidden-title .unlisted}}

<section class="frontmatter copyright-page" epub:type="copyright-page">
<h1 class="frontmatter-heading">Copyright</h1>
<p>{escape(COPYRIGHT_NOTICE)}</p>
</section>
"""


def render_blank_page() -> str:
    """Render the blank page that immediately precedes chapter one.

    Returns:
        Markdown for an intentionally blank page.
    """
    logger.trace("Rendering blank page before first chapter")

    return """# Blank Page {.hidden-title .unlisted}

<section class="blank-page" aria-hidden="true" epub:type="pagebreak">
<p>&#160;</p>
</section>
"""


def render_continue_page(book: BookDefaults, books: tuple[BookDefaults, ...]) -> str:
    """Render the end page for one book.

    Args:
        book: Current book split definition.
        books: All configured book split definitions.

    Returns:
        Markdown for the end page.
    """
    logger.trace(f"Rendering continue page for book {book.number}")

    next_book = next((item for item in books if item.number == book.number + 1), None)
    if next_book:
        message = f"Continue reading Super Gene: {next_book.title}."
    else:
        message = "You have reached the end of this Super Gene reading edition."

    return f"""# Continue Reading {{.backmatter-title .unlisted}}

<section class="backmatter continue-page" epub:type="backmatter">
<h1 class="frontmatter-heading">Continue Reading</h1>
<p>{escape(message, quote=False)}</p>
</section>
"""


def first_bodymatter_input(generated_inputs: list[Path]) -> Path:
    """Return the first generated chapter input path.

    Args:
        generated_inputs: Generated book-ready Markdown files in reading order.

    Returns:
        The first generated chapter file, or the first input as a fallback.

    Raises:
        RuntimeError: If no generated inputs were provided.
    """
    logger.trace("Resolving first bodymatter input")

    if not generated_inputs:
        msg = "Cannot render defaults without generated input files"
        raise RuntimeError(msg)
    return next(
        (
            path
            for path in generated_inputs
            if re.match(r"^\d{4}-\d+-.*\.md$", path.name)
        ),
        generated_inputs[0],
    )


def generated_chapter_filename(index: int, source_path: Path) -> str:
    """Return the generated file name for a chapter source file.

    Args:
        index: One-based position within the generated input sequence.
        source_path: Original chapter Markdown path.

    Returns:
        Ordered generated chapter file name.
    """
    logger.trace(f"Rendering generated file name for {source_path.name}")

    return f"{index:04d}-{source_path.name}"


def build_book_inputs(
    book: BookDefaults,
    books: tuple[BookDefaults, ...],
    chapters: list[Path],
    book_inputs_root: Path,
    voice_matcher: VoiceLineMatcher | None = None,
) -> list[Path]:
    """Write generated book-ready input files for one book.

    Args:
        book: Current book split definition.
        books: All configured book split definitions.
        chapters: Raw converted chapter Markdown paths in reading order.
        book_inputs_root: Root directory for generated book inputs.
        voice_matcher: Optional matcher for Voice of the World notices.

    Returns:
        Ordered generated Markdown paths for Pandoc.
    """
    logger.info(f"Building generated inputs for Super Gene book {book.number}")

    target_dir = book_inputs_root / book_input_dir(book)
    target_dir.mkdir(parents=True, exist_ok=True)
    for stale_input in target_dir.glob("*.md"):
        stale_input.unlink()

    generated: list[tuple[str, str]] = [
        ("0001-also-in-series.md", render_also_in_series_page(book, books)),
        ("0002-title-page-artwork.md", render_title_page_artwork(book)),
        ("0003-title-page.md", render_title_page(book)),
        ("0004-copyright.md", render_copyright_page()),
        ("0005-blank-before-chapter.md", render_blank_page()),
    ]

    for offset, chapter_path in enumerate(chapters, start=6):
        chapter_number = chapter_index(chapter_path)
        chapter_id = f"chapter-{chapter_number}"
        generated.append(
            (
                generated_chapter_filename(offset, chapter_path),
                render_chapter(
                    chapter_path.read_text(encoding="utf-8"),
                    chapter_number=chapter_number,
                    chapter_id=chapter_id,
                    voice_matcher=voice_matcher,
                ),
            )
        )

    generated.append(("9999-continue.md", render_continue_page(book, books)))

    output_paths: list[Path] = []
    for filename, contents in generated:
        output_path = target_dir / filename
        output_path.write_text(contents, encoding="utf-8")
        output_paths.append(output_path)
    return output_paths


def render_stylesheet() -> str:
    """Render the shared EPUB stylesheet for generated Super Gene books.

    Returns:
        CSS containing Bookerly font faces, retained converter classes, and
        HWF-inspired chapter-opening classes.
    """
    logger.trace("Rendering generated EPUB stylesheet")

    return """@font-face {
  font-family: "Bookerly";
  font-style: normal;
  font-weight: normal;
  src: url("../fonts/Bookerly.ttf") format("truetype");
}

@font-face {
  font-family: "Bookerly";
  font-style: italic;
  font-weight: normal;
  src: url("../fonts/Bookerly Italic.ttf") format("truetype");
}

@font-face {
  font-family: "Bookerly";
  font-style: normal;
  font-weight: bold;
  src: url("../fonts/Bookerly Bold.ttf") format("truetype");
}

@font-face {
  font-family: "Bookerly";
  font-style: italic;
  font-weight: bold;
  src: url("../fonts/Bookerly Bold Italic.ttf") format("truetype");
}

body,
.calibre {
  display: block;
  font-family: "Bookerly", Georgia, serif;
  font-size: 1em;
  line-height: 1.35;
  padding-left: 0;
  padding-right: 0;
  margin: 0 5pt;
  -webkit-hyphens: auto;
  hyphens: auto;
  overflow-wrap: normal;
  word-break: normal;
}

p {
  margin: 0;
}

p::after {
  content: "";
  display: table;
  clear: both;
}

.calibre4 {
  font-weight: bold;
}

.calibre5 {
  font-style: italic;
}

.calibre6 {
  display: block;
  font-size: 1.41667em;
  font-weight: bold;
  line-height: 1.2;
  text-align: center;
  margin: 10% 0;
}

.calibre8 {
  border-collapse: collapse;
  border-spacing: 2px;
  display: table;
  text-align: center;
  text-indent: 0;
  width: 90%;
  margin: 0 auto;
  border: 1px solid #7a7a7a;
}

.calibre9 {
  display: table-row-group;
  vertical-align: middle;
}

.calibre10 {
  display: table-row;
  vertical-align: inherit;
}

.calibre11 {
  display: table-cell;
  text-align: inherit;
  vertical-align: inherit;
  padding: 1px;
  border: 1px solid #7a7a7a;
}

h1.hidden-title {
  display: none;
  line-height: 1.2;
}

.chapter {
  break-before: left;
  page-break-before: left;
}

.element {
  display: block;
}

.heading1 {
  display: block;
  margin: 0 6% 2em 6%;
  min-height: 12em;
  text-align: center;
}

.heading-contents1 {
  display: block;
  padding-top: 5em;
}

.element-number {
  display: block;
  font-size: 0.91667em;
  font-weight: normal;
  letter-spacing: 0.2em;
  text-align: center;
  text-transform: uppercase;
  margin: 0;
}

.element-number-block {
  display: block;
  min-height: 1.5em;
}

.title {
  display: block;
  font-size: 1em;
  font-weight: normal;
  letter-spacing: 0.15em;
  page-break-inside: avoid;
  text-align: center;
  text-transform: uppercase;
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
  margin: 0;
}

.title-block {
  display: block;
  font-size: 0.91667em;
  padding-top: 0;
}

.title-subtitle-block {
  display: block;
  padding-top: 0;
}

.chapter-text {
  display: block;
}

.chapter-text p {
  text-align: justify;
  text-indent: 1.5em;
  margin: 0;
  -webkit-hyphens: auto;
  hyphens: auto;
  overflow-wrap: normal;
  word-break: normal;
}

.chapter-text .first2 {
  text-align: justify;
  text-indent: 0;
}

.profile-table-wrap {
  margin: 1em 6%;
  page-break-inside: avoid;
  break-inside: avoid;
}

.profile-table {
  border-collapse: collapse;
  border-spacing: 0;
  width: 100%;
  margin: 0 auto;
  page-break-inside: avoid;
}

.profile-table th,
.profile-table td {
  border-top: 1px solid #7a7a7a;
  border-bottom: 1px solid #7a7a7a;
  border-left: 0;
  border-right: 0;
  padding: 0.3em 0.5em;
  vertical-align: top;
  text-indent: 0;
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
}

.profile-table th:first-child,
.profile-table td:first-child {
  border-left: 1px solid #7a7a7a;
}

.profile-table th:last-child,
.profile-table td:last-child {
  border-right: 1px solid #7a7a7a;
}

.profile-table th {
  background-color: #111;
  color: #eee;
  font-weight: bold;
  text-align: left;
  width: 42%;
}

@media (prefers-color-scheme: dark) {
  .profile-table th {
    background-color: #eee;
    color: #111;
  }
}

.profile-table .profile-value {
  text-align: left;
}

.profile-table .numeric-value {
  text-align: right;
}

.world-voice-card {
  border: 1px solid #7a7a7a;
  background-color: #f4f4f4;
  margin: 1em 8%;
  padding: 0.75em 1em;
  page-break-inside: avoid;
  break-inside: avoid;
  text-align: center;
}

.world-voice-card,
.world-voice,
.world-voice em,
.world-voice-inline {
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
}

.world-voice {
  font-family: "Courier New", Courier, monospace;
  font-size: 0.8em;
  font-style: normal;
  font-weight: normal;
  text-align: center;
  text-indent: 0;
  margin: 0;
}

.chapter-text .world-voice,
.chapter-text .world-voice em {
  text-align: center;
  text-indent: 0;
}

.world-voice em,
.world-voice-inline {
  display: block;
  font-style: normal;
  font-weight: normal;
  padding: 0;
  text-indent: 0;
}

.world-voice-inline {
  display: inline;
  text-indent: 0;
}

.first-letter,
.dropcap {
  float: left;
  font-family: "Bookerly", Georgia, serif;
  font-size: 325%;
  line-height: 0.85;
  margin: -0.04em 0.05em -0.1em 0;
  text-transform: uppercase;
}

.frontmatter,
.backmatter {
  break-before: page;
  page-break-before: always;
  page-break-inside: avoid;
  break-inside: avoid;
  text-align: center;
  margin: 20% 8% 0 8%;
}

.frontmatter-heading,
.book-title {
  font-size: 1.2em;
  font-weight: normal;
  letter-spacing: 0.12em;
  text-align: center;
  text-transform: uppercase;
  margin: 0 0 2em 0;
  page-break-after: avoid;
  break-after: avoid;
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
}

.series-name,
.book-subtitle,
.book-author,
.series-book,
.current-series-book {
  display: block;
  text-align: center;
  margin: 0.5em 0;
  -webkit-hyphens: none;
  hyphens: none;
  overflow-wrap: normal;
  word-break: normal;
}

.current-series-book {
  font-weight: bold;
}

.producer-credit {
  margin-top: 18em;
  page-break-inside: avoid;
  break-inside: avoid;
}

.producer-credit p {
  text-align: center;
  margin: 0.5em 0;
}

.also-in-series {
  page-break-inside: avoid;
  break-inside: avoid;
}

.also-in-series ol {
  page-break-before: avoid;
  break-before: avoid;
  margin-top: 0;
}

.title-page-artwork {
  margin: 0;
  padding: 0;
  text-align: center;
}

.title-page-artwork-frame {
  display: block;
  text-align: center;
  margin: 0;
  padding: 0;
}

.title-page-artwork-image {
  display: block;
  height: auto;
  max-height: 95vh;
  max-width: 100%;
  object-fit: contain;
  margin: 0 auto;
  padding: 0;
}

.copyright-page p,
.continue-page p {
  text-align: center;
  text-indent: 0;
}

.blank-page {
  break-before: page;
  break-after: page;
  page-break-before: always;
  page-break-after: always;
  min-height: 95vh;
}
"""


def write_stylesheet(assets_dir: Path) -> Path:
    """Write the generated shared stylesheet.

    Args:
        assets_dir: Converted book assets directory.

    Returns:
        Path to the written stylesheet.
    """
    logger.info(f"Writing generated EPUB stylesheet to {assets_dir}")

    assets_dir.mkdir(parents=True, exist_ok=True)
    stylesheet_path = assets_dir / "stylesheet.css"
    stylesheet_path.write_text(render_stylesheet(), encoding="utf-8")
    return stylesheet_path


def copy_bookerly_fonts(static_fonts_dir: Path, assets_dir: Path) -> list[Path]:
    """Copy Bookerly font files into the EPUB asset directory.

    Args:
        static_fonts_dir: Repository static font source directory.
        assets_dir: Converted book assets directory.

    Returns:
        Paths to copied font files.
    """
    logger.info(f"Copying Bookerly fonts from {static_fonts_dir} to {assets_dir}")

    target_dir = assets_dir / "fonts"
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for font_name in (
        "Bookerly.ttf",
        "Bookerly Italic.ttf",
        "Bookerly Bold.ttf",
        "Bookerly Bold Italic.ttf",
    ):
        source_path = static_fonts_dir / font_name
        target_path = target_dir / font_name
        shutil.copy2(source_path, target_path)
        copied.append(target_path)
    return copied


def insert_start_landmark(nav_xhtml: str, start_href: str) -> str:
    """Insert a start-reading landmark into an EPUB nav document.

    Args:
        nav_xhtml: EPUB nav document text.
        start_href: Href to the first chapter from the EPUB root.

    Returns:
        Nav document text with a bodymatter landmark.
    """
    logger.trace(f"Inserting EPUB nav start landmark for {start_href}")

    link = START_READING_LINK.format(href=start_href)
    if link in nav_xhtml:
        return nav_xhtml
    landmarks_marker = '<nav epub:type="landmarks"'
    if landmarks_marker not in nav_xhtml:
        return nav_xhtml
    ordered_list_start = nav_xhtml.find("<ol>", nav_xhtml.find(landmarks_marker))
    if ordered_list_start == -1:
        return nav_xhtml
    insert_at = ordered_list_start + len("<ol>")
    return f'{nav_xhtml[:insert_at]}\n<li>{link}</li>{nav_xhtml[insert_at:]}'


def insert_start_guide_reference(content_opf: str, start_href: str) -> str:
    """Insert a Kindle-friendly start-reading guide reference.

    Args:
        content_opf: EPUB OPF package document text.
        start_href: Href to the first chapter from the EPUB root.

    Returns:
        OPF document text with a guide reference.
    """
    logger.trace(f"Inserting OPF guide start reference for {start_href}")

    reference = START_READING_REFERENCE.format(href=start_href)
    if f'href="{start_href}"' in content_opf and 'title="Start Reading"' in content_opf:
        return content_opf
    guide_close = "</guide>"
    if guide_close in content_opf:
        return content_opf.replace(guide_close, f"    {reference}\n  {guide_close}", 1)

    package_close = "</package>"
    if package_close not in content_opf:
        return content_opf
    guide = f"\n  <guide>\n    {reference}\n  </guide>\n"
    return content_opf.replace(package_close, f"{guide}{package_close}", 1)


def write_replaced_epub_members(epub_path: Path, replacements: dict[str, str]) -> None:
    """Rewrite an EPUB archive with selected text members replaced.

    Args:
        epub_path: EPUB archive path.
        replacements: Archive member names mapped to replacement text.
    """
    logger.info(f"Patching EPUB archive {epub_path}")

    temporary_path = epub_path.with_suffix(".tmp.epub")
    with zipfile.ZipFile(epub_path, "r") as source_archive:
        members = source_archive.infolist()
        with zipfile.ZipFile(temporary_path, "w") as target_archive:
            for member in members:
                data = source_archive.read(member.filename)
                if member.filename in replacements:
                    data = replacements[member.filename].encode("utf-8")
                target_archive.writestr(member, data)
    temporary_path.replace(epub_path)


def patch_epub_start_landmark(epub_path: Path, start_href: str = "text/ch005.xhtml") -> None:
    """Patch a built EPUB so supported readers can open at the first chapter.

    Args:
        epub_path: Built EPUB archive path.
        start_href: Href to the first chapter from the EPUB root.
    """
    configure_logging()
    logger.info(f"Adding start-reading landmark to {epub_path}")

    with zipfile.ZipFile(epub_path, "r") as archive:
        nav_xhtml = archive.read("EPUB/nav.xhtml").decode("utf-8")
        content_opf = archive.read("EPUB/content.opf").decode("utf-8")

    replacements = {
        "EPUB/nav.xhtml": insert_start_landmark(nav_xhtml, start_href),
        "EPUB/content.opf": insert_start_guide_reference(content_opf, start_href),
    }
    write_replaced_epub_members(epub_path, replacements)


def relative_defaults_path(path: Path) -> str:
    """Return a Pandoc defaults path relative to the defaults directory.

    Args:
        path: Generated input path below ``converted/Super Gene``.

    Returns:
        Path expression usable from a defaults file.
    """
    logger.trace(f"Rendering defaults path for {path}")

    parts = path.parts
    book_inputs_index = parts.index("book-inputs")
    relative_path = "/".join(parts[book_inputs_index:])
    return f"${{.}}/../{relative_path}"


def render_defaults(book: BookDefaults, generated_inputs: list[Path]) -> str:
    """Render one Pandoc defaults YAML document.

    Args:
        book: Book split definition.
        generated_inputs: Generated book-ready Markdown files in reading order.

    Returns:
        A Pandoc defaults YAML document.
    """
    logger.trace("Entering render_defaults")

    book_label = f"Book {book.number} of Super Gene"
    cover_path = (
        "${.}/../../../assets/covers/super-gene/"
        f"book-{book.number:02d}-{book.slug}-ai-redraw-with-text.png"
    )
    output_path = f"${{.}}/../books/book-{book.number:02d}-{book.slug}.epub"

    lines = [
        "# Generated by scripts/generate_pandoc_defaults.py",
        f"# {book_label}: {book.title}",
        "from: markdown+yaml_metadata_block+smart",
        "to: epub3",
        "standalone: true",
        "table-of-contents: true",
        "toc-depth: 1",
        "split-level: 1",
        "epub-chapter-level: 1",
        "epub-title-page: false",
        "resource-path:",
        "  - ${.}/..",
        "  - ${.}/../assets",
        "  - ${.}/../assets/fonts",
        "  - ${.}/../../../assets/covers/super-gene",
        "  - ${.}/../../../assets/titlepage-artwork",
        "css:",
        "  - ${.}/../assets/stylesheet.css",
        "  - ${.}/../assets/page_styles.css",
        "epub-fonts:",
        "  - ${.}/../assets/fonts/Bookerly.ttf",
        "  - ${.}/../assets/fonts/Bookerly Italic.ttf",
        "  - ${.}/../assets/fonts/Bookerly Bold.ttf",
        "  - ${.}/../assets/fonts/Bookerly Bold Italic.ttf",
        f"epub-cover-image: {quote_yaml(cover_path)}",
        f"output-file: {quote_yaml(output_path)}",
        "metadata:",
        f"  title: {quote_yaml(f'Super Gene: {book.title}')}",
        f"  subtitle: {quote_yaml(book_label)}",
        "  author:",
        "    - Twelve-Winged Dark Seraphim",
        "  lang: en",
        f"  identifier: {quote_yaml(f'super-gene-book-{book.number:02d}')}",
        "  publisher: Max Ludden",
        "  series: Super Gene",
        f"  series-index: {book.number}",
        "  bodymatter:",
        f"    start: {quote_yaml(relative_defaults_path(first_bodymatter_input(generated_inputs)))}",
        "    epub-type: bodymatter",
        "  subject:",
        "    - Super Gene",
        "    - Web novel",
        "input-files:",
    ]
    lines.extend(f"  - {quote_yaml(relative_defaults_path(path))}" for path in generated_inputs)
    return "\n".join(lines) + "\n"


def main() -> None:
    """Generate defaults files for all configured books."""
    configure_logging()
    logger.trace("Entering main")

    repo_root = Path(__file__).resolve().parents[1]
    converted_dir = repo_root / "converted" / "Super Gene"
    chapters_dir = converted_dir / "chapters"
    defaults_dir = converted_dir / "defaults"
    books_dir = converted_dir / "books"
    book_inputs_root = converted_dir / "book-inputs"
    assets_dir = converted_dir / "assets"
    static_fonts_dir = repo_root / "static" / "fonts"
    voice_seed_path = repo_root / "static" / "voice_of_the_world.txt"

    defaults_dir.mkdir(parents=True, exist_ok=True)
    books_dir.mkdir(parents=True, exist_ok=True)
    book_inputs_root.mkdir(parents=True, exist_ok=True)
    write_stylesheet(assets_dir)
    copy_bookerly_fonts(static_fonts_dir, assets_dir)
    voice_matcher = VoiceLineMatcher.from_seed_path(voice_seed_path)

    for book in BOOKS:
        chapters = chapter_files(chapters_dir, book)
        generated_inputs = build_book_inputs(
            book,
            BOOKS,
            chapters,
            book_inputs_root,
            voice_matcher=voice_matcher,
        )
        output_path = defaults_dir / f"book-{book.number:02d}-{book.slug}.yaml"
        output_path.write_text(render_defaults(book, generated_inputs), encoding="utf-8")


if __name__ == "__main__":
    main()
