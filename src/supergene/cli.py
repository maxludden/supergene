"""Unzip epub module."""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Annotated

import typer
from rich import get_console
from rich.console import Console
from rich_gradient.gradient import Gradient
from rich.traceback import install as tr_install


app = typer.Typer(
    rich_markup_mode="rich",
    add_completion=False,
    help="Unzip an EPUB3 ebook into a directory.",
)

# Console
def get_rich_console(console: Console|None = None) -> Console:
    """Get a rich.console.Console to print to the terminal."""
    if not console:
        console = get_console()
    tr_install(console=console)
    return console


def unzip_epub(epub_path: Path, output_dir: Path | None = None) -> Path:
    """Extract an EPUB file and return the destination directory."""
    source = epub_path.expanduser()
    if not source.exists():
        raise FileNotFoundError(f"EPUB file not found: {source}")

    if not source.is_file():
        raise ValueError(f"EPUB path is not a file: {source}")

    if source.suffix.lower() != ".epub":
        raise ValueError(f"Expected an .epub file: {source}")

    destination = output_dir.expanduser() if output_dir else source.with_suffix("")
    destination.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(source) as epub:
            epub.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid EPUB zip archive: {source}") from exc

    return destination


@app.command()
def main(
    epub: Annotated[Path, typer.Argument(help="Path to an .epub file")],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Directory to extract into. Defaults to the EPUB filename without .epub.",
        ),
    ] = None,
) -> None:
    """Unzip epub to file directory."""
    try:
        destination = unzip_epub(epub, output)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"Extracted {epub} to {destination}")
