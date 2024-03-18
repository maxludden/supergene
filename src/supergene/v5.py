"""V5: voice of the world"""

# ruff: noqa: F401
import re
from datetime import datetime
from enum import IntEnum
from functools import singledispatch, singledispatchmethod
from multiprocessing import cpu_count
from os import getenv
from pathlib import Path
from typing import Any, Generator, List, Optional, Tuple

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
from cheap_repr import normal_repr, register_repr  # type: ignore
from loguru import logger
from maxgradient import Color, Gradient, GradientRule
from pydantic import Field, computed_field, field_validator
from pydantic.networks import AnyUrl
from pymongo import MongoClient
from rich.columns import Columns
from rich.console import Console, ConsoleOptions, Group, RenderResult, NewLine
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
from rich.table import Column, Row, Table
from rich.text import Text
from rich.traceback import install as tr_install
from snoop import snoop  # type: ignore

# import torch
from torch import Tensor
from transformers import AutoTokenizer  # type: ignore
from transformers import (
    AutoModel,
    PreTrainedModel,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
)

from supergene.connect import MongoDB
from supergene.v3 import V3
from supergene.v4 import V4

model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast = (
    AutoTokenizer.from_pretrained(model_name)
)
model: PreTrainedModel = AutoModel.from_pretrained(model_name)
# logger.add(
#     "logs/v5.log",
#     level="DEBUG",
#     colorize=True,
#     backtrace=True,
#     diagnose=True,
#     catch=True,
# )


class V5(Document):
    """Represents a chapter in a document. Version 4.

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
    section: int = Field(
        ...,
        title="Section",
        description="The section number of the chapter.",
        ge=1,
        le=17,
    )
    book: int = Field(..., title="Book", description="The book number of the chapter.")
    order: int = Field(..., title="Order", description="The order of the chapter.")
    title: str = Field(..., title="Title", description="The title of the chapter.")
    created: datetime = Field(
        ..., title="Created", description="The date and time the chapter was created."
    )
    modified: datetime = Field(
        default_factory=datetime.now,
        title="Modified",
        description="The date and time the chapter was modified.",
    )
    url: Optional[AnyUrl] = None
    text: str = Field(..., title="Text", description="The text of the chapter")
    trimmed_text: str = Field(
        ..., title="Trimmed Text", description="The trimmed text of the chapter."
    )
    version: int = Field(
        default=3, title="Version", description="The version of the document.", ge=1
    )
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
        name = "v5"

    def gen_embeddings(self) -> List[float]:
        """Generate the embeddings for the chapter."""

        def tensor_to_list(tensor: Tensor) -> List[float]:
            """Convert a tensor to a list."""
            return tensor.cpu().detach().numpy().tolist()

        # Tokenize the text
        inputs = tokenizer(
            self.text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
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

    def __rich__(self) -> Layout:
        """Render the document to the console."""

        layout = Layout(name="root")
        layout.split_row(
            Layout(" ", name="left", ratio=1),
            Layout(" ", name="main", ratio=6),
            Layout(" ", name="right", ratio=1),
        )

        rule = GradientRule(title=f"Chapter {self.chapter} | {self.title}")

        meta_table1 = Table(
            show_header=True, show_edge=True, expand=True, pad_edge=False
        )
        meta_table1.add_column(
            "[i b #dddddd]Chapter[/]", justify="center", style="bold #00afff"
        )
        meta_table1.add_column(
            "[i b #dddddd]Section[/]", justify="center", style="bold #00ffa0"
        )
        meta_table1.add_column(
            "[i b #dddddd]Book[/]", justify="center", style="bold #ffafff"
        )
        meta_table1.add_column(
            "[i b #dddddd]Version[/]", justify="center", style="bold #ffffff"
        )
        meta_table1.add_row(
            f"{self.chapter}", f"{self.section}", f"{self.book}", f"{self.version}"
        )

        meta_table2 = Table(
            show_header=False,
            show_edge=True,
            expand=True,
            pad_edge=False,
            row_styles=["on #020202", "on #040404"],
        )
        meta_table2.add_column("Key", justify="right", style="italic #5f00af")
        meta_table2.add_column("Value", justify="left", style="bold #AFFF00")
        meta_table2.add_row("Created", f"{self.created.isoformat()}")
        meta_table2.add_row("Modified", f"{self.modified.isoformat()}")
        meta_table2.add_row("Filepath", f"{self.filepath}")

        text = f"## {self.title}\n\n### Chapter {self.chapter}\n\n{self.text}"
        markdown = Markdown(text, style="#afff00")

        layout["main"].update(
            Group(
                NewLine(2),
                meta_table1,
                meta_table2,
                NewLine(2),
                Panel(
                    Group(
                        rule,
                        markdown
                    ),
                    expand=True
                )
            )
        )

        return layout

    @classmethod
    def test(cls) -> None:
        db = MongoDB([V3, V4, V5])  # type: ignore
        db.connect()  # type: ignore
        chapter_44 = V4.find_one(V4.chapter == 44).run()
        if not chapter_44:
            raise ValueError("Chapter 44 not found")
        db.console.print(V5(**chapter_44.model_dump()), justify="center")


if __name__ == "__main__":
    V5.test()
