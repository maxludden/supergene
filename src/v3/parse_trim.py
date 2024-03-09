# ruff: noqa: F401
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from typing import Generator, List, Optional

from maxgradient import GradientRule
from rich.markdown import Markdown
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm
from snoop import snoop  # type: ignore

from v3._chapter import Chapter, V3Chapter
from v3.console import Console, Progress, get_console, get_progress

# from dotenv import load_dotenv
# from pymongo import MongoClient
# from pydantic import BaseModel, Field, root_validator
# from bunnet import Document, PydanticObjectId, Replace, before_event, after_event
from v3.mongo import Mongo
from v3.unparsed import Unparsed

_console: Console = get_console()
progress: Progress = get_progress(_console)
console = progress.console


@snoop()
def trim_text(unparsed: Unparsed) -> Chapter:
    """Trim the text of the chapter by removing unnecessary lines."""
    text: str = unparsed.text
    chapter_str: str = f"{unparsed.chapter}"
    _ch: int = int(chapter_str)
    v3 = V3Chapter.find_one({"chapter": _ch}).run()
    title: str = unparsed.title
    if not v3:
        raise ValueError(f"Chapter {chapter_str} not found in V3")
    else:
        v3_title: str = v3.title
        v3_first: str = v3.text.split("\n\n")[0]

    skip_words: List[str] = [
        "chapter",
        chapter_str,
        title,
        v3_title,
        "translator",
        "nyoi-bo",
        "studio",
        "editor",
        ":",
        "-",
    ]

    split_text: List[str] = text.split("\n\n")
    start: int = 0
    _trimmed_text: List[str] = []
    for i, line in enumerate(split_text):
        skip: int = 0
        for word in skip_words:
            if word in line.lower():
                skip += 1
                continue
            if skip >= 2:
                break

                skip += 1
                continue
            else:
                continue

        # if we made it here, we can skip this line
        if skip:
            if v3_first.lower() in line.lower():
                start = 1
                break
            start = i + 1
            _trimmed_text.append(line)
            continue
        else:
            break
    chapter_text: str = "\n\n".join(split_text[start:])
    trimmed_text: str = "\n\n".join(split_text[:start])
    chapter = Chapter(
        chapter=unparsed.chapter,
        order=unparsed.chapter,
        created=datetime.now(),
        title=unparsed.title,
        url=unparsed.url,
        text=chapter_text,
        trimmed_text=trimmed_text,
        version=unparsed.version,
        filename=unparsed.filename,
        filepath=str(unparsed.filepath),
        tags=["trimmed"],
    )
    chapter.create()
    return chapter


def get_chapter_numbers() -> list:  # type: ignore
    """Get all the chapters."""
    _chapters = Unparsed.all().to_list()
    chapters: List[int] = []
    for chapter in _chapters:
        chapters.append(chapter.chapter)
    chapters = sorted(chapters)
    return chapters


@snoop()
def create_chapters() -> None:
    mongo = Mongo()
    mongo._connect()
    console = get_console()
    progress: Progress = Progress(
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
    total: int = Unparsed.count()

    with progress:
        progress.console.print(f"Total Chapters: {total}")
        trim = progress.add_task("Trimming Chapters", total=total)
        with ThreadPoolExecutor(max_workers=cpu_count() - 1) as executor:
            futures = executor.map(trim_text, Unparsed.all().run())

            for future in as_completed(futures):  # type: ignore
                chapter: Chapter = future.result  # type: ignore
                progress.advance(trim, 1.0)
                if chapter.chapter % 100 == 0:
                    progress.console.print(
                        GradientRule(f"Chapter {chapter.chapter} Trimmed")
                    )
                    progress.console.line(2)
                    progress.console.log(Markdown(chapter.text))
                    progress.console.line(2)


if __name__ == "__main__":
    mongo = Mongo()
    mongo._connect()
    create_chapters()  # type: ignore
