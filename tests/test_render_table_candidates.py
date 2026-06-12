from __future__ import annotations

import json
from pathlib import Path

from supergene.render_table_candidates import render_table_candidates_html


def test_render_table_candidates_html_renders_proposed_tables(tmp_path: Path) -> None:
    report_path = tmp_path / "table_candidates.json"
    output_path = tmp_path / "table_candidates.html"
    report_path.write_text(
        json.dumps(
            {
                "summary": {
                    "chapters_dir": "converted/Super Gene/chapters",
                    "total_candidates": 1,
                    "by_kind": {"voice_of_world": 1},
                },
                "candidates": [
                    {
                        "kind": "voice_of_world",
                        "chapter_path": "converted/Super Gene/chapters/001.md",
                        "start_line": 22,
                        "end_line": 22,
                        "original_text": "**“Black beetle killed.”**",
                        "proposed_html": '<div class="voice-of-world"><em>Black beetle killed.</em></div>',
                        "confidence": 0.8,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rendered = render_table_candidates_html(report_path, output_path)

    html = output_path.read_text(encoding="utf-8")
    assert rendered == output_path
    assert "<h1>Table Candidate Preview</h1>" in html
    assert "<h2>Rendered Suggestion</h2>" in html
    assert '<div class="voice-of-world"><em>Black beetle killed.</em></div>' in html
    assert ".voice-of-world" in html
    assert "&lt;table&gt;" not in html
    assert "converted/Super Gene/chapters/001.md:22" in html
    assert "**“Black beetle killed.”**" in html
