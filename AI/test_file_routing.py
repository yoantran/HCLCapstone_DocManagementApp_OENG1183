import sys
from unittest.mock import patch

sys.path.insert(0, ".")

from file_routing import detect_processing_path, render_pdf_first_page

with open("samples/balance_sheet/DAN_Baocaotaichinh_Q4_2018.pdf", "rb") as f:
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
    # DAN_Baocaotaichinh_Q4_2018.pdf is a real financial report, ~2370 chars
    # of extracted text -- well above the 50-char scanned threshold.
    assert detect_processing_path("report.pdf", _TEXT_NATIVE_PDF_BYTES) == "text_native"


def test_unsupported_extension_raises():
    try:
        detect_processing_path("notes.txt", b"irrelevant")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_render_pdf_first_page_returns_bgr_array():
    image = render_pdf_first_page(_TEXT_NATIVE_PDF_BYTES)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.dtype.name == "uint8"


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
