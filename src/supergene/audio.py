from __future__ import annotations

from datetime import datetime
from os import environ, getenv
from pathlib import Path
from subprocess import run
from typing import List, Tuple, Optional

from dotenv import load_dotenv
from bunnet import Document, View, init_bunnet
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from supergene import Log

load_dotenv()
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

class Mongo:
    def __init__(self) -> None:
        mongo_uri = getenv("MONGO_URI", "op://Dev/Mongo/Database/uri")
        self.client: MongoClient = MongoClient(mongo_uri)
        self.db: Database = self.client["supergene"]


    def get_chapters(self) -> List[Chapter]:
        chapter_col: Collection = self.db["chapter"]
        chapters = chapter_col.find().to_list()
        return chapters

if __name__ == '__main__':
    db = Mongo()
    chapters = db.get_chapters()
    print(chapters)
    log.info("Chapters retrieved.")
