# ruff: noqa: F401
from supergene.chapter import Chapter
from supergene.client import Client
from supergene.console import get_console, make_layout, get_progress
from supergene.unparsed import Unparsed

from rich.console import Console
from rich.progress import Progress

global console
console: Console = get_console()


