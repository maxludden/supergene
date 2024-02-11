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
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.progress import BarColumn, MofNCompleteColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Row, Table
from rich.text import Text
from snoop import snoop

from supergene.chapter import V3Chapter, Chapter
from supergene.console import Console, Progress, get_console, get_progress
from supergene.mongo import Mongo
from supergene.unparsed import Unparsed



console = get_console()
progress = get_progress(console)
skip_words: List[str] = [
    "chapter", "translator", "nyoi-bo", "studio", "editor"]
skip_patterns: List[Pattern] = [
    re.compile(f"{word}", re.IGNORECASE) for word in skip_words
]

@snoop()
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

@snoop()
def trim_texts() -> None:
    """Remove the header from the unparsed chapter text"""
    mongo=Mongo()
    mongo.connect()
    progress = get_progress(console)
    with progress:
        trim = progress.add_task(description="Trimming Chapters' Text", total=Unparsed.count())
        for doc in Unparsed.all(sort="chapter"):
            progress.update(trim, advance=0.6, description=f"Processing Chapter {doc.chapter}...")
            chapter: int = doc.chapter
            title: str = doc.title
            text: str = doc.text
            trimmed_text, updated_text = trim_text(text, chapter, title)
            chapter_doc = Chapter.find_one(Chapter.chapter==chapter).run()
            if chapter_doc:
                chapter_doc.update(Set({"text": updated_text})).run()
                progress.update(trim, advance=0.1)
                chapter_doc.update(Set({"trimmed_text": trimmed_text})).run()
                progress.update(trim, advance=0.1)
                chapter_doc.update(Set({"title": title})).run()
                progress.update(trim, advance=0.2)
                progress.console.print(Gradient(f"Chapter {chapter} trimmed."))
            else:
                raise FileNotFoundError(f"Chapter {chapter} not found in the database.")

if __name__ == "__main__":  # pragma: no cover
    trim_texts()
    progress.console.print(Gradient("All chapters trimmed."))
    progress.stop()  # type: ignore
    progress.console.print(Gradient("Exiting..."))
    exit(0) 
