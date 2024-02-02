from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic.networks import AnyUrl
from rich.layout import Layout

from bunnet import Document, PydanticObjectId


class Chapter(Document):
    _id = PydanticObjectId()
    chapter: int = Field(
        title="Chapter",
        ge=1,
        lt=3465,
        description="The number of the chapter",
    )
    section: int = Field(
        title="Section",
        ge=1,
        le=17,
        description="The number of the section"
    )
    book: int = Field(
        title="Book", ge=1, le=10,  
        description="The number of the book"
    )
    title: str = Field(
        title="Title",
        description="The title of the chapter",
    )
    modified: datetime = Field(
        default_factory=datetime.now,
        title="Modified",
        description="The date and time the chapter was last modified",)
    url: Optional[AnyUrl] = Field(
        title="Url",
        description="The url of the chapter",
    )
    text: str
    version: str = Field(pattern=r"\d+\.\d+\.\d+")
    filename: str
    filepath: str | Path

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
