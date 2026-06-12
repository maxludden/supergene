"""Run Super Gene Pandoc builds with Rich progress reporting."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys
from pathlib import Path
from typing import Protocol, Sequence

from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)


@dataclass(frozen=True, slots=True)
class PandocBook:
    """Describe one Super Gene book build target.

    Attributes:
        number: One-based book number.
        title: Display title for the book.
        defaults_path: Repository-relative Pandoc defaults file path.
        output_path: Repository-relative output EPUB path.
    """

    number: int
    title: str
    defaults_path: Path
    output_path: Path

    @property
    def label(self) -> str:
        """Return the concise display label for this book."""
        logger.trace(f"Rendering label for Pandoc book {self.number}")
        return f"Book {self.number:02d} - {self.title}"


class CommandRunner(Protocol):
    """Callable interface for running subprocess commands."""

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and return its completed process.

        Args:
            command: Command and arguments to run.
            cwd: Working directory for the command.
            text: Whether output should be decoded as text.
            capture_output: Whether stdout and stderr should be captured.

        Returns:
            The completed subprocess result.
        """
        logger.trace("Entering CommandRunner.__call__")
        raise NotImplementedError


class PandocBuildError(RuntimeError):
    """Raised when generated-input or Pandoc subprocess execution fails."""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        output: str,
        command_name: str,
    ) -> None:
        """Initialize the build error.

        Args:
            command: Command that failed.
            returncode: Process return code.
            output: Captured stdout and stderr text.
            command_name: Human-readable command label.
        """
        logger.trace(f"Creating PandocBuildError for {command_name}")

        self.command = tuple(command)
        self.returncode = returncode
        self.output = output
        self.command_name = command_name
        super().__init__(f"{command_name} exited with status {returncode}")


def project_root() -> Path:
    """Return the repository root for the installed package."""
    logger.trace("Resolving project root")
    return Path(__file__).resolve().parents[2]


def pandoc_books(repo_root: Path | None = None) -> tuple[PandocBook, ...]:
    """Return configured Pandoc book targets.

    Args:
        repo_root: Repository root used for locating the generator script.

    Returns:
        Book targets matching ``scripts/generate_pandoc_defaults.py``.
    """
    logger.trace("Loading Pandoc book catalog")

    root = repo_root or project_root()
    return tuple(
        PandocBook(
            number=book.number,
            title=book.title,
            defaults_path=Path(
                f"converted/Super Gene/defaults/book-{book.number:02d}-{book.slug}.yaml"
            ),
            output_path=Path(f"converted/Super Gene/books/book-{book.number:02d}-{book.slug}.epub"),
        )
        for book in _load_generator_books(root)
    )


def build_book(
    book_number: int,
    *,
    repo_root: Path | None = None,
    runner: CommandRunner = subprocess.run,
    console: Console | None = None,
) -> None:
    """Generate inputs and build one Super Gene book with Pandoc.

    Args:
        book_number: One-based book number to build.
        repo_root: Repository root for command execution.
        runner: Subprocess runner, injectable for tests.
        console: Rich console for progress output.

    Raises:
        ValueError: If the book number is not configured.
        PandocBuildError: If input generation or Pandoc exits non-zero.
    """
    logger.trace(f"Building Pandoc book {book_number}")

    root = repo_root or project_root()
    book = _book_by_number(book_number, root)
    with _pandoc_progress(console) as progress:
        total_task = progress.add_task("Building 1 book", total=1)
        _generate_inputs(root, runner, progress)
        _run_pandoc(book, root, runner, progress)
        progress.update(total_task, advance=1, description="Built 1 book")


def build_all_books(
    *,
    repo_root: Path | None = None,
    runner: CommandRunner = subprocess.run,
    console: Console | None = None,
) -> None:
    """Generate inputs and build every configured Super Gene book with Pandoc.

    Args:
        repo_root: Repository root for command execution.
        runner: Subprocess runner, injectable for tests.
        console: Rich console for progress output.

    Raises:
        PandocBuildError: If input generation or Pandoc exits non-zero.
    """
    logger.trace("Building all Pandoc books")

    root = repo_root or project_root()
    books = pandoc_books(root)
    with _pandoc_progress(console) as progress:
        total_task = progress.add_task("Building books", total=len(books))
        _generate_inputs(root, runner, progress)
        for book in books:
            _run_pandoc(book, root, runner, progress)
            progress.update(total_task, advance=1, description=f"Built {book.label}")


