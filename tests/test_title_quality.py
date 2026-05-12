from __future__ import annotations

from pathlib import Path

from supergene.title_quality import find_missing_terminal_t_title_issues


def test_find_missing_terminal_t_title_issues_parses_frontmatter_titles(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text(
        "---\n"
        "index: 1\n"
        'title: "Chapter 1651 - Guardian Spiri"\n'
        "---\n"
        "# Chapter 1651 - Guardian Spiri\n",
        encoding="utf-8",
    )
    (chapters_dir / "002.md").write_text(
        "---\n"
        "index: 2\n"
        'title: "Chapter 1652 - Guardian Spirit"\n'
        "---\n"
        "# Chapter 1652 - Guardian Spirit\n",
        encoding="utf-8",
    )

    issues = find_missing_terminal_t_title_issues(chapters_dir, lexicon={"spirit"})

    assert len(issues) == 1
    assert issues[0].chapter_path == chapters_dir / "001.md"
    assert issues[0].title == "Chapter 1651 - Guardian Spiri"
    assert issues[0].word == "Spiri"
    assert issues[0].suggestion == "Spirit"


def test_find_missing_terminal_t_title_issues_handles_common_super_gene_title_words(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    chapters_dir.mkdir()
    (chapters_dir / "001.md").write_text('---\ntitle: "Chapter 1778 - The Fight to Extinguish the Ligh"\n---\n', encoding="utf-8")
    (chapters_dir / "002.md").write_text('---\ntitle: "Chapter 1757 - Ghost Eye Beas"\n---\n', encoding="utf-8")

    issues = find_missing_terminal_t_title_issues(chapters_dir)

    assert [(issue.word, issue.suggestion) for issue in issues] == [("Ligh", "Light"), ("Beas", "Beast")]
