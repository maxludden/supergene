from pathlib import Path
from typing import List, Optional, Any
from collections.abc import Generator
import markdown_it as md
from rich.progress import Progress, TextColumn, SpinnerColumn, BarColumn, MofNCompleteColumn, TaskProgressColumn, TimeElapsedColumn
from rich.console import Console
from ludden_logging import log, console
from dotenv import load_dotenv

load_dotenv()
progress = Progress(
    TextColumn("[progress.description]{task.description}"),
    SpinnerColumn(),
    BarColumn(bar_width=None),
    MofNCompleteColumn(),
    TaskProgressColumn(),
    TimeElapsedColumn(),
    console=console,
)

class ParseChapters:
    """Read and parse chapters of super gene with markdown-it ollama, and llama@3."""
    ROOT_DIR = Path(__file__).parent.parent
    STATIC_DIR = ROOT_DIR / "static"
    CHAPTERS_DIR = STATIC_DIR / "docs" / "chapters"

    def __init__(self, start: int = 1, end: int = 3463) -> None:
        pass



    @staticmethod
    def get_paths(start: int = 1, end: int = 3462) -> List[Path]:
        """Return a list of chapters from the docs/chapters directory."""
        chapters_dir: Path = Path("docs/chapters")
        paths: List[Path] = []
        for i in range(start, end):
            index: str = f"{str(i).zfill(5)}.txt"
            path = ParseChapters.CHAPTERS_DIR / f"{index}"
            paths.append(path)
        return paths

    @staticmethod
    def get_chapters(start: int = 1, end: int = 3462) -> Generator[str, None, None]:
        """Read chapters.

        Args:
            paths: List of paths to chapters."""
        paths: List[Path] = ParseChapters.get_paths(start, end)
        total: int = len(paths)
        with progress:
            read = progress.add_task("Reading chapters", total=total)
            for i, chapter in enumerate(paths, 1):
                with open(chapter, "r", encoding="utf-8") as f:
                    text: str = f.read()
                    yield text
                progress.update(read, completed=i, total=total)




