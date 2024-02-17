from datetime import datetime
from typing import IO, Callable, Mapping, Optional, Union, List, Tuple

from maxgradient.default_styles import DEFAULT_STYLES
from rich._log_render import FormatTimeCallable
from rich.console import Console, HighlighterType
from rich.emoji import EmojiVariant
from rich.highlighter import ReprHighlighter
from rich.layout import Layout
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    ProgressColumn
)
from rich.style import StyleType
from rich.theme import Theme
from rich.traceback import install as tr_install

from snoop import snoop # type: ignore
from cheap_repr import register_repr, normal_repr # type: ignore


def get_console(
    force_terminal: Optional[bool] = None,
    force_jupyter: Optional[bool] = None,
    force_interactive: Optional[bool] = None,
    soft_wrap: bool = False,
    theme: Optional[Theme] = Theme(DEFAULT_STYLES),
    stderr: bool = False,
    file: Optional[IO[str]] = None,
    quiet: bool = False,
    width: Optional[int] = None,
    height: Optional[int] = None,
    style: Optional[StyleType] = None,
    no_color: Optional[bool] = None,
    tab_size: int = 8,
    record: bool = False,
    markup: bool = True,
    emoji: bool = True,
    emoji_variant: Optional[EmojiVariant] = None,
    highlight: bool = True,
    log_time: bool = True,
    log_path: bool = True,
    log_time_format: Union[str, FormatTimeCallable] = "[%X]",
    highlighter: Optional[HighlighterType] = ReprHighlighter(),
    legacy_windows: Optional[bool] = None,
    safe_box: bool = True,
    get_datetime: Optional[Callable[[], datetime]] = None,
    get_time: Optional[Callable[[], float]] = None,
    _environ: Optional[Mapping[str, str]] = None,
    traceback: bool = True,
) -> Console:
    """
    A high level console interface.

    Args:
        color_system (str, optional): The color system supported by your terminal,
            either ``"standard"``, ``"256"`` or ``"truecolor"``. Leave as ``"auto"`` to autodetect.
        force_terminal (Optional[bool], optional): Enable/disable terminal control codes, or None to auto-detect terminal. Defaults to None.
        force_jupyter (Optional[bool], optional): Enable/disable Jupyter rendering, or None to auto-detect Jupyter. Defaults to None.
        force_interactive (Optional[bool], optional): Enable/disable interactive mode, or None to auto detect. Defaults to None.
        soft_wrap (Optional[bool], optional): Set soft wrap default on print method. Defaults to False.
        theme (Theme, optional): An optional style theme object, or ``None`` for default theme.
        stderr (bool, optional): Use stderr rather than stdout if ``file`` is not specified. Defaults to False.
        file (IO, optional): A file object where the console should write to. Defaults to stdout.
        quiet (bool, Optional): Boolean to suppress all output. Defaults to False.
        width (int, optional): The width of the terminal. Leave as default to auto-detect width.
        height (int, optional): The height of the terminal. Leave as default to auto-detect height.
        style (StyleType, optional): Style to apply to all output, or None for no style. Defaults to None.
        no_color (Optional[bool], optional): Enabled no color mode, or None to auto detect. Defaults to None.
        tab_size (int, optional): Number of spaces used to replace a tab character. Defaults to 8.
        record (bool, optional): Boolean to enable recording of terminal output,
            required to call :meth:`export_html`, :meth:`export_svg`, and :meth:`export_text`. Defaults to False.
        markup (bool, optional): Boolean to enable :ref:`console_markup`. Defaults to True.
        emoji (bool, optional): Enable emoji code. Defaults to True.
        emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.
        highlight (bool, optional): Enable automatic highlighting. Defaults to True.
        log_time (bool, optional): Boolean to enable logging of time by :meth:`log` methods. Defaults to True.
        log_path (bool, optional): Boolean to enable the logging of the caller by :meth:`log`. Defaults to True.
        log_time_format (Union[str, TimeFormatterCallable], optional): If ``log_time`` is enabled, either string for strftime or callable that formats the time. Defaults to "[%X] ".
        highlighter (HighlighterType, optional): Default highlighter.
        legacy_windows (bool, optional): Enable legacy Windows mode, or ``None`` to auto detect. Defaults to ``None``.
        safe_box (bool, optional): Restrict box options that don't render on legacy Windows.
        get_datetime (Callable[[], datetime], optional): Callable that gets the current time as a datetime.datetime object (used by Console.log),
            or None for datetime.now.
        get_time (Callable[[], time], optional): Callable that gets the current time in seconds, default uses time.monotonic.
        traceback (bool, optional): Enable traceback. Defaults to True.
    """

    console = Console(
        force_terminal=force_terminal,
        force_jupyter=force_jupyter,
        force_interactive=force_interactive,
        soft_wrap=soft_wrap,
        theme=theme,
        stderr=stderr,
        file=file,
        quiet=quiet,
        width=width,
        height=height,
        style=style,
        no_color=no_color,
        tab_size=tab_size,
        record=record,
        markup=markup,
        emoji=emoji,
        emoji_variant=emoji_variant,
        highlight=highlight,
        log_time=log_time,
        log_path=log_path,
        log_time_format=log_time_format,
        highlighter=highlighter,
        legacy_windows=legacy_windows,
        safe_box=safe_box,
        get_datetime=get_datetime,
        get_time=get_time,
        _environ=_environ,
    )
    if traceback:
        tr_install(console=console, show_locals=True)  # type: ignore
    return console


def make_layout(self) -> Layout:
    """Generate a layout to display the chapter's text."""
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=1),
    )
    layout.split_row(
        Layout(name="left_margin", size=4),
        Layout(name="article"),
        Layout(name="right_margin", size=4),
    )
    return layout

register_repr(Progress)(normal_repr)

@snoop()
def get_progress_columns(console: Console) -> Tuple[List[str|ProgressColumn], Console, int]:
    """Get a progress bar setup.
    
    Args:
        console (Console): the console object
    
    Returns:
        Tuple[List[str|ProgressColumn], Console, int]: a tuple of the:
            - list of columns
            - console object
            - the number of refreshes of the progress bar per second
    """
    return (
        [
            TextColumn(
            "[progress.description]{task.description}[/]",
            justify="right"
            ),
            BarColumn(
                bar_width=None
            ),
            TextColumn(
                "[progress.percentage]{task.percentage:>3.1f}%"
            ),
            "•",
            MofNCompleteColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn()
        ],
        console,
        60
    )



global console
console = get_console()
