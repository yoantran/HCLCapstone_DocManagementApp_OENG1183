import sys
from unittest.mock import patch

import numpy as np

sys.path.insert(0, ".")

import module2_ocr_extraction
import module2_text_extraction
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


def test_ocr_path_multipage_merges_fields_and_places_boxes_on_correct_page():
    # Issue #286 -- a scanned multi-page PDF used to only ever OCR page 1
    # (render_pdf_first_page). No real scanned multi-page PDF exists in
    # samples/ (every real PDF fixture has a genuine text layer, routing
    # "text_native" not "ocr") -- exercises the merge + box-composite
    # logic directly via mocks, same as #283's balance-sheet test above.
    page0 = np.full((50, 50, 3), 255, dtype=np.uint8)
    page1 = np.full((50, 50, 3), 255, dtype=np.uint8)

    base_fields = {
        "name": None, "bsb": None, "account_number": None, "address": None,
        "abn": [], "phone": [], "dates": [], "salary": [],
        "income": None, "income_basis": None, "annual_salary": None, "pay_period_days": None,
    }
    page0_fields = {**base_fields, "salary": ["$100"]}
    page1_fields = {**base_fields, "salary": ["$200"], "name": "Jane Doe"}

    page0_boxes = [
        {"field": "salary", "value": "$100", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1, "detection_method": "regex"}
    ]
    page1_boxes = [
        {"field": "name", "value": "Jane Doe", "x_pct": 0.1, "y_pct": 0.2, "w_pct": 0.3, "h_pct": 0.1, "detection_method": "regex"}
    ]

    with patch("pipeline.detect_processing_path", return_value="ocr"), \
         patch("pipeline.render_pdf_all_pages", return_value=[page0, page1]), \
         patch.object(
             module2_ocr_extraction, "extract_fields",
             side_effect=[
                 {"fields": page0_fields, "line_boxes": [], "tables": [], "table_ocr_preds": [], "text": "", "balance_sheet_section": None, "balance_sheet_prefer_col": None},
                 {"fields": page1_fields, "line_boxes": [], "tables": [], "table_ocr_preds": [], "text": "", "balance_sheet_section": None, "balance_sheet_prefer_col": None},
             ],
         ), \
         patch("module3_redaction.find_sensitive_boxes", side_effect=[page0_boxes, page1_boxes]):
        result = process_document("scan.pdf", b"irrelevant")

    assert result["error"] is None
    # list-shaped field: concatenated across pages, not "first wins"
    assert result["fields"]["salary"] == ["$100", "$200"]
    # scalar field: first non-null wins -- only found on page 2
    assert result["fields"]["name"] == "Jane Doe"

    items = result["redaction"]["items"]
    salary_item = next(i for i in items if i["field"] == "salary")
    name_item = next(i for i in items if i["field"] == "name")
    # page 0 (offset 0): composite y_pct == its own page-local y_pct * (page_h / total_h) = 0.1 * 50/100
    assert salary_item["y_pct"] == 0.05
    # page 1 (offset 50px on a 100px-tall composite): 0.2 * 50 = 10, +50 offset = 60, /100 = 0.6
    assert name_item["y_pct"] == 0.6
    assert name_item["y_pct"] > salary_item["y_pct"]


def test_ocr_path_carries_balance_sheet_section_across_pages():
    # Issue #297 -- a balance-sheet section header on one page with its
    # bare "Total" row on the next only resolves if the section-
    # tracking state (extract_balance_sheet_fields_en's own
    # current_section_field) survives the page boundary. Verifies
    # _run_ocr_path actually threads page 1's returned
    # balance_sheet_section into page 2's initial_section kwarg, not
    # just that the merged result happens to come out right.
    page0 = np.full((50, 50, 3), 255, dtype=np.uint8)
    page1 = np.full((50, 50, 3), 255, dtype=np.uint8)
    base_fields = {
        "name": None, "bsb": None, "account_number": None, "address": None,
        "abn": [], "phone": [], "dates": [], "salary": [],
        "income": None, "income_basis": None, "annual_salary": None, "pay_period_days": None,
        "total_current_liabilities": None,
    }
    with patch("pipeline.detect_processing_path", return_value="ocr"), \
         patch("pipeline.render_pdf_all_pages", return_value=[page0, page1]), \
         patch.object(
             module2_ocr_extraction, "extract_fields",
             side_effect=[
                 {"fields": base_fields, "line_boxes": [], "tables": [], "table_ocr_preds": [], "text": "", "balance_sheet_section": "total_current_liabilities", "balance_sheet_prefer_col": None},
                 {"fields": {**base_fields, "total_current_liabilities": 45000.0}, "line_boxes": [], "tables": [], "table_ocr_preds": [], "text": "", "balance_sheet_section": None, "balance_sheet_prefer_col": None},
             ],
         ) as mock_extract, \
         patch("module3_redaction.find_sensitive_boxes", return_value=[]):
        result = process_document("scan.pdf", b"irrelevant")

    assert result["error"] is None
    assert result["fields"]["total_current_liabilities"] == 45000.0
    assert mock_extract.call_args_list[0].kwargs.get("initial_section") is None
    assert mock_extract.call_args_list[1].kwargs.get("initial_section") == "total_current_liabilities"


