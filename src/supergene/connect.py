"""Connect to the MongoDB database."""

# ruff: noqa: F401
from os import getenv
from typing import Any, List, Optional

from bunnet import Document, init_bunnet

# from cheap_repr import normal_repr, register_repr  # type: ignore
from dotenv import load_dotenv
from maxgradient import Color, Gradient
from pymongo import MongoClient
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

load_dotenv()


class Database:
    """The MongoDB Client.

    Args:
        documents: The document models to initialize the database with.
        console (Console, optional): The Rich console.
        progress (Progress, optional): The Rich progress bar.
    
    Attributes:
        console (Console): The Rich console.
        progress (Progress): The Rich progress bar.
    
    Methods:
        get_console: Get the Rich console.
        get_progress: Get the Rich progress bar.
        connect: Connect to the MongoDB database.
    """

    def __init__(
        self,
        documents: Optional[List[Document]],
        *,
        console: Optional[Console] = None,
        progress: Optional[Progress] = None,
    ) -> None:
        """Initialize the MongoDB client."""
        self.uri = getenv(
            "SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri"
        )
        self.client: MongoClient = MongoClient(self.uri)
        self.console = console or self.get_console()
        self.progress = progress or self.get_progress(self.console)
        self.documents = documents

    @staticmethod
    def get_console() -> Console:
        """Get the Rich console."""
        console = Console()
        tr_install(console=console)
        return console

    @property
    def console(self) -> Console:
        """Get the Rich console."""
        return self.get_console()

    @console.setter
    def console(self, console: Optional[Console]) -> None:
        """Set the Rich console."""
        if console is None:
            console = Console()
            tr_install(console=console)
        self._console = console

    def get_progress(self, console: Optional[Console] = None) -> Progress:
        """Get the Rich progress bar."""
        if console is None:
            console = self.console
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            MofNCompleteColumn(),
            "•",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        )

    @property
    def progress(self) -> Progress:
        """Get the Rich progress bar."""
        if self._progress is None:
            self._progress: Progress = self.get_progress()
        return self._progress

    @progress.setter
    def progress(
        self, progress: Optional[Progress], console: Optional[Console]
    ) -> None:
        if console is None:
            console = self.console
        if progress is None:
            self._progress = self.get_progress(console)
        else:
            self._progress = progress

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

    def _success_panel(self) -> Panel:
        """Rich.panel.Panel containing a success message for connecting to with the database."""
        self.connect()
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
        self.console.line(2)
        return Panel(
            message,
            title=title_gradient,
            border_style="bold #3f5f3f",
            width=60,
            expand=False,
            padding=(1, 4),
        )
