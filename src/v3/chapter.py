# ruff: noqa: F401
import re
from datetime import datetime
from enum import Enum, auto
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bunnet import (
    Document,
    Insert,
    PydanticObjectId,
    Replace,
    after_event,
    before_event,
)
from maxgradient import Color, Gradient
from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic.networks import AnyUrl
from rich.layout import Layout
from rich.table import Row, Table
from rich.text import Text

from v3.unparsed import Unparsed


class Format(BaseModel):
    """The format of the chapter's text."""

    HTML: str = ".html"
    MARKDOWN: str = ".md"
    TEXT: str = ".txt"


class Version(Document):
    """A version of a chapters text.

    Attributes:
        major (int): The major version number.
        minor (int): The minor version number.
        patch (int): The patch version number.
        date (datetime): The date and time the version was created.
        text (str): The text of the version.
    """
    chapter: int = Field(ge=1, le=3462, title="Chapter")
    date: datetime = Field(
        default_factory=datetime.now,
        title="Date",
        description="The date and time the version was created.",
    )
    version: str = Field(
        pattern=r"\d+\.\d+\.\d+",
        title="Version",
        description="The version of the chapter's text.",
    )
    text: str
    format: str = Field(title="Format", description="The format of the version's text.")

    def __eq__(self, other: Any) -> bool:
        """Check if two versions are equal."""
        match self.chapter:
            case _ if isinstance(other, Version):
                if self.major == other.major:
                    if self.minor == other.minor:
                        return self.patch == other.patch
                    else:
                        return False
                else:
                    return False

            case _:
                return False

    @property
    @computed_field
    def major(self) -> int:
        """Get the major version number."""
        return int(self.version.split(".")[0])

    @property
    @computed_field
    def minor(self) -> int:
        """Get the minor version number."""
        return int(self.version.split(".")[1])

    @property
    @computed_field
    def patch(self) -> int:
        """Get the patch version number."""
        return int(self.version.split(".")[2])

    @before_event(Insert)
    def set_date(self) -> None:
        """Set the date."""
        self.date = datetime.now()

    class Settings:
        name = "version"


