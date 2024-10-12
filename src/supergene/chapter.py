# ruff: noqa: F401
from datetime import datetime
from subprocess import run
from typing import Any, List, Optional, TypeAlias, Literal
from pathlib import Path
from os import getenv, environ
from enum import Enum, auto

from bunnet import Document, PydanticObjectId, init_bunnet
from fastapi import FastAPI, HTTPException, Request, status
from pendulum import DateTime, now
from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pymongo import MongoClient, ReturnDocument
from pymongo.database import Database
from pymongo.collection import Collection
from rich.text import Text

from dotenv import load_dotenv
from supergene import Log, Console

load_dotenv()
log = Log()

Release: TypeAlias = Literal['major','minor','patch']

class Chapter(Document):
    """Chapter class to store chapter information."""

    chapter: int = Field(..., ge=1, lt=3462, title="Chapter number.")
    section: int = Field(..., ge=1, le=18, title="Section number.")
    book: int = Field(..., ge=1, title="Book number.")
    title: str = Field(..., title="Title of the chapter.")
    text: str = Field(..., title="Text of the chapter.")
    trimmed_text: str = Field(..., title="Trimmed text of the chapter.")
    created: DateTime = Field(default_factory=now, title="Date and time the chapter was created.")
    modified: DateTime = Field(default_factory=now, title="Date and time the chapter was last modified.")
    text_embed: List[float] = Field(..., title="Text embedding of the chapter.")
    _major: int = Field(title="Major version number.", default=0)
    _minor: int = Field(title="Minor version number.", default=1)
    _patch: int = Field(title="Patch version number.", default=0)

    @computed_field()
    def version(self) -> str:
        return f"{self._major}.{self._minor}.{self._patch}"


    def update_version(self, type: Release = 'patch') -> str:
        """Update the version number based on the update type."""
        log.trace(f"Entered `update_version` with type: {type}...")
        msg: Text = Text(f"[#999999]Updated version from [b #af99ff]{self._major}.{self._minor}.{self._patch}[/b #af99ff] [#999999]to[/#999999]", end="")
        match type:
            case 'major':
                self._major += 1
                self._minor = 0
                self._patch = 0
                mode = "major"
            case 'minor':
                self._minor += 1
                self._patch = 0
                mode = "minor"
            case 'patch':
                self._patch += 1
                mode = "patch"
            case _:
                raise ValueError(f"Invalid update type: {type}")
        msg.append(f"[b#af00ff]{self._major}.{self._minor}.{self._patch}")

        return f"{self._major}.{self._minor}.{self._patch}"

    class Settings:
        name = "chapter"
        indexes = [
            {"fields": ["chapter", "section", "book"]},
            {"fields": ["chapter"], "unique": True},
            {"fields": ["text"], "type": "text"},
            {"fields": ["text_embed"], "type": "2dsphere"}
        ]

    def save(self, release: Release = 'patch', *args, **kwargs):
        self.modified = now()
        self.update_version(release)
        log.info(f"Saving chapter: {self.title}")
        return super().save(*args, **kwargs)

# class Settings(BaseSettings):
#     """Settings for the application."""
#     # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
#     MONGO_URI: str = Field(default = getenv("MONGO_URI"), description="MongoDB URI.")
#     DATABASE_NAME: str = Field(default = getenv("DATABASE_NAME"), description="Database name.")
#     COLLECTION_NAME: str = Field(default = getenv("COLLECTION_NAME"), description="Collection name.")
#     LAST: Optional[str] = getenv("LAST")
#     if LAST is not None:
#         last: int = int(LAST)

#     class Config:
#         env_file = ".env"
#         env_file_encoding = "utf-8"


# class Chapter(BaseModel):
#     """The base model for a chapter."""

#     chapter: int = Field(
#         ..., ge=1, lt=3462, description="Chapter number.", examples=["1", "2", "2000"]
#     )
#     section: int = Field(
#         ..., ge=1, le=18, description="Section number.", examples=["1", "3", "18"]
#     )
#     book: int = Field(..., ge=1, le=10, description="Book number.", examples=["1"])
#     description: str = Field(
#         ...,
#         description="description of the chapter.",
#         examples=["supergene", "harvest"],
#     )
#     text: str = Field(..., description="Text of the chapter.")
#     trimmed_text: str = Field(
#         ...,
#         title="Trimmed Text",
#         description="The text that precedes the content of the chapter, such as the chapter title and translator information.",
#         examples=[
#             "Chapter 1 - Supergene\n\nChapter 1: Supergene\n\nTranslator: Nyoi-Bo Studio Editor: Nyoi-Bo Studio",
#             "Chapter 9 - Sacred-Blood Creature\n\nChapter 9: Sacred-blood Creature\n\nTranslator: Nyoi-Bo Studio Editor: Nyoi-Bo Studio",
#         ],
#     )
#     text_embed: List[float] = Field(
#         ...,
#         description="Text embedding of the chapter.",
#         examples=[0.1, 0.2, 0.3]
#     )
#     created: datetime = Field(
#         default_factory=now().isoformat,
#         title="Created",
#         description="Date and time the chapter was created.",
#     )
#     modified: datetime = Field(
#         default_factory=now().isoformat,
#         title="Modified",
#         description="Date and time the chapter was last modified.",
#     )
#     version: float = Field(
#         0.1, title="Version", description="The version of the chapter."
#     )

#     @classmethod
#     def pre_update(cls, update_data: dict, **kwargs) -> dict:
#         """Pre-update hook for the chapter."""
#         update_data["modified"] = now().isoformat()
#         update_data["version"] = float(update_data["version"]) + 0.1
#         return update_data

#     @computed_field
#     def audio_path(self) -> Path:
#         """Computed field for the audio path of the chapter."""
#         return Path(f"audio/{str(self.chapter).zfill(4)}.mp3")

if __name__=="__main__":
    from rich.console import Console


    console = Console()
    log.success("[i #0099ff]Initializing[/] [b #ffffff]Super Gene API[/][i #0099ff]..")

    load_dotenv()
    settings = Settings()
    client: MongoClient = MongoClient(settings.MONGO_URI)
    db: Database = client[settings.DATABASE_NAME]

    try:
        init_bunnet(
        database=db,
        connection_string=settings.MONGO_URI
    )
        app = FastAPI(title="Super Gene API", description="API for Super Gene", version="0.1.0")
    except ConnectionError as ce:
        console.print(f"Connection Error: {ce}")
        exit(1)


