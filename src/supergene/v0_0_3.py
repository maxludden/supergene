"""v0.0.3
    update the section and book
"""

# ruff: noqa: F401
import re
from datetime import datetime
from enum import IntEnum
from functools import singledispatch, singledispatchmethod
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from typing import Any, List, Optional, Tuple

import torch
from bunnet import (
    Document,
    Insert,
    PydanticObjectId,
    Replace,
    after_event,
    before_event,
    init_bunnet,
)
from maxgradient import Color, Gradient
from pydantic import Field, computed_field, field_validator
from pydantic.networks import AnyUrl
from pymongo import MongoClient
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Row, Table
from rich.text import Text
from rich.traceback import install as tr_install

# import torch
from torch import Tensor
from transformers import AutoTokenizer  # type: ignore
from transformers import (
    AutoModel,
    PreTrainedModel,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
)

from supergene.v0_0_2 import Version0_0_2


# global console
def get_console() -> Console:
    """Get the console."""
    console = Console()
    tr_install(console=console)
    return console


console = Console()

# global progress
global progress
progress = Progress(
    TextColumn("[progress.description]{task.description}[/]", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    MofNCompleteColumn(),
    "•",
    TimeElapsedColumn(),
    TimeRemainingColumn(),
    console=get_console(),
)

model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast = (
    AutoTokenizer.from_pretrained(model_name)
)
model: PreTrainedModel = AutoModel.from_pretrained(model_name)


def connect() -> None:
    """Connect to the MongoDB database."""
    uri = getenv("SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri")
    client: MongoClient = MongoClient(uri)
    docs: List[Any] = [Version0_0_2, Version0_0_3]
    init_bunnet(
        database=client.supergene,
        document_models=docs,
    )


def get_embeddings(text: str) -> List[float]:
    """Generate the embeddings for the chapter."""

    def tensor_to_list(tensor: Tensor) -> List[float]:
        """Convert a tensor to a list."""
        return tensor.cpu().detach().numpy().tolist()

    # Tokenize the text
    inputs = tokenizer(
        text, padding=True, truncation=True, max_length=512, return_tensors="pt"
    )

    # Generate embeddings
    with torch.no_grad():
        outputs = model(**inputs)

    # Extract embeddings
    embeddings: Tensor = outputs.last_hidden_state.mean(
        dim=1
    )  # You can experiment with pooling strategies
    embeddings_list: List[float] = tensor_to_list(embeddings)
    return embeddings_list


def get_section(chapter: int) -> int:
    """Get the section number of the chapter.

    Args:
        chapter (int): The number of the chapter.

    Returns:
        int: The section number of the chapter.
    """
    match chapter:
        case _ if chapter < 425:
            return 1
        case _ if 425 <= chapter < 883:
            return 2
        case _ if 883 <= chapter < 1339:
            return 3
        case _ if 1339 <= chapter < 1679:
            return 4
        case _ if 1679 <= chapter < 1712:
            return 5
        case _ if 1712 <= chapter < 1821:
            return 6
        case _ if 1821 <= chapter < 1961:
            return 7
        case _ if 1961 <= chapter < 2166:
            return 8
        case _ if 2166 <= chapter < 2205:
            return 9
        case _ if 2205 <= chapter < 2300:
            return 10
        case _ if 2300 <= chapter < 2444:
            return 11
        case _ if 2444 <= chapter < 2640:
            return 12
        case _ if 2444 <= chapter < 2766:
            return 13
        case _ if 2766 <= chapter < 2892:
            return 14
        case _ if 2892 <= chapter < 3034:
            return 15
        case _ if 3034 <= chapter < 3304:
            return 16
        case _ if 3304 <= chapter <= 3462:
            return 17
        case _:
            raise ValueError(f"Chapter {chapter} does not have a section.")


def get_book(chapter: int) -> int:
    """Get the book number of the chapter."""
    section = Version0_0_3.get_section(chapter)
    match section:
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
            raise ValueError(f"Section {section} does not have a book.")


class Version0_0_3(Document):
    """Represents a chapter in a document. Version 0.0.2.

    Attributes:
        _id (PydanticObjectId): The unique identifier of the chapter.
        chapter (int): The number of the chapter.
        order (int): The order of the chapter.
        title (str): The title of the chapter.
        created (datetime): The date and time the chapter was created.
        modified (datetime): The date and time the chapter was last modified.
        url (Optional[AnyUrl]): The url of the chapter.
        text (str): The text of the chapter.
        trimmed_text (str): The trimmed text of the chapter.
        version (str): The version of the document.
        filename (str): The filename of the chapter with file extension.
        filepath (str): The complete path to the file.
        tags (List[str]): A list of tags for the chapter.
        section (int): The section number of the chapter.
        book (int): The book number of the chapter."""

    _id = PydanticObjectId()
    chapter: int = Field(
        title="Chapter",
        ge=1,
        lt=3465,
        description="The number of the chapter",
    )
    order: int = Field(title="Order", ge=0, le=3462)
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
    trimmed_text: str = Field(
        ..., title="Trimmed Text", description="The trimmed text of the chapter."
    )
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

    class Settings:
        name = "v0.0.3"

    def __eq__(self, other: Any) -> bool:
        """Check if two chapters are equal."""
        if not isinstance(other, Version0_0_2):
            return False
        elif self.chapter != other.chapter:
            return False
        return self.text == other.text

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
            case _ if 2444 <= self.chapter < 2766:
                return 13
            case _ if 2766 <= self.chapter < 2892:
                return 14
            case _ if 2892 <= self.chapter < 3034:
                return 15
            case _ if 3034 <= self.chapter < 3304:
                return 16
            case _ if 3304 <= self.chapter <= 3462:
                return 17
            case _:
                raise ValueError(f"Chapter {self.chapter} does not have a section.")

    @staticmethod
    def get_section(chapter: int) -> int:
        """Get the section number of the chapter."""
        match chapter:
            case _ if chapter < 425:
                return 1
            case _ if 425 <= chapter < 883:
                return 2
            case _ if 883 <= chapter < 1339:
                return 3
            case _ if 1339 <= chapter < 1679:
                return 4
            case _ if 1679 <= chapter < 1712:
                return 5
            case _ if 1712 <= chapter < 1821:
                return 6
            case _ if 1821 <= chapter < 1961:
                return 7
            case _ if 1961 <= chapter < 2166:
                return 8
            case _ if 2166 <= chapter < 2205:
                return 9
            case _ if 2205 <= chapter < 2300:
                return 10
            case _ if 2300 <= chapter < 2444:
                return 11
            case _ if 2444 <= chapter < 2640:
                return 12
            case _ if 2444 <= chapter < 2766:
                return 13
            case _ if 2766 <= chapter < 2892:
                return 14
            case _ if 2892 <= chapter < 3034:
                return 15
            case _ if 3034 <= chapter < 3304:
                return 16
            case _ if 3304 <= chapter <= 3462:
                return 17
            case _:
                raise ValueError(f"Chapter {chapter} does not have a section.")

    @staticmethod
    def get_book(chapter: int) -> int:
        """Get the book number of the chapter."""
        section = Version0_0_3.get_section(chapter)
        match section:
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
                raise ValueError(f"Section {section} does not have a book.")

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
    def version_major(self) -> int:
        """Get the major version of the document."""
        return int(self.version.split(".")[0])

    @property
    @computed_field
    def version_minor(self) -> int:
        """Get the minor version of the document."""
        return int(self.version.split(".")[1])

    @property
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

    def get_embeddings(self, text: str) -> List[float]:
        """Generate the embeddings for the chapter."""

        def tensor_to_list(tensor: Tensor) -> List[float]:
            """Convert a tensor to a list."""
            return tensor.cpu().detach().numpy().tolist()

        # Tokenize the text
        inputs = tokenizer(
            text, padding=True, truncation=True, max_length=512, return_tensors="pt"
        )

        # Generate embeddings
        with torch.no_grad():
            outputs = model(**inputs)

        # Extract embeddings
        embeddings: Tensor = outputs.last_hidden_state.mean(
            dim=1
        )  # You can experiment with pooling strategies
        embeddings_list: List[float] = tensor_to_list(embeddings)
        return embeddings_list

    @property
    @computed_field
    def embeddings(self) -> List[float]:
        """Generate the embeddings for the chapter."""
        return self.get_embeddings(self.text)

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

    @classmethod
    def create_v0_0_3(cls, version: Version0_0_2) -> "Version0_0_3":
        """Create a new chapter."""
        console = get_console()
        tr_install(console=console)

        # section = get_section(version.chapter)
        # book = get_book(section)
        # console.log(f"Chapter {version.chapter} - Section {section} | Book {book}")
        return cls(
            chapter=version.chapter,
            order=version.chapter,
            title=version.title,
            created=version.created,
            url=version.url,
            text=version.text,
            trimmed_text=version.trimmed_text,
            version="0.0.3",
            filename=version.filename,
            filepath=version.filepath,
            tags=version.tags,
        )

    @classmethod
    def init_collection(cls) -> None:
        """Initialize the collection."""

        connect()
        console = get_console()
        console.log("Connected to Supergene Database.")

        total_items = Version0_0_2.count()
        v2 = Version0_0_2.all(sort="chapter").to_list()
        with progress:
            init_v3 = progress.add_task("Initializing Collection...", total=total_items)
            console = progress.console

            for _, chapter in enumerate(v2, 1):
                progress.update(
                    init_v3,
                    advance=0.2,
                    description=f"Chapter {chapter.chapter}...",
                )
                # progress.console.log("Creating...")
                new_chapter = cls.create_v0_0_3(chapter)
                Version0_0_3.insert(new_chapter)
                # progress.console.log(
                #     f"Created Chapter {new_chapter.chapter}..."
                # )
                progress.update(
                    init_v3,
                    advance=0.8,
                    description=f"Finished Chapter {chapter.chapter}.",
                )


if __name__ == "__main__":

    doc = Version0_0_3.find_one(Version0_0_3.chapter == 1).run()
    if not doc:
        raise ValueError(f"Chapter {1} not found in the database.")
    text = doc.text
    embeddings = get_embeddings(text)
    connect()
    console = get_console()
    console.log("Connected to Supergene Database.")

    data: Columns = Columns(
        [
            Panel(
                Text(str(embedding), style="bold #00afff", justify="center"),
                expand=False,
            )
            for embedding in embeddings
        ],
        equal=True,
    )
    console.print(data, justify="center")
