"""Convert EPUB files into Markdown chapters with preserved metadata and assets."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

import ebooklib
from bs4 import BeautifulSoup, Tag
from ebooklib import epub
from loguru import logger
from markdownify import ATX, markdownify


@dataclass(frozen=True)
class BookMetadata:
    """Metadata extracted from an EPUB package.

        Attributes:
            title: Book title from Dublin Core metadata, or a fallback title.
            creators: Creator names listed in the EPUB metadata.
            language: Optional language code from the EPUB metadata.
            identifiers: Identifier values declared by the EPUB.
        """

    title: str
    creators: list[str]
    language: str | None
    identifiers: list[str]


@dataclass(frozen=True)
class ConversionWarning:
    """Non-fatal conversion issue captured for later review.

        Attributes:
            code: Stable warning category.
            message: Human-readable warning detail.
            source_href: Optional EPUB href that caused the warning.
        """

    code: str
    message: str
    source_href: str | None = None


@dataclass(frozen=True)
class ChapterResult:
    """Output details for one converted chapter.

        Attributes:
            index: One-based chapter index in output order.
            title: Chapter title used for frontmatter and slugging.
            depth: Table-of-contents nesting depth.
            source_href: Original EPUB href for the chapter.
            output_path: Markdown file written for the chapter.
        """

    index: int
    title: str
    depth: int
    source_href: str
    output_path: Path


@dataclass(frozen=True)
class ConversionResult:
    """Complete result of converting one EPUB.

        Attributes:
            metadata: EPUB metadata used during conversion.
            output_dir: Root directory containing the converted book.
            chapters: Chapter files written during conversion.
            warnings: Non-fatal conversion warnings.
        """

    metadata: BookMetadata
    output_dir: Path
    chapters: list[ChapterResult]
    warnings: list[ConversionWarning]


@dataclass(frozen=True)
class ConversionProgress:
    """Progress event emitted after a chapter is written.

        Attributes:
            completed: Count of chapters written so far.
            total: Total conversion entries selected for processing.
            title: Title of the chapter just written.
            output_path: Markdown path written for the chapter.
        """

    completed: int
    total: int
    title: str
    output_path: Path


@dataclass(frozen=True)
class TocEntry:
    """Chapter-like entry resolved from an EPUB TOC or spine.

        Attributes:
            title: Display title for the entry.
            href: EPUB document href, optionally with a fragment.
            depth: Nesting depth from the TOC walk.
        """

    title: str
    href: str
    depth: int


ProgressCallback = Callable[[ConversionProgress], None]
GENO_POINT_TYPES = ("Primitive", "Ordinary", "Mutant", "Sacred-Blood")
GENO_POINT_ALIASES = {
    "Primitive": ("Primitive", ""),
    "Ordinary": ("Ordinary",),
    "Mutant": ("Mutant",),
    "Sacred-Blood": ("Sacred-Blood", "Sacred Blood", "Sacred"),
}


def convert_epub(
    epub_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> ConversionResult:
    """Convert an EPUB file into Markdown chapter files.

        Args:
            epub_path: Source EPUB file path.
            output_dir: Directory where the converted book directory will be created.
            overwrite: Whether to replace an existing converted book directory.
            progress_callback: Optional callback invoked after each chapter is written.

        Returns:
            Metadata, chapter paths, and warnings from the conversion.

        Raises:
            FileNotFoundError: If the source EPUB does not exist.
            FileExistsError: If output already exists and overwrite is false.
        """
    source = Path(epub_path)
    root = Path(output_dir)
    logger.trace(f"Starting EPUB conversion: source={source} output_dir={root} overwrite={overwrite}")
    if not source.exists():
        raise FileNotFoundError(source)

    book = epub.read_epub(str(source))
    metadata = _metadata(book)
    book_dir = root / _safe_folder_name(metadata.title or source.stem)
    if book_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Output directory already exists: {book_dir}")
        shutil.rmtree(book_dir)

    chapters_dir = book_dir / "chapters"
    assets_dir = book_dir / "assets"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[ConversionWarning] = []
    # EbookLib exposes documents by internal archive names; normalize those
    # names once so TOC hrefs, spine entries, and asset links can all compare
    # against the same key format.
    document_items: dict[str, Any] = {
        _clean_item_name(item.get_name()): item
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    }
    entries = _toc_entries(book)
    if not entries:
        warnings.append(ConversionWarning("missing_toc", "No table of contents found; using spine order."))
        entries = _spine_entries(book, document_items)
    else:
        # Some generated EPUBs include a partial TOC but a fuller spine. When
        # the spine has more chapter-like documents, prefer it to avoid silently
        # dropping chapters from the Markdown output.
        spine_entries = _spine_entries(book, document_items)
        if len(spine_entries) > len(entries):
            warnings.append(
                ConversionWarning(
                    "incomplete_toc",
                    f"Table of contents has {len(entries)} entries; spine has {len(spine_entries)} chapter-like documents. Using spine order.",
                )
            )
            entries = spine_entries

    logger.trace(f"Resolved {len(entries)} conversion entries for {source}")
    copied_assets = _copy_assets(book, assets_dir)
    logger.trace(f"Copied {len(copied_assets)} EPUB assets into {assets_dir}")
    chapters: list[ChapterResult] = []
    used_slugs: dict[str, int] = {}

    # Keep progress based on selected entries rather than written chapters, so
    # skipped/missing documents still leave an honest denominator in the UI.
    total_entries = len(entries)
    for entry in entries:
        doc_name, anchor = _split_href(entry.href)
        item = document_items.get(doc_name)
        if item is None:
            warnings.append(
                ConversionWarning("missing_document", f"TOC entry points to missing document: {doc_name}", entry.href)
            )
            continue

        soup = BeautifulSoup(item.get_content(), "html.parser")
        fragment = _chapter_fragment(soup, anchor, entry, warnings)
        _rewrite_asset_links(fragment, doc_name, copied_assets)
        _split_profile_table_geno_points(fragment)
        _annotate_source_styles(fragment)
        markdown = markdownify(
            str(fragment),
            heading_style=ATX,
            table_infer_header=True,
            keep_inline_images_in=["td", "th"],
            wrap=False,
        ).strip()

        index = len(chapters) + 1
        slug = _unique_slug(entry.title, used_slugs)
        output_path = chapters_dir / f"{index:03d}-{slug}.md"
        source_id = anchor or _first_element_id(fragment)
        output_path.write_text(
            _frontmatter(
                {
                    "index": index,
                    "title": entry.title,
                    "toc_depth": entry.depth,
                    "source_href": entry.href,
                    "source_id": source_id,
                    "book_title": metadata.title,
                    "creators": metadata.creators,
                    "language": metadata.language,
                    "asset_root": "../assets",
                }
            )
            + "\n"
            + markdown
            + "\n",
            encoding="utf-8",
        )
        chapters.append(ChapterResult(index, entry.title, entry.depth, entry.href, output_path))
        if progress_callback:
            progress_callback(ConversionProgress(index, total_entries, entry.title, output_path))

    _write_json(book_dir / "metadata.json", asdict(metadata))
    if warnings:
        _write_json(book_dir / "warnings.json", [asdict(warning) for warning in warnings])

    logger.trace(f"Finished EPUB conversion: chapters={len(chapters)} warnings={len(warnings)} output={book_dir}")
    return ConversionResult(metadata, book_dir, chapters, warnings)


def _metadata(book: epub.EpubBook) -> BookMetadata:
    """Extract normalized Dublin Core metadata from an EPUB book."""
    logger.trace("Entering _metadata")
    title = _first_metadata(book, "title") or "Untitled"
    creators = [value.strip() for value, _attrs in book.get_metadata("DC", "creator") if value and value.strip()]
    language = _first_metadata(book, "language")
    identifiers = [value.strip() for value, _attrs in book.get_metadata("DC", "identifier") if value and value.strip()]
    return BookMetadata(title=title, creators=creators, language=language, identifiers=identifiers)


def _first_metadata(book: epub.EpubBook, name: str) -> str | None:
    """Return the first non-empty metadata value for a Dublin Core field."""
    logger.trace("Entering _first_metadata")
    values = book.get_metadata("DC", name)
    for value, _attrs in values:
        if value and value.strip():
            return value.strip()
    return None


def _toc_entries(book: epub.EpubBook) -> list[TocEntry]:
    """Flatten the EPUB table of contents into ordered conversion entries."""
    logger.trace("Entering _toc_entries")
    entries: list[TocEntry] = []

    def walk(nodes: object, depth: int) -> None:
        """Walk nested EPUB TOC nodes and append resolved entries."""
        logger.trace("Entering walk")
        # EbookLib represents TOC sections as nested tuples/lists, while leaf
        # entries expose href/file_name attributes. Handle both shapes in one
        # recursive walk to preserve reading order and nesting depth.
        if isinstance(nodes, (list, tuple)):
            for node in nodes:
                if isinstance(node, tuple) and len(node) == 2:
                    section, children = node
                    section_title = getattr(section, "title", "")
                    section_href = getattr(section, "href", "")
                    if section_href:
                        entries.append(TocEntry(section_title or section_href, section_href, depth))
                    walk(children, depth + 1)
                    continue
                walk(node, depth)
            return

        href = getattr(nodes, "href", None) or getattr(nodes, "file_name", None)
        if href:
            title = getattr(nodes, "title", None) or getattr(nodes, "get_title", lambda: None)() or href
            entries.append(TocEntry(str(title), str(href), depth))

    walk(book.toc, 0)
    return entries


def _spine_entries(book: epub.EpubBook, document_items: dict[str, Any]) -> list[TocEntry]:
    """Build chapter-like entries from the EPUB spine as a TOC fallback."""
    logger.trace("Entering _spine_entries")
    entries: list[TocEntry] = []
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None:
            continue
        name = _clean_item_name(item.get_name())
        if name in document_items and name.lower() not in {"nav.xhtml", "toc.ncx"}:
            title = _document_title(item) or Path(name).stem
            # The spine also contains non-chapter documents in many EPUBs; the
            # title check keeps the fallback from emitting nav/about pages.
            if not _looks_like_chapter(title):
                continue
            entries.append(TocEntry(str(title), name, 0))
    return entries


def _document_title(item: Any) -> str | None:
    """Infer a document title from EPUB metadata or heading content."""
    logger.trace("Entering _document_title")
    title = getattr(item, "title", None)
    if title:
        return str(title).strip()
    soup = BeautifulSoup(item.get_content(), "html.parser")
    heading = soup.find(["h1", "h2", "h3", "title"])
    if heading:
        return heading.get_text(" ", strip=True)
    return None


def _looks_like_chapter(title: str) -> bool:
    """Return whether text matches the chapter heuristic."""
    logger.trace("Entering _looks_like_chapter")
    return bool(re.search(r"\bchapter\s+\d+\b", title, re.IGNORECASE))


def _copy_assets(book: epub.EpubBook, assets_dir: Path) -> dict[str, str]:
    """Copy supported EPUB assets into the converted asset directory."""
    logger.trace("Entering _copy_assets")
    copied: dict[str, str] = {}
    asset_types = {
        ebooklib.ITEM_IMAGE,
        ebooklib.ITEM_STYLE,
        ebooklib.ITEM_FONT,
        ebooklib.ITEM_VIDEO,
        ebooklib.ITEM_AUDIO,
    }
    for item in book.get_items():
        if item.get_type() not in asset_types:
            continue
        name = _clean_item_name(item.get_name())
        target = assets_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.get_content())
        copied[name] = f"../assets/{name}"
    return copied


def _chapter_fragment(
    soup: BeautifulSoup,
    anchor: str | None,
    entry: TocEntry,
    warnings: list[ConversionWarning],
) -> Tag:
    """Select the HTML fragment that should become a Markdown chapter."""
    logger.trace("Entering _chapter_fragment")
    body = soup.body or soup
    if not anchor:
        return body

    target = soup.find(id=anchor)
    if target is None:
        warnings.append(ConversionWarning("missing_anchor", f"Anchor not found; emitted whole document: {anchor}", entry.href))
        return body
    if isinstance(target, Tag) and target.name in {"section", "article", "chapter", "div", "body"}:
        return target

    # Anchors often land on headings inside a larger chapter section. Prefer
    # that enclosing semantic block so the Markdown file contains the full
    # chapter instead of only the heading node.
    parent = target.find_parent(["section", "article", "div"])
    if isinstance(parent, Tag):
        return parent

    warnings.append(ConversionWarning("ambiguous_anchor", f"Anchor has no safe enclosing section: {anchor}", entry.href))
    wrapper = soup.new_tag("section")
    current: Tag | None = target if isinstance(target, Tag) else None
    while current is not None:
        next_sibling = current.find_next_sibling()
        wrapper.append(current.extract())
        # Stop at the next anchored sibling to avoid swallowing the following
        # chapter when a TOC anchor points into a flat XHTML document.
        if isinstance(next_sibling, Tag) and next_sibling.has_attr("id"):
            break
        current = next_sibling if isinstance(next_sibling, Tag) else None
    return wrapper


def _rewrite_asset_links(fragment: Tag, doc_name: str, copied_assets: dict[str, str]) -> None:
    """Rewrite local asset references in a chapter fragment."""
    logger.trace("Entering _rewrite_asset_links")
    base = PurePosixPath(doc_name).parent
    for tag, attr in [("img", "src"), ("image", "href"), ("a", "href"), ("link", "href"), ("source", "src")]:
        for node in fragment.find_all(tag):
            value = node.get(attr)
            if not isinstance(value, str) or _is_external_url(value):
                continue
            href, suffix = _href_without_fragment(value)
            # EPUB asset links are relative to the source document. Resolve that
            # relative path before looking it up in the copied-asset map.
            normalized = _clean_item_name(str((base / href).as_posix()))
            if normalized in copied_assets:
                node[attr] = copied_assets[normalized] + suffix


def _annotate_source_styles(fragment: Tag) -> None:
    """Preserve source CSS classes as data attributes before Markdown conversion."""
    logger.trace("Entering _annotate_source_styles")
    soup = fragment if isinstance(fragment, BeautifulSoup) else fragment.find_parent()
    owner = soup if isinstance(soup, BeautifulSoup) else BeautifulSoup("", "html.parser")
    for node in list(fragment.find_all(True)):
        classes = node.get("class") or []
        node_id = node.get("id")
        if not classes and not node_id:
            continue
        # markdownify discards most class/id information. Insert source comments
        # so later cleanup can still find where styled EPUB blocks came from.
        parts = [node.name]
        if node_id:
            parts.append(f"#{node_id}")
        if classes:
            parts.append("." + ".".join(str(class_name) for class_name in classes))
        node.insert_before(owner.new_string(f"\n<!-- source: {''.join(parts)} -->\n"))


def _split_profile_table_geno_points(fragment: Tag) -> None:
    """Expand combined profile table Geno Points Gained rows.

    Args:
        fragment: Chapter HTML fragment to mutate before Markdown conversion.
    """
    logger.trace("Splitting profile table Geno Points Gained rows")

    for row in list(fragment.find_all("tr")):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) != 2:
            continue
        label_cell, value_cell = cells
        label = label_cell.get_text(" ", strip=True).lower()
        if label != "geno points gained":
            continue
        point_rows = _parse_geno_point_rows(value_cell.get_text(" ", strip=True))
        if not point_rows:
            continue
        for replacement in reversed(_render_geno_point_row_tags(fragment, point_rows)):
            row.insert_after(replacement)
        row.decompose()


def _parse_geno_point_rows(value: str) -> list[tuple[str, str]]:
    """Parse first-sanctuary Geno Point totals from row text.

    Args:
        value: Source text from a combined ``Geno points gained`` table cell.

    Returns:
        Ordered ``(type, amount)`` pairs for all first-sanctuary Geno Point
        types, or an empty list when the value does not contain a supported
        total.
    """
    logger.trace("Parsing profile table Geno Point rows")

    parsed_amounts: dict[str, str] = {}
    for point_type in GENO_POINT_TYPES:
        match = _match_geno_point_amount(value, point_type)
        if match:
            parsed_amounts[point_type] = match.group("amount")
    if not parsed_amounts:
        return []
    return [(point_type, parsed_amounts.get(point_type, "0")) for point_type in GENO_POINT_TYPES]


def _match_geno_point_amount(value: str, point_type: str) -> re.Match[str] | None:
    """Return the numeric amount for one Geno Point type.

    Args:
        value: Source value from a combined profile table row.
        point_type: Canonical Geno Point type label.

    Returns:
        Regex match containing the ``amount`` group, or ``None`` when the type
        is not present.
    """
    logger.trace(f"Matching profile table Geno Point amount for {point_type}")

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


def _render_geno_point_row_tags(fragment: Tag, point_rows: list[tuple[str, str]]) -> list[Tag]:
    """Build HTML table rows for expanded Geno Points Gained values.

    Args:
        fragment: Chapter HTML fragment used to locate the owning soup.
        point_rows: Canonical point labels and numeric amounts.

    Returns:
        Table row tags that can replace the combined source row.
    """
    logger.trace("Rendering profile table Geno Point row tags")

    soup = fragment if isinstance(fragment, BeautifulSoup) else fragment.find_parent()
    owner = soup if isinstance(soup, BeautifulSoup) else BeautifulSoup("", "html.parser")
    rows: list[Tag] = []

    header = owner.new_tag("tr", attrs={"class": "geno-points-gained"})
    heading = owner.new_tag("th", attrs={"colspan": "2", "style": "text-align:center;"})
    heading.string = "Geno Points Gained"
    header.append(heading)
    rows.append(header)

    for point_type, amount in point_rows:
        row = owner.new_tag("tr")
        label = owner.new_tag("th")
        label.string = point_type
        value = owner.new_tag("td", attrs={"class": "profile-value numeric-value"})
        value.string = amount
        row.append(label)
        row.append(value)
        rows.append(row)
    return rows


def _split_href(href: str) -> tuple[str, str | None]:
    """Split an EPUB href into document path and optional fragment."""
    logger.trace("Entering _split_href")
    split = urlsplit(href)
    doc_name = _clean_item_name(unquote(split.path))
    return doc_name, unquote(split.fragment) if split.fragment else None


def _href_without_fragment(href: str) -> tuple[str, str]:
    """Remove a URL fragment without normalizing the href body."""
    logger.trace("Entering _href_without_fragment")
    split = urlsplit(href)
    suffix = f"#{split.fragment}" if split.fragment else ""
    return unquote(split.path), suffix


def _clean_item_name(name: str) -> str:
    """Normalize an EPUB item name to a decoded POSIX-style path."""
    logger.trace("Entering _clean_item_name")
    return str(PurePosixPath(unquote(name))).lstrip("/")


def _is_external_url(value: str) -> bool:
    """Return whether a link points outside the EPUB package."""
    logger.trace("Entering _is_external_url")
    scheme = urlsplit(value).scheme
    return bool(scheme and scheme not in {"", "file"})


def _first_element_id(fragment: Tag) -> str | None:
    """Return the first element id found in an HTML fragment."""
    logger.trace("Entering _first_element_id")
    if fragment.has_attr("id"):
        return str(fragment["id"])
    node = fragment.find(id=True)
    return str(node["id"]) if node else None


def _frontmatter(values: dict[str, object]) -> str:
    """Render a dictionary as Markdown YAML frontmatter."""
    logger.trace("Entering _frontmatter")
    lines = ["---"]
    for key, value in values.items():
        lines.extend(_yaml_value(key, value))
    lines.append("---")
    return "\n".join(lines)


def _yaml_value(key: str, value: object) -> list[str]:
    """Render one YAML scalar or list field."""
    logger.trace("Entering _yaml_value")
    if value is None:
        return [f"{key}: null"]
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        return [f"{key}:"] + [f"  - {_yaml_scalar(item)}" for item in value]
    return [f"{key}: {_yaml_scalar(value)}"]


def _yaml_scalar(value: object) -> str:
    """Render a Python value as a YAML scalar string."""
    logger.trace("Entering _yaml_scalar")
    text = str(value)
    if not text or text.strip() != text or any(char in text for char in ":#[]{}&*!|>'\"%@`\n"):
        return json.dumps(text)
    return text


def _write_json(path: Path, value: object) -> None:
    """Write UTF-8 JSON with stable indentation."""
    logger.trace("Entering _write_json")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _unique_slug(title: str, used: dict[str, int]) -> str:
    """Create a unique slug for a chapter title."""
    logger.trace("Entering _unique_slug")
    slug = _slugify(title) or "chapter"
    used[slug] = used.get(slug, 0) + 1
    if used[slug] == 1:
        return slug
    return f"{slug}-{used[slug]}"


def _slugify(value: str) -> str:
    """Convert display text into a lowercase URL-style slug."""
    logger.trace("Entering _slugify")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:80].strip("-")


def _safe_folder_name(value: str) -> str:
    """Return a filesystem-safe folder name for a book title."""
    logger.trace("Entering _safe_folder_name")
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip(" .") or "book"
