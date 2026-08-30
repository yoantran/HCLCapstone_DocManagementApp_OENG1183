import base64
import os
import tempfile

import cv2
import numpy as np

import module1_opencv
import module2_ocr_extraction
import module2_text_extraction
import module3_redaction
import module4_loan_rules
import income_normalization
from field_extraction_en import extract_balance_sheet_fields_en
from file_routing import detect_processing_path, render_pdf_all_pages, stack_pages_vertically

_EMPTY_RESULT = {
    "processing_path": None,
    "fields": None,
    "redaction": None,
    "loan_readiness": None,
    "balance_sheet_readiness": None,
    "quality": None,
    "preview_image_base64": None,
    "sensitive_field_keys": [],
    "error": None,
}

# Issue #163 -- any of these present means real balance-sheet table data
# was extracted, regardless of document type. Content-driven, not gated
# on proposed_monthly_repayment (a company's balance-sheet health isn't
# about a specific proposed repayment) -- unlike loan_readiness above.
_BALANCE_SHEET_FIELD_KEYS = (
    "total_current_assets",
    "total_current_liabilities",
    "total_liabilities",
    "total_equity",
)


# Issue #286 -- extract_regex_fields_en's own return shape: these 4 keys
# are .findall() lists (every real occurrence across the document), every
# other field is a single first-match-wins scalar (or, for income, a
# scalar PAIR with income_basis that must stay together). Merging pages
# with the wrong shape either drops real list occurrences (treating a
# list field as scalar) or corrupts a scalar field into a list. "dates"
# isn't a redaction-relevant field (not in module3_redaction's
# SENSITIVE_FIELD_KEYS) but is still list-shaped in `fields` itself, so
# it's included here for correctness of the merged fields dict, even
# though it never reaches find_sensitive_boxes.
_LIST_FIELD_KEYS = ("abn", "phone", "dates", "salary")


def _merge_page_fields(accumulated: dict, page_fields: dict) -> None:
    for key in _LIST_FIELD_KEYS:
        if key in page_fields:
            accumulated.setdefault(key, [])
            accumulated[key].extend(page_fields.get(key) or [])
    if accumulated.get("income") is None and page_fields.get("income") is not None:
        accumulated["income"] = page_fields["income"]
        accumulated["income_basis"] = page_fields.get("income_basis")
    for key, value in page_fields.items():
        if key in _LIST_FIELD_KEYS or key in ("income", "income_basis"):
            continue
        if value is not None and accumulated.get(key) is None:
            accumulated[key] = value


def _run_ocr_path(filename: str, file_bytes: bytes, include_preview: bool = False) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        raw_pages = render_pdf_all_pages(file_bytes)
    else:
        raw_pages = [cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)]

    # Issue #286 -- a scanned multi-page PDF used to only ever OCR page 1
    # (render_pdf_first_page), missing real content on every later page --
    # same page-1-only bug #283/#284 fixed for the text-native path, here
    # on the OCR path. Loop every page: merge fields (shape-aware, see
    # _merge_page_fields), and run find_sensitive_boxes per page against
    # THAT PAGE's own (unmerged) field results -- naturally scoped to what
    # genuinely exists on this page, no risk of a page-3 value getting
    # boxed on page 1 just because it's present in the merged dict.
    enhanced_pages = []
    fields: dict = {}
    per_page_boxes: list[dict] = []
    worst_blur = None
    worst_contrast = None
    any_low_quality = False

    for page_index, raw_image in enumerate(raw_pages):
        enhanced = module1_opencv.enhance(raw_image)
        enhanced_image = enhanced["image"]
        enhanced_pages.append(enhanced_image)

        if worst_blur is None or enhanced["blur_score"] < worst_blur:
            worst_blur = enhanced["blur_score"]
        if worst_contrast is None or enhanced["contrast_score"] < worst_contrast:
            worst_contrast = enhanced["contrast_score"]
        any_low_quality = any_low_quality or enhanced["low_quality"]

        ocr_result = module2_ocr_extraction.extract_fields(enhanced_image)
        _merge_page_fields(fields, ocr_result["fields"])

        page_boxes = module3_redaction.find_sensitive_boxes(
            enhanced_image, ocr_result["fields"], table_ocr_preds=ocr_result["table_ocr_preds"]
        )
        per_page_boxes.extend({**box, "page_index": page_index} for box in page_boxes)

    quality = {
        "blur_score": worst_blur,
        "contrast_score": worst_contrast,
        "low_quality": any_low_quality,
    }
    # Issue #286 -- each box above is percentages relative to its OWN
    # page's enhanced image; the redacted-preview endpoint renders one
    # composite (file_routing.stack_pages_vertically), so every box must
    # be converted into that composite's coordinate space before storage
    # -- a page-2 box left as page-2-relative would land on the wrong
    # region once drawn against the full multi-page composite.
    boxes = module3_redaction.boxes_to_composite_pct(per_page_boxes, enhanced_pages)
    redaction = {"type": "boxes", "items": boxes}

    # Issue: redaction boxes are percentages relative to the ENHANCED image
    # (post deskew/autocrop), not the raw upload -- autocrop alone can shrink
    # dimensions by 20%+, so overlaying boxes on the original file is visibly
    # wrong. Opt-in only (demo use) -- BE's real /process calls never set
    # this, so production aiResult never carries an embedded image (would
    # bloat the jsonb column on every document for no real benefit there).
    preview_image_base64 = None
    if include_preview:
        composite = stack_pages_vertically(enhanced_pages)
        ok, buf = cv2.imencode(".png", composite)
        if ok:
            preview_image_base64 = base64.b64encode(buf.tobytes()).decode("ascii")

    return fields, redaction, quality, preview_image_base64


