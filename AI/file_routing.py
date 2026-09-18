"""
Decides which processing path a document takes before Module 1/2 ever run.
Extension alone is unambiguous for everything except .pdf, which could be
either a scanned image with no text layer or a real text-native document.
"""
import bisect
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

# Same env-var-override-with-OS-default pattern module2_ocr_tesseract.py
# already uses for TESSERACT_CMD -- apt's libreoffice-writer package (see
# Dockerfile) puts `soffice` on PATH in the deployed container, but
# Windows needs the full install path.
_SOFFICE_BIN = os.environ.get(
    "SOFFICE_BIN", r"C:\Program Files\LibreOffice\program\soffice.exe" if os.name == "nt" else "soffice"
)

# Real text-native documents (contracts, balance sheets) run to thousands
# of characters; a genuinely scanned PDF with no text layer extracts to
# zero or near-zero. Deliberately low, safe cutoff -- see
# docs/superpowers/specs/2026-08-10-process-endpoint-design.md Decision 3.
SCANNED_PDF_TEXT_THRESHOLD = 50

_OCR_EXTENSIONS = {"png", "jpg", "jpeg"}
_TEXT_NATIVE_EXTENSIONS = {"docx", "csv"}


def _extension(filename: str) -> str:
    parts = filename.lower().rsplit(".", 1)
    return parts[1] if len(parts) == 2 else ""


def _pdf_text_length(pdf_bytes: bytes) -> int:
    # ponytail: close each page/textpage explicitly, not just the parent
    # PdfDocument -- module2_text_extraction.extract_text_from_pdf already
    # hit the real consequence of skipping this (a native file handle held
    # open until GC, blocking os.unlink() on Windows with WinError 32).
    # Applying the same pattern here for consistency.
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        total = 0
        for page in pdf:
            textpage = page.get_textpage()
            total += len(textpage.get_text_range().strip())
            textpage.close()
            page.close()
        return total
    finally:
        pdf.close()


def detect_processing_path(filename: str, file_bytes: bytes) -> str:
    ext = _extension(filename)
    if ext in _OCR_EXTENSIONS:
        return "ocr"
    if ext in _TEXT_NATIVE_EXTENSIONS:
        return "text_native"
    if ext == "pdf":
        try:
            text_length = _pdf_text_length(file_bytes)
        except Exception as e:
            # Real, confirmed bug: this only caught pdfium.PdfiumError, but
            # a malformed PDF can make the underlying native library raise
            # other exception types too. Anything not caught here escaped
            # detect_processing_path uncaught, past pipeline.py's own
            # `except ValueError`, and out of process_document entirely --
            # a raw unhandled 500 instead of this app's own structured
            # {"error": ...} contract every other failure path maintains.
            raise ValueError(f"malformed or unreadable PDF: {e}") from e
        return "ocr" if text_length < SCANNED_PDF_TEXT_THRESHOLD else "text_native"
    raise ValueError(f"unsupported file extension: {ext!r}")


def render_pdf_first_page(pdf_bytes: bytes, scale: float = 3.5) -> np.ndarray:
    """First page only -- see design doc Decision 4 for the documented
    multi-page simplification. Same render mechanism
    measure_accuracy_image.py's docx_to_png already uses (pypdfium2
    page.render), minus the docx->pdf conversion step since the input
    here is already a PDF."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[0]
    try:
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    finally:
        page.close()
        pdf.close()


def render_pdf_all_pages(pdf_bytes: bytes, scale: float = 3.5) -> list[np.ndarray]:
    """Issue #283 -- renders every page, not just the first. A real
    multi-page text-native document's sensitive content isn't guaranteed
    to be on page 1 (confirmed: Pay-slip-template-sts-FILLED-*.docx's real
    filled fields sit on page 3, pages 1-2 are the Fair Work template's
    own fixed instructional text) -- render_pdf_first_page alone means the
    redacted-preview endpoint would render/search a page that was never
    the one with anything sensitive on it."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        images = []
        for page in pdf:
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            images.append(cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR))
            page.close()
        return images
    finally:
        pdf.close()


