"""pdf_pages.py — shared PDF page counting for Typst-compiled derivations.

`report.typ` AND `slides.typ` both compile through `typst-py` to a PDF;
counting distinct `/Type /Page` objects directly in the bytes is robust to
`/Pages` tree key ordering and applies identically to both templates — one
implementation, not a copy per capability (`pdf.py::compile_report`,
`slides.py::compile_slides`).
"""

from __future__ import annotations

import re

# Individual page objects, e.g. `/Type/Page/Resources ...` — the negative
# lookahead excludes `/Type/Pages` (the page TREE node) and other siblings
# like `/Type/PageLabel` (any letter right after "Page" disqualifies it, not
# just "s" — a `/PageLabel` object matched a naive `(?!s)` lookahead and
# silently double-counted pages until this was caught against a real render).
_PAGE_OBJECT_RE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """Count `/Type /Page` objects (the individual pages, never the `/Pages`
    tree node) directly in the PDF bytes — robust to key ordering inside the
    `/Pages` dict (no dependency on `/Count` appearing right after
    `/Type /Pages`, which may have `/Kids` or other keys interleaved)."""
    return len(_PAGE_OBJECT_RE.findall(pdf_bytes))
