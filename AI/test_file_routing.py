import sys
from unittest.mock import patch

import numpy as np

sys.path.insert(0, ".")

from file_routing import (
    detect_processing_path,
    render_pdf_all_pages,
    render_pdf_first_page,
    stack_pages_vertically,
)

with open("samples/en_balance_sheet/IC-Small-Business-Balance-Sheet-Example-11260_PDF.pdf", "rb") as f:
    _TEXT_NATIVE_PDF_BYTES = f.read()


def test_image_extensions_route_to_ocr():
    assert detect_processing_path("photo.png", b"irrelevant") == "ocr"
    assert detect_processing_path("photo.JPG", b"irrelevant") == "ocr"
    assert detect_processing_path("photo.jpeg", b"irrelevant") == "ocr"


def test_docx_and_csv_route_to_text_native():
    assert detect_processing_path("contract.docx", b"irrelevant") == "text_native"
    assert detect_processing_path("data.csv", b"irrelevant") == "text_native"


def test_pdf_with_little_text_routes_to_ocr():
    with patch("file_routing._pdf_text_length", return_value=10):
        assert detect_processing_path("scan.pdf", b"irrelevant") == "ocr"


def test_pdf_with_much_text_routes_to_text_native():
    with patch("file_routing._pdf_text_length", return_value=500):
        assert detect_processing_path("report.pdf", b"irrelevant") == "text_native"


def test_real_text_native_pdf_sample():
    # IC-Small-Business-Balance-Sheet-Example-11260_PDF.pdf is a real
    # Australian balance sheet template, ~1702 chars of extracted text --
    # well above the 50-char scanned threshold.
    assert detect_processing_path("report.pdf", _TEXT_NATIVE_PDF_BYTES) == "text_native"


def test_unsupported_extension_raises():
    try:
        detect_processing_path("notes.txt", b"irrelevant")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_malformed_pdf_raises_value_error():
    # A .pdf extension with content pdfium can't actually parse (e.g. a
    # truncated/corrupt upload) must surface as ValueError -- same shape
    # as the unsupported-extension case -- not an unhandled PdfiumError
    # that would 500 the /process endpoint (#153).
    try:
        detect_processing_path("broken.pdf", b"%PDF-1.4\n%%EOF")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_render_pdf_first_page_returns_bgr_array():
    image = render_pdf_first_page(_TEXT_NATIVE_PDF_BYTES)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.dtype.name == "uint8"


def test_render_pdf_all_pages_renders_every_page():
    # Issue #283 -- _TEXT_NATIVE_PDF_BYTES has 3 real pages; the pre-#283
    # render_pdf_first_page only ever returned 1.
    images = render_pdf_all_pages(_TEXT_NATIVE_PDF_BYTES)
    assert len(images) == 3
    for image in images:
        assert image.ndim == 3
        assert image.shape[2] == 3


def test_stack_pages_vertically_combines_all_pages_top_to_bottom():
    images = render_pdf_all_pages(_TEXT_NATIVE_PDF_BYTES)
    composite = stack_pages_vertically(images)
    assert composite.shape[1] == max(img.shape[1] for img in images)
    assert composite.shape[0] == sum(img.shape[0] for img in images)


def test_stack_pages_vertically_pads_narrower_pages():
    tall_narrow = np.zeros((10, 5, 3), dtype=np.uint8)
    short_wide = np.full((4, 8, 3), 255, dtype=np.uint8)
    composite = stack_pages_vertically([tall_narrow, short_wide])
    assert composite.shape == (14, 8, 3)
    # the padded region (right of the narrow page) must be white, not
    # leftover garbage or black
    assert composite[0, 6].tolist() == [255, 255, 255]


def test_stack_pages_vertically_pads_narrower_grayscale_pages():
    # Issue #286 -- module1_opencv.enhance() output (the OCR path's
    # per-page images) is single-channel grayscale, not 3-channel BGR
    # like render_pdf_all_pages's output. A hardcoded 3-channel pad shape
    # would raise on this via np.hstack's shape mismatch.
    tall_narrow = np.zeros((10, 5), dtype=np.uint8)
    short_wide = np.full((4, 8), 255, dtype=np.uint8)
    composite = stack_pages_vertically([tall_narrow, short_wide])
    assert composite.shape == (14, 8)
    assert composite[0, 6] == 255


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
