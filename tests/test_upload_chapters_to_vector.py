from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from rich.panel import Panel
from typer.testing import CliRunner


runner = CliRunner()
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "upload_chapters_to_vector.py"
SPEC = importlib.util.spec_from_file_location("upload_chapters_to_vector", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
upload_script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upload_script)


class FakeOpenAI:
    pass


def test_typer_cli_uploads_top_level_markdown_files(monkeypatch, tmp_path: Path) -> None:
    chapter = tmp_path / "001.md"
    chapter.write_text("# Chapter\n", encoding="utf-8")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "002.md").write_text("# Nested\n", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr(upload_script, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(upload_script, "setup_logging", lambda: None)

    def fake_upload_files(client: FakeOpenAI, file_paths: list[Path]) -> list[str]:
        calls["client"] = client
        calls["file_paths"] = file_paths
        return ["file-1"]

    def fake_attach_files_to_vector_store(client: FakeOpenAI, file_ids: list[str]) -> None:
        calls["attached_client"] = client
        calls["file_ids"] = file_ids

    monkeypatch.setattr(upload_script, "upload_files", fake_upload_files)
    monkeypatch.setattr(upload_script, "attach_files_to_vector_store", fake_attach_files_to_vector_store)

    result = runner.invoke(upload_script.app, [str(tmp_path), "--no-recursive"])

    assert result.exit_code == 0
    assert "Found 1 markdown file(s)." in result.stdout
    assert calls["file_paths"] == [chapter]
    assert calls["file_ids"] == ["file-1"]


def test_setup_logging_uses_error_console_for_terminal_messages(monkeypatch, tmp_path: Path) -> None:
    messages: list[object] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(upload_script.err_console, "print", lambda message, **kwargs: messages.append(message))

    upload_script.setup_logging()
    upload_script.logger.error("Terminal-only failure")

    assert any(isinstance(message, Panel) for message in messages)
    assert any("#ec7063" in str(message.border_style) for message in messages if isinstance(message, Panel))


def test_log_to_err_console_prints_panel_with_message_metadata_and_level_color(monkeypatch) -> None:
    panels: list[object] = []
    record = {
        "level": SimpleNamespace(name="ERROR", no=40),
        "time": datetime(2026, 5, 11, 14, 30, 0),
        "file": SimpleNamespace(name="upload_chapters_to_vector.py"),
        "line": 66,
        "function": "upload_files",
        "message": "Failed to upload file",
    }
    message = SimpleNamespace(record=record)

    monkeypatch.setattr(upload_script.err_console, "print", lambda panel, **kwargs: panels.append(panel))

    upload_script.log_to_err_console(message)

    panel = panels[0]
    assert isinstance(panel, Panel)
    assert "#ec7063" in str(panel.border_style)
    assert "ERROR" in str(panel.title)
