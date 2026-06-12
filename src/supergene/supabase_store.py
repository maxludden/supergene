"""Store converted Super Gene books, chapters, warnings, and assets in Supabase."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from loguru import logger

from supergene.converter import ConversionResult
from os import getenv
from dotenv import load_dotenv


@dataclass(frozen=True)
class SupabaseStorageConfig:
    """Supabase Storage target for converted EPUB assets.

        Attributes:
            bucket: Storage bucket name.
            asset_prefix: Optional prefix prepended to uploaded asset paths.
        """

    bucket: str
    asset_prefix: str = "books"
    upsert_assets: bool = True
    row_batch_size: int = 100


@dataclass(frozen=True)
class SupabaseStoreResult:
    """Summary of rows and files stored in Supabase.

        Attributes:
            book_id: Deterministic ID assigned to the stored book.
            chapter_count: Number of chapter rows upserted.
            warning_count: Number of warning rows inserted.
            uploaded_assets: Storage object paths uploaded for assets.
        """

    book_id: str
    chapter_count: int
    warning_count: int
    uploaded_assets: list[str]


def store_conversion_in_supabase(
    conversion: ConversionResult,
    config: SupabaseStorageConfig,
    *,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
    client: Any | None = None,
) -> SupabaseStoreResult:
    """Store converted EPUB metadata/content in Postgres and assets in Storage."""
    logger.trace(f"Starting Supabase store for {conversion.output_dir}")
    if client is None:
        if not supabase_url or not supabase_key:
            try: 
                # Environment values keep CLI usage light while still allowing
                # tests and callers to inject explicit credentials or a fake.
                load_dotenv()
                supabase_url = getenv("SUPABASE_URL")
                supabase_key = getenv("SUPABASE_KEY")
            except:
                raise ValueError("supabase_url and supabase_key are required when client is not provided")
        from supabase import create_client
        assert supabase_url and supabase_key
        client = create_client(supabase_url, supabase_key)

    source_fingerprint = _source_fingerprint(conversion)
    book_payload = {
        "source_fingerprint": source_fingerprint,
        "title": conversion.metadata.title,
        "creators": conversion.metadata.creators,
        "language": conversion.metadata.language,
        "identifiers": conversion.metadata.identifiers,
        "local_output_path": str(conversion.output_dir),
    }
    book_response = client.table("books").upsert(book_payload, on_conflict="source_fingerprint").execute()
    if not getattr(book_response, "data", None):
        raise RuntimeError("Supabase did not return a book row")
    # The Supabase client returns dynamic JSON-like data; cast after the runtime
    # existence check so static typing stays honest without changing behavior.
    book_rows = cast("list[dict[str, Any]]", book_response.data)
    book_id = str(book_rows[0]["id"])
    logger.trace(f"Upserted Supabase book row {book_id}")

    asset_root = f"{config.asset_prefix.strip('/')}/{book_id}/assets"
    uploaded_assets = _upload_assets(client, config, conversion.output_dir / "assets", asset_root)
    logger.trace(f"Uploaded {len(uploaded_assets)} assets to bucket {config.bucket}")

    chapter_rows = []
    for chapter in conversion.chapters:
        markdown = chapter.output_path.read_text(encoding="utf-8")
        chapter_rows.append(
            {
                "book_id": book_id,
                "chapter_index": chapter.index,
                "title": chapter.title,
                "toc_depth": chapter.depth,
                "source_href": chapter.source_href,
                # Markdown output uses local relative asset links. Replace those
                # with storage URIs so stored chapter content remains portable.
                "markdown": markdown.replace("../assets", f"storage://{config.bucket}/{asset_root}"),
                "local_path": str(chapter.output_path),
                "asset_root": f"storage://{config.bucket}/{asset_root}",
            }
        )
    for batch in _batches(chapter_rows, config.row_batch_size):
        client.table("chapters").upsert(batch, on_conflict="book_id,chapter_index").execute()
        logger.trace(f"Upserted {len(batch)} chapter rows for book {book_id}")

    warning_rows = [
        {
            "book_id": book_id,
            "code": warning.code,
            "message": warning.message,
            "source_href": warning.source_href,
        }
        for warning in conversion.warnings
    ]
    for batch in _batches(warning_rows, config.row_batch_size):
        client.table("conversion_warnings").insert(batch).execute()
        logger.trace(f"Inserted {len(batch)} warning rows for book {book_id}")

    logger.trace(f"Finished Supabase store for book {book_id}")
    return SupabaseStoreResult(
        book_id=book_id,
        chapter_count=len(chapter_rows),
        warning_count=len(warning_rows),
        uploaded_assets=uploaded_assets,
    )


def _upload_assets(client: Any, config: SupabaseStorageConfig, assets_dir: Path, asset_root: str) -> list[str]:
    """Upload converted asset files into Supabase Storage."""
    logger.trace("Entering _upload_assets")
    if not assets_dir.exists():
        return []

    uploaded: list[str] = []
    bucket = client.storage.from_(config.bucket)
    for path in sorted(item for item in assets_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(assets_dir).as_posix()
        storage_path = f"{asset_root}/{relative}"
        # Supabase Storage benefits from explicit MIME metadata for EPUB assets,
        # but unknown extensions should still upload as binary.
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        bucket.upload(
            storage_path,
            path.read_bytes(),
            {"content-type": content_type, "upsert": "true" if config.upsert_assets else "false"},
        )
        uploaded.append(storage_path)
    return uploaded


def _batches(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    """Split rows into fixed-size batches for Supabase writes."""
    logger.trace("Entering _batches")
    batch_size = max(1, size)
    return [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]


def _source_fingerprint(conversion: ConversionResult) -> str:
    """Build a deterministic fingerprint for a converted book."""
    logger.trace("Entering _source_fingerprint")
    digest = hashlib.sha256()
    digest.update(conversion.metadata.title.encode("utf-8"))
    for identifier in conversion.metadata.identifiers:
        digest.update(b"\0")
        digest.update(identifier.encode("utf-8"))
    for chapter in conversion.chapters:
        digest.update(b"\0")
        # Include both original hrefs and generated Markdown bytes; this changes
        # when chapter ordering/content changes but stays independent of local
        # output directory paths.
        digest.update(chapter.source_href.encode("utf-8"))
        digest.update(chapter.output_path.read_bytes())
    return digest.hexdigest()
