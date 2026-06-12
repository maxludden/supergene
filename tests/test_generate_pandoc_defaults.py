"""Tests for generated Super Gene Pandoc book inputs."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_generator_module() -> ModuleType:
    """Load the generator script as a module for direct behavior tests."""
    spec = importlib.util.spec_from_file_location(
        "generate_pandoc_defaults",
        PROJECT_ROOT / "scripts" / "generate_pandoc_defaults.py",
    )
    if spec is None or spec.loader is None:
        msg = "Unable to load scripts/generate_pandoc_defaults.py"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = load_generator_module()
BOOKS = generator.BOOKS
BookDefaults = generator.BookDefaults
build_book_inputs = generator.build_book_inputs
render_chapter = generator.render_chapter
render_continue_page = generator.render_continue_page
render_defaults = generator.render_defaults
render_stylesheet = generator.render_stylesheet
patch_epub_start_landmark = generator.patch_epub_start_landmark
VoiceLineMatcher = generator.VoiceLineMatcher
render_world_voice_card = generator.render_world_voice_card
style_status_profile_tables = generator.style_status_profile_tables
style_voice_of_the_world_lines = generator.style_voice_of_the_world_lines


def test_render_chapter_replaces_source_heading_with_styled_opening() -> None:
    """Generated chapters expose a hidden split header and visible title block."""
    source = """---
index: 1
title: "Chapter 1 : Supergene"
---
# Chapter 1 <!-- source: span.hidden-title --> : Supergene

<!-- source: span.dropcap -->
By a stony creek, Han Sen waited.

The valley was quiet.
"""

    rendered = render_chapter(source, chapter_number=1, chapter_id="chapter-1")

    assert "# Chapter 1: Supergene {.hidden-title}" in rendered
    assert '<section id="chapter-1" class="chapter element" role="doc-chapter" epub:type="bodymatter chapter">' in rendered
    assert '<div class="element-number">1</div>' in rendered
    assert '<h1 class="title">Supergene</h1>' in rendered
    assert '<p class="first2"><span class="first-letter">B</span>y a stony creek, Han Sen waited.</p>' in rendered
    assert "The valley was quiet." in rendered
    assert '<!-- source: span.dropcap -->' not in rendered
    assert "# Chapter 1 <!-- source: span.hidden-title --> : Supergene" not in rendered


def test_style_status_profile_tables_renders_known_profile_block() -> None:
    """Known status/profile lines render as an EPUB-safe table."""
    body = """Han Sen: Not evolved.

Status: None.

Life span: 200 years.

Required for evolution: 100 geno points.

Geno points gained: 79.

Beast souls gained: none.

Han Sen looked frustrated."""

    rendered = style_status_profile_tables(body)

    assert '<table class="profile-table">' in rendered
    assert '<th scope="row">Han Sen</th>' in rendered
    assert '<td class="profile-value">Not evolved.</td>' in rendered
    assert '<th scope="row">Required for evolution</th>' in rendered
    assert '<td class="profile-value numeric-value">100 geno points.</td>' in rendered
    assert "Beast souls gained" in rendered
    assert "Han Sen looked frustrated." in rendered


def test_style_status_profile_tables_preserves_unrelated_key_value_text() -> None:
    """Ordinary key/value prose is not converted into a profile table."""
    body = """Location: Steel Armour Shelter.

Han Sen looked around."""

    assert style_status_profile_tables(body) == body


def test_render_chapter_tables_profile_before_first_prose_dropcap() -> None:
    """A leading profile table is not treated as the first prose paragraph."""
    source = """---
index: 82
title: "Chapter 82 : Fighting Luo Tianyang"
---
# Chapter 82 <!-- source: span.hidden-title --> : Fighting Luo Tianyang

Han Sen: Not evolved.

Status: None.

Life span: 200 years.

