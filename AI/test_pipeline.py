import sys

sys.path.insert(0, ".")

from pipeline import process_document

with open("samples/en_contract/part-time-employment-contract.docx", "rb") as f:
    _DOCX_BYTES = f.read()

with open("samples/en_pay_slip/Screenshot 2026-07-28 152419.png", "rb") as f:
    _IMAGE_BYTES = f.read()


def test_docx_routes_text_native_and_returns_spans():
    result = process_document("payslip.docx", _DOCX_BYTES)
    assert result["error"] is None
    assert result["processing_path"] == "text_native"
    assert result["fields"] is not None
    assert result["redaction"]["type"] == "spans"
    assert result["quality"] is None
    assert result["loan_readiness"] is None


def test_image_routes_ocr_and_returns_boxes():
    result = process_document("payslip.png", _IMAGE_BYTES)
    assert result["error"] is None
    assert result["processing_path"] == "ocr"
    assert result["fields"] is not None
    assert result["redaction"]["type"] == "boxes"
    assert result["quality"] is not None
    assert "blur_score" in result["quality"]


def test_unsupported_extension_produces_error_not_exception():
    result = process_document("notes.txt", b"just some text")
    assert result["error"] is not None
    assert result["processing_path"] is None
    assert result["fields"] is None


def test_corrupt_supported_extension_produces_error_not_exception():
    result = process_document("fake.docx", b"this is not a real docx file")
    assert result["error"] is not None
    assert result["fields"] is None


def test_loan_readiness_populates_when_repayment_provided():
    result = process_document(
        "payslip.docx", _DOCX_BYTES,
        proposed_monthly_repayment=1_000_000,
        existing_monthly_debt=None,
    )
    assert result["error"] is None
    # loan_readiness runs iff Module 2 found an income value on this doc --
    # the -FILLED templates are Faker-generated and may or may not include
    # one; assert the *shape* is consistent rather than a specific verdict.
    if result["fields"].get("income") is not None:
        assert result["loan_readiness"] is not None
        assert result["loan_readiness"]["verdict"] in ("READY", "NOT_READY", "INSUFFICIENT_DATA")
    else:
        assert result["loan_readiness"]["verdict"] == "INSUFFICIENT_DATA"


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
