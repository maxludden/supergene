#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any, Iterable
from os import getenv

import typer
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.style import Style
from rich.text import Text

load_dotenv()
OPENAI_API_KEY=getenv("OPENAI_API_KEY")
VECTOR_STORE_ID = "vs_6a020a5b07a08191a60e51b82fb87a73"
CHAPTERS_DIR: Path = Path('converted/Super Gene/chapters')
console = Console()
err_console: Console = Console(stderr=True)
app = typer.Typer(
    help="Upload all .md files in a directory to an OpenAI Vector Store.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
_client = OpenAI(api_key=OPENAI_API_KEY)

progress = Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(bar_width=None),
    TaskProgressColumn(),
    TimeElapsedColumn(),
    console=console,
    transient=True
)


def log_panel_style(level_no: int) -> Style:
    match level_no:
        case _ if level_no <= 5:
            return Style(color="#999999")
        case _ if level_no <= 10:
            return Style(color="#5DADE2")
        case _ if level_no <= 20:
            return Style(color="#58D68D")
        case _ if level_no <= 25:
            return Style(color="#2ECC71", bold=True)
        case _ if level_no <= 30:
            return Style(color="#F4D03F")
        case _ if level_no <= 40:
            return Style(color="#EC7063")
        case _:
            return Style(color="#AF7AC5", bold=True)


def log_to_err_console(message: object) -> None:
    """Log a message to the error rich console."""
    record: dict[str, Any] = getattr(message, "record")
    level = record["level"]
    style = log_panel_style(level.no)
    file = record["file"]
    source = f"{file.name}:{record['line']}"
    timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S")

    metadata = Text.assemble(
        ("level=", "dim"),
        (level.name, style),
        ("  time=", "dim"),
        (timestamp, "default"),
        ("  source=", "dim"),
        (source, "default"),
        ("  function=", "dim"),
        (record["function"], "default"),
    )
    body = Group(metadata, Text(record["message"]))

    err_console.print(
        Panel(
            body,
            title=f"[{escape(level.name.upper())}]",
            border_style=style,
            title_align="left",
        )
    )


def setup_logging() -> None:
    """Set up logging with Loguru"""
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        "logs/vector.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="TRACE",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"),
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        log_to_err_console,
        level="INFO",
        format="{message}",
        colorize=False,
    )


def find_markdown_files(
    directory: Path = CHAPTERS_DIR,
    recursive: bool = True
    ) -> list[Path]:
    """Find the markdown files to upload to the vector storage."""
    logger.trace(f"Searching for markdown files in {directory}, recursive={recursive}")

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    pattern = "**/*.md" if recursive else "*.md"

    files = sorted(
        path
        for path in directory.glob(pattern)
        if path.is_file()
    )

    logger.info(f"Found {len(files)} markdown file(s)")
    return files


def upload_files(client: OpenAI, file_paths: Iterable[Path], ) -> list[str]:
    """Upload files to OpenAI."""
    file_paths = list(file_paths)
    file_ids: list[str] = []

    with progress:
        upload_task = progress.add_task(
            "Uploading markdown files...",
            total=len(file_paths),
        )

        for path in file_paths:
            logger.info(f"Uploading file: {path}")

            try:
                progress.update(upload_task, description=f"Uploading {path.name}")

                with path.open("rb") as file:
                    uploaded = client.files.create(
                        file=file,
                        purpose="assistants",
                    )

                file_ids.append(uploaded.id)

                logger.info(f"Uploaded {path} as {uploaded.id}")

            except Exception:
                logger.exception(f"Failed to upload file: {path}")
                raise

            finally:
                progress.advance(upload_task)

    logger.info(f"Uploaded {len(file_ids)} file(s)")
    return file_ids


def chunked(items: list[str], size: int) -> Iterable[list[str]]:
    """Helper chunking function."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def attach_files_to_vector_store(client: OpenAI, file_ids: list[str]) -> None:
    """Attach files to vector storage."""
    batches = list(chunked(file_ids, 2000))

    with progress:
        attach_task = progress.add_task(
            "Attaching files to vector store...",
            total=len(batches),
        )

        for index, batch_file_ids in enumerate(batches, start=1):
            logger.info(
                f"Attaching batch {index}/{len(batches)} "
                f"with {len(batch_file_ids)} file(s) to vector store {VECTOR_STORE_ID}"
            )

            try:
                progress.update(
                    attach_task,
                    description=f"Attaching batch {index}/{len(batches)}",
                )

                batch = client.vector_stores.file_batches.create_and_poll(
                    vector_store_id=VECTOR_STORE_ID,
                    file_ids=batch_file_ids,
                )

                logger.info(f"Batch {index} status: {batch.status}")
                logger.info(f"Batch {index} file counts: {batch.file_counts}")

                if batch.status != "completed":
                    raise RuntimeError(
                        f"Vector store batch {index} did not complete: {batch.status}"
                    )

            except Exception:
                logger.exception(f"Failed to attach batch {index}")
                raise

            finally:
                progress.advance(attach_task)


@app.command()
def upload(
    directory: Annotated[
        Path,
        typer.Argument(
            help="Directory containing .md files.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,

        ),
    ] = CHAPTERS_DIR,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive/--no-recursive",
            help="Scan subdirectories for markdown files.",
        ),
    ] = True,
) -> None:
    """Upload chapters to vector storage."""
    setup_logging()

    logger.info("Starting markdown upload")
    logger.info(f"Directory: {directory}")
    logger.info(f"Recursive: {recursive}")
    logger.info(f"Vector store ID: {VECTOR_STORE_ID}")

    md_files = find_markdown_files(directory, recursive=recursive)

    if not md_files:
        console.print(f"[yellow]No .md files found in:[/yellow] {directory}")
        logger.warning(f"No .md files found in {directory}")
        return

    console.print(f"Found [bold]{len(md_files)}[/bold] markdown file(s).")

    file_ids = upload_files(_client, md_files)

    if not file_ids:
        console.print("[yellow]No files were uploaded.[/yellow]")
        logger.warning("No files were uploaded")
        return

    attach_files_to_vector_store(_client, file_ids)

    console.print("[green]Done.[/green]")
    logger.success("Finished successfully")


def main() -> None:
    """Main function to upload chapters to vector storage."""
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as ki:
        logger.warning("Cancelled by user")
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise SystemExit(130) from ki
    except Exception as exc:
        logger.exception("Fatal error")
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from exc
