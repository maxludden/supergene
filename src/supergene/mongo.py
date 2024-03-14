from os import getenv
from typing import Any, List, Optional

from bunnet import init_bunnet

# from cheap_repr import normal_repr, register_repr  # type: ignore
from dotenv import load_dotenv
from maxgradient import Color, Gradient
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm
from rich.text import Text
from rich.traceback import install as tr_install

# from snoop import snoop  # type: ignore
# from supergene.embeddings import Embeddings
# from supergene.v0_0_1 import Version0_0_1
# from supergene.v0_0_2 import Version0_0_2
from supergene.v3 import V3

load_dotenv()


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
    docs: List[Any] = [V3]

    # @snoop(watch=["self", "uri", "client", "database"])
    def __init__(
        self,
        *,
        database: str = "supergene",
        document_models: Optional[List[Any]] = docs,
        console: Optional[Console] = None,
    ) -> None:
        """Initialize the client."""
        if console is None:
            console = self.console
        uri = getenv(
            "SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri"
        )
        self.uri = f"{uri}"
        self.models: List[str] = document_models or self.docs

    def connect(self):
        """Connect to the MongoDB database."""
        try:
            init_bunnet(database=self.client.supergene, document_models=self.models)  # type: ignore
        except ConnectionFailure as cf:
            self.console.print(cf)
        else:
            if not self.connected:
                self.console.print(self._success_panel(), justify="center")
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

    @property
    def console(self) -> Console:
        """Generate a rich.console.Console."""
        console = Console()
        tr_install(console=console)
        return console

    @property
    def progress(self, console: Optional[Console] = None) -> Progress:  # type: ignore
        """Generate a progress bar."""
        if not console:
            console = self.console
        progress = Progress(
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
        return progress

    @staticmethod
    def _success_panel() -> Panel:
        """Rich.panel.Panel containing a success message for connecting to with the database."""
        mongo = Mongo()
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
        mongo.console.line(2)
        return Panel(
            message,
            title=title_gradient,
            border_style="bold #3f5f3f",
            width=60,
            expand=False,
            padding=(1, 4),
        )

    @classmethod
    def mongo_connect(cls, uri: Optional[str] = None):
        """Connect to the MongoDB database."""
        if uri is None:
            uri = getenv(
                "SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri"
            )
        console = Console()
        try:
            client: MongoClient = MongoClient(uri)
            db = client.supergene
        except ConnectionFailure as cf:
            console.log(cf)
        else:
            console.print(cls._success_panel(), justify="center")
            return db


# register_repr(Mongo)(normal_repr)

if __name__ == "__main__":  # pragma: no cover
    mongo = Mongo()

    print_chapter_1 = Confirm.ask("Print Chapter 1?", console=mongo.console)
    if print_chapter_1:
        ch1 = V3.find_one(V3.chapter == 1).run()
        if ch1:
            mongo.console.print(Panel(Markdown(ch1.text), width=100), justify="center")
        else:
            mongo.console.print("Chapter 1 not found.")
