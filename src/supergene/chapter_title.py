# ruff: noqa: F401
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from enum import Enum
from multiprocessing import cpu_count
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple


from bunnet.odm.operators.update.general import Set
from loguru import logger
from maxgradient import Gradient
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.progress import BarColumn, MofNCompleteColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Row, Table
from rich.text import Text

from supergene.chapter import V3Chapter, Chapter
from supergene.console import Console, Progress, get_console
from supergene.mongo import Mongo
from supergene.unparsed import Unparsed

_console: Console = get_console()
progress: Progress = Progress(
    TextColumn("[bold #00AFFF]{task.description}[/]", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    MofNCompleteColumn(),
    "•",
    TimeElapsedColumn(),
    console=_console,
    refresh_per_second=60,
)
# console = progress.console

logger.remove()
logger.add(
    "logs/debug.log", level="DEBUG", colorize=False, backtrace=True, diagnose=True
)
logger.add(lambda msg: progress.console.log(msg, log_locals=True), level="SUCCESS")
CH_REGEX = re.compile(r"(chapter\W+\d+[ -:]+)", re.IGNORECASE)


def titlecase(title: str, *, chapter: Optional[int]) -> str:
    """Return the title in titlecase.

        Args:
            title (str): The title you want to titlecase. If not provided, \
the user will be prompted to enter the title.
            chapter (int, optional): The chapter number. If not provided, the user will be prompted to enter the chapter number.
        Returns:
            str: The title in titlecase.
        """
    if title == "":
        if chapter is None:
            assert (
                chapter
            ), "If no title is provided, the chapter number is required to prompt the user for the title."
        title = Prompt.ask(f"Enter the title of the Chapter {chapter}:")
    if len(title) == 1:
        return title.capitalize()
    transitional_words = [
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "en",
        "for",
        "if",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "per",
        "the",
        "to",
        "vs",
    ]
    # Lowercasing the entire title
    title = title.lower()

    # Splitting the title into words
    word_list = re.split(" ", title)
    final = [str(word_list[0]).capitalize()]  # Capitalizing the first word

    # Capitalizing words that are not in the transitional words list
    for word in word_list[1:]:
        word = str(word)
        final.append(word if word in transitional_words else word.capitalize())

    # Joining the words back into a title
    return " ".join(final)


def read_toc() -> Dict[str, str]:
    """Read the table of contents from the file."""
    with open("static/toc.json", "r") as file:
        toc = json.load(file)
    return toc

def get_title(chapter: int, toc: Dict[str, str] = read_toc()) -> str:
    """Retrieve the title of the chapter from MongoDB.

    Args:
        chapter (int): the chapter number

    Returns:
        str: the title of the chapter
    """
    title = toc.get(str(chapter))
    if not title:
        raise ValueError(f"Chapter {chapter} not found in the table of contents.")
    return title

def update_chapter(chapter: int, title: str, progress: Progress) -> Chapter:
    """Update the title of the chapter in MongoDB.

    Args:
        chapter (int): the chapter number
        title (str): the title of the chapter
    """
    doc = Chapter.find_one(Chapter.chapter == chapter).run()
    skipped = []
    if not doc:
        skipped.append(chapter)
        progress.console.log(f"Chapter {chapter} not found in the database.")
        raise ValueError(f"Chapter {chapter} not found in the database.")
    else:
        doc.update(Set({Chapter.title: title}))
        return doc

def main() -> None:
    console = get_console()
    with Progress(
        TextColumn("[progress.description]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=60,
    ) as progress:
        update_titles = progress.add_task("Updating Chapter Titles...", total = 3462)
        mongo=Mongo()
        mongo.connect()
        for k, v in read_toc().items():
            progress.update(update_titles, advance=0.6, description=f"Updating Chapter {k}...")
            chapter: int = int(k)
            title: str = v
            result = update_chapter(chapter, title, progress) # type: ignore # noqa: F841
            progress.update(update_titles, advance=0.4, description=f"Chapter {k} Updated.")

def concurrent_main() -> None:
    console = get_console()
    with Progress(
        TextColumn("[progress.description]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=60,
    ) as progress:
        update_titles = progress.add_task("Updating Chapter Titles...", total = 3462)
        mongo=Mongo()
        mongo.connect()
        with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
            futures: List[Future] = []
            for k, v in read_toc().items():
                chapter: int = int(k)
                title: str = v
                future: Future = executor.submit(update_chapter, chapter, title, progress)
                futures.append(future)
            for index, future in enumerate(as_completed(futures)):
                progress.update(update_titles, advance=1, description=f"Chapter {k} Updated.")

if __name__ == "__main__":
    concurrent_main()
    # main()
