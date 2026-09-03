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

Issue #323 -- also renders the resulting PDF's page 0 the exact same way
main.py's real /apply-redaction OCR-path branch does (file_routing.
render_pdf_all_pages), saving it into samples/_redaction_annotation/ so
measure_redaction_accuracy.py's real 108-image corpus (IMAGE_DIR reads a
pre-rendered PNG by filename, doesn't render PDFs itself) can actually
score this sample -- Payslip-scanned.pdf was a real #309 gap: added as a
new local sample, spot-verified once by hand, but carried zero automated
IoU-scored coverage. samples/ is gitignored (whole tree), so this
generated PNG can't be committed directly either -- same reason this
whole file exists instead of committing Payslip-scanned.pdf itself.
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


def make_scanned_pdf_ground_truth_image(pdf_path: str, png_path: str) -> None:
    import cv2

    from file_routing import render_pdf_all_pages

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pages = render_pdf_all_pages(pdf_bytes)
    cv2.imwrite(png_path, pages[0])


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "samples/en_pay_slip/Payslip.jpg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "samples/en_pay_slip/Payslip-scanned.pdf"
    make_scanned_pdf(src, dst)
    print(f"saved {dst}")

    gt_png = sys.argv[3] if len(sys.argv) > 3 else "samples/_redaction_annotation/Payslip-scanned_p0.png"
    make_scanned_pdf_ground_truth_image(dst, gt_png)
    print(f"saved {gt_png}")
