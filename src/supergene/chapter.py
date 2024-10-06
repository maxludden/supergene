import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, computed_field
from bson import ObjectId
from pymongo import MongoClient, ReturnDocument
from fastapi import Query
from pymongo.cursor import Cursor
from pymongo.collection import Collection
from dotenv import load_dotenv

from supergene import Log

# ----- Load Environment Variables -----
load_dotenv()
log = Log()
console = log.console
templates = Jinja2Templates(directory="templates")

# ----- Configuration -----
URI = os.getenv('MONGO_URI', "op://Dev/Mongo/Database/uri")
DB = os.getenv('supergene', "op://Dev/Mongo/Database/name")
CHAPTERS = os.getenv('chapters', "op://Dev/Mongo/Database/collection")
LAST = os.getenv('LAST', '0')  # Currently not used; can be integrated based on specific requirements

# ----- Pydantic Models -----

class PyObjectId(ObjectId):
    """Custom Pydantic field for MongoDB ObjectId"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid ObjectId')
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, field):
        schema.update(type='string')
        return schema

class ChapterBase(BaseModel):
    """The base model for a chapter."""
    chapter: int = Field(
        ...,
        ge=1,
        lt=3462,
        description="Chapter number.",
        examples=['1','2', '2000']
    )
    section: int = Field(
        ...,
        ge=1,
        le=18,
        description="Section number.",
        examples=['1', '3', '18']
    )
    book: int = Field(
        ...,
        ge=1,
        le=10,
        description="Book number.",
        examples=['1']
    )
    description: str = Field(
        ...,
        description="description of the chapter.",
        examples=['supergene', 'harvest']
    )
    text: str = Field(
        ...,
        description="Text of the chapter."
    )
    trimmed_text: str = Field(
        ...,
        description="Trimmed text of the chapter."
    )
    text_embed: List[float] = Field(
        ...,
        description="Text embedding of the chapter.",
        examples=[0.1, 0.2, 0.3]
    )
    created: datetime = Field(
        default_factory=datetime.now().isoformat,
        title="Created",
        description="Date and time the chapter was created."
    )
    modified: datetime = Field(
        default_factory=datetime.now().isoformat,
        title="Modified",
        description="Date and time the chapter was last modified."
    )
    version: float = Field(
        0.1,
        title="Version",
        description="The version of the chapter."
    )

    @computed_field
    def audio_path(self) -> Path:
        """Computed field for the audio path of the chapter."""
        return Path(f"audio/{str(self.chapter).zfill(4)}.mp3")

    @field_validator('chapter')
    def validate_chapter(cls, v):
        if not isinstance(v, int):
            raise TypeError("Chapter.chapter must be an integer.)")
        if v < 1 or v > 3462:
            raise ValueError('Chapter.chapter must be between 1 and 3462.')
        return v

    @field_validator('section')
    def validate_section(cls, v):
        if not isinstance(v, int):
            raise TypeError("Chapter.section must be an integer.)")
        if v < 1 or v > 18:
            raise ValueError('Chapter.section must be between 1 and 18.')
        return v

    @field_validator('book')
    def validate_book(cls, v):
        if not isinstance(v, int):
            raise TypeError("Chapter.book must be an integer.)")
        if v < 1 or v > 10:
            raise ValueError('Chapter.book must be between in the range of 1 to 10.')
        return v


class ChapterCreate(ChapterBase):
    pass  # Inherits all fields from ChapterBase


class ChapterUpdate(BaseModel):
    chapter: Optional[int] = Field(
        None,
        ge=1,
        lt=3462,
        title="Chapter",
        description="The chapter number.",
        examples=['1','2', '2000']
    )
    section: Optional[int] = Field(
        None,
        ge=1,
        le=18, title="Section",
        description="The section the chapter is in.",
        examples=['1', '3', '18']
    )
    book: Optional[int] = Field(
        None,
        ge=1,
        le=1,
        title="Book",
        description="Which book the chapter is in.",
        examples=['1', '2']
    )
    title: Optional[str] = Field(
        None,
        title="Title",
        description="The title of the chapter.",
        examples=['supergene']
    )
    text: Optional[str] = Field(
        None,
        title="Text",
        description="The text of the chapter."
    )
    trimmed_text: Optional[str] = Field(
        None,
        title="Trimmed Text",
        description="Trimmed text of the chapter."
    )
    text_embed: Optional[List[float]] = Field(
        None,
        title="Text Embeddings",
        description="Text embedding of the chapter.",
        examples=[0.1, 0.2, 0.3]
    )
    version: Optional[int] = Field(
        None,
        title="Version",
        description="The version of the chapter.",
        examples=[0.1, 0.5,1.0, 2,2]
    )


class Chapter(ChapterBase):
    created: datetime = Field(default_factory=datetime.utcnow, title="Date and time the chapter was created.")
    modified: datetime = Field(default_factory=datetime.utcnow, title="Date and time the chapter was last modified.")
    version: float = Field(default=0.1, title="Version", description="The version of the chapter.")

    def some_method(self):
        # Example method that should not be serialized
        pass

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }
        # Exclude methods from serialization
        exclude = {"some_method"}

# ----- Database Connection -----

client: MongoClient = MongoClient(URI)
db = client.supergene
collection: Collection = db['chapters']

# Ensure indexes for optimal querying (optional but recommended)
try:
    collection.create_index([("chapter", 1)], unique=True)
except Exception:
    pass

# ----- FastAPI Application -----

app = FastAPI(title="Super Gene", description="API for performing CRUD operations on chapters.", version="0.0.1")

# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----- CRUD Endpoints -----

@app.post("/chapters", response_model=Chapter, status_code=status.HTTP_201_CREATED)
async def create_chapter(chapter: ChapterCreate):
    """
    Create a new chapter.
    """
    chapter_dict = chapter.model_dump()
    chapter_dict['created'] = datetime.now().isoformat()
    chapter_dict['modified'] = datetime.now().isoformat()
    chapter_dict['version'] = 1.0
    try:
        result = collection.insert_one(chapter_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    created_chapter = collection.find_one({"_id": result.inserted_id})
    return created_chapter

@app.get("/chapters", response_class=HTMLResponse)
async def get_chapters(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    """
    Retrieve a paginated list of chapters.

    Args:
        page (int): The page number. Defaults to 1.
        page_size (int): The number of items per page. Defaults to 10.
    """
    total_chapters = collection.count_documents({})
    chapters = list(collection.find().skip((page - 1) * page_size).limit(page_size))
    return templates.TemplateResponse("chapters.html", {
        "request": request,
        "chapters": chapters,
        "page": page,
        "page_size": page_size,
        "total_chapters": total_chapters
    })

@app.get("/chapters/{chapter}", response_class=HTMLResponse)
async def get_chapter(request: Request, chapter: int, version: Optional[float] = None):
    """
    Retrieve a version of a chapter. if version is not provided, the latest version is returned.

    Args:
        chapter (int): The chapter number.
        version (float, optional): The version of the chapter. Defaults to None.
    """
    if version is not None:
        chapter_doc: Optional[Chapter] = collection.find_one({"chapter": chapter, "version": version})
    else:
        chapter_doc = collection.find_one({"chapter": chapter})
    if not chapter_doc:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found.")
    return templates.TemplateResponse("chapter.html", {"request": request, "chapter": chapter_doc})

@app.get("/chapters/{chapter}/versions", response_model=List[Chapter])
async def get_chapter_versions(chapter: int):
    """
    Retrieve all versions of a chapter.
    """
    chapter_docs: List[Chapter] = list(collection.find({"chapter": chapter}).sort("version", -1))
    if not chapter_docs:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found.")
    return chapter_docs

@app.get("/chapters/{chapter}/latest", response_model=Chapter)
async def get_latest_chapter(chapter: int):
    """
    Retrieve the latest version of a chapter.
    """
    chapter_doc: Optional[Chapter] = collection.find_one({"chapter": chapter}, sort=[("version", -1)])
    if not chapter_doc:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found.")
    return chapter_doc

@app.get("/chapters/{chapter}/{version}", response_model=Chapter)
async def get_chapter_version(chapter: int, version: float):
    """
    Retrieve a specific version of a chapter.
    """
    chapter_doc: Optional[Chapter] = collection.find_one({"chapter": chapter, "version": version})
    if not chapter_doc:
        raise HTTPException(status_code=404, detail=f"Version {version} of Chapter {chapter} not found.")
    return chapter_doc

@app.put("/chapters/{chapter}", response_model=Chapter)
async def update_chapter(chapter: int, update: ChapterUpdate):
    """
    Update an existing chapter by its ID.
    """
    chapter_doc: Optional[Chapter] = collection.find_one({"chapter": chapter})
    if not chapter_doc:
        raise HTTPException(status_code=400, detail=f"Chapter {chapter} not found.")

    update_data = chapter_doc.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=401, detail="No fields to update.")

    # Automatically update the 'modified' timestamp and increment 'version'
    update_fields = {k: v for k, v in update_data.items() if k != 'version'}
    update_operation = {
        "$set": {
            **update_fields,
            "modified": datetime.utcnow()
        },
        "$inc": {"version": 1}
    }

    try:
        updated_chapter = collection.find_one_and_update(
            {"chapter": chapter},
            update_operation,
            return_document=ReturnDocument.AFTER
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated_chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return updated_chapter

@app.delete("/chapters/{chapter}/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chapter(chapter: int, version: float):
    """
    Delete a version of a chapter.
    """
    chapter_docs: Cursor = collection.find({"chapter": chapter})
    if chapter_docs is None:
        raise HTTPException(
            status_code=400,
            detail="Chapter not found")
    else:
        versions: List[float] = []
        for doc in chapter_docs:
            versions.append(doc['version'])

        if version not in versions:
            raise HTTPException(
                status_code=400,
                detail="Version not found")
    result = collection.delete_one(
        {
            "chapter": chapter,
            "version": version
        }
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Unable to delete Chapter {chapter}'s version {version}.")
    return

# ----- Run the Application -----
# Use the following command to run the server:
# uvicorn your_script_name:app --host 0.0.0.0 --port 8000 --reload