class Chapter(Document):
    """A chapter of the novel Super Gene with metadata and the different revisions of the text.

    Attributes:
        chapter (int): The number of the chapter.
        order (int): The order of the chapter.
        filename (str): The filename of the chapter with file extension.
        filepath (str): The complete path to the file.
        title (str): The title of the chapter.
        url (Optional[AnyUrl]): The url of the chapter.
        text (str): The latest revision of the chapter's text.
        trimmed_text (str): The trimmed text of the chapter.
        version (str): The version of the chapter.
        tags (List[str]): A list of tags for the chapter.

    Managed Attributes:
        _id (PydanticObjectId): The unique identifier of the chapter.
        created (datetime): The date and time the chapter was created.
        modified (datetime): The date and time the chapter was last modified.
        section (int): The section number of the chapter.
        book (int): The book number of the chapter.
    """

    _id = PydanticObjectId()
    chapter: int = Field(
        title="Chapter",
        ge=1,
        le=3462,
        description="The number of the chapter",
    )
    order: int = Field(title="Order", ge=0, le=3462)
    filename: str = Field(
        title="Filename",
        description="The filename of the chapter with file extension",
        examples=["00001.txt", "1234.md"],
    )
    filepath: str = Field(
        title="Filepath",
        description="The complete path to the file.",
        examples=[
            "/Users/maxludden/path/to/file.txt",
            "/home/maxludden/path/to/file.md"
            "/Users/maxludden/dev/pandoc/data/default",
        ],
    )
    title: str = Field(
        title="Title",
        description="The title of the chapter",
        examples=[
            "Supergene",
            "Ass Freak",
        ],
    )
    created: datetime = Field(
        title="Created",
        description="The date and time the chapter was created",
        frozen=True,
    )
    modified: datetime = Field(
        default_factory=datetime.now,
        title="Modified",
        description="The date and time the chapter was last modified",
    )
    url: Optional[AnyUrl] = Field(
        title="Url",
        description="The url of the chapter",
    )
    text: str = Field(title="Text", description="The text of the chapter")
    trimmed_text: str = Field(
        ..., title="Trimmed Text", description="The trimmed text of the chapter."
    )
    tags: List[str] = Field(
        title="Tags",
        description="A list of tags for the chapter",
        examples=[["Voice of God", "Table", "beast soul"]],
        default=[],
    )
    version: str = Field(pattern=r"\d+\.\d+\.\d+")
    versions: List[Version] = Field(
        title="Versions",
        description="The different versions of the chapter's text.",
        default=[],
    )

    class Settings:
        name = "base_chapter"

    def __eq__(self, other: Any) -> bool:
        """Check if two chapters are equal."""
        match self.chapter:
            case _ if isinstance(other, Chapter):
                return self.chapter == other.chapter
            case _ if issubclass(other, Chapter):
                return self.chapter == other.chapter
            case _:
                return False

    def __str__(self) -> str:
        """Return the chapter's title."""
        return f"{self.title}"

    def __int__(self) -> int:
        """Return the chapter's number."""
        return self.chapter

    def __repr__(self) -> str:
        """Get the string representation of the chapter."""
        return f"Chapter {self.chapter}: {self.title}"

    @property
    @computed_field
    def section(self) -> int:
        """Get the section number of the chapter."""
        match self.chapter:
            case _ if self.chapter < 425:
                return 1
            case _ if 425 <= self.chapter < 883:
                return 2
            case _ if 883 <= self.chapter < 1339:
                return 3
            case _ if 1339 <= self.chapter < 1679:
                return 4
            case _ if 1679 <= self.chapter < 1712:
                return 5
            case _ if 1712 <= self.chapter < 1821:
                return 6
            case _ if 1821 <= self.chapter < 1961:
                return 7
            case _ if 1961 <= self.chapter < 2166:
                return 8
            case _ if 2166 <= self.chapter < 2205:
                return 9
            case _ if 2205 <= self.chapter < 2300:
                return 10
            case _ if 2300 <= self.chapter < 2444:
                return 11
            case _ if 2444 <= self.chapter < 2640:
                return 12
            case _ if 2641 <= self.chapter < 2766:
                return 13
            case _ if 2766 <= self.chapter < 2892:
                return 14
            case _ if 2892 <= self.chapter < 3034:
                return 15
            case _ if 3034 <= self.chapter < 3304:
                if self.chapter == 3095 or self.chapter == 3117:
                    raise ValueError(f"Invalid chapter: {self.chapter}")
                return 16
            case _ if 3304 <= self.chapter <= 3462:
                return 17
            case _:
                raise ValueError(f"Chapter {self.chapter} does not have a section.")

    @property
    @computed_field
    def book(self) -> int:
        """Get the book number of the chapter."""
        match self.section:
            case 1:
                return 1
            case 2:
                return 2
            case 3:
                return 3
            case 4:
                return 4
            case 5:
                return 4
            case 6:
                return 5
            case 7:
                return 5
            case 8:
                return 6
            case 9:
                return 6
            case 10:
                return 7
            case 11:
                return 7
            case 12:
                return 8
            case 13:
                return 8
            case 14:
                return 9
            case 15:
                return 9
            case 16:
                return 10
            case 17:
                return 10
            case _:
                raise ValueError(f"Section {self.section} does not have a book.")

    @property
    @computed_field
    def major(self) -> int:
        """Get the major version of the document."""
        return int(self.version.split(".")[0])

    @property
    @computed_field
    def minor(self) -> int:
        """Get the minor version of the document."""
        return int(self.version.split(".")[1])

    @property
    @computed_field
    def patch(self) -> int:
        """Get the patch version of the document."""
        return int(self.version.split(".")[2])

    @before_event(Insert)
    def set_created(self) -> None:
        """Set the created date."""
        self.created = datetime.now()

    @before_event(Insert, Replace)
    def set_modified(self) -> None:
        """Set the modified date."""
        self.modified = datetime.now()

    def get_latest_version(self) -> str:
        """Get the latest version of the chapter's text."""
        latest_version = "0.0.0"
        for version in self.versions:
            if version.version > latest_version:
                latest_version = version.version
        return latest_version

    def get_updated_text(self) -> str:
        """Get the updated text of the chapter."""
        latest_version = self.get_latest_version()
        for version in self.versions:
            if version.version == latest_version:
                return version.text
        return self.text

    @after_event(Insert, Replace)
    def update_version_text(self) -> None:
        """Update the latest version of the text and its version"""
        latest_version: str = self.get_latest_version()
        if latest_version > self.version:
            self.version = latest_version
            self.text = self.get_updated_text()

    @field_validator("title")
    @classmethod
    def titlecase_title(cls, value: str) -> str:
        """Custom titlecase the chapter's title."""
        return cls.titlecase(value)

    @field_validator("tags")
    @classmethod
    def ensure_no_duplicate_tags(cls, value: List[str]) -> List[str]:
        """Ensure there are no duplicate tags."""
        return list(set(value))

    @field_validator("chapter")
    @classmethod
    def ensure_skipped_chapters(cls, value: int) -> int:
        """Ensure the chapters 3095 & 3117 are skipped."""
        if value == 3095 or value == 3117:
            raise ValueError(f"Chapter {value} isn't skipped.")
        return value

    @staticmethod
    def titlecase(title: str) -> str:
        """
        Custom titlecase the chapter's title.

        Args:
            title (str): The string you want to transform.

        Returns:
            str: The transformed string.
        """
        title = title.lower()
        articles = [
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
        word_list = re.split(" ", title)
        final = [str(word_list[0]).capitalize()]
        for word in word_list[1:]:
            word = str(word)
            final.append(word if word in articles else word.capitalize())

        result = " ".join(final)
        return result

    def make_layout(self) -> Layout:
        """Generate a layout to display the chapter's text."""
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )
        layout.split_row(
            Layout(name="left_margin", size=4),
            Layout(name="article"),
            Layout(name="right_margin", size=4),
        )
        return layout

    @classmethod
    def create_chapters_from_unparsed(cls) -> None:
        """Create Chapter documents from Unparsed documents."""
        from v3.mongo import Mongo
        mongo = Mongo()
        mongo._connect()
        for item in Unparsed.all(sort="chapter").to_list():
            chapter: int = item.chapter
            title: str = item.title
            text: str = item.text
            created: datetime = datetime.now()
            modified: datetime = item.modified
            version: str = "0.0.1"
            filename: str = item.filename
            filepath: str | Path = item.filepath
            new_version: Version = Version(
                chapter=chapter,
                version=version,
                text=text,
                format=Format().TEXT,
            )
            new_chapter = Chapter(
                chapter=chapter,
                order=chapter,
                title=title,
                text=text,
                trimmed_text=item.trimmed_text,
                created=created,
                modified=modified,
                version=version,
                versions=[new_version],
                filename=filename,
                filepath=str(filepath),
                url=item.url,
            )
            Unparsed.insert(new_chapter)


if __name__ == "__main__":  # pragma: no cover
    from os import getenv

    from dotenv import load_dotenv
    from pymongo import MongoClient
    from rich.console import Console

    from v3.mongo import Mongo
    mongo = Mongo()
    mongo._connect()
    for item in Unparsed.all(sort="chapter").to_list():
        chapter: int = item.chapter
        title: str = item.title
        text: str = item.text
        created: datetime = datetime.now()
        modified: datetime = item.modified
        version: str = "0.0.1"
        filename: str = item.filename
        filepath: str | Path = item.filepath
        new_version: Version = Version(
            chapter=chapter,
            version=version,
            text=text,
            format=Format().TEXT,
        )
        Version.insert(new_version)
        new_chapter = Chapter(
            chapter=chapter,
            order=chapter,
            title=title,
            text=text,
            trimmed_text=item.trimmed_text,
            created=created,
            modified=modified,
            version=version,
            versions=[new_version],
            filename=filename,
            filepath=str(filepath),
            url=item.url,
        )
        Unparsed.insert(new_chapter)
