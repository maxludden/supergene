from os import getenv
from typing import List, Optional, Any

from bunnet import init_bunnet
from dotenv import load_dotenv
from maxgradient import Gradient, Color
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from rich.panel import Panel
from rich.markdown import Markdown


from supergene.chapter import Chapter, V3Chapter
from supergene.unparsed import Unparsed
from supergene.console import Console, get_console

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

    """

    docs: List[Any] = [Chapter, Unparsed, V3Chapter]

    def __init__(
        self,
        *,
        database: str = "supergene",
        document_models: Optional[List[Any]] = docs,
    ) -> None:
        """Initialize the client."""
        uri = getenv(
            "SUPERGENE", "op://Personal/ixzlwkey4nyc2w54fathyi4ilq/Database/uri"
        )
        self.uri = f"{uri}"
        self.models: List[str] = document_models or self.docs

    def connect(self):
        """Connect to the MongoDB database."""
        try:
            init_bunnet(database=self.client.supergene, document_models=self.models) # type: ignore
        except ConnectionFailure as cf:
            console.print(cf)
        else:
            console.print(self._success_panel(), justify="center")

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
        colors= [Color("#008f00"), Color("#00ff00"), Color("#8fff0f"), Color("#cfffcf")]
        gradient = Gradient(
            "Super Gene", colors=colors # type: ignore
        )
        console.line(2)
        return Panel(
            Gradient(
                "Connected to MongoDB: `mongo.supergene`",
                colors=colors, # type: ignore
                style="bold",
                justify="center",
            ),
            title=gradient,
            border_style="bold #3f5f3f",
            width=60,
            expand=False,
        )


# def database(client: MongoClient, db: str="supergene") -> Database:
#     """Get the database from the client."""
#     return client[db]

# def init(self, document_models: Optional[List[Document]] = None), connection_string: str):
#     """Initialize bunnet."""
#     init_bunnet(connection_string=self.uri, document_models=document_models)  # type: ignore


if __name__ == "__main__":  # pragma: no cover
    console = get_console()
    mongo = Mongo()
    mongo.connect()
    ch1 = Unparsed.find_one(Unparsed.chapter == 1).run()
    if ch1:
        console.print(Markdown(ch1.text))
