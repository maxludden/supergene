# ruff: noqa: F401
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from enum import Enum
from multiprocessing import cpu_count
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from loguru import logger
from maxgradient import Gradient
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.progress import BarColumn, MofNCompleteColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Row, Table
from rich.text import Text

from supergene.chapter import V3Chapter
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


def get_unparsed_title(chapter: int) -> str:
    """Get the title of the chapter from the Unparsed collection.

    Args:
        chapter (int): the chapter number
    """
    _chapter: Optional[Unparsed] = Unparsed.find_one(Unparsed.chapter == chapter).run()
    if _chapter:
        return _chapter.title
    else:
        mongo = Mongo()
        client: MongoClient = mongo.client
        db = client.supergene
        collection = db.unparsed

        _chapter = collection.find_one({"chapter": chapter})
        if _chapter:
            return _chapter.title
        raise AttributeError(f"Chapter {chapter} not found in Unparsed collection.")


def get_v3_title(chapter_num: int) -> str:
    """Get the title of the chapter."""
    chapter: Optional[V3Chapter] = V3Chapter.find_one({"chapter": chapter_num}).run()
    if chapter:
        return chapter.title
    else:
        mongo = Mongo()
        client: MongoClient = mongo.client
        db = client.supergene
        collection = db.V3Chapter

        chapter = collection.find_one({"chapter": chapter_num})
        if chapter:
            return chapter.title

        return get_unparsed_title(chapter_num)


def get_toc_title(chapter_num: int) -> str:
    """Get the title of the chapter."""
    toc_path: Path = Path("/Users/maxludden/dev/py/supergene/static/toc.json")
    with open(toc_path, "r") as toc_file:
        data = dict(json.load(toc_file))
        title = data.get(str(chapter_num))
        if title is None:
            raise IndexError(
                f"Title for the chapter {chapter_num} not found in the table of contents."
            )
        return title


def _toc_table() -> Table:
    """Generate a table to display the table of contents."""
    table = Table(
        title=Gradient("Table of Contents", style="bold"),
        expand=False,
        row_styles=["on #222222", "on #060606"],
        border_style="bold #8fafff",
    )
    table.add_column("Chapter", justify="right", style="bold #00afff")
    table.add_column("Title", justify="default", style="b #cfcfcf")
    return table


def read_toc_json() -> dict:
    toc_path: Path = Path("/Users/maxludden/dev/py/supergene/static/toc.json")
    with open(toc_path, "r") as toc_file:
        data = dict(json.load(toc_file))
    return data


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


def update_title(doc: Unparsed) -> Unparsed:
    """Update the title of the chapter."""
    chapter: int = doc.chapter
    title = get_toc_title(chapter)

    doc.title = titlecase(title, chapter=doc.chapter)
    doc.save()  # type: ignore
    return doc


def update_titles() -> None:
    """Update the titles in the V3Chapter collection."""
    console = Console()
    progress = Progress(
        TextColumn("[bold #00AFFF]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=60,
    )
    mongo = Mongo()
    mongo.connect()
    with progress:
        update_titles = progress.add_task("Updating titles", total=Unparsed.count())
        for doc in Unparsed.all(sort="chapter"):
            update_title(doc)
            progress.update(
                update_titles, advance=1, description=f"Chapter {doc.chapter}"
            )
            progress.console.print(
                f"Updated title for Chapter {doc.chapter}: {doc.title}"
            )


def cc_update_titles() -> None:
    """Update the titles in the V3Chapter collection."""
    console = Console()
    progress = Progress(
        TextColumn("[bold #00AFFF]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        console=console,
        refresh_per_second=60,
    )
    mongo = Mongo()
    mongo.connect()
    with progress:
        update_titles = progress.add_task("Updating titles", total=Unparsed.count())
        with ThreadPoolExecutor(max_workers=cpu_count() - 2) as executor:
            docs = Unparsed.all(sort="chapter").run()
            futures = executor.submit(update_title, docs)  # type: ignore

            for future in as_completed(futures):  # type: ignore
                try:
                    doc = future.result()  # type: ignore
                except Exception as e:
                    progress.console.print(f"An error occurred: {e}")
                else:
                    progress.update(
                        update_titles, advance=1, description=f"Chapter {doc.chapter}"
                    )
                    progress.console.print(
                        f"Updated title for Chapter {doc.chapter}: {doc.title}"
                    )


if __name__ == "__main__":
    update_titles()
