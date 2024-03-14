# ruff: noqa: F401
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import Progress  # , TaskID
from rich.traceback import install as tr_install

from supergene.mongo import Mongo
from supergene.v3 import V3


def main() -> None:
    try:
        mongo = Mongo()
        mongo.connect()
    except Exception as e:
        print(e)
    else:
        console: Console = mongo.console
        tr_install(console=console)
        progress: Progress = mongo.progress
        book_lengths = []
        for book_num in range(1, 11):
            try:
                book_docs = V3.find(V3.book == book_num).run()

                book_length = len(book_docs)
                book_lengths.append(book_length)
            except Exception as e:
                print(e)
        with progress:
            books = progress.add_task("Working on Books", total=10)
            for book_num in range(1, 11):

                progress.update(
                    books, advance=1, description=f"Working on Book {book_num}..."
                )
                docs = V3.find(V3.book == book_num).to_list()
                if not docs:
                    raise ValueError(
                        f"Book {book_num}'s chapters not found in the database."
                    )
                total = len(docs)
                chapters = progress.add_task(
                    f"Concatinating Book {book_num}'s text...", total=total
                )
                text = ""
                for doc in docs:
                    progress.update(
                        chapters,
                        advance=1,
                        description=f"Working on Chapter {doc.chapter}...",
                    )
                    text = "\n\n---\n\n".join([text, doc.text])
                console.print(text)
                progress.update(books, advance=1)
                path = Path.cwd() / "static" / "text" / "book{str(book).zfill(2)}.txt"
                with open(path, "w") as outfile:
                    outfile.write(text)


if __name__ == "__main__":
    main()