def test_text_native_pdf_carries_balance_sheet_section_across_pages():
    # Issue #297 -- same page-boundary gap as the OCR path above, on
    # the text-native PDF loop instead. Page 1's table has ONLY the
    # section header (no Total row yet); page 2's has ONLY the bare
    # Total row -- neither page alone can resolve this without the
    # section carried across the loop's own iterations.
    fake_page = np.full((20, 20, 3), 255, dtype=np.uint8)
    with patch("pipeline.render_pdf_all_pages", return_value=[fake_page, fake_page]), \
         patch.object(
             module2_ocr_extraction, "ocr_document",
             side_effect=[
                 {"tables": ["<table>page1</table>"]},
                 {"tables": ["<table>page2</table>"]},
             ],
         ), \
         patch.object(
             module2_ocr_extraction, "html_table_to_rows",
             side_effect=[
                 [["Current/short-term Liabilities"]],
                 [["Total", "$45,000"]],
             ],
         ):
        result = process_document("balance-sheet.pdf", _PDF_BYTES)

    assert result["error"] is None
    assert result["fields"]["total_current_liabilities"] == 45000.0


def test_text_native_pdf_carries_balance_sheet_prefer_col_across_pages():
    # Issue #345 -- same page-boundary gap #297 fixed for section-tracking,
    # confirmed real on Balance-sheet-template-FILLED-300.pdf: its period
    # header ("[Year1]".."[Year5]") lands on one page while the actual
    # Total Assets row sits on the next. Page 1's table has ONLY a
    # current-is-leftmost header (so a rightmost-fallback would pick the
    # wrong, older figure); page 2's has ONLY the values row -- proves
    # pipeline.py's own text-native loop threads the detected column
    # across its iterations, not just that extract_balance_sheet_fields_en
    # can do it in isolation (test_field_extraction_en.py already covers
    # that).
    fake_page = np.full((20, 20, 3), 255, dtype=np.uint8)
    with patch("pipeline.render_pdf_all_pages", return_value=[fake_page, fake_page]), \
         patch.object(
             module2_ocr_extraction, "ocr_document",
             side_effect=[
                 {"tables": ["<table>page1</table>"]},
                 {"tables": ["<table>page2</table>"]},
             ],
         ), \
         patch.object(
             module2_ocr_extraction, "html_table_to_rows",
             side_effect=[
                 [["", "CURRENT YR.", "PRIOR YR."]],
                 [["Total Assets", "$120,000.00", "$100,000.00"]],
             ],
         ):
        result = process_document("balance-sheet.pdf", _PDF_BYTES)

    assert result["error"] is None
    assert result["fields"]["total_assets"] == 120000.0


def test_text_native_pdf_suppresses_salary_when_balance_sheet_detected():
    # Issue #347 -- extract_fields_from_text_en's own #219 suppression
    # ("a balance-sheet-shaped table means every dollar figure is a false
    # salary match") only fires when its table_rows argument is populated,
    # but module2_text_extraction.extract_fields(path) never passes
    # table_rows for a standalone .pdf (only the .docx path builds it) --
    # so the initial text_result["fields"] this function starts from can
    # never get suppressed there. This loop's OWN per-page OCR-table
    # recovery discovers balance-sheet fields entirely separately, after
    # that initial call already returned, and never re-applies the same
    # suppression -- confirmed real on Balance-sheet-template-FILLED-300.pdf:
    # all 25 real dollar figures on the page got spuriously redacted as
    # "salary" on top of the genuine balance-sheet totals.
    fake_page = np.full((20, 20, 3), 255, dtype=np.uint8)
    fake_text_fields = {
        "name": None, "address": None, "bsb": None, "account_number": None,
        "abn": [], "phone": [], "dates": [], "income": None, "income_basis": None,
        "annual_salary": None, "pay_period_days": None,
        "salary": ["$135", "$144"],
    }
    with patch("pipeline.render_pdf_all_pages", return_value=[fake_page]), \
         patch.object(
             module2_text_extraction, "extract_fields",
             return_value={"fields": dict(fake_text_fields), "text": "irrelevant"},
         ), \
         patch.object(module2_ocr_extraction, "ocr_document", return_value={"tables": ["<table>ignored</table>"]}), \
         patch.object(module2_ocr_extraction, "html_table_to_rows", return_value=[["Total Assets", "$425,000"]]):
        result = process_document("balance-sheet.pdf", _PDF_BYTES)

    assert result["error"] is None
    assert result["fields"]["total_assets"] == 425000.0
    assert result["fields"]["salary"] == []


