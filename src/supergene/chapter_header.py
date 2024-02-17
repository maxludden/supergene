"""The script is to remove the header from the unparsed chapter text"""
# ruff: noqa: F401
import json
import re
from re import Pattern
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from enum import Enum
from multiprocessing import cpu_count
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple
from datetime import datetime

from bunnet.odm.operators.update.general import Set
from loguru import logger
from maxgradient import Gradient
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pydantic import BaseModel
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.progress import BarColumn, MofNCompleteColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, TaskID
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Row, Table
from rich.text import Text
from snoop import snoop # type: ignore

from supergene.chapter import V3Chapter, Chapter
from supergene.console import Progress, get_console, get_progress_columns
from supergene.mongo import Mongo
from supergene.unparsed import Unparsed



skip_words: List[str] = [
    "chapter", "translator", "nyoi-bo", "studio", "editor"]
skip_patterns: List[Pattern] = [
    re.compile(f"{word}", re.IGNORECASE) for word in skip_words
]


# @snoop()
def get_chapter(chapter: int) -> Tuple[int, str, str]:
    """Retrieve the chapter from MongoDB.
    
    Args:
        chapter (int): the chapter number

    Returns:
        Tuple[int, str, str]: a tuple of the:
            - chapter number
            - title
            - text
    """

    doc = Unparsed.find_one(Unparsed.chapter==chapter).run()
    if not doc:
        raise ValueError(f"Chapter {chapter} not found in the database.")
    return doc.chapter, doc.title, doc.text

# @snoop()
def trim_text(text: str, chapter: int, title: str) -> Tuple[str, str]:
    """Remove the header from the unparsed chapter text

    Args:
        text (str): the unparsed chapter text
        chapter (int): the chapter number
        title (str): the title of the chapter

    Returns:
        Tuple[str, str]: a tuple of the:
            - trimmed text: the header text removed from the text
            - updated text: the text with the header removed
    """
    split_text = text.split("\n\n")
    start: int = 0
    for i, line in enumerate(split_text):
        for pattern in skip_patterns:
            if pattern.search(line):
                start = i + 1
                break
            elif str(chapter).lower() in line.lower() or title.lower() in line.lower():
                start = i + 1
                break
            else:
                continue
        if i > start:
            break
    updated_text = '\n\n'.join(split_text[start:])
    trimmed_text = '\n\n'.join(split_text[:start])
    return trimmed_text, updated_text

class ChapterProjection(BaseModel):
    """Projection of the Chapter model"""
    chapter: int
    title: str
    text: str
    trimmed_text: str

# @snoop()
def update_chapter(chapter: int, title: str, text: str, trimmed_text: str, progress: Progress, task_id: TaskID) -> None:
    """Update the chapter with the trimmed text"""
    doc = Chapter.find_one(Chapter.chapter==chapter).run()
    if doc:
        progress.update(task_id, advance=0.1, description=f"Updating Chapter {doc.chapter}...")
        assert chapter == doc.chapter, f"Chapter {chapter} not found in the database."
        doc.update(Set({"title": title})).update(Set({"text": text})).update(Set({"trimmed_text": trimmed_text}))
        progress.update(task_id, advance=0.1, description=f"Chapter {doc.chapter} Updated.")
            

# @snoop()
def main() -> None:
    """Remove the header from the unparsed chapter text"""
    console = get_console()
    with Progress(
        TextColumn("[progress.description]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
        refresh_per_second=60,
    ) as progress:
        mongo =  Mongo()
        mongo.connect()
        trim = progress.add_task(description="Trimming Chapters Text", total=Unparsed.count())
        for doc in Unparsed.all(sort="chapter"):
            progress.update(trim, advance=0.1, description=f"Retrieving Chapter {doc.chapter}...")
            if not doc:
                raise ValueError(f"Chapter {doc.chapter} not found in the database.")

            progress.update(trim, advance=0.1, description=f"Trimming Chapter {doc.chapter}'s Text...")
            trimmed_text, updated_text = trim_text(doc.text, doc.chapter, doc.title)


            progress.update(trim, advance=0.4, description=f"Trimmed Chapter {doc.chapter}...")
            
            progress.update(trim, advance=0.2, description=f"Processing Chapter {doc.chapter}...")
            chapter_doc = Chapter.find_one(Chapter.chapter==doc.chapter).run()
            if not chapter_doc:
                raise ValueError(f"Chapter {doc.chapter} not found in the database.")
            doc.update(Set({"title": doc.title})).update(Set({"text": updated_text})).update(Set({"trimmed_text": trimmed_text}))
    

def concurrent_main():
    """Remove the header from the unparsed chapter text"""
    console = get_console()
    with Progress(
        TextColumn(
            "[progress.description]{task.description}[/]",
            justify="right"
        ),
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
        mongo =  Mongo()
        mongo.connect()
        trim = progress.add_task(description="Trimming Chapters Text", total=Unparsed.count())
        with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
            futures: List[Future] = [] # type: ignore
            for doc in Unparsed.all(sort="chapter"):
                if doc.chapter <= 784:
                    progress.update(trim, advance=1, description=f"Trimmed Chapter {doc.chapter}...")
                    continue
                future = executor.submit(trim_text, doc.text, doc.chapter, doc.title)
                future.add_done_callback(lambda future: progress.update(trim, advance=0.1, description=f"Trimmed Chapter {doc.chapter}..."))
                futures.append(future)
            for future in as_completed(futures):
                trimmed_text, updated_text = future.result()
                progress.update(trim, advance=0.2, description=f"Processing Chapter {doc.chapter}...")
                chapter_doc = Chapter.find_one(Chapter.chapter==doc.chapter).run()
                if not chapter_doc:
                    raise ValueError(f"Chapter {doc.chapter} not found in the database.")
                doc.update(Set({"title": doc.title})).update(Set({"text": updated_text})).update(Set({"trimmed_text": trimmed_text}))
                progress.update(trim, advance=0.2, description=f"Chapter {doc.chapter} Updated.")
                progress.update(trim, advance=0.2, description=f"Trimmed Chapter {doc.chapter}...")
                progress.update(trim, advance=0.4, description=f"Processing Chapter {doc.chapter}...")
if __name__ == "__main__":  # pragma: no cover
    concurrent_main()
    
