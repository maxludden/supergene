"""V4: Update the section and book"""
# ruff: noqa: F401
import re
from datetime import datetime
from enum import IntEnum
from functools import singledispatch, singledispatchmethod
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from typing import Any, List, Optional, Tuple, Generator

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
from rich.console import Console, ConsoleOptions, RenderResult
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
from snoop import snoop # type: ignore
from cheap_repr import register_repr, normal_repr # type: ignore
from supergene.v3 import V3

# import torch
from torch import Tensor
from transformers import AutoTokenizer  # type: ignore
from transformers import (
    AutoModel,
    PreTrainedModel,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
)

# global console
def get_console() -> Console:
    """Get the console."""
    console = Console()
    tr_install(console=console)
    return console

def get_progress(console: Console = get_console()) -> Progress:
    """Get the progress."""
    return Progress(
        TextColumn("[progress.description]{task.description}[/]", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        MofNCompleteColumn(),
        "•",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

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

def get_section(chapter: int) -> int:
    """Get the section number of the chapter.
    
    Args:
        chapter (int): The number of the chapter.

    Returns:
        int: The section number of the chapter.
    """
    if chapter < 425:
        return 1
    elif 425 <= chapter < 883:
        return 2
    elif 883 <= chapter < 1339:
        return 3
    elif 1339 <= chapter < 1679:
        return 4
    elif 1679 <= chapter < 1712:
        return 5
    elif 1712 <= chapter < 1821:
        return 6
    elif 1821 <= chapter < 1961:
        return 7
    elif 1961 <= chapter < 2166:
        return 8
    elif 2166 <= chapter < 2205:
        return 9
    elif 2205 <= chapter < 2300:
        return 10
    elif 2300 <= chapter < 2444:
        return 11
    elif 2444 <= chapter < 2640:
        return 12
    elif 2444 <= chapter < 2766:
        return 13
    elif 2766 <= chapter < 2892:
        return 14
    elif 2892 <= chapter < 3034:
        return 15
    elif 3034 <= chapter < 3304:
        return 16
    elif 3304 <= chapter <= 3462:
        return 17
    else:
        raise ValueError(f"Chapter {chapter} does not have a section.")


def get_book(chapter: int) -> int:
    """Get the book number of the chapter.
    
    Args:
        chapter (int): The number of the chapter.

    Returns:
        int: The book number of the chapter.
    """
    section = V3.get_section(chapter)
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


def connect() -> None:
    """Connect to the MongoDB database."""
    uri = getenv("SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri")
    client: MongoClient = MongoClient(uri)
    docs: List[Any] = [V3]
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


class V4(Document):
    """Represents a chapter in a document. Version 0.0.2.

    Attributes:
        id (PydanticObjectId): The unique identifier of the chapter.
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
        
    """
    chapter: int = Field(..., title="Chapter", description="The number of the chapter.")
    section: int = Field(..., title="Section", description="The section number of the chapter." ,ge=1, le=17)
    book: int = Field(..., title="Book", description="The book number of the chapter.")
    order: int = Field(..., title="Order", description="The order of the chapter.")
    title: str = Field(..., title="Title", description="The title of the chapter.")
    created: datetime = Field(..., title="Created", description="The date and time the chapter was created.")
    modified: datetime = Field(default_factory=datetime.now, title="Modified", description="The date and time the chapter was modified.")
    url: Optional[AnyUrl] = None
    text: str = Field(..., title="Text", description="The text of the chapter")
    trimmed_text: str = Field(
        ...,
        title="Trimmed Text",
        description="The trimmed text of the chapter."
    )
    version: int = Field(default=3, title="Version", description="The version of the document.", ge=1)
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
        name = "v4"

    @classmethod
    @snoop
    def update(cls, v3: V3) -> None:
        chapter: int = v3.chapter
        section: int = V3.get_section(chapter)
        book: int = V3.get_book(chapter)
        order: int = v3.order
        title: str = v3.title
        created: datetime = v3.created
        modified: datetime = v3.modified
        url: Optional[AnyUrl] = v3.url
        text: str = v3.text
        trimmed_text: str = v3.trimmed_text
        version: int = 4
        filename: str = v3.filename
        filepath: str = v3.filepath
        tags: List[str] = v3.tags
        new_v4 = V4(
            chapter=chapter,
            section=section,
            book=book,
            order=order,
            title=title,
            created=created,
            modified=modified,
            url=url,
            text=text,
            trimmed_text=trimmed_text,
            version=version,
            filename=filename,
            filepath=filepath,
            tags=tags,
        )
        V4.insert(new_v4) # type: ignore

    @classmethod
    def main(cls) -> None:
        with progress:
            chapter_task = progress.add_task("Processing chapters...", total=3462)
            for chapter in range(1, 3463):
                v3: Optional[V3] = V3.find_one(V3.chapter==chapter).run()
                if v3:
                    V4.update(v3)
                progress.update(chapter_task, advance=1)

    @classmethod
    def connect(cls) -> None:
        """Connect to the MongoDB database."""
        uri = getenv("SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri")
        client: MongoClient = MongoClient(uri)
        docs: List[Any] = [V3, V4]
        init_bunnet(
            database=client.supergene,
            document_models=docs,
        )

register_repr(V4)(normal_repr)

if __name__ == '__main__':
    V4.connect()
    V4.main()
    print("Done")
