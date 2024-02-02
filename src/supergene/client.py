from os import getenv
from sys import argv
from typing import List

from bunnet import init_bunnet
from dotenv import load_dotenv
from pymongo import MongoClient
from rich.markdown import Markdown
from rich.pager import SystemPager
from rich.prompt import IntPrompt

from supergene.chapter import Chapter
from supergene.console import get_console
from supergene.unparsed import Unparsed


class Client:

    def __init__(
        self, *, db: str = "supergene", document_models: List = [Unparsed, Chapter]
    ) -> None:
        if db:
            self.db: str = str(db)
        else:
            self.db = "supergene"

        self.document_models = document_models

    @property
    def uri(self) -> str:
        """Get the connection string for the database"""
        load_dotenv()
        uri = getenv("SUPERGENE", "op://Personal/Mongo/connection uri")
        return uri

    @property
    def connection_string(self) -> str:
        """Get the connection string for the database"""
        return f"{self.uri}/{self.db}"

    @property
    def client(self) -> MongoClient:
        """Get the connection string for the database"""
        return MongoClient(self.connection_string)

    def init(self):
        """Initialize bunnet."""
        init_bunnet(connection_string=self.uri, document_models=[Unparsed, Chapter])  # type: ignore


if __name__ == "__main__":  # pragma: no cover
    console = get_console()
    pager = SystemPager()
    mongo = Client()
    mongo.init()

    if argv[1]:
        chapter = int(argv[1])
    else:
        chapter = IntPrompt.ask("Which chapter?", default=1)

    doc = Chapter.find_one(chapter=chapter).run()  # type: ignore

    if doc:
        with console.pager(styles=True):
            console.print(Markdown(doc.text))
