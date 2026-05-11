supergene
=========

`supergene` is a small CLI for unpacking EPUB3 ebook files.

Supabase Auth API
-----------------

The project also exposes a small FastAPI app with Supabase Auth:

```bash
cp .env.example .env
# fill in SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY
uv run uvicorn supergene.web:app --reload
```

Routes:

- `GET /health` is public.
- `POST /auth/login` accepts `{"email": "...", "password": "..."}` and returns a Supabase session.
- `GET /me` is protected. Call it with `Authorization: Bearer <access_token>`.

Use a Supabase publishable key in the app environment. Do not put a `service_role` or secret key in client-facing code.

Usage
-----

```bash
supergene path/to/book.epub
```

By default, the EPUB is extracted to a sibling directory named after the ebook:

```text
path/to/book/
```

To choose the destination directory:

```bash
supergene path/to/book.epub --output path/to/unpacked-book
```
