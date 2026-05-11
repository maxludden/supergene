from __future__ import annotations

import zipfile
from pathlib import Path


PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02"
    b"\xfeA\xe2&\xb9\x00\x00\x00\x00IEND\xaeB`\x82"
)


def write_epub(path: Path, toc_hrefs: tuple[str, str] = ("chapters.xhtml#c1", "chapters.xhtml#c2")) -> None:
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
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:test:supergene</dc:identifier>
    <dc:title>Fixture Book</dc:title>
    <dc:creator>Max Example</dc:creator>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapters" href="chapters.xhtml" media-type="application/xhtml+xml"/>
    <item id="pixel" href="images/pixel.png" media-type="image/png"/>
    <item id="style" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="nav"/>
    <itemref idref="chapters"/>
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
        <li><a href="{toc_hrefs[0]}">Chapter One</a></li>
        <li><a href="{toc_hrefs[1]}">Chapter Two</a></li>
      </ol>
    </nav>
  </body>
</html>
""",
        )
        zf.writestr(
            "OEBPS/chapters.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
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
      <table><tr><th>Name</th><th>Value</th></tr><tr><td>Gene</td><td>7</td></tr></table>
    </section>
  </body>
</html>
""",
        )
        zf.writestr("OEBPS/style.css", ".opening { font-style: italic; }")
        zf.writestr("OEBPS/images/pixel.png", PIXEL_PNG)
