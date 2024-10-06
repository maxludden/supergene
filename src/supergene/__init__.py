from typing import Optional, List, Any
from dotenv import load_dotenv
from os import getenv, environ

from loguru import logger
from loguru._logger import Logger
import loguru
from rich.console import Console, JustifyMethod, OverflowMethod
from rich.progress import Progress, TextColumn, MofNCompleteColumn,BarColumn, TimeElapsedColumn, TimeRemainingColumn, TaskID
from rich.traceback import install as tr_install
from rich.prompt import IntPrompt
from rich.style import Style
from rich.panel import Panel
from pydantic import BaseModel, computed_field
from rich_gradient import Gradient

load_dotenv()
format = getenv("LOG_FORMAT", "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.configure(
    handlers=[
        {
            "sink": "logs/trace.log",
            "level": "TRACE",
            "format": format,
            "colorize": False,
        }
    ]
)



class Settings(BaseModel):
    """Settings class to store global variables."""
    uri: str = getenv("MONGO_URI", "op://Dev/Mongo/Database/uri")
    db: str = getenv("DATABASE_NAME", "op://Dev/Mongo/Database/name")
    collection: str = getenv("COLLECTION_NAME", "op://Dev/Mongo/Database/collection")

    @computed_field
    def last(self) -> int:
        last = int(getenv("LAST", "0"))

        if last and last != 0:
            return last
        else:
            last = int(getenv("LAST") or IntPrompt.ask("Enter the last chapter number:"))
            environ["LAST"] = str(last)
            return last


class Log:
    def __init__(
        self,
        console: Optional[Console] = None,
        progress: Optional[Progress] = None,
        settings: Optional[Settings] = None) -> None:
        """Generate a logger object that can be passed around globally to other classes and modules.

        Args:
            console(Console, optional): Rich Console object. Defaults to None.
            progress (Optional[Progress]): Rich Progress object. Defaults to None.
            logger (Logger): Loguru logger object. Defaults to logger.
            settings (Settings, optional): Settings object. Defaults to Settings().
        """
        self.console = console or self.get_console()
        self.progress = progress or self.get_progress()
        self.settings: Settings = settings or Settings()
        self.trace("Log object initialized.")


    def get_console(self) -> Console:
        """Generate a Rich Console object."""
        self.trace("Entering Log.get_console()...")
        console = Console()
        tr_install(console=console)
        self.trace("Exiting Log.get_console() -> Console")
        return console


    def get_progress(
        self,
        progress: Optional[Progress] = None,
        console: Optional[Console] = None) -> Progress:
        """Generate a Rich Progress object.

        Args:
            progress (Optional[Progress], optional): Progress object. Defaults to None.
            console (Optional[Console], optional): Console object. Defaults to None.
        """
        self.trace("Entering Log.get_project()...")
        if not progress:
            progress = Progress(
                TextColumn("[bold blue]{task.fields[name]}", justify="right"),
                MofNCompleteColumn(),
                BarColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console or self.get_console()
            )
        self.trace("Exiting Log.get_project() -> Project")
        return progress

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message at the specified level.

        Args:
            message (str): Message to log.
            level (str, optional): Log level. Defaults to "INFO".
        """
        logger.log(level, message)

    def trace(self, message: str) -> None:
        """Log a message with the log level trace.

        Args:
            message (str): Message to log.
        """
        logger.trace(message)

    def debug(self, message: str) -> None:
        """Log a message with the log level debug.

        Args:
            message (str): Message to log.
        """
        logger.debug(message)

    def info(self, message: str) -> None:
        """Log a message with the log level info.

        Args:
            message (str): Message to log.
        """
        logger.info(message)

    def success(self, message: str) -> None:
        """Log a message with the log level success.

        Args:
            message (str): Message to log.
        """
        logger.success(message)

    def warning(self, message: str) -> None:
        """Log a message with the log level warning.

        Args:
            message (str): Message to log.
        """
        logger.warning(message)

    def error(self, message: str) -> None:
        """Log a message with the log level error.

        Args:
            message (str): Message to log.
        """
        logger.error(message)

    def critical(self, message: str) -> None:
        """Log a message with the log level critical.

        Args:
            message (str): Message to log.
        """
        logger.critical(message)

    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: str | Style | None = None,
        justify: JustifyMethod | None = None,
        overflow: OverflowMethod | None = None,
        no_wrap: bool | None = None,
        emoji: bool | None = None,
        markup: bool | None = None,
        highlight: bool | None = None,
        width: int | None = None,
        height: int | None = None,
        crop: bool = True,
        soft_wrap: bool | None = None,
        new_line_start: bool = False) -> None:
        """Print a message to the console.

        Args:
            *objects (Any): Objects to print.
            sep (str, optional): Separator. Defaults to " ".
            end (str, optional): End. Defaults to "\n".
            style (str | Style | None, optional): Style. Defaults to None.
            justify (JustifyMethod | None, optional): Justify. Defaults to None.
            overflow (OverflowMethod | None, optional): Overflow. Defaults to None.
            no_wrap (bool | None, optional): No wrap. Defaults to None.
            emoji (bool | None, optional): Emoji. Defaults to None.
            markup (bool | None, optional): Markup. Defaults to None.
            highlight (bool | None, optional): Highlight. Defaults to None.
            width (int | None, optional): Width. Defaults to None.
            height (int | None, optional): Height. Defaults to None.
            crop (bool, optional): Crop. Defaults to True.
            soft_wrap (bool | None, optional): Soft wrap. Defaults to None.
            new_line_start (bool, optional): New line start. Defaults to False.
        """
        self.trace(f"Printing: {objects}")
        self.console.print(
            *objects,
            sep=sep,
            end=end,
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            emoji=emoji,
            markup=markup,
            highlight=highlight,
            width=width,
            height=height,
            crop=crop,
            soft_wrap=soft_wrap,
            new_line_start=new_line_start
        )

if __name__=="__main__":
    log = Log()
    log.trace("Log object initialized.")
    log.info("Log object initialized.")
    log.success("Log object initialized.")
    log.warning("Log object initialized.")
    log.error("Log object initialized.")
    log.critical("Log object initialized.")
    log.print(
        Panel(
            Gradient(
                "Log ready... ✅",
                colors=[
                    "#00ff00",
                    "#55ff55",
                    "#88ff88"
                ]
            ),
            expand = False,
            border_style = "bold green",
            title = Gradient("Log"),
        ),
        justify = "center"
    )