def test_text_native_pdf_cross_checks_corrupted_totals_row_against_plain_text():
    # Issue #345 -- confirmed real on Balance-sheet-template-FILLED-300.pdf,
    # found re-investigating this issue after PR #346: even with #345's
    # own column-index carry correctly detecting prefer_col=7 from a clean
    # header row, the ACTUAL totals row on the next page independently got
    # corrupted by table-structure recognition -- a duplicated "TOTAL
    # ASSETS" label token split into its own spurious trailing cell,
    # giving this ONE row 8 cells instead of the header's 9, in a
    # different arrangement (real dump, from direct investigation):
    #   ['Total 0 TOT $74, AL 000 ASSE TS', '0 $97, 000', '0',
    #    '0 $144 ,000', '0 $84, 000', '', 'TOT AL ASSE TS', '$135 ,000']
    # The carried index 7 (correct for the header) lands on the stray
    # displaced value ($135,000, actually year 3's figure) instead of the
    # real rightmost one ($84,000, at index 4 in this row's own corrupted
    # layout). The raw pdfium TEXT layer for the same row reads the
    # genuine values in clean left-to-right order with none of this
    # corruption (real confirmed evidence) -- used here as a cross-check
    # when the table-row path's own value doesn't match what plain text
    # independently shows for this label.
    fake_page = np.full((20, 20, 3), 255, dtype=np.uint8)
    header_row = ["", "", "Curr ent asset S", "[Yea r1]", "[Yea r2]", "[Yea r3]", "[Yea r4]", "[Yea r5]", ""]
    corrupted_totals_row = [
        "Total 0 TOT $74, AL 000 ASSE TS", "0 $97, 000", "0",
        "0 $144 ,000", "0 $84, 000", "", "TOT AL ASSE TS", "$135 ,000",
    ]
    # Real pdfium raw text for this exact document (direct dump) mid-word-
    # wraps the LABEL text itself too, not just the dollar figures --
    # "TOT\r\nAL \r\nASSE\r\nTS", never a contiguous "Total"/"Assets"
    # substring -- must still be found. Also includes the REAL next
    # section (a bare "Total" sub-row for current liabilities, this
    # template's own real shape per #167/#297) so the window boundary is
    # proven to stop at the end of THIS row's own 5 values, not bleed
    # into the next unrelated "Total" row and pick up ITS last value
    # ($45,000) instead -- confirmed real, this is exactly what a first,
    # too-permissive fix attempt did (labels-only boundary, no bare
    # "Total" as a boundary too).
    plain_text = (
        "TOT\r\nAL \r\nASSE\r\nTS\r\n$74,\r\n000\r\n$97,\r\n000\r\n$135\r\n,000\r\n"
        "$144\r\n,000\r\n$84,\r\n000\r\nCurr\r\nent/\r\nshort\r\n-\r\nterm\r\nliabil\r\nities\r\n"
        "Cred\r\nit \r\ncard\r\ns \r\npaya\r\nble\r\nMore\r\n\r\n"
        "Total $103,\r\n000\r\n$104\r\n,000\r\n$51,\r\n000\r\n$50,\r\n000\r\n$45,\r\n000"
    )
    fake_text_fields = {
        "name": None, "address": None, "bsb": None, "account_number": None,
        "abn": [], "phone": [], "dates": [], "income": None, "income_basis": None,
        "annual_salary": None, "pay_period_days": None, "salary": [],
    }
    with patch("pipeline.render_pdf_all_pages", return_value=[fake_page, fake_page]), \
         patch.object(
             module2_text_extraction, "extract_fields",
             return_value={"fields": dict(fake_text_fields), "text": plain_text},
         ), \
         patch.object(
             module2_ocr_extraction, "ocr_document",
             side_effect=[{"tables": ["<table>header</table>"]}, {"tables": ["<table>totals</table>"]}],
         ), \
         patch.object(
             module2_ocr_extraction, "html_table_to_rows",
             side_effect=[[header_row], [corrupted_totals_row]],
         ):
        result = process_document("balance-sheet.pdf", _PDF_BYTES)

    assert result["error"] is None
    assert result["fields"]["total_assets"] == 84000.0


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
