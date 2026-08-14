"""
Decides which processing path a document takes before Module 1/2 ever run.
Extension alone is unambiguous for everything except .pdf, which could be
either a scanned image with no text layer or a real text-native document.
"""
import cv2
import numpy as np
import pypdfium2 as pdfium

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
