from __future__ import annotations

from datetime import datetime
from os import environ, getenv
from pathlib import Path
from subprocess import run
from typing import List, Tuple

from bunnet import Document, View, init_bunnet
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from supergene import Log

log: Log = Log()


class Chapter(Document):
    """Chapter class to store chapter information."""

    chapter: int = Field(..., ge=1, lt=3462, title="Chapter number.")
    section: int = Field(..., ge=1, le=18, title="Section number.")
    book: int = Field(..., ge=1, le=1, title="Book number.")
    title: str = Field(..., title="Title of the chapter.")
    text: str = Field(..., title="Text of the chapter.")
    trimmed_text: str = Field(..., title="Trimmed text of the chapter.")
    created: datetime = Field(..., title="Date and time the chapter was created.")
    modified: datetime = Field(
        ..., title="Date and time the chapter was last modified."
    )
    text_embed: List[float] = Field(..., title="Text embedding of the chapter.")
    version: int = Field(..., title="The version of the chapter.")

    class Settings:
        name = "chapter"


def init(
    models: List[type[Document] | type[View] | str] | None = [Chapter],
) -> Database:
    mongo_uri = getenv("MONGO_URI", "mongodb://localhost:27017")
    client: MongoClient = MongoClient(mongo_uri)
    db = client.get_database("supergene")
    init_bunnet(database=db, document_models=[models])  # type: ignore
    log.info("MongoDB connection initialized with bunnet.")
    return db


if __name__ == "__main__":
    db = init()
    log.info("Database initialized.")
    log.info("Chapter document model initialized.")
    chapter1 = Chapter.find_one({"chapter": 1}).run()
    if chapter1 is None:
        log.print("[b #0099ff]Chapter[/][b white] 1[/][b #0099ff] not found.[/]")
    else:
        title = chapter1.title.title()
        chapter_header: str = (
            f"# [b #0099ff]Chapter[/][b white] {chapter1.chapter}[/][b #0099ff][/]"
        )
        md = f"Chapter {chapter1.chapter}: {title}\n\n{chapter1.text}"

        log.print(md)
