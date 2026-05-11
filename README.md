# supergene

Utilities for turning EPUB ebooks into source-faithful, LLM-editable Markdown.

## EPUB to Markdown

From Python:

```python
from supergene import convert_epub

result = convert_epub("book.epub", "converted", overwrite=True)
print(result.output_dir)
```

From the command line:

```bash
supergene epub-to-md book.epub converted --overwrite
```

To also store the converted book in Supabase:

```bash
supergene epub-to-md book.epub converted --overwrite \
  --supabase-url "$SUPABASE_URL" \
  --supabase-key "$SUPABASE_KEY" \
  --supabase-bucket epub-assets
```

The converter writes one folder per book containing:

- `metadata.json` with extracted EPUB metadata
- `chapters/*.md` with rich YAML frontmatter and Markdown content
- `assets/*` with copied EPUB assets and rewritten chapter links
- `warnings.json` when the converter had to continue through uncertain EPUB structure

## Supabase Setup

Run `sql/supabase_schema.sql` against your Supabase database, then create a private Storage bucket named `epub-assets`.

The schema uses RLS and grants access to `service_role` only by default. Use a server-side key in your shell environment for CLI imports; do not expose that key in browser code.
