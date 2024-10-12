from datetime import datetime
from typing import List
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, computed_field


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
        title="Trimmed Text",
        description="The text that precedes the content of the chapter, such as the chapter title and translator information.",
        examples=[
            "Chapter 1 - Supergene\n\nChapter 1: Supergene\n\nTranslator: Nyoi-Bo Studio Editor: Nyoi-Bo Studio",
            "Chapter 9 - Sacred-Blood Creature\n\nChapter 9: Sacred-blood Creature\n\nTranslator: Nyoi-Bo Studio Editor: Nyoi-Bo Studio"
        ]
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