def stack_pages_vertically(images: list[np.ndarray]) -> np.ndarray:
    """Issue #283 -- combines multiple rendered pages into one composite
    image (top to bottom, left-aligned) so the redacted-preview endpoint's
    existing single-PNG response contract doesn't need to change to
    support multi-page documents. Pages narrower than the widest one are
    padded white on the right -- real PDFs from one source document
    normally share a single page size, so this rarely actually triggers,
    but a mismatched width would otherwise silently misalign
    resolve_item_boxes_via_pdf_text's x_pct math against this image.

    Issue #286 -- padding shape must match each image's own dimensionality,
    not assume 3-channel BGR. This function is also reused for
    module1_opencv.enhance() output on the OCR path, which is single-
    channel grayscale (enhance() never converts back to BGR) -- a
    hardcoded 3-channel pad would raise on any two differently-sized
    grayscale pages via np.hstack's shape mismatch."""
    max_w = max(img.shape[1] for img in images)
    rows = []
    for img in images:
        h, w = img.shape[:2]
        if w < max_w:
            pad_shape = (h, max_w - w) if img.ndim == 2 else (h, max_w - w, img.shape[2])
            pad = np.full(pad_shape, 255, dtype=img.dtype)
            img = np.hstack([img, pad])
        rows.append(img)
    return np.vstack(rows)


