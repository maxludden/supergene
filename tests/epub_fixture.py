from __future__ import annotations

import zipfile
from pathlib import Path


PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02"
    b"\xfeA\xe2&\xb9\x00\x00\x00\x00IEND\xaeB`\x82"
)


def write_epub(
    path: Path,
    toc_hrefs: tuple[str, ...] = ("chapters.xhtml#c1", "chapters.xhtml#c2"),
    *,
    split_documents: bool = False,
    include_profile_table: bool = False,
) -> None:
    """Write a small EPUB fixture for converter tests.

    Args:
        path: Destination EPUB path.
        toc_hrefs: Hrefs to include in the navigation document.
        split_documents: Whether chapters should be emitted as separate XHTML files.
        include_profile_table: Whether chapter two should include a status profile table.
    """
    manifest_documents = (
        '<item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>\n'
        '    <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>'
        if split_documents
        else '<item id="chapters" href="chapters.xhtml" media-type="application/xhtml+xml"/>'
    )
    spine_documents = (
        "    <itemref idref=\"chapter1\"/>\n    <itemref idref=\"chapter2\"/>"
        if split_documents
        else '    <itemref idref="chapters"/>'
    )
    labels = ["Chapter One", "Chapter Two"]
    toc_items = "\n".join(
        f'        <li><a href="{href}">{labels[index] if index < len(labels) else "Chapter Link"}</a></li>'
        for index, href in enumerate(toc_hrefs)
    )
    table_html = _chapter_table_html(include_profile_table)
    with zipfile.ZipFile(path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(
            mimetype,
            "application/epub+zip",
        )
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        zf.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:test:supergene</dc:identifier>
    <dc:title>Fixture Book</dc:title>
    <dc:creator>Max Example</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    {manifest_documents}
    <item id="pixel" href="images/pixel.png" media-type="image/png"/>
    <item id="style" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="nav"/>
{spine_documents}
  </spine>
</package>
""",
        )
        zf.writestr(
            "OEBPS/nav.xhtml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Navigation</title></head>
  <body>
    <nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">
      <ol>
{toc_items}
      </ol>
    </nav>
  </body>
</html>
""",
        )
        if split_documents:
            zf.writestr(
                "OEBPS/chapter1.xhtml",
                """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter One</title><link href="style.css" rel="stylesheet"/></head>
  <body>
    <section id="c1" class="chapter lead">
      <h1>Chapter 1: Chapter One</h1>
      <p class="opening">Hello <em>styled</em> world.</p>
      <p><img src="images/pixel.png" alt="Pixel" /></p>
    </section>
  </body>
</html>
""",
            )
            zf.writestr(
                "OEBPS/chapter2.xhtml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter Two</title><link href="style.css" rel="stylesheet"/></head>
  <body>
    <section id="c2" class="chapter">
      <h1>Chapter 2: Chapter Two</h1>
      <blockquote><p>A quoted line.</p></blockquote>
      {table_html}
    </section>
  </body>
</html>
""",
            )
        else:
            zf.writestr(
                "OEBPS/chapters.xhtml",
                f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapters</title><link href="style.css" rel="stylesheet"/></head>
  <body>
    <section id="c1" class="chapter lead">
      <h1>Chapter One</h1>
      <p class="opening">Hello <em>styled</em> world.</p>
      <p><img src="images/pixel.png" alt="Pixel" /></p>
    </section>
    <section id="c2" class="chapter">
      <h1>Chapter Two</h1>
      <blockquote><p>A quoted line.</p></blockquote>
      {table_html}
    </section>
  </body>
</html>
""",
            )
        zf.writestr("OEBPS/style.css", ".opening { font-style: italic; }")
        zf.writestr("OEBPS/images/pixel.png", PIXEL_PNG)


def _chapter_table_html(include_profile_table: bool) -> str:
    """Return the chapter two table HTML for the fixture.

    Args:
        include_profile_table: Whether to return a status profile table.

    Returns:
        XHTML table markup for the test EPUB.
    """
    if not include_profile_table:
        return "<table><tr><th>Name</th><th>Value</th></tr><tr><td>Gene</td><td>7</td></tr></table>"
    return (
        '<table class="profile-table"><tbody>'
        '<tr><th scope="row">Geno points gained</th>'
        '<td class="profile-value numeric-value">79 geno points; 8 sacred geno points</td></tr>'
        "</tbody></table>"
    )