Han Sen looked at his current data.
"""

    rendered = render_chapter(source, chapter_number=82, chapter_id="chapter-82")

    assert '<table class="profile-table">' in rendered
    assert '<p class="first2"><span class="first-letter">H</span>an Sen looked at his current data.</p>' in rendered
    assert '<span class="first-letter">H</span>an Sen: Not evolved.' not in rendered


def test_render_continue_page_points_to_next_book_and_handles_final_book() -> None:
    """Back matter invites readers to the next split book when one exists."""
    first_page = render_continue_page(BOOKS[0], BOOKS)
    final_page = render_continue_page(BOOKS[-1], BOOKS)

    assert "Continue reading Super Gene: Second God's Sanctuary." in first_page
    assert "You have reached the end of this Super Gene reading edition." in final_page


def test_render_stylesheet_contains_bookerly_and_chapter_title_classes() -> None:
    """The generated stylesheet packages Bookerly and HWF-inspired classes."""
    stylesheet = render_stylesheet()

    assert '@font-face' in stylesheet
    assert 'font-family: "Bookerly"' in stylesheet
    assert 'url("../fonts/Bookerly.ttf")' in stylesheet
    assert ".element-number" in stylesheet
    assert ".title-block" in stylesheet
    assert "break-before: left" in stylesheet
    assert "\n.hidden-title {\n  display: none;" not in stylesheet
    assert "h1.hidden-title {\n  display: none;" in stylesheet
    assert ".world-voice-card" in stylesheet
    assert ".world-voice-inline" in stylesheet
    assert 'font-family: "Courier New", Courier, monospace;' in stylesheet
    assert "font-size: 0.8em;" in stylesheet
    assert "font-style: normal;" in stylesheet
    assert "margin: 1em 8%;" in stylesheet
    assert "text-indent: 0;" in stylesheet
    assert "display: block;" in stylesheet
    assert "padding: 0;" in stylesheet
    assert "text-align: center;" in stylesheet
    assert ".chapter-text .world-voice," in stylesheet
    assert ".chapter-text .world-voice em {" in stylesheet
    assert "page-break-after: avoid;" in stylesheet
    assert ".also-in-series ol" in stylesheet
    assert "page-break-before: avoid;" in stylesheet
    assert "-webkit-hyphens: none;" in stylesheet
    assert "hyphens: none;" in stylesheet
    assert ".chapter-text p {\n  text-align: justify;\n  text-indent: 1.5em;\n  margin: 0;\n  -webkit-hyphens: auto;\n  hyphens: auto;" in stylesheet
    assert ".world-voice-card {\n  border: 1px solid #7a7a7a;" in stylesheet
    assert ".world-voice-card,\n.world-voice,\n.world-voice em,\n.world-voice-inline {" in stylesheet
    assert ".series-name,\n.book-subtitle,\n.book-author,\n.series-book,\n.current-series-book {" in stylesheet
    assert ".profile-table" in stylesheet
    assert ".profile-table th" in stylesheet
    assert ".profile-table .numeric-value" in stylesheet
    assert "text-align: right;" in stylesheet
    assert "overflow-wrap: normal;" in stylesheet
    assert "word-break: normal;" in stylesheet


def test_voice_matcher_loads_static_seed_examples() -> None:
    """The generator can load curated Voice of the World examples."""
    matcher = VoiceLineMatcher.from_seed_path(PROJECT_ROOT / "static" / "voice_of_the_world.txt")

    assert matcher.is_voice_line("Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.")
    assert not matcher.is_voice_line("Why is this black beetle so strange?")


def test_style_voice_of_the_world_lines_cards_standalone_seed_match() -> None:
    """Standalone matched system notices become bordered cards."""
    matcher = VoiceLineMatcher.from_seed_lines(
        [
            "Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.",
        ]
    )

    rendered = style_voice_of_the_world_lines(
        '**“Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.”**',
        matcher,
    )

    assert rendered == render_world_voice_card(
        "“Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.”"
    )


def test_render_world_voice_card_strips_spaces_before_quote() -> None:
    """Voice cards do not preserve leading spaces before the opening quote."""
    rendered = render_world_voice_card(
        "   “Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.”"
    )

    assert "<em>“Black beetle killed." in rendered
    assert "<em>   “" not in rendered


def test_style_voice_of_the_world_lines_preserves_ordinary_bold_dialogue() -> None:
    """Bold dialogue stays untouched when it does not match voice seeds."""
    matcher = VoiceLineMatcher.from_seed_lines(
        [
            "Black beetle killed. No beast soul gained. Eat the flesh of the black beetle to gain zero to ten geno points randomly.",
        ]
    )
    dialogue = '**“Why is this black beetle so strange?”** Han Sen stared at the golden black beetle.'

    assert style_voice_of_the_world_lines(dialogue, matcher) == dialogue


def test_style_voice_of_the_world_lines_preserves_bold_thought_with_voice_keywords() -> None:
    """Inline thoughts with system-like words are not styled without voice context."""
    matcher = VoiceLineMatcher.from_seed_lines(["Black beetle flesh eaten. Zero geno points gained."])
    thought = (
        "**“I have received zero geno points from more than thirty black beetles in a row. "
        "When will I ever finish the first evolution?”** Han Sen looked frustrated."
    )

    assert style_voice_of_the_world_lines(thought, matcher) == thought


def test_style_voice_of_the_world_lines_marks_inline_voice_notice() -> None:
    """Inline voice notices receive inline styling without moving prose."""
    matcher = VoiceLineMatcher.from_seed_lines(["Flesh of black beetle eaten. One sacred geno point gained."])
    line = "He ate the meat and heard the voice say, **“Flesh of black beetle eaten. One sacred geno point gained.”**"

    rendered = style_voice_of_the_world_lines(line, matcher)

    assert "He ate the meat and heard the voice say," in rendered
    assert '<span class="world-voice-inline"><em>“Flesh of black beetle eaten. One sacred geno point gained.”</em></span>' in rendered


def test_build_book_inputs_writes_frontmatter_blank_chapter_and_backmatter(tmp_path: Path) -> None:
    """Book input generation writes ordered book-ready Markdown files."""
    chapters_dir = tmp_path / "chapters"
    book_inputs_root = tmp_path / "book-inputs"
    chapters_dir.mkdir()
    chapter_path = chapters_dir / "001-chapter-1-supergene.md"
    chapter_path.write_text(
        """---
