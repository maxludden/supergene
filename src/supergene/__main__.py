from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from supergene.converter import convert_epub
from supergene.supabase_store import SupabaseStorageConfig, store_conversion_in_supabase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="supergene")
    subparsers = parser.add_subparsers(dest="command", required=True)
    convert_parser = subparsers.add_parser("epub-to-md", help="Convert an EPUB into chapter Markdown files.")
    convert_parser.add_argument("epub_path", type=Path)
    convert_parser.add_argument("output_dir", type=Path)
    convert_parser.add_argument("--overwrite", action="store_true", help="Replace an existing book output directory.")
    convert_parser.add_argument("--supabase-url", help="Supabase project URL for storing converted output.")
    convert_parser.add_argument("--supabase-key", help="Supabase API key for storing converted output.")
    convert_parser.add_argument("--supabase-bucket", help="Supabase Storage bucket for EPUB assets.")

    args = parser.parse_args(argv)
    if args.command == "epub-to-md":
        if not args.epub_path.is_file() or args.epub_path.suffix.lower() != ".epub":
            parser.error("epub_path must be an .epub file, not a directory or project folder")
        supplied_supabase_args = [args.supabase_url, args.supabase_key, args.supabase_bucket]
        if any(supplied_supabase_args) and not all(supplied_supabase_args):
            parser.error("--supabase-url, --supabase-key, and --supabase-bucket must be provided together")
        if args.supabase_url and not _is_supabase_api_url(args.supabase_url):
            parser.error(
                "--supabase-url must be the HTTPS Supabase API URL, "
                "for example https://PROJECT_REF.supabase.co; do not use a postgresql:// database URL"
            )
        try:
            result = convert_epub(args.epub_path, args.output_dir, overwrite=args.overwrite)
            if args.supabase_url and args.supabase_key and args.supabase_bucket:
                store_result = store_conversion_in_supabase(
                    result,
                    SupabaseStorageConfig(bucket=args.supabase_bucket),
                    supabase_url=args.supabase_url,
                    supabase_key=args.supabase_key,
                )
                print(
                    f"Stored book {store_result.book_id} in Supabase "
                    f"({store_result.chapter_count} chapters, {len(store_result.uploaded_assets)} assets)",
                    file=sys.stderr,
                )
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {len(result.chapters)} chapters to {result.output_dir}", file=sys.stderr)
        for warning in result.warnings:
            print(f"warning[{warning.code}]: {warning.message}", file=sys.stderr)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _is_supabase_api_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and (parsed.hostname or "").endswith(".supabase.co")


if __name__ == "__main__":
    raise SystemExit(main())
