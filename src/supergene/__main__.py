from __future__ import annotations

from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import typer
from loguru import logger
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn

from supergene.converter import ConversionProgress, ConversionResult, convert_epub
from supergene.logging import configure_logging
from supergene.supabase_store import SupabaseStorageConfig, store_conversion_in_supabase
from supergene.table_candidates import write_table_candidate_report


app = typer.Typer(no_args_is_help=True)


@app.command("epub-to-md")
def epub_to_md(
    epub_path: Annotated[Path, typer.Argument(help="EPUB file to convert.")],
    output_dir: Annotated[Path, typer.Argument(help="Directory where converted Markdown output will be written.")],
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Replace an existing book output directory.")] = False,
    supabase_url: Annotated[
        str | None,
        typer.Option("--supabase-url", help="Supabase project URL for storing converted output."),
    ] = None,
    supabase_key: Annotated[
        str | None,
        typer.Option("--supabase-key", help="Supabase API key for storing converted output."),
    ] = None,
    supabase_bucket: Annotated[
        str | None,
        typer.Option("--supabase-bucket", help="Supabase Storage bucket for EPUB assets."),
    ] = None,
) -> None:
    """Convert an EPUB into chapter Markdown files."""
    configure_logging()
    if not epub_path.is_file() or epub_path.suffix.lower() != ".epub":
        _usage_error("epub_path must be an .epub file, not a directory or project folder")
    supplied_supabase_args = [supabase_url, supabase_key, supabase_bucket]
    if any(supplied_supabase_args) and not all(supplied_supabase_args):
        _usage_error("--supabase-url, --supabase-key, and --supabase-bucket must be provided together")
    if supabase_url and not _is_supabase_api_url(supabase_url):
        _usage_error(
            "--supabase-url must be the HTTPS Supabase API URL, "
            "for example https://PROJECT_REF.supabase.co; do not use a postgresql:// database URL"
        )
    try:
        logger.info("Converting {} to {}", epub_path, output_dir)
        result = _convert_with_progress(epub_path, output_dir, overwrite=overwrite)
        if supabase_url and supabase_key and supabase_bucket:
            logger.info("Storing converted book in Supabase bucket {}", supabase_bucket)
            store_result = store_conversion_in_supabase(
                result,
                SupabaseStorageConfig(bucket=supabase_bucket),
                supabase_url=supabase_url,
                supabase_key=supabase_key,
            )
            logger.info(
                "Stored book {} in Supabase ({} chapters, {} assets)",
                store_result.book_id,
                store_result.chapter_count,
                len(store_result.uploaded_assets),
            )
    except Exception as exc:
        logger.error("{}", exc)
        raise typer.Exit(1) from exc
    logger.info("Wrote {} chapters to {}", len(result.chapters), result.output_dir)
    for warning in result.warnings:
        logger.warning("warning[{}]: {}", warning.code, warning.message)


@app.command("table-report")
def table_report(
    chapters_dir: Annotated[Path, typer.Argument(help="Directory containing Markdown chapter files.")],
    output_path: Annotated[Path, typer.Argument(help="Path to write the table candidate JSON report.")],
) -> None:
    """Find lines that may be better formatted as HTML tables."""
    configure_logging()
    if not chapters_dir.is_dir():
        _usage_error("chapters_dir must be a directory containing Markdown chapter files")
    try:
        candidates = write_table_candidate_report(chapters_dir, output_path)
    except Exception as exc:
        logger.error("{}", exc)
        raise typer.Exit(1) from exc
    logger.info("Wrote {} table candidates to {}", len(candidates), output_path)


def main() -> None:
    app()


def _is_supabase_api_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and (parsed.hostname or "").endswith(".supabase.co")


def _usage_error(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(2)


def _convert_with_progress(epub_path: Path, output_dir: Path, *, overwrite: bool) -> ConversionResult:
    console = Console(stderr=True)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
        redirect_stdout=False,
        redirect_stderr=False,
    ) as progress:
        task_id = progress.add_task("Writing chapters", total=None)

        def update(event: ConversionProgress) -> None:
            progress.update(task_id, total=event.total, completed=event.completed, description=f"Writing {event.title}")

        return convert_epub(epub_path, output_dir, overwrite=overwrite, progress_callback=update)


if __name__ == "__main__":
    main()
