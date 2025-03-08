"""Rich logger setup and usage."""

from __future__ import annotations

import atexit
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import loguru
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.style import Style
from rich.text import Text
from rich.traceback import install as tr_install
from rich_gradient import Color, Gradient

__all__ = [
    "get_console",
    "get_logger",
    "get_progress",
    "find_cwd",
    "CWD",
    "LOGS_DIR",
    "RUN_FILE",
    "FORMAT",
    "trace_sink",
]

def get_progress(console: Optional[Console] = None) -> Progress:
    """Initialize the progress bar and return it."""
    if console is None:
        console = Console()
    progress = Progress(
        SpinnerColumn(spinner_name="earth"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        MofNCompleteColumn(),
    )
    progress.start()
    return progress


def get_console(
    record: bool = False,
    console: Console = Console()) -> Console:
    """Initialize the console and return it.

    Args:
        console (Console, optional): A Rich console. Defaults to Console().

    Returns:
        Console: A Rich console.
    """
    console.record = record
    tr_install(console=console)

    return console


def find_cwd(
    start_dir: Path = Path(__file__).parent.parent, verbose: bool = False
) -> Path:
    """Find the current working directory.

    Args:
        start_dir (Path, optional): The starting directory. Defaults to Path.cwd().
        verbose (bool, optional): Print the output of the where command. Defaults to False.

    Returns:
        Path: The current working directory.
    """
    cwd: Path = start_dir
    while not (cwd / "pyproject.toml").exists():
        cwd = cwd.parent
        if cwd == Path.home():
            break
    if verbose:
        console = get_console()
        console.line(2)
        console.print(
            Panel(
                f"[i #5f00ff]{cwd.resolve()}",
                title=Gradient(
                    "Current Working Directory",
                    colors=[
                        Color("#ff005f"),
                        Color("#ff00af"),
                        Color("#ff00ff"),
                    ],
                    style="bold",
                ).as_text(),
            )
        )
        console.line(2)
    return cwd


CWD: Path = find_cwd()
LOGS_DIR: Path = CWD / "logs"  # Replace with the actual logs directory
RUN_FILE: Path = LOGS_DIR / "run.txt"
FORMAT: str = (
    "{time:hh:mm:ss.SSS} | {file.name: ^12} | Line {line} | \
{level} ➤ {message}"
)


def trace_sink() -> Dict[str, Any]:
    """Return the trace sink configuration."""
    return {
        "sink": str((LOGS_DIR / "trace.log").resolve()),
        "format": FORMAT,
        "level": "TRACE",
        "backtrace": True,
        "diagnose": True,
        "colorize": False,
        "mode": "w",
    }


def setup() -> int:
    """Setup the logger and return the run count."""
    console = get_console()
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True)
        console.print(f"Created Logs Directory: {LOGS_DIR}")
    if not RUN_FILE.exists():
        with open(RUN_FILE, "w", encoding="utf-8") as f:
            f.write("0")
            console.print("Created Run File, Set to 0")

    with open(RUN_FILE, "r", encoding="utf-8") as f:
        run = int(f.read())
        return run


def read() -> int:
    """Read the run count from the file."""
    console = get_console()
    if not RUN_FILE.exists():
        console.print("[b #ff0000]Run File Not Found[/][i #ff9900], Creating...[/]")
        setup()
    with open(RUN_FILE, "r", encoding="utf-8") as f:
        run = int(f.read())
    return run


def get_logger(
    handlers: List[Dict[str, Any]] = [trace_sink()],
    progress: Optional[Progress]|bool = None
) -> loguru.Logger:
    """
    Initialize the logger with default sinks and return it.

    Parameters:
        handlers (List[Dict[str, Any]], optional): Additional handlers to configure.

    Returns:
        logger: Configured logger instance.
    """
    # Setup run extra key
    run = read() or setup()  # Ensure setup() returns a valid extra dictionary
    log = loguru.logger.bind(sink="rich")
    # Remove existing handlers and configure
    log.remove()
    log.configure(
        handlers=[
            {
                "sink": RichSink(),
                "format": "{message}",
                "level": "DEBUG",
                "backtrace": True,
                "diagnose": True,
                "colorize": False,
            },
            {
                "sink": str(LOGS_DIR / "trace.log"),
                "format": FORMAT,
                "level": "TRACE",
                "backtrace": True,
                "diagnose": True,
                "colorize": False,
                "mode": "w",
                "retention": "30 minutes",
            },
        ],
        extra={"run": run},
    )
    return log


def write(run: int) -> None:
    def retain_last_three_runs() -> None:
        """Retain the last three runs of the trace log."""
        if not LOGS_DIR.exists():
            LOGS_DIR.mkdir(parents=True)
        run_files = sorted(
            LOGS_DIR.glob("trace_*.log"), key=lambda p: int(p.stem.split("_")[1])
        )
        if len(run_files) >= 3:
            for old_run in run_files[:-2]:
                old_run.unlink()

    def write(run: int) -> None:
        """Write the run count to the file and retain the last three runs of the trace log."""
        retain_last_three_runs()
        with open(RUN_FILE, "w", encoding="utf-8") as f:
            f.write(str(run))
        trace_log = LOGS_DIR / "trace.log"
        if trace_log.exists():
            trace_log.rename(LOGS_DIR / f"trace_{run}.log")

    """Write the run count to the file."""
    with open(RUN_FILE, "w", encoding="utf-8") as f:
        f.write(str(run))