def convert_docx_to_pdf_bytes(docx_bytes: bytes, timeout: float = 60.0) -> bytes:
    """Issue #208 -- lets a docx reuse render_pdf_all_pages/
    render_pdf_first_page and resolve_item_boxes_via_pdf_text unchanged, by
    converting it to a PDF first (same mechanism measure_accuracy_image.py's
    docx_to_pngs already proved out). Issue #283 -- main.py's caller renders
    every page for a text-native item's span, not just page 1 (see
    render_pdf_all_pages's own docstring); this function only handles the
    docx->pdf conversion step, the multi-page-vs-first-page choice is the
    caller's. A unique -env:UserInstallation profile directory per call is
    required, not optional -- concurrent soffice invocations sharing the
    default profile lock each other out under real concurrent requests,
    not just a hypothetical race. Must be a proper file:// URI
    (Path.as_uri(), not a hand-built f"file://{path}") -- on Windows a
    hand-built one misparses the drive letter as a hostname, which breaks
    soffice's own profile writes and surfaces as an opaque "libpng error:
    Write Error", confirmed by direct testing.

    No "undecodable docx" test exists for this function deliberately --
    tried it (arbitrary short byte string named .docx) and LibreOffice's
    own format autodetection is lenient enough to parse it as plain text
    and successfully render a real page anyway, confirmed by direct
    testing. The undecodable-input failure path is proven instead via the
    PDF case (test_apply_redaction_undecodable_pdf_is_422), which shares
    the exact same except-Exception-here-raises-422 handling in main.py."""
    with tempfile.TemporaryDirectory() as out_dir, tempfile.TemporaryDirectory() as profile_dir:
        docx_path = Path(out_dir) / f"{uuid.uuid4().hex}.docx"
        docx_path.write_bytes(docx_bytes)
        subprocess.run(
            [
                _SOFFICE_BIN,
                "--headless",
                "--invisible",
                "--nologo",
                "--nofirststartwizard",
                "--norestore",
                f"-env:UserInstallation={Path(profile_dir).as_uri()}",
                "--convert-to", "pdf",
                "--outdir", out_dir,
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=timeout,
        )
        return docx_path.with_suffix(".pdf").read_bytes()


def _find_dewrapped_span(tp, value: str, start: int = 0) -> tuple[int, int] | None:
    """Issue #327 -- fallback for resolve_item_boxes_via_pdf_text's exact
    tp.search() when a value's own literal characters got split by a real
    \\r\\n line-wrap inside the PDF's text layer (LibreOffice wrapping a
    narrow table-cell value). Builds a \\r/\\n-stripped copy of the page's
    full text alongside a same-length index map (dewrapped position ->
    original tp character index), searches for `value` in the dewrapped
    copy via plain substring search, then translates a match's [start,
    end) back into the ORIGINAL character range tp.count_rects/get_rect
    require -- those operate on tp's own unstripped character indices,
    not the dewrapped string's positions.

    `start` is an ORIGINAL (tp-space) character index to resume from --
    real, confirmed bug fixed here: this used to always search from
    position 0, so when the SAME value appeared twice on a page and BOTH
    occurrences were wrapped, only the first was ever found (the caller
    only invoked this on a genuinely-first search, never on a resumed
    one). Converted to dewrapped-space via bisect on index_map before
    searching, since `start` arrives in the original, unstripped space."""
    raw = tp.get_text_range()
    dewrapped_chars = []
    index_map = []
    for i, ch in enumerate(raw):
        if ch in "\r\n":
            continue
        dewrapped_chars.append(ch)
        index_map.append(i)
    dewrapped = "".join(dewrapped_chars)

    dewrapped_start = bisect.bisect_left(index_map, start)
    pos = dewrapped.find(value, dewrapped_start)
    if pos == -1:
        return None
    end_pos = pos + len(value) - 1
    orig_start = index_map[pos]
    orig_end = index_map[end_pos]
    return orig_start, orig_end - orig_start + 1


def resolve_item_boxes_via_pdf_text(pdf_bytes: bytes, items: list[dict]) -> list[dict]:
    """Issue #208 -- a text-native document's redaction.items are spans
    (character offsets into extracted text, see pipeline.py's
    _run_text_native_path), not pixel boxes -- there was never a rendered
    page for them to be boxes against until now. An item that already has
    x_pct (the OCR/scanned-PDF shape, #207) is passed through unchanged.
    An item without one is resolved by searching its `value` string
    directly in the rendered document's own text layer -- avoids ever
    having to align two independent text-extraction passes (python-docx's
    vs pdfium's own), which is a real, separate risk this sidesteps rather
    than solves.

    Issue #283 -- searches EVERY page, not just page 0 (a real, confirmed
    case: a multi-page docx's actual sensitive content can sit on page 3
    while page 1 is fixed template boilerplate -- searching only page 0
    meant those values were never found, never redacted, silently). The
    matched box is converted into stack_pages_vertically's composite
    coordinate space using each page's own get_size() (PDF points, not
    rendered pixels) to compute the cumulative vertical offset -- render
    scale is constant across pages, so the ratio is identical either way,
    and this avoids coupling box resolution to an actual render call. For
    a single-page document this reduces to exactly the pre-#283 math
    (offset 0, composite width/height == the one page's own) --
    deliberately verified so existing single-page callers see no change.

    An item whose value isn't found in the text layer is dropped, not
    guessed at -- same accepted "skip, don't fabricate a box" pattern
    module3_redaction.find_sensitive_boxes already uses when a match has
    no overlapping OCR word box. SENSITIVE_FIELD_KEYS still strips the
    field from aiResult.fields regardless of whether its box resolves.

    Issue #327 -- a docx upload's own value (extracted via python-docx's
    clean cell text at upload time, e.g. "$92,000", no internal
    whitespace) can fail to literally match here even though it's really
    on the page: LibreOffice's OWN docx->pdf conversion (this function
    always searches a FRESH re-conversion, not the bytes extraction ran
    against) wraps a narrow table cell's value across the PDF's own text
    layer -- confirmed real via a direct raw-text dump: "$92,000" appears
    as "$92,\r\n000", literal \r\n mid-number. tp.search() is a literal,
    non-fuzzy substring search, so it can never match across that break.
    Confirmed real and reproduced twice independently: 0/5 real balance-
    sheet totals resolved on a real multi-page docx-derived PDF before
    this fix. _find_dewrapped_span falls back to searching a \r\n-
    stripped copy of the page's own text (offset-mapped back to the
    original character indices count_rects/get_rect need) only when the
    exact literal search above finds nothing -- the common, unaffected
    case (confirmed real: 8/9 real non-tabular payslip fields on the
    same conversion path) pays no extra cost. Strips ONLY \r/\n, not all
    whitespace -- real inter-word spaces are the genuine separators
    between adjacent values/words in the source content, and stripping
    them too would risk gluing two unrelated real values together into a
    false-positive match."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        sizes = [page.get_size() for page in pdf]
        total_h = sum(h for _, h in sizes)
        max_w = max(w for w, _ in sizes)
        offsets = []
        acc = 0.0
        for _, h in sizes:
            offsets.append(acc)
            acc += h

        resolved = []
        # Issue #347 -- two items can carry the identical value string (a
        # real, confirmed shape: SALARY_RE-truncated fragments collide far
        # more than full values, but even a full value can genuinely repeat
        # across rows/years on a real balance sheet). Searching from
        # index=0 every time made every item sharing a value resolve to
        # the SAME first occurrence -- every other real occurrence in the
        # document was left completely unredacted, not just imprecisely
        # boxed. Track the next search start per (page, value) so each
        # subsequent item with the same value continues past the last
        # match found for it on that page, landing on the next distinct
        # occurrence instead of re-finding the first one.
        next_start: dict[tuple[int, str], int] = {}
        for item in items:
            if "x_pct" in item:
                resolved.append(item)
                continue
            value = str(item.get("value") or "")
            if not value:
                continue
            match_box = None
            for page_index, page in enumerate(pdf):
                # ponytail: close page/textpage before the next iteration
                # (continue or break) -- this loop re-enumerates every page
                # for every item, so an unclosed tp/page here compounds
                # fast on a multi-item, multi-page document. Same class of
                # native-resource leak module2_text_extraction.py's own
                # comment documents as real (WinError 32 on Windows).
                try:
                    page_w, page_h = sizes[page_index]
                    tp = page.get_textpage()
                    try:
                        start_index = next_start.get((page_index, value), 0)
                        match = tp.search(value, index=start_index).get_next()
                        if match is None:
                            # Issue #327 -- exact search found nothing from
                            # start_index onward; try the \r\n-dewrapped
                            # fallback, resumed from the same start_index,
                            # before moving to the next page. Real,
                            # confirmed bug fixed here: this used to only
                            # run when start_index == 0 (a genuinely
                            # first-ever search), so a SECOND occurrence of
                            # a value that was ITSELF wrapped could never
                            # be found -- the exact search from a nonzero
                            # start_index always failed on a still-wrapped
                            # occurrence, and the dewrap retry was skipped
                            # entirely on the assumption this page's
                            # occurrences were already exhausted.
                            match = _find_dewrapped_span(tp, value, start=start_index)
                            if match is None:
                                continue
                        start, count = match
                        next_start[(page_index, value)] = start + count
                        n_rects = tp.count_rects(start, count)
                        if n_rects == 0:
                            continue
                        rects = [tp.get_rect(i) for i in range(n_rects)]
                        left = min(r[0] for r in rects)
                        bottom = min(r[1] for r in rects)
                        right = max(r[2] for r in rects)
                        top = max(r[3] for r in rects)
                        match_box = (page_index, page_w, page_h, left, bottom, right, top)
                        break
                    finally:
                        tp.close()
                finally:
                    page.close()
            if match_box is None:
                continue
            page_index, page_w, page_h, left, bottom, right, top = match_box
            offset = offsets[page_index]
            resolved.append(
                {
                    **item,
                    "x_pct": left / max_w,
                    "y_pct": (offset + (page_h - top)) / total_h,
                    "w_pct": (right - left) / max_w,
                    "h_pct": (top - bottom) / total_h,
                }
            )
        return resolved
    finally:
        pdf.close()


if __name__ == "__main__":
    # reportlab is a one-off dev-tool dependency for these self-checks
    # only (imported inside this guard, never at module load time, so
    # production's own import chain never needs it) -- same precedent
    # _make_scanned_pdf_sample.py already established this session, and
    # confirmed already available in this venv from that work.
    import tempfile

    from reportlab.pdfgen import canvas

    def _build_pdf(lines: list[tuple[int, int, str]]) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        c = canvas.Canvas(path, pagesize=(300, 200))
        for x, y, text in lines:
            c.drawString(x, y, text)
        c.save()
        with open(path, "rb") as f:
            return f.read()

    def test_resolve_finds_value_on_a_single_line():
        pdf_bytes = _build_pdf([(20, 150, "Total $92,000 value")])
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, [{"field": "total_current_assets", "value": "$92,000"}])
        assert len(resolved) == 1
        assert "x_pct" in resolved[0]

    def test_resolve_falls_back_to_dewrapped_search_when_value_wraps():
        # Issue #327 -- real confirmed artifact: pdfium inserts a literal
        # \r\n between two visually-separate drawString calls, same as
        # LibreOffice's own docx->pdf conversion wrapping a narrow table
        # cell's value mid-number (confirmed via a direct raw-text dump
        # on a real converted document). Two-line layout here reproduces
        # that exact shape (verified: pdfium reads this back as
        # "Total $92,\r\n000 value").
        pdf_bytes = _build_pdf([(20, 150, "Total $92,"), (20, 130, "000 value")])
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, [{"field": "total_current_assets", "value": "$92,000"}])
        assert len(resolved) == 1
        assert "x_pct" in resolved[0]

    def test_resolve_drops_item_when_value_genuinely_absent():
        pdf_bytes = _build_pdf([(20, 150, "Nothing relevant here")])
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, [{"field": "total_assets", "value": "$92,000"}])
        assert resolved == []

    def test_resolve_passes_through_items_that_already_have_x_pct():
        pdf_bytes = _build_pdf([(20, 150, "irrelevant")])
        item = {"field": "bsb", "value": "123-456", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1}
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, [item])
        assert resolved == [item]

    def test_resolve_gives_each_duplicate_value_its_own_distinct_box():
        # Issue #347 -- confirmed real on Balance-sheet-template-FILLED-
        # 300.pdf: several distinct real dollar figures (different table
        # rows/years) happen to share the identical printed string (e.g.
        # "$74" after SALARY_RE truncation, but the same collision can
        # happen with full untruncated values too -- a real balance sheet
        # can genuinely repeat a figure across years/rows). Each call here
        # always searched from index=0 with no memory of a prior match, so
        # every item sharing a value collapsed onto the SAME first
        # occurrence -- every other real occurrence in the document was
        # left completely unredacted, not just imprecisely boxed.
        pdf_bytes = _build_pdf([(20, 150, "$74,000"), (20, 100, "$74,000")])
        items = [
            {"field": "total_assets", "value": "$74,000"},
            {"field": "total_liabilities", "value": "$74,000"},
        ]
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, items)
        assert len(resolved) == 2
        positions = {(r["x_pct"], r["y_pct"]) for r in resolved}
        assert len(positions) == 2, "both real occurrences must get their own distinct box"

    def test_resolve_finds_second_occurrence_when_both_are_wrapped():
        # Real, confirmed bug: when the same value appears twice on a page
        # and BOTH occurrences are line-wrapped, only the first was ever
        # found -- the dewrap retry used to only run on a genuinely
        # first-ever search (start_index == 0), so the exact search's
        # failure on the second occurrence (still wrapped, so it can never
        # match literally) fell into the "already exhausted" branch and
        # skipped the dewrap retry entirely, silently dropping a real,
        # repeated, sensitive dollar figure from redaction.
        pdf_bytes = _build_pdf([
            (20, 170, "$74,"), (20, 150, "000"),
            (20, 110, "$74,"), (20, 90, "000"),
        ])
        items = [
            {"field": "total_assets", "value": "$74,000"},
            {"field": "total_liabilities", "value": "$74,000"},
        ]
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, items)
        assert len(resolved) == 2, "both wrapped occurrences must resolve, not just the first"
        positions = {(r["x_pct"], r["y_pct"]) for r in resolved}
        assert len(positions) == 2, "each wrapped occurrence must get its own distinct box"

    def test_resolve_drops_extra_duplicate_item_once_occurrences_exhausted():
        # Same cursor-tracking mechanism, opposite edge: only ONE real
        # occurrence exists but TWO items request it (e.g. a genuine
        # duplicate span from an upstream matching bug) -- the second must
        # be dropped (matches the existing "not found -> drop" contract),
        # never silently reuse the first occurrence's box a second time.
        pdf_bytes = _build_pdf([(20, 150, "$74,000")])
        items = [
            {"field": "total_assets", "value": "$74,000"},
            {"field": "total_liabilities", "value": "$74,000"},
        ]
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, items)
        assert len(resolved) == 1

    tests = [
        test_resolve_finds_value_on_a_single_line,
        test_resolve_falls_back_to_dewrapped_search_when_value_wraps,
        test_resolve_drops_item_when_value_genuinely_absent,
        test_resolve_passes_through_items_that_already_have_x_pct,
        test_resolve_gives_each_duplicate_value_its_own_distinct_box,
        test_resolve_finds_second_occurrence_when_both_are_wrapped,
        test_resolve_drops_extra_duplicate_item_once_occurrences_exhausted,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
