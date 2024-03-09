from os import getenv
from typing import Any, List, Optional

from bunnet import init_bunnet
from dotenv import load_dotenv
from maxgradient import Color, Gradient
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from rich.panel import Panel
from rich.text import Text

from v3._chapter import Chapter, Chapter_v4, V3Chapter, V4Chapter
from v3.chapter import Chapter as _Chapter
from v3.console import Console, get_console
from v3.unparsed import Unparsed

load_dotenv()
console: Console = get_console()


class Mongo:
    """The MongoDB client.

    Attributes:
        uri (str): the connection string to the MongoDB database.
        client (MongoClient): the MongoDB client.
        db (Database): the MongoDB database.

    Classmethods:
        __init__(cls, document_models: Optional[List[Document]] = None, database: str = "superene")

    Methods:
        connect(self): Connect to the MongoDB database.
    """

    connected: bool = False
    docs: List[Any] = [Chapter, Unparsed, V3Chapter, V4Chapter, Chapter_v4, _Chapter]

    def __init__(
        self,
        *,
        database: str = "supergene",
        document_models: Optional[List[Any]] = docs,
        console: Console = get_console(),
    ) -> None:
        """Initialize the client."""
        uri = getenv(
            "SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri"
        )
        self.uri = f"{uri}"
        self.models: List[str] = document_models or self.docs
        self.console = console

    def _connect(self):
        """Connect to the MongoDB database."""
        try:
            init_bunnet(database=self.client.supergene, document_models=self.models)  # type: ignore
        except ConnectionFailure as cf:
            console.print(cf)
        else:
            if not self.connected:
                console.print(self._success_panel(), justify="center")
                self.connected = True

    @property
    def uri(self) -> str:
        """Get the connection URI."""
        return self._uri

    @uri.setter
    def uri(self, uri: str) -> None:
        """Set the connection URI."""
        self._uri = uri

    @property
    def client(self) -> MongoClient:
        """Get the client."""
        return MongoClient(self.uri)

    @property
    def database(self) -> Database:
        """Get the database from the client."""
        return self.client.supergene

    @staticmethod
    def _success_panel() -> Panel:
        """Rich.panel.Panel containing a success message for connecting to with the database."""
        colors = [
            Color("#008f00"),
            Color("#00ff00"),
            Color("#8fff0f"),
            Color("#cfffcf"),
        ]
        title_gradient = Gradient("Bunnet ODM", colors=colors, style="bold")  # type: ignore
        message: Text = Text.assemble(
            Gradient("Connected to MongoDB:\n\n", colors=colors, style="italic").as_text(),  # type: ignore
            Gradient(
                "supergene",
                colors=[
                    Color("#8fff8f"),
                    Color("#a0ffa0"),
                    Color("#afffaf"),
                    Color("#cfffcf"),
                ],
                style="bold",
            ).as_text(),  # type: ignore
            justify="center",
        )
        console.line(2)
        return Panel(
            message,
            title=title_gradient,
            border_style="bold #3f5f3f",
            width=60,
            expand=False,
            padding=(1, 4),
        )
