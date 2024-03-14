from pathlib import Path
from rich.console import Console
from supergene.mongo import Mongo
from typing import Set, Generator
from re import search
from pydantic import BaseModel

BOOKS = Path.home() / "dev" / "py" / "archive" / "superforge" / "books"
WORLD_VOICE = []

mongo = Mongo()
console: Console = mongo.console
progress = mongo.progress

class VoiceOfTheWorld(BaseModel):
    examples: Set[str]
    DIR: Path = Path("/Users/maxludden/dev/py/supergene/static/voice_of_the_world")
    
    def __init__(self) -> None:
        super().__init__()
        self.examples = set()
        if not self.DIR.exists():
            self.DIR.mkdir()
        
        with progress:
            books = progress.add_task("Working on Books", total=10)
            self.examples == ()
            for book in self.walk_books():
                book_number: int = self.get_book_number(book)
                self.examples = set(f"Book {book_number}\n\n")
                for chapter in self.walk_chapters(book):
                    for line in self.walk_lines(chapter):
                        self.examples.add(line)
                self.write_examples(book)


    def walk_books(self) -> Generator[Path, None, None]:
        """Walk the book directorier"""
        books = Path.home() / "dev" / "py" / "archive" / "superforge" / "books"
        for book in books.iterdir():
            yield book

    def get_book_number(self, book: Path) -> int:
        """Get the book number from the book directory"""
        book_num = search(r"\d+", str(book.name))
        if book_num:
            return int(book_num.group())
        else:
            raise ValueError(f"Book number not found in {book.name}")

    def walk_chapters(self, book: Path) -> Generator[Path, None, None]:
        """Walk the chapters in the book directory"""
        for file in book.iterdir():
            if file.suffix == ".md":
                yield file

    def walk_lines(self, chapter: Path) -> Generator[str, None, None]:
        """Walk the lines in the chapter"""
        with open(chapter, "r") as infile:
            lines = infile.readlines()
            for line in lines:
                if ">" in line:
                    yield line

    def write_examples(self, book: int) -> bool:
        """Append the examples to the output file.
        
        Args:
            book (int): The book number
        
        Returns:
            bool: True, if successful
        """
        try:
            with open(self.DIR / f"book{str(book).zfill(2)}.txt", "w") as outfile:
                outfile.write("\n".join(self.examples))
        except IOError as e:
            raise IOError(f"Error writing to file: {e}")
        else:
            return True
        
def _first_try():
    with progress:
        books = progress.add_task("Working on Books", total=10)

        
        
        for i in range(1,11):
            progress.update(books, description=f"Working on Book {i}", advance=1)
            zfill = str(i).zfill(2)
            BOOK_PATH = f"book{zfill}"
            MD = BOOKS / BOOK_PATH / "md"
            WORLD_VOICE.append(f"\n\nBook {i}")
            voice: set[str] = set()
            for file in MD.iterdir():
            
                if file.suffix == ".md":
                    with open(file, "r") as infile:
                        lines = infile.readlines()
                        for line in lines:
                            if line[0] == ">":
                                voice.add(line.strip())
                else:
                    continue
                            
    filepath = Path.home() / "dev" / "py" / "supergene" / "static" / "voice_of_the_world.txt"
    with open (filepath, 'w') as outfile:
        outfile.write('\n\n'.join(WORLD_VOICE))
