from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from supergene import convert_epub, store_conversion_in_supabase
from supergene.supabase_store import SupabaseStorageConfig
from epub_fixture import PIXEL_PNG, write_epub


class FakeExecuteResponse:
    def __init__(self, data: list[dict[str, object]]) -> None:
        self.data = data


class FakeTableQuery:
    def __init__(self, client: FakeSupabaseClient, table: str) -> None:
        self.client = client
        self.table = table
        self.operation = ""
        self.payload: object = None
        self.on_conflict: str | None = None

    def upsert(self, payload: object, on_conflict: str | None = None) -> FakeTableQuery:
        self.operation = "upsert"
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    def insert(self, payload: object) -> FakeTableQuery:
        self.operation = "insert"
        self.payload = payload
        return self

    def execute(self) -> FakeExecuteResponse:
        self.client.table_calls.append(
            {
                "table": self.table,
                "operation": self.operation,
                "payload": self.payload,
                "on_conflict": self.on_conflict,
            }
        )
        if self.table == "books":
            return FakeExecuteResponse([{"id": "book-123"}])
        return FakeExecuteResponse([])


class FakeBucket:
    def __init__(self, client: FakeSupabaseClient, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def upload(self, path: str, file: bytes, file_options: dict[str, str]) -> object:
        self.client.uploads.append(
            {
                "bucket": self.bucket,
                "path": path,
                "file": file,
                "file_options": file_options,
            }
        )
        return object()


class FakeStorage:
    def __init__(self, client: FakeSupabaseClient) -> None:
        self.client = client

    def from_(self, bucket: str) -> FakeBucket:
        return FakeBucket(self.client, bucket)


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.table_calls: list[dict[str, Any]] = []
        self.uploads: list[dict[str, Any]] = []
        self.storage = FakeStorage(self)

    def table(self, table: str) -> FakeTableQuery:
        return FakeTableQuery(self, table)


def test_store_conversion_in_supabase_upserts_rows_and_uploads_assets(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    write_epub(epub_path, ("chapters.xhtml#missing", "chapters.xhtml#c2"))
    conversion = convert_epub(epub_path, tmp_path / "out")
    client = FakeSupabaseClient()

    result = store_conversion_in_supabase(
        conversion,
        SupabaseStorageConfig(bucket="epub-assets"),
        client=client,
    )

    assert result.book_id == "book-123"
    assert result.uploaded_assets == [
        "books/book-123/assets/images/pixel.png",
        "books/book-123/assets/style.css",
    ]
    assert result.chapter_count == 2
    assert result.warning_count == 1

    book_call = client.table_calls[0]
    assert book_call["table"] == "books"
    assert book_call["operation"] == "upsert"
    assert book_call["on_conflict"] == "source_fingerprint"
    book_payload = cast("dict[str, Any]", book_call["payload"])
    assert book_payload["title"] == "Fixture Book"

    chapter_call = next(call for call in client.table_calls if call["table"] == "chapters")
    chapter_rows = chapter_call["payload"]
    assert isinstance(chapter_rows, list)
    chapter_rows = cast("list[dict[str, Any]]", chapter_rows)
    assert chapter_rows[0]["book_id"] == "book-123"
    assert chapter_rows[0]["markdown"].startswith("---")
    assert chapter_rows[0]["asset_root"] == "storage://epub-assets/books/book-123/assets"

    warning_call = next(call for call in client.table_calls if call["table"] == "conversion_warnings")
    warning_rows = warning_call["payload"]
    assert isinstance(warning_rows, list)
    warning_rows = cast("list[dict[str, Any]]", warning_rows)
    assert warning_rows[0]["code"] == "missing_anchor"

    assert client.uploads[0] == {
        "bucket": "epub-assets",
        "path": "books/book-123/assets/images/pixel.png",
        "file": PIXEL_PNG,
        "file_options": {"content-type": "image/png", "upsert": "true"},
    }
    assert client.uploads[1]["path"] == "books/book-123/assets/style.css"
    assert client.uploads[1]["file_options"] == {"content-type": "text/css", "upsert": "true"}


def test_cli_requires_supabase_url_key_and_bucket_together(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    write_epub(epub_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "supergene",
            "epub-to-md",
            str(epub_path),
            str(tmp_path / "out"),
            "--supabase-url",
            "https://example.supabase.co",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    assert "--supabase-url, --supabase-key, and --supabase-bucket must be provided together" in completed.stderr


def test_cli_rejects_postgres_connection_string_as_supabase_url(tmp_path: Path) -> None:
    epub_path = tmp_path / "fixture.epub"
    write_epub(epub_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "supergene",
            "epub-to-md",
            str(epub_path),
            str(tmp_path / "out"),
            "--supabase-url",
            "postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
            "--supabase-key",
            "secret",
            "--supabase-bucket",
            "epub-assets",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    assert "--supabase-url must be the HTTPS Supabase API URL" in completed.stderr
