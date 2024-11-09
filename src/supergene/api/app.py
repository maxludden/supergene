
from pathlib import Path
from typing import List
from os import getenv

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from ludden_logging import log
from supabase import create_client, Client
from sqlmodel import Field, Session, SQLModel, create_engine, select


sqlite_file_name: str = "supergene.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()
CWD = Path.cwd()
log.info(f"Current working directory: {CWD}")

# Load Jinja2 templates
templates_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(templates_dir))

# Path to chapters and stylesheets
CHAPTERS_DIR = Path(__file__).parent.parent / "docs" / "chapters"
print(CHAPTERS_DIR)
STYLESHEET_PATH = "static/stylesheets/styles.css"


def get_chapter_paths() -> List[Path]:
    """Return a list of chapter paths sorted in numeric order."""
    return sorted(CHAPTERS_DIR.iterdir(), key=lambda p: int(p.stem))


def read_chapter(path: Path) -> str:
    """Read the content of a chapter file."""
    with path.open("r", encoding="utf-8") as file:
        return file.read()


@app.get("/", response_class=HTMLResponse)
async def read_chapters(request: Request):
    chapter_paths = get_chapter_paths()
    chapters = [read_chapter(path) for path in chapter_paths]

    template = env.get_template("chapters.html")
    html_content = template.render(chapters=chapters, stylesheet=STYLESHEET_PATH)
    return HTMLResponse(content=html_content)


# Static files configuration
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.parent.parent / "docs"),
    name="static",
)
