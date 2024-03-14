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
from bunnet.odm.operators.update.general import Set
from cheap_repr import normal_repr, register_repr  # type: ignore
from loguru import logger
from maxgradient import Color, Gradient
from pydantic import Field, computed_field, field_validator
from pydantic.networks import AnyUrl
from pymongo import MongoClient
from rich import get_console
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
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

from supergene.v0_0_2 import Version0_0_2
from supergene.v3 import V3

logger.add(
    sink="logs/embeddings_debug.log",
    level="DEBUG",
    colorize=False,
    backtrace=True,
    diagnose=True,
    catch=True,
)
logger.add(
    sink="logs/embeddings_info.log",
    level="INFO",
    colorize=False,
    backtrace=True,
    diagnose=True,
    catch=True,
)


def connect() -> None:
    uri = getenv("SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri")
    client: MongoClient = MongoClient(uri)
    docs: List[Any] = [Version0_0_2, V3, Embeddings]
    init_bunnet(
        database=client.supergene,
        document_models=docs,
    )


model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer: PreTrainedTokenizer | PreTrainedTokenizerFast = (
    AutoTokenizer.from_pretrained(model_name)
)
model: PreTrainedModel = AutoModel.from_pretrained(model_name)


def tensor_to_list(tensor: Tensor) -> List[float]:
    """Convert a tensor to a list."""
    return tensor.cpu().detach().numpy().tolist()


def get_embeddings(chapter: int) -> List[float]:
    """Generate the embeddings for the chapter."""

    # Retrieve the chapter text
    doc = Version0_0_2.find_one(Version0_0_2.chapter == chapter).run()
    if not doc:
        raise ValueError(f"Chapter {chapter} not found in the database.")
    text = doc.text

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


class Embeddings(Document):
    """The embeddings for the chapters."""

    chapter: int = Field(..., description="The chapter number.")
    embeddings: List[float] = Field(
        default=[], description="The embeddings for the chapter.", title="Embeddings"
    )
    tokens: List[str] = Field(
        default=[],
        description="The tokens corresponding to the embeddings.",
        title="Tokens",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="The date the embeddings were created.",
    )

    class Settings:
        name = "embeddings"

    @staticmethod
    def generate_embeddings(chapter: int) -> Tuple[List[float], List[str]]:
        """Generate the embeddings and tokens for the chapter."""
        doc = V3.find_one(V3.chapter == chapter).run()
        if not doc:
            raise ValueError(f"Chapter {chapter} not found in the database.")
        text = doc.text.lower()

        # Tokenize the text
        inputs = tokenizer(
            text, padding=True, truncation=True, max_length=512, return_tensors="pt"
        )

        # Extract tokens
        tokens: List[str] = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])  # type: ignore

        # Generate embeddings
        with torch.no_grad():
            outputs = model(**inputs)

        # Extract embeddings
        embeddings: Tensor = outputs.last_hidden_state.mean(
            dim=1
        )  # You can experiment with pooling strategies
        embeddings_list: List[float] = tensor_to_list(embeddings)
        return embeddings_list, tokens


register_repr(Embeddings)(normal_repr)
register_repr(V3)(normal_repr)
register_repr(Panel)(normal_repr)
register_repr(Markdown)(normal_repr)
register_repr(Text)(normal_repr)
register_repr(Table)(normal_repr)
register_repr(Gradient)(normal_repr)
register_repr(Columns)(normal_repr)


# @snoop(watch=["chapter", "embeddings", "tokens"])
# # @logger.catch()
def main() -> None:
    from rich.pretty import Pretty

    from supergene.mongo import Mongo
    from supergene.v3 import V3

    mongo = Mongo()
    mongo.connect()
    console = mongo.console

    doc = V3.find_one(V3.chapter == 1).run()
    if not doc:
        raise ValueError("Chapter 1 not found in the database.")
    text = doc.text
    console.print(
        Panel(
            Markdown(text, style="bold #dfdfdf"),
            title=Gradient("Chapter 1", colors=["magenta", "violet", "purple"]),
            expand=False,
        )
    )
    embeddings, tokens = Embeddings.generate_embeddings(1)
    console.log(f"Embeddings Length: {len(embeddings[0])}")
    console.log(f"Tokens Length: {len(tokens)}")
    if len(embeddings) != len(tokens):
        raise ValueError("The embeddings and tokens do not have the same length.")

    table = Table(
        title=Gradient("Super Gene Embeddings", style="bold"),
        show_lines=True,
        expand=False,
    )
    table.add_column("Embedding", style="bold#00afff", justify="right")
    table.add_column("Token", style="bold #CBC192", justify="left")

    for embedding, token in embeddings, tokens:
        if str(embedding).startswith("0"):
            formatted_embedding = f" {embedding}"
        table.add_row(formatted_embedding, str(token))

    console.print(table)


if __name__ == "__main__":
    main()
