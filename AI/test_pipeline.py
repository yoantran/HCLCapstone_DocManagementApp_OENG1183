import sys
from unittest.mock import patch

import numpy as np

sys.path.insert(0, ".")

import module2_ocr_extraction
from pipeline import process_document

with open("samples/en_contract/part-time-employment-contract.docx", "rb") as f:
    _DOCX_BYTES = f.read()

with open("samples/en_pay_slip/Screenshot 2026-07-28 152419.png", "rb") as f:
    _IMAGE_BYTES = f.read()

with open("samples/en_balance_sheet/Machias_Balance-sheet-template.pdf", "rb") as f:
    _PDF_BYTES = f.read()


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


def test_sensitive_field_keys_matches_redaction_items():
    result = process_document("payslip.png", _IMAGE_BYTES)
    assert result["error"] is None
    item_fields = {item["field"] for item in result["redaction"]["items"]}
    # sensitive_field_keys is now the full detector-configured set, a
    # superset of whatever was actually found on this specific document --
    # a detection miss must never make a field silently "not sensitive."
    assert item_fields <= set(result["sensitive_field_keys"])
    assert "annual_salary" in result["sensitive_field_keys"]


def test_sensitive_field_keys_empty_when_no_items_detected():
    result = process_document("notes.txt", b"just some text")
    # unsupported extension -- error path, sensitive_field_keys must still
    # be present (never a missing key) so BE's parser doesn't need a
    # separate null-check for this specific field.
    assert result["sensitive_field_keys"] == []


def test_text_native_pdf_balance_sheet_totals_found_on_a_later_page():
    # Issue #283 -- the balance-sheet table-harvesting step used to render
    # only page 1 (render_pdf_first_page); a real multi-page PDF whose
    # totals table sits on a later page got nothing. No real fixture in
    # samples/en_balance_sheet/ currently has real (non-placeholder)
    # totals split across pages -- the ones checked while investigating
    # this turned out to be blank templates -- so this exercises the merge
    # logic directly via mocks rather than claiming a real-corpus repro.
    # Page 1 has no table at all; page 2's table has the real total.
    fake_page = np.full((20, 20, 3), 255, dtype=np.uint8)
    with patch("pipeline.render_pdf_all_pages", return_value=[fake_page, fake_page]), \
         patch.object(
             module2_ocr_extraction,
             "ocr_document",
             side_effect=[{"tables": []}, {"tables": ["<table>ignored, html_table_to_rows is mocked</table>"]}],
         ), \
         patch.object(
             module2_ocr_extraction,
             "html_table_to_rows",
             return_value=[["Total Assets", "$425,000"]],
         ):
        result = process_document("balance-sheet.pdf", _PDF_BYTES)

    assert result["error"] is None
    assert result["fields"]["total_assets"] == 425000.0


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
