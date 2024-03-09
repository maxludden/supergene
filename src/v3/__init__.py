# ruff: noqa: F401
from rich.console import Console
from rich.progress import Progress

from v3.chapter import Chapter
from v3.mongo import Mongo
from v3.console import get_console, get_progress_columns, make_layout
from v3.unparsed import Unparsed

global console
console: Console = get_console()