def _pandoc_progress(console: Console | None) -> Progress:
    """Create the Rich progress renderer used by Pandoc builds.

    Args:
        console: Optional console override.

    Returns:
        Configured Rich progress instance.
    """
    logger.trace("Creating Pandoc Rich progress renderer")

    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console or Console(stderr=True),
        transient=False,
        redirect_stdout=False,
        redirect_stderr=False,
    )


def _load_generator_books(repo_root: Path) -> tuple[object, ...]:
    """Load book definitions from the Pandoc defaults generator.

    Args:
        repo_root: Repository root containing ``scripts/generate_pandoc_defaults.py``.

    Returns:
        Tuple of generator book definitions.
    """
    logger.trace("Loading book definitions from generator script")

    import importlib.util

    generator_path = repo_root / "scripts" / "generate_pandoc_defaults.py"
    spec = importlib.util.spec_from_file_location("_supergene_generate_pandoc_defaults", generator_path)
    if spec is None or spec.loader is None:
        msg = f"Unable to load {generator_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return tuple(module.BOOKS)


def _book_by_number(book_number: int, repo_root: Path) -> PandocBook:
    """Return the configured book for a one-based book number.

    Args:
        book_number: Book number to find.
        repo_root: Repository root used to load the book catalog.

    Returns:
        Matching Pandoc book target.

    Raises:
        ValueError: If no book matches the number.
    """
    logger.trace(f"Resolving Pandoc book {book_number}")

    for book in pandoc_books(repo_root):
        if book.number == book_number:
            return book
    msg = f"Unknown Super Gene book number: {book_number}"
    raise ValueError(msg)


def _generate_inputs(repo_root: Path, runner: CommandRunner, progress: Progress) -> None:
    """Run the generated Pandoc input/defaults script.

    Args:
        repo_root: Repository root for command execution.
        runner: Subprocess runner.
        progress: Rich progress renderer to update.

    Raises:
        PandocBuildError: If the generator exits non-zero.
    """
    logger.trace("Generating Pandoc inputs before build")

    task_id = progress.add_task("Generating Pandoc inputs", total=None)
    command = [sys.executable, "scripts/generate_pandoc_defaults.py"]
    result = runner(command, cwd=repo_root, text=True, capture_output=True)
    _raise_for_failure(command, result, "Generate inputs")
    progress.update(task_id, completed=1, total=1, description="Generated Pandoc inputs")


def _run_pandoc(
    book: PandocBook,
    repo_root: Path,
    runner: CommandRunner,
    progress: Progress,
) -> None:
    """Run Pandoc for one generated book defaults file.

    Args:
        book: Book target to build.
        repo_root: Repository root for command execution.
        runner: Subprocess runner.
        progress: Rich progress renderer to update.

    Raises:
        PandocBuildError: If Pandoc exits non-zero.
    """
    logger.trace(f"Running Pandoc for {book.label}")

    task_id = progress.add_task(f"Pandoc {book.label}", total=None)
    output_path = repo_root / book.output_path
    output_path.unlink(missing_ok=True)
    command = ["pandoc", "--defaults", book.defaults_path.as_posix()]
    result = runner(command, cwd=repo_root, text=True, capture_output=True)
    _raise_for_failure(command, result, "Pandoc")
    progress.update(task_id, completed=1, total=1, description=f"Finished {book.label}")


def _raise_for_failure(
    command: Sequence[str],
    result: subprocess.CompletedProcess[str],
    command_name: str,
) -> None:
    """Raise a build error if a subprocess result failed.

    Args:
        command: Command that produced the result.
        result: Completed process result.
        command_name: Human-readable command label.

    Raises:
        PandocBuildError: If ``result.returncode`` is non-zero.
    """
    logger.trace(f"Checking {command_name} subprocess result")

    if result.returncode == 0:
        return
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    msg = f"{command_name} exited with status {result.returncode}"
    raise PandocBuildError(command, result.returncode, output or msg, command_name)