def increment() -> int:
    """Increment the run count and write it to the file."""
    log = get_logger()
    log.trace("Incrementing Run Count...")
    run = read()
    run += 1
    write(run)
    return run


class RichSink:
    """A loguru sink that uses the great `rich` library to print log messages.

    Args:
        run (Optional[int], optional): The current run number. If None, it will \
be read from a file. Defaults to None.
        console (Optional[Console]): A Rich console. If None, it will be \
initialized. Defaults to None.
    """

    LEVEL_STYLES: Dict[str, Style] = {
        "TRACE": Style(italic=True),
        "DEBUG": Style(color="#aaaaaa"),
        "INFO": Style(color="#00afff"),
        "SUCCESS": Style(bold=True, color="#00ff00"),
        "WARNING": Style(italic=True, color="#ffaf00"),
        "ERROR": Style(bold=True, color="#ff5000"),
        "CRITICAL": Style(bold=True, color="#ff0000"),
    }

    GRADIENTS: Dict[str, List[Color]] = {
        "TRACE": [Color("#888888"), Color("#aaaaaa"), Color("#cccccc")],
        "DEBUG": [Color("#338888"), Color("#55aaaa"), Color("#77cccc")],
        "INFO": [Color("#008fff"), Color("#00afff"), Color("#00cfff")],
        "SUCCESS": [Color("#00aa00"), Color("#00ff00"), Color("#afff00")],
        "WARNING": [Color("#ffaa00"), Color("#ffcc00"), Color("#ffff00")],
        "ERROR": [Color("#ff0000"), Color("#ff5500"), Color("#ff7700")],
        "CRITICAL": [Color("#ff0000"), Color("#ff005f"), Color("#ff00af")],
    }

    def __init__(
        self, run: Optional[int] = None, console: Optional[Console] = None
    ) -> None:
        if run is None:
            try:
                run = read()
            except FileNotFoundError:
                run = setup()
        self.run = run
        self.console = console or get_console()

    def __call__(self, message) -> None:
        record = message.record
        level = record["level"].name
        colors = self.GRADIENTS[level]
        style = self.LEVEL_STYLES[level]

        # title
        title: Text = Gradient(
            f" {level} | {record['file'].name} | Line {record['line']} ", colors=colors
        ).as_text()
        title.highlight_words("|", style="italic #666666")
        title.stylize(Style(reverse=True))

        # subtitle
        subtitle: Text = Text.assemble(
            Text(f"Run {self.run}"),
            Text(" | "),
            Text(record["time"].strftime("%H:%M:%S.%f")[:-3]),
            Text(record["time"].strftime(" %p")),
        )
        subtitle.highlight_words(":", style="dim #aaaaaa")

        # Message
        message_text: Text = Gradient(record["message"], colors, style="bold")
        # Generate and print log panel with aligned title and subtitle
        log_panel: Panel = Panel(
            message_text,
            title=title,
            title_align="left",  # Left align the title
            subtitle=subtitle,
            subtitle_align="right",  # Right align the subtitle
            border_style=style + Style(bold=True),
            padding=(1, 2),
        )
        self.console.print(log_panel)

    @classmethod
    def rich_sink(cls, message: loguru.Message) -> None:
        """A loguru sink that uses the great `rich` library to print log messages."""
        record: loguru.Record = message.record
        level: loguru.RecordLevel = record["level"]
        level_name: str = level.name
        colors: List[Color] = cls.GRADIENTS[level_name]
        style: Style = cls.LEVEL_STYLES[level_name]

        # title
        title: Text = Gradient(
            f" {level} | {record['file'].name} | Line {record['line']} ", colors=colors
        ).as_text()
        title.highlight_words("|", style="italic #999999")
        title.stylize(Style(reverse=True))

        # subtitle
        run: int = read()
        subtitle: Text = Text.assemble(
            Text(f"Run {run}"),
            Text(" | "),
            Text(record["time"].strftime("%H:%M:%S.%f")[:-3]),
            Text(record["time"].strftime(" %p")),
        )
        subtitle.highlight_words(":", style="dim #aaaaaa")

        # Message
        message_text: Text = Gradient(record["message"], colors, style="bold")
        # Generate and print log panel with aligned title and subtitle
        log_panel: Panel = Panel(
            message_text,
            title=title,
            title_align="left",  # Left align the title
            subtitle=subtitle,
            subtitle_align="right",  # Right align the subtitle
            border_style=style + Style(bold=True),
            padding=(1, 2),
        )
        console = get_console(True)
        console.print(log_panel)
        record["extra"]["rich"] = console.export_text()


def on_exit():
    """At exit, read the run number and increment it."""
    try:
        log = get_logger()
        run = read()
        log.info(f"Run {run} Completed")
    except FileNotFoundError as fnfe:
        log.error(fnfe)
        run = setup()
        log.info(f"Run {run} Completed")
    run = increment()


atexit.register(on_exit)

if __name__ == "__main__":
    log: loguru.Logger = get_logger()

    log.info("Started")
    log.trace("Trace")
    log.debug("Debug")
    log.info("Info")
    log.success("Success")
    log.warning("Warning")
    log.error("Error")
    log.critical("Critical")

    sys.exit(0)
