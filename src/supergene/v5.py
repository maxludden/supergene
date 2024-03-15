"""V4: Update the section and book"""

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

from supergene.v3 import V3
from supergene.v4 import V4
from supergene.connect import Database



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
        name = "v5"
