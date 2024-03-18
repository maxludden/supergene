"""View text files in the terminal."""

# ruff: noqa: F401
from os import environ, getenv
from pathlib import Path
from sys import argv
from typing import Any, Optional

from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.reactive import var
from textual.widgets import Button, Footer, Header, Markdown, MarkdownViewer, Static
from textual.screen import Screen

class ChapterSearch(Screen):
    BINDINGS=[
        ("enter", "search", "Search"),
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit")
    ]

    def compose(self) -> ComposeResult:
        yield Static("Enter the chapter number:", id="chapter_prompt")

class WorldVoiceApp(App):
    BINDINGS = [
        ("tab", "next", "Next"),
        ("shift+tab", "previous", "Previous"),
        ("space", "toggle_selection", "Toggle Selection"),
        ("q", "quit", "Quit"),
    ]

    path = var(Path(__file__).parent)
    mdoe = var()
    CURRENT_PATH: Path = Path.cwd() / "src" / "tui" / "current_chapter.txt"

    @classmethod
    def get_current_chapter(cls) -> int:
        """Get the current chapter."""
        if len(argv) > 1:
            current_chapter: int = int(argv[1])
            return cls.write_current_chapter(current_chapter)

        load_dotenv()
        # Environmental Variable
        current = int(getenv("CURRENT", None))  # type: ignore
        if current:
            current_chapter = int(current) + 1
            return cls.write_current_chapter(current)
        else:
            # Read from File
            if not cls.CURRENT_PATH.exists():
                with open(cls.CURRENT_PATH, "w") as outfile:
                    outfile.write("1")
            with open(cls.CURRENT_PATH, "r") as infile:
                current = int(infile.read())
                return cls.write_current_chapter(current)

    @classmethod
    def write_current_chapter(cls, chapter: int) -> int:
        """Write the current chapter."""
        try:
            environ["CURRENT"] = str(chapter)
            with open(cls.CURRENT_PATH, "w") as outfile:
                outfile.write(str(chapter))

        except FileNotFoundError as fnfe:
            raise FileNotFoundError from fnfe
        except IOError as ioe:
            raise IOError from ioe
        return chapter

    @property
    def markdown_viewer(self) -> MarkdownViewer:
        """Get the Markdown widget."""
        return self.query_one(MarkdownViewer)

    @property
    def mode(self) -> App

    def compose(self) -> ComposeResult:
        yield Header(name="mode", id="header", show_clock=True, classes="mode")

        yield MarkdownViewer()
        yield Footer()
