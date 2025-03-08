from os import getenv
from typing import Any, List, Optional

import openai
from dotenv import load_dotenv
from openai.types import Embedding
from pymongo import MongoClient
from pymongo.collection import Collection
from rich import inspect as rich_inspect
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.prompt import Confirm
import loguru # type: ignore

from supergene.config.log import get_logger, get_console, get_progress

load_dotenv()
console = get_console()
progress = get_progress(console=console)
log = get_logger()


# MongoDB configuration
MONGO_URI: str = getenv("MONGO_URI", "op://Dev/Mongo/Database/uri")
DB_NAME: str = getenv("DATABASE_NAME", "supergene")
COLLECTION_NAME: str = getenv("COLLECTION_NAME", "chapters")

# OpenAI configuration
OPENAI_API_KEY = getenv("OPENAI_API_KEY", "op://Personal/Chat GTP/API Keys/my key")
EMBEDDING_MODEL = "text-embedding-ada-002"  # Example embedding model

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generates an embedding for the given text using OpenAI's API.

    Args:
        text: The text to generate the embedding for.

    Returns:
        Optional[List[float]] The generated embedding as a list of floats.
    """
    try:
        response = openai.embeddings.create(input=text, model=EMBEDDING_MODEL)
        embed: List[Embedding] = response.data
        return embed[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def update_chapter_with_embedding(
    chapter_id: int,
    embedding: List[float],
    collection: Collection,
    task: TaskID
) -> None:
    """
    Updates the MongoDB document with the generated embedding.

    Args:
        chapter_id: The ID of the chapter.
        embedding: The embedding to update.
        collection: The MongoDB collection to update.
    """

    try:
        progress.update(task, advance=1)
        collection.update_one({"_id": chapter_id}, {"$set": {"embedding": embedding}})
        progress.console.print(f"[i #aaffaa]Successfully updated [/][#ffffff]Chapter {chapter_id}[/][i #aaffaa] with embedding[/]]")
    except Exception as e:
        print(f"Error updating chapter {chapter_id}: {e}")


def main(verbose: bool = False) -> None:
    """
    Main function to generate embeddings for chapters \
that don't have them in the MongoDB collection.

    Args:
        verbose (bool): If True, prints detailed information \
about each chapter being processed.
    """
    # Connect to MongoDB
    client: MongoClient = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Fetch chapters that don't have embeddings
    chapters = list(collection.find({"embedding": {"$exists": False}}))
    total: int = len(chapters)
    with progress:
        embed = progress.add_task("Generating embeddings...", total=total)
        for index, chapter in enumerate(chapters):
            if index < 2 or index % 20 == 0:
                # Inspect chapter if verbose
                if verbose:
                    loop: bool = True
                    while loop:
                        rich_inspect(chapter)
                        if not Confirm.ask("Create embedding for this chapter?"):
                            break


            chapter_id = chapter["_id"]
            chapter_text = chapter["text"]
            chapter_number: int = chapter["chapter"]
            progress.update(embed, description=f"Generating embedding for Chapter {chapter_number}...")

            if not chapter_text:
                log.warning(f"Chapter {chapter_number} has no text.")
                continue


            embedding = generate_embedding(chapter_text)


            if embedding:
                update_chapter_with_embedding(chapter_id, embedding, collection, embed)


if __name__ == "__main__":
    main()
