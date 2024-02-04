from os import getenv
from typing import List, Optional

from bunnet import init_bunnet
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.database import Database
from rich.panel import Panel
from rich.text import Text, TextType
from maxgradient import Gradient, GradientRule

from supergene.console import Console, Progress, get_console, get_progress

load_dotenv()

class Client:
    """The MongoDB client.
    
    Attributes:
        uri (str): the connection string to the MongoDB database.
        client (MongoClient): the MongoDB client.
        db (Database): the MongoDB database.
    
    Classmethods:
        __init__(cls, document_models: Optional[List[Document]] = None, database: str = "superene")

    """
    docs: List[str] = ["chapter", "unparsed"]

    def __init__(self, document_models: Optional[List[str]] = docs, database: str = "superene") -> None:
        """Initialize the client."""
        
        global console, progress
        console: Console = get_console()
        progress: Progress = get_progress(console)
        with progress:
            print = progress.console.print
            print("[i dim]Generating MongoDB Connection String...[/]")
            uri = getenv("SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri")
            self.uri = f"{uri}/{database}"
            progress_taskid = progress.add_task("Connecting to MongoDB...", total=2)
            progress.update(progress_taskid, advance=1)

            try:
                
                init_bunnet(
                    database= self.database,
                    connection_string = self.uri,
                    document_models=document_models or ["chapter", "unparsed"]
                )
                console.line(2)
                console.print(self._success_panel(), justify="center")
                console.line(2)
            except ConnectionFailure as cf:
                progress.console,print()
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

    def _success_panel(self) -> Panel:
        """Rich.panel.Panel containing a success message for connecting to with the database."""
        
        gradient = Gradient(
                "Super Gene",
                colors = ["#008f00", "#00ff00", "#8fff0f", "#cfffcf"]
        )
        return Panel(
            Text(
                "Connected to MongoDB: `mongo.supergene`",
                style="b #cfcfcf",
                justify='center'
            ),
            title = gradient,
            border_style="bold #3f5f3f",
            width = 60,
            expand = False
        )
        
# def database(client: MongoClient, db: str="supergene") -> Database:
#     """Get the database from the client."""
#     return client[db]

# def init(self, document_models: Optional[List[Document]] = None), connection_string: str):
#     """Initialize bunnet."""
#     init_bunnet(connection_string=self.uri, document_models=document_models)  # type: ignore

