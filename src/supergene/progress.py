from typing import Optional, Tuple
from time import sleep

from rich.live import Live
from rich.progress import (
    BarColumn,
    GetTimeCallable,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from supergene.console import Console, get_console

progress = Progress(
    TextColumn("[italic]{task.description}[/]", justify="right"),
    BarColumn(bar_width=None,
              complete_style="bold #89E6FA"),
    TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
    "•",
    MofNCompleteColumn(),
    "•",
    TimeElapsedColumn(),
    "•",
    TimeRemainingColumn(),
    console=get_console(),
    refresh_per_second=60,
)


def get_progress(
    *columns,
    console: Console = get_console(),
    return_live: bool = False,
    auto_refresh: bool = True,
    refresh_per_second: float = 30,
    speed_estimate_period: float = 30,
    transient: bool = False,
    redirect_stdout: bool = True,
    redirect_stderr: bool = True,
    get_time: GetTimeCallable | None = None,
    disable: bool = False,
    expand: bool = True,
) -> Tuple[Progress, Optional[Live]]|Progress:
    """Get a progress bar setup.

    Args:
        console (Console): the console object
        return_live (bool): whether to return the live object
        auto_refresh (bool): whether to automatically refresh the progress bar
        refresh_per_second (float): the number of refreshes of the progress bar per second
        speed_estimate_period (float): the time period over which to estimate the speed
        transient (bool): whether to display the progress bar transiently
        redirect_stdout (bool): whether to redirect stdout. Defaults to True.
        redirect_stderr (bool): whether to redirect stderr. Defaults to True.
        get_time (GetTimeCallable | None): a callable to get the current time
        disable (bool): whether to disable the progress bar
        expand (bool): whether to expand the progress bar. Defaults to True.

    Returns:
        Progress: the progress bar
        Optional[Live]: the live object
    """
    if not console:
        console = get_console()

    progress = Progress(
        *columns,
        console=console,
        auto_refresh=auto_refresh,
        refresh_per_second=refresh_per_second,
        speed_estimate_period=speed_estimate_period,
        transient=transient,
        redirect_stdout=redirect_stdout,
        redirect_stderr=redirect_stderr,
        get_time=get_time,
        disable=disable,
        expand=expand,
    )
    if return_live:
        live = Live(progress, console=console)
        return progress, live
    return progress, None


if __name__ == "__main__":
    with progress:
        task1 = progress.add_task("Downloading", total=1000)
        task2 = progress.add_task("Processing", total=1000)
        while not progress.finished:
            sleep(0.02)
            progress.update(task1, advance=0.5)
            progress.update(task2, advance=0.3)
    print("Done")
