from maxgradient import Gradient
from rich.live import Live
from rich.table import Table
from rich.text import Text

from supergene.chapter import V4Chapter
from supergene.console import Console, get_console
from supergene.mongo import Mongo
from supergene.progress import get_progress, progress


def generate_table() -> Table:
    """Generate a table to display the chapter's order and variance."""
    table = Table(
        expand=False,
        width=100,
        show_header=True,
        row_styles=["on #111111", "on #333333"],
    )

    table.add_column(Gradient("Order", style="bold"), justify="right", no_wrap=True)
    table.add_column(Gradient("Chapter", style="bold"), justify="right", no_wrap=True)
    table.add_column(Gradient("Title", style="bold"), justify="right", no_wrap=True)
    table.add_column(Gradient("Delta", style="bold"), justify="right", no_wrap=True)
    return table


def index_table() -> None:
    """Generate  table to display the chapter's order and variance."""
    mongo = Mongo()
    mongo.connect()

    table = generate_table()

    mongo = Mongo()
    mongo.connect()
    chapters = V4Chapter.all(sort="chapter").to_list()
    _console: Console = get_console()
    progress, live = get_progress(console=_console, return_live=True)
    if live:

        console = live.console
        with live:
            console = live.console
            index_task = progress.add_task("Indexing chapters", total=len(chapters))
            x: int = 1
            for count, chapter in enumerate(chapters, 1):
                progress.update(index_task, advance=1)
                if count == chapter.chapter:
                    delta = Text("0", style="bold #89E6FA")
                elif count < chapter.chapter:
                    delta = Text(
                        f"+{str(chapter.chapter - count):>7}", style="bold #00ff00"
                    )
                else:
                    delta = Text(
                        f"-{str(count - chapter.chapter):>7}", style="bold #ffaf00"
                    )

                if x == chapter:
                    title = Text(chapter.title, style="bold #00afff")
                else:
                    title = Text(chapter.title, style="bold #ffffff")

                table.add_row(
                    Text(str(count)), Text(str(chapter.chapter)), title, delta
                )
    else:
        console = progress.console
        with live:
            console = live.console
            index_task = progress.add_task("Indexing chapters", total=len(chapters))
            tun: int = 1
            for count, chapter in enumerate(chapters, 1):
                progress.update(index_task, advance=1)
                if count == chapter.chapter:
                    delta = Text("0", style="bold #89E6FA")
                elif count < chapter.chapter:
                    delta = Text(
                        f"+{str(chapter.chapter - count):>7}", style="bold #00ff00"
                    )
                else:
                    delta = Text(
                        f"-{str(count - chapter.chapter):>7}", style="bold #ffaf00"
                    )

                if x == chapter:
                    title = Text(chapter.title, style="bold #00afff")
                else:
                    title = Text(chapter.title, style="bold #ffffff")

                table.add_row(
                    Text(str(count)), Text(str(chapter.chapter)), title, delta
                )


def main() -> None:
    mongo = Mongo()
    mongo.connect()
    _console: Console = get_console()

    count = V4Chapter.count()  # 3462
    table = Table(
        expand=False,
        width=100,
        show_header=True,
        row_styles=["on #111111", "on #222222"],
    )
    with Live(table, console=_console, refresh_per_second=60):
        with progress:
            console = progress.console
            index_task = progress.add_task("Indexing chapters", total=count)
            for index in range(1, count + 1):
                progress.update(index_task, advance=1)
                chapter = V4Chapter.find_one(V4Chapter.chapter == index).run()
                if chapter:
                    continue
                else:
                    table.add_row(
                        Text(str(index)),
                        Text(f"Chapter {index} Not Found", style="bold #ff0000"),
                        Text("None", style="bold #ff0000"),
                    )
            console.print("Done!")


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
