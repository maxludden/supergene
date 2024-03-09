from pathlib import Path
from rich.console import Console
from supergene.mongo import Mongo
from typing import Set

BOOKS = Path.home() / "dev" / "py" / "archive" / "superforge" / "books"
WORLD_VOICE = []

mongo = Mongo()
console: Console = mongo.console
progress = mongo.progress


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
                            WORLD_VOICE.append(line)
            else:
                continue
                        
filepath = Path.home() / "dev" / "py" / "supergene" / "static" / "voice_of_the_world.txt"
with open (filepath, 'w') as outfile:
    outfile.write('\n\n'.join(WORLD_VOICE))
