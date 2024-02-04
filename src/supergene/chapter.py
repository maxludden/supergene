# ruff: noqa: F401
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any
from enum import IntEnum
import re

from bunnet import Document, PydanticObjectId, before_event, after_event, Insert, Replace
from pydantic import Field, computed_field, BaseModel, field_validator
from pydantic.networks import AnyUrl
from rich.layout import Layout

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
    title: str = Field(
        title="Title",
        description="The title of the chapter"
    )
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
        default = []
    )


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
    
    def __eq__(self, other: Any) -> bool:
        """Check if two chapters are equal."""
        if not isinstance(other, Chapter):
            return False
        elif self.chapter != other.chapter:
            return False
        return self.text == other.text
        
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

    def trim_text(self) -> str:
        """Trim the text of the chapter by removing unnecessary lines."""
        text: str = self.text
        chapter_str: str = f"{self.chapter}"
        title: str = self.title

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
        return "\n\n".join(split_text[start:])
