"""
Issue #309 -- builds a real scanned-PDF sample: wraps an already-real
photographed image in a PDF container with no text layer, so
file_routing.detect_processing_path's ext=="pdf" branch (checks
_pdf_text_length against SCANNED_PDF_TEXT_THRESHOLD) actually gets
exercised by something real, not just the blank text-native PDF
templates already in the corpus. samples/en_pay_slip/Payslip.jpg is
reused as-is -- no synthetic scan-artifact simulation needed, it's
already a real photographed document, same image already used elsewhere
this session (#306) -- just wrapped through the PDF-container path
instead of the direct .jpg upload path.

Not part of production's import chain (main.py/pipeline.py never generate
PDFs, only consume them) -- reportlab is a one-off dev-tool dependency
here, same as _fill_templates.py already using `faker` without either
being in requirements.txt (that file's own header scopes it to main.py's
production import chain only).
"""

import sys

from PIL import Image
from reportlab.pdfgen import canvas


def make_scanned_pdf(image_path: str, pdf_path: str) -> None:
    img = Image.open(image_path)
    w, h = img.size
    c = canvas.Canvas(pdf_path, pagesize=(w, h))
    c.drawImage(image_path, 0, 0, width=w, height=h)
    c.save()


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "samples/en_pay_slip/Payslip.jpg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "samples/en_pay_slip/Payslip-scanned.pdf"
    make_scanned_pdf(src, dst)
    print(f"saved {dst}")
