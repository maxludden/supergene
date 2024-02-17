# ruff: noqa: F401
from rich.console import Console
from rich.progress import Progress

from supergene.chapter import Chapter
from supergene.mongo import Mongo
from supergene.console import get_console, get_progress_columns, make_layout
from supergene.unparsed import Unparsed

global console
console: Console = get_console()