def _run_text_native_path(filename: str, file_bytes: bytes) -> dict:
    ext = "." + filename.lower().rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        text_result = module2_text_extraction.extract_fields(tmp_path)
    finally:
        os.unlink(tmp_path)

    fields = text_result["fields"]

    # Issue #170 -- pdfium has no table-structure recovery the way
    # python-docx's table object model does, so a text-native PDF never
    # got any balance-sheet totals. Keep pdfium's own text extraction
    # (more accurate than re-OCR'ing a real text layer) but additionally
    # render the page and reuse the already-proven OCR table pipeline
    # (#171 hardened this exact path) just to harvest table structure --
    # no new extraction technique, purely content-driven (a no-op if the
    # PDF has no tables at all).
    #
    # Issue #283 -- the totals table isn't guaranteed to be on page 1: 2
    # of the 4 real multi-page balance-sheet PDFs in samples/en_balance_
    # sheet/ have their actual "Total Assets" table on page 2, with page 1
    # holding unrelated content -- render_pdf_first_page alone silently
    # returned zero totals for those two real files. OCR every page
    # (these documents are short, 2-4 pages in the real corpus -- not the
    # OCR-path scanned-PDF cost concern #283 also flagged separately for
    # a genuinely long scanned document) and merge each page's result
    # into `fields`, first non-null wins per key. Merging per-page
    # results rather than concatenating table_rows across pages avoids
    # extract_balance_sheet_fields_en's own section-tracking (a bare
    # "Total" row resolved via the current section header, see its own
    # docstring) getting corrupted by a page boundary landing mid-section.
    if ext == ".pdf":
        for page_image in render_pdf_all_pages(file_bytes):
            enhanced = module1_opencv.enhance(page_image)
            ocr_doc = module2_ocr_extraction.ocr_document(enhanced["image"])
            table_rows = [
                row for html in ocr_doc["tables"] for row in module2_ocr_extraction.html_table_to_rows(html)
            ]
            if not table_rows:
                continue
            page_fields = extract_balance_sheet_fields_en(table_rows)
            for key, value in page_fields.items():
                if value is not None and fields.get(key) is None:
                    fields[key] = value

    spans = module3_redaction.find_sensitive_spans(text_result["text"], fields)
    redaction = {"type": "spans", "items": spans}
    return fields, redaction, None, None


def process_document(
    filename: str,
    file_bytes: bytes,
    proposed_monthly_repayment: float | None = None,
    existing_monthly_debt: float | None = None,
    include_preview: bool = False,
) -> dict:
    try:
        path = detect_processing_path(filename, file_bytes)
    except ValueError as e:
        return {**_EMPTY_RESULT, "sensitive_field_keys": [], "error": str(e)}

    try:
        if path == "ocr":
            fields, redaction, quality, preview_image = _run_ocr_path(filename, file_bytes, include_preview)
        else:
            fields, redaction, quality, preview_image = _run_text_native_path(filename, file_bytes)

        loan_readiness = None
        if proposed_monthly_repayment is not None:
            normalized = income_normalization.normalize_monthly_income(fields)
            loan_readiness = module4_loan_rules.assess_loan_readiness(
                monthly_income=normalized["monthly_income"],
                income_basis=normalized["income_basis"],
                proposed_monthly_repayment=proposed_monthly_repayment,
                existing_monthly_debt=existing_monthly_debt,
            )
            loan_readiness["income_source"] = normalized["income_source"]

        balance_sheet_readiness = None
        if any(fields.get(key) is not None for key in _BALANCE_SHEET_FIELD_KEYS):
            balance_sheet_readiness = module4_loan_rules.assess_balance_sheet_readiness(
                total_current_assets=fields.get("total_current_assets"),
                total_current_liabilities=fields.get("total_current_liabilities"),
                total_liabilities=fields.get("total_liabilities"),
                total_equity=fields.get("total_equity"),
            )

        return {
            "processing_path": path,
            "fields": fields,
            "redaction": redaction,
            "loan_readiness": loan_readiness,
            "balance_sheet_readiness": balance_sheet_readiness,
            "quality": quality,
            "preview_image_base64": preview_image,
            "sensitive_field_keys": list(module3_redaction.SENSITIVE_FIELD_KEYS),
            "error": None,
        }
    except Exception as e:
        return {**_EMPTY_RESULT, "processing_path": path, "sensitive_field_keys": [], "error": str(e)}