index: 1
title: "Chapter 1 : Supergene"
---
# Chapter 1 <!-- source: span.hidden-title --> : Supergene

By a stony creek, Han Sen waited.
""",
        encoding="utf-8",
    )
    book = BookDefaults(1, "First God's Sanctuary", 1, 1, "first-gods-sanctuary")

    generated_files = build_book_inputs(book, (book, BOOKS[1]), [chapter_path], book_inputs_root)

    assert [path.name for path in generated_files] == [
        "0001-also-in-series.md",
        "0002-title-page.md",
        "0003-copyright.md",
        "0004-blank-before-chapter.md",
        "0005-001-chapter-1-supergene.md",
        "9999-continue.md",
    ]
    assert generated_files[0].read_text(encoding="utf-8").count("Super Gene:") == 2
    assert '<section id="also-in-series-page" class="frontmatter also-in-series"' in generated_files[
        0
    ].read_text(encoding="utf-8")
    assert '<h1 class="frontmatter-heading">Also in Series</h1>' in generated_files[0].read_text(
        encoding="utf-8"
    )
    assert "# Also in Series {.hidden-title .unlisted}" in generated_files[0].read_text(
        encoding="utf-8"
    )
    assert "# Also in Series {.frontmatter-title .unlisted}" not in generated_files[0].read_text(
        encoding="utf-8"
    )
    title_page = generated_files[1].read_text(encoding="utf-8")
    assert "# Title Page {.hidden-title .unlisted}" in title_page
    assert '<p class="series-name">Super Gene</p>' in title_page
    assert '<h1 class="book-title">First God&#x27;s Sanctuary</h1>' in title_page
    assert "<h1 class=\"book-title\">Super Gene:" not in title_page
    assert '<p class="book-author">Twelve-Winged Dark Seraphim</p>' in title_page
    assert '<div class="producer-credit">' in title_page
    assert "Produced By" in title_page
    assert "Max Ludden" in title_page
    copyright_page = generated_files[2].read_text(encoding="utf-8")
    assert "# Copyright {.hidden-title .unlisted}" in copyright_page
    assert "# Copyright {.frontmatter-title .unlisted}" not in copyright_page
    assert "Original text by Twelve-Winged Dark Seraphim." in copyright_page
    assert "Dark Burning Angel" not in copyright_page
    assert "blank-page" in generated_files[3].read_text(encoding="utf-8")
    assert '<div class="element-number">1</div>' in generated_files[4].read_text(encoding="utf-8")


def test_render_defaults_uses_generated_inputs_and_epub_landmark_metadata(tmp_path: Path) -> None:
    """Pandoc defaults consume generated inputs and point readers at chapter one."""
    book = BookDefaults(1, "First God's Sanctuary", 1, 1, "first-gods-sanctuary")
    generated_files = [
        tmp_path / "book-inputs" / "book-01-first-gods-sanctuary" / "0001-also-in-series.md",
        tmp_path / "book-inputs" / "book-01-first-gods-sanctuary" / "0005-001-chapter-1-supergene.md",
    ]

    defaults = render_defaults(book, generated_files)

    assert "${.}/../book-inputs/book-01-first-gods-sanctuary/0001-also-in-series.md" in defaults
    assert "${.}/../book-inputs/book-01-first-gods-sanctuary/0005-001-chapter-1-supergene.md" in defaults
    assert "bodymatter:" in defaults
    assert "0005-001-chapter-1-supergene.md" in defaults
    assert "epub-fonts:" in defaults
    assert "${.}/../assets/fonts/Bookerly.ttf" in defaults
    assert "${.}/../chapters/" not in defaults
    assert "    - Twelve-Winged Dark Seraphim" in defaults
    assert "Dark Burning Angel" not in defaults


def test_patch_epub_start_landmark_adds_nav_and_guide_entries(tmp_path: Path) -> None:
    """A built EPUB can be patched to start supported readers at chapter one."""
    epub_path = tmp_path / "book.epub"
    nav = """<html xmlns:epub="http://www.idpf.org/2007/ops">
<body>
<nav epub:type="landmarks" id="landmarks" hidden="hidden">
<ol>
<li><a href="text/cover.xhtml" epub:type="cover">Cover</a></li>
</ol>
</nav>
</body>
</html>
"""
    opf = """<package version="3.0" xmlns="http://www.idpf.org/2007/opf">
<metadata></metadata>
<manifest></manifest>
<spine></spine>
<guide>
<reference type="cover" title="Cover" href="text/cover.xhtml" />
</guide>
</package>
"""
    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("EPUB/nav.xhtml", nav)
        archive.writestr("EPUB/content.opf", opf)
        archive.writestr("EPUB/text/ch005.xhtml", "<html />")

    patch_epub_start_landmark(epub_path, "text/ch005.xhtml")

    with zipfile.ZipFile(epub_path) as archive:
        patched_nav = archive.read("EPUB/nav.xhtml").decode("utf-8")
        patched_opf = archive.read("EPUB/content.opf").decode("utf-8")

    assert '<a href="text/ch005.xhtml" epub:type="bodymatter">Start Reading</a>' in patched_nav
    assert '<reference type="text" title="Start Reading" href="text/ch005.xhtml" />' in patched_opf
    assert patched_opf.count("<guide>") == 1
