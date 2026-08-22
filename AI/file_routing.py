"""
Decides which processing path a document takes before Module 1/2 ever run.
Extension alone is unambiguous for everything except .pdf, which could be
either a scanned image with no text layer or a real text-native document.
"""
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
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        total = 0
        for page in pdf:
            text = page.get_textpage().get_text_range()
            total += len(text.strip())
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
        except pdfium.PdfiumError as e:
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
    try:
        bitmap = pdf[0].render(scale=scale)
        pil_image = bitmap.to_pil()
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    finally:
        pdf.close()


def convert_docx_to_pdf_bytes(docx_bytes: bytes, timeout: float = 60.0) -> bytes:
    """Issue #208 -- lets a docx reuse render_pdf_first_page and
    resolve_item_boxes_via_pdf_text unchanged, by converting it to a PDF
    first (same mechanism measure_accuracy_image.py's docx_to_pngs already
    proved out, minus the multi-page loop -- this pipeline only ever
    redacts page 1, same simplification render_pdf_first_page already
    makes). A unique -env:UserInstallation profile directory per call is
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


def resolve_item_boxes_via_pdf_text(pdf_bytes: bytes, items: list[dict]) -> list[dict]:
    """Issue #208 -- a text-native document's redaction.items are spans
    (character offsets into extracted text, see pipeline.py's
    _run_text_native_path), not pixel boxes -- there was never a rendered
    page for them to be boxes against until now. An item that already has
    x_pct (the OCR/scanned-PDF shape, #207) is passed through unchanged.
    An item without one is resolved by searching its `value` string
    directly in THIS SAME rendered page's own text layer -- avoids ever
    having to align two independent text-extraction passes (python-docx's
    vs pdfium's own), which is a real, separate risk this sidesteps rather
    than solves.

    An item whose value isn't found in the text layer is dropped, not
    guessed at -- same accepted "skip, don't fabricate a box" pattern
    module3_redaction.find_sensitive_boxes already uses when a match has
    no overlapping OCR word box. A real, confirmed cause: some balance-
    sheet templates' table cells are narrow enough that LibreOffice's own
    docx->pdf conversion wraps a value like "$140,000" across two lines,
    splitting it in the text layer -- a rendering-fidelity limitation of
    the conversion step itself, not something to special-case here (see
    #208's own issue history). SENSITIVE_FIELD_KEYS still strips the
    field from aiResult.fields regardless of whether its box resolves."""
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        page = pdf[0]
        page_w, page_h = page.get_size()
        tp = page.get_textpage()
        resolved = []
        for item in items:
            if "x_pct" in item:
                resolved.append(item)
                continue
            value = str(item.get("value") or "")
            if not value:
                continue
            match = tp.search(value, index=0).get_next()
            if match is None:
                continue
            start, count = match
            n_rects = tp.count_rects(start, count)
            if n_rects == 0:
                continue
            rects = [tp.get_rect(i) for i in range(n_rects)]
            left = min(r[0] for r in rects)
            bottom = min(r[1] for r in rects)
            right = max(r[2] for r in rects)
            top = max(r[3] for r in rects)
            resolved.append(
                {
                    **item,
                    "x_pct": left / page_w,
                    "y_pct": 1 - (top / page_h),
                    "w_pct": (right - left) / page_w,
                    "h_pct": (top - bottom) / page_h,
                }
            )
        return resolved
    finally:
        pdf.close()
