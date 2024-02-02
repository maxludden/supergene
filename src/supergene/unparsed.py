from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic.networks import AnyUrl
from pymongo import ASCENDING

from bunnet import Document, PydanticObjectId


class Unparsed(Document):
    _id = PydanticObjectId()
    chapter: int = Field(ge=1, lt=3465)
    title: str
    modified: datetime = Field(default_factory=datetime.now)
    url: Optional[AnyUrl]
    text: str
    version: str = Field(pattern=r"\d+\.\d+\.\d+")
    filename: str
    filepath: str | Path

    class Settings:
        name = "unparsed"
        indexes = [[("chapter", ASCENDING), ("_id", ASCENDING)]]
