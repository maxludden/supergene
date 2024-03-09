from datetime import datetime
from pathlib import Path
from typing import Optional

# from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pydantic import Field
from pydantic.networks import AnyUrl
from pymongo import ASCENDING

from bunnet import Document, PydanticObjectId


class Version0_0_1(Document):
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
        name = "v0.0.1"
        indexes = [[("chapter", ASCENDING), ("_id", ASCENDING)]]

    @classmethod
    def init_collection(cls, db: Database) -> Collection:
        return db[cls.Settings.name]

    
