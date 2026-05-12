from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import unquote, urlsplit

import ebooklib
from bs4 import BeautifulSoup, Tag
from ebooklib import epub
from loguru import logger
from markdownify import ATX, markdownify


@dataclass(frozen=True)
class BookMetadata:
    title: str
    creators: list[str]
    language: str | None
    identifiers: list[str]


@dataclass(frozen=True)
class ConversionWarning:
    code: str
    message: str
    source_href: str | None = None


@dataclass(frozen=True)
class ChapterResult:
    index: int
    title: str
    depth: int
    source_href: str
    output_path: Path


@dataclass(frozen=True)
class ConversionResult:
    metadata: BookMetadata
    output_dir: Path
    chapters: list[ChapterResult]
    warnings: list[ConversionWarning]


@dataclass(frozen=True)
class ConversionProgress:
    completed: int
    total: int
    title: str
    output_path: Path


@dataclass(frozen=True)
class TocEntry:
    title: str
    href: str
    depth: int


ProgressCallback = Callable[[ConversionProgress], None]


def convert_epub(
    epub_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> ConversionResult:
    source = Path(epub_path)
    root = Path(output_dir)
    logger.trace("Starting EPUB conversion: source={} output_dir={} overwrite={}", source, root, overwrite)
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
    document_items = {
        _clean_item_name(item.get_name()): item
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    }
    entries = _toc_entries(book)
    if not entries:
        warnings.append(ConversionWarning("missing_toc", "No table of contents found; using spine order."))
        entries = _spine_entries(book, document_items)
    else:
        spine_entries = _spine_entries(book, document_items)
        if len(spine_entries) > len(entries):
            warnings.append(
                ConversionWarning(
                    "incomplete_toc",
                    f"Table of contents has {len(entries)} entries; spine has {len(spine_entries)} chapter-like documents. Using spine order.",
                )
            )
            entries = spine_entries

    logger.trace("Resolved {} conversion entries for {}", len(entries), source)
    copied_assets = _copy_assets(book, assets_dir)
    logger.trace("Copied {} EPUB assets into {}", len(copied_assets), assets_dir)
    chapters: list[ChapterResult] = []
    used_slugs: dict[str, int] = {}

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

    logger.trace("Finished EPUB conversion: chapters={} warnings={} output={}", len(chapters), len(warnings), book_dir)
    return ConversionResult(metadata, book_dir, chapters, warnings)


def _metadata(book: epub.EpubBook) -> BookMetadata:
    title = _first_metadata(book, "title") or "Untitled"
    creators = [value.strip() for value, _attrs in book.get_metadata("DC", "creator") if value and value.strip()]
    language = _first_metadata(book, "language")
    identifiers = [value.strip() for value, _attrs in book.get_metadata("DC", "identifier") if value and value.strip()]
    return BookMetadata(title=title, creators=creators, language=language, identifiers=identifiers)


def _first_metadata(book: epub.EpubBook, name: str) -> str | None:
    values = book.get_metadata("DC", name)
    for value, _attrs in values:
        if value and value.strip():
            return value.strip()
    return None


def _toc_entries(book: epub.EpubBook) -> list[TocEntry]:
    entries: list[TocEntry] = []

    def walk(nodes: object, depth: int) -> None:
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


def _spine_entries(book: epub.EpubBook, document_items: dict[str, object]) -> list[TocEntry]:
    entries: list[TocEntry] = []
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None:
            continue
        name = _clean_item_name(item.get_name())
        if name in document_items and name.lower() not in {"nav.xhtml", "toc.ncx"}:
            title = _document_title(item) or Path(name).stem
            if not _looks_like_chapter(title):
                continue
            entries.append(TocEntry(str(title), name, 0))
    return entries


def _document_title(item: object) -> str | None:
    title = getattr(item, "title", None)
    if title:
        return str(title).strip()
    soup = BeautifulSoup(item.get_content(), "html.parser")
    heading = soup.find(["h1", "h2", "h3", "title"])
    if heading:
        return heading.get_text(" ", strip=True)
    return None


def _looks_like_chapter(title: str) -> bool:
    return bool(re.search(r"\bchapter\s+\d+\b", title, re.IGNORECASE))


def _copy_assets(book: epub.EpubBook, assets_dir: Path) -> dict[str, str]:
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
    body = soup.body or soup
    if not anchor:
        return body

    target = soup.find(id=anchor)
    if target is None:
        warnings.append(ConversionWarning("missing_anchor", f"Anchor not found; emitted whole document: {anchor}", entry.href))
        return body
    if isinstance(target, Tag) and target.name in {"section", "article", "chapter", "div", "body"}:
        return target

    parent = target.find_parent(["section", "article", "div"])
    if isinstance(parent, Tag):
        return parent

    warnings.append(ConversionWarning("ambiguous_anchor", f"Anchor has no safe enclosing section: {anchor}", entry.href))
    wrapper = soup.new_tag("section")
    current: Tag | None = target if isinstance(target, Tag) else None
    while current is not None:
        next_sibling = current.find_next_sibling()
        wrapper.append(current.extract())
        if isinstance(next_sibling, Tag) and next_sibling.has_attr("id"):
            break
        current = next_sibling if isinstance(next_sibling, Tag) else None
    return wrapper


def _rewrite_asset_links(fragment: Tag, doc_name: str, copied_assets: dict[str, str]) -> None:
    base = PurePosixPath(doc_name).parent
    for tag, attr in [("img", "src"), ("image", "href"), ("a", "href"), ("link", "href"), ("source", "src")]:
        for node in fragment.find_all(tag):
            value = node.get(attr)
            if not value or _is_external_url(value):
                continue
            href, suffix = _href_without_fragment(value)
            normalized = _clean_item_name(str((base / href).as_posix()))
            if normalized in copied_assets:
                node[attr] = copied_assets[normalized] + suffix


def _annotate_source_styles(fragment: Tag) -> None:
    soup = fragment if isinstance(fragment, BeautifulSoup) else fragment.find_parent()
    owner = soup if isinstance(soup, BeautifulSoup) else BeautifulSoup("", "html.parser")
    for node in list(fragment.find_all(True)):
        classes = node.get("class") or []
        node_id = node.get("id")
        if not classes and not node_id:
            continue
        parts = [node.name]
        if node_id:
            parts.append(f"#{node_id}")
        if classes:
            parts.append("." + ".".join(str(class_name) for class_name in classes))
        node.insert_before(owner.new_string(f"\n<!-- source: {''.join(parts)} -->\n"))


def _split_href(href: str) -> tuple[str, str | None]:
    split = urlsplit(href)
    doc_name = _clean_item_name(unquote(split.path))
    return doc_name, unquote(split.fragment) if split.fragment else None


def _href_without_fragment(href: str) -> tuple[str, str]:
    split = urlsplit(href)
    suffix = f"#{split.fragment}" if split.fragment else ""
    return unquote(split.path), suffix


def _clean_item_name(name: str) -> str:
    return str(PurePosixPath(unquote(name))).lstrip("/")


def _is_external_url(value: str) -> bool:
    scheme = urlsplit(value).scheme
    return bool(scheme and scheme not in {"", "file"})


def _first_element_id(fragment: Tag) -> str | None:
    if fragment.has_attr("id"):
        return str(fragment["id"])
    node = fragment.find(id=True)
    return str(node["id"]) if node else None


def _frontmatter(values: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in values.items():
        lines.extend(_yaml_value(key, value))
    lines.append("---")
    return "\n".join(lines)


def _yaml_value(key: str, value: object) -> list[str]:
    if value is None:
        return [f"{key}: null"]
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        return [f"{key}:"] + [f"  - {_yaml_scalar(item)}" for item in value]
    return [f"{key}: {_yaml_scalar(value)}"]


def _yaml_scalar(value: object) -> str:
    text = str(value)
    if not text or text.strip() != text or any(char in text for char in ":#[]{}&*!|>'\"%@`\n"):
        return json.dumps(text)
    return text


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _unique_slug(title: str, used: dict[str, int]) -> str:
    slug = _slugify(title) or "chapter"
    used[slug] = used.get(slug, 0) + 1
    if used[slug] == 1:
        return slug
    return f"{slug}-{used[slug]}"


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:80].strip("-")


def _safe_folder_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip(" .") or "book"
