# ruff: noqa: F401
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import IntEnum
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, Generator, List, Optional

from bunnet import (
    Document,
    Insert,
    PydanticObjectId,
    Replace,
    after_event,
    before_event,
)
from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic.networks import AnyUrl
from rich.layout import Layout

from supergene.client import MongoClient, mongoclient
from supergene.console import Console, Progress, get_console, get_progress
from supergene.unparsed import Unparsed


# from enum import Enum
class Stage(IntEnum):
    """The stage of the document."""

    UNPARSED = 0
    TRIMMED = 1
    PARSED = 2
    FORMATTED = 3
    MARKDOWN = 4


class Chapter(Document):
    """Represents a chapter in a document."""

    _id = PydanticObjectId()
    chapter: int = Field(
        title="Chapter",
        ge=1,
        lt=3465,
        description="The number of the chapter",
    )
    order: int = Field(
        title="Order",
        ge=0,
    )
    title: str = Field(title="Title", description="The title of the chapter")
    created: datetime = Field()
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
    version: str = Field(pattern=r"\d+\.\d+\.\d+")
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
    tags: List[str] = Field(
        title="Tags",
        description="A list of tags for the chapter",
        examples=[["Voice of God", "Table", "beast soul"]],
        default=[],
    )

    def __eq__(self, other: Any) -> bool:
        """Check if two chapters are equal."""
        if not isinstance(other, Chapter):
            return False
        elif self.chapter != other.chapter:
            return False
        return self.text == other.text

    @computed_field
    def version_major(self) -> int:
        """Get the major version of the document."""
        return int(self.version.split(".")[0])

    @computed_field
    def version_minor(self) -> int:
        """Get the minor version of the document."""
        return int(self.version.split(".")[1])

    @computed_field
    def version_patch(self) -> int:
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

    @field_validator("title")
    @classmethod
    def titlecase_title(cls, value: str) -> str:
        """Custom titlecase the chapter's title."""
        return cls.max_title(value)

    @field_validator("tags")
    @classmethod
    def ensure_no_duplicate_tags(cls, value: List[str]) -> List[str]:
        """Ensure there are no duplicate tags."""
        return list(set(value))

    @staticmethod
    def max_title(title) -> str:
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


def trim_text(chapter: Unparsed) -> Chapter:
    """Trim the text of the chapter by removing unnecessary lines."""
    text: str = chapter.text
    chapter_str: str = f"{chapter.chapter}"
    title: str = chapter.title

    skip_words: List[str] = [
        "chapter",
        chapter_str,
        title,
        "translator",
        "nyoi-bo",
        "studio",
        "editor",
        " - ",
        ": ",
    ]

    split_text: List[str] = text.split("\n\n")
    start: int = 0

    for i, line in enumerate(split_text):
        skip: int = 0
        for word in skip_words:
            if word in line:
                skip += 1
                continue
            if skip >= 2:
                break
            else:
                continue

        # if we made it here, we can skip this line
        if skip:
            start = i + 1
            continue
        else:
            break
    chapter_text: str = "\n\n".join(split_text[start:])
    return Chapter(
        chapter=chapter.chapter,
        order=chapter.order,
        created=chapter.created,
        title=chapter.title,
        url=chapter.url,
        text=chapter_text,
        version=chapter.version,
        filename=chapter.filename,
        filepath=str(chapter.filepath),
        tags=chapter.tags,
    )


def trim_all_chapters(
    progress: Progress = get_progress(),
) -> Generator[Chapter, None, None]:
    """Trim all the chapters."""
    with progress:
        uri_taskid = progress.add_task(
            "Retrieving MongoDB connection string...", total=2,
        )
        try:
            client = mongoclient().
            progress.update(
                uri_taskid, advance=1, description="Retrieved MongoDB Connection String"
            )
        except ConnectionError as ce:
            progress.console.log(f"[i #cfcfcf]ConnectionError:[/] {ce}")
            raise ce
        else:
            try:

        get_chapters: TaskID = progress.add_task("Retrieving chapters", total)

    with ThreadPoolExecutor(max_workers=cpu_count() - 2) as executor:
        results = list(executor.map(trim_text, chapters))

    for result in results.as_completed():
        yield result


if __name__ == "__main__":
    pass
    with ThreadPoolExecutor(max_workers=cpu_count() - 2) as executor:
        results = list(executor.map(trim_text, chapters))

    for result in results.as_completed():
        yield result

if __name__ == "__main__":
    pass
