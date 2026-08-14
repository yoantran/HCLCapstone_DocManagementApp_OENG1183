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
from file_routing import detect_processing_path, render_pdf_first_page

_EMPTY_RESULT = {
    "processing_path": None,
    "fields": None,
    "redaction": None,
    "loan_readiness": None,
    "balance_sheet_readiness": None,
    "quality": None,
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


def _run_ocr_path(filename: str, file_bytes: bytes) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        image = render_pdf_first_page(file_bytes)
    else:
        image = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    enhanced = module1_opencv.enhance(image)
    quality = {
        "blur_score": enhanced["blur_score"],
        "contrast_score": enhanced["contrast_score"],
        "low_quality": enhanced["low_quality"],
    }
    ocr_result = module2_ocr_extraction.extract_fields(enhanced["image"])
    fields = ocr_result["fields"]
    boxes = module3_redaction.find_sensitive_boxes(enhanced["image"], fields)
    redaction = {"type": "boxes", "items": boxes}
    return fields, redaction, quality


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
    spans = module3_redaction.find_sensitive_spans(text_result["text"], fields)
    redaction = {"type": "spans", "items": spans}
    return fields, redaction, None


def process_document(
    filename: str,
    file_bytes: bytes,
    proposed_monthly_repayment: float | None = None,
    existing_monthly_debt: float | None = None,
) -> dict:
    try:
        path = detect_processing_path(filename, file_bytes)
    except ValueError as e:
        return {**_EMPTY_RESULT, "error": str(e)}

    try:
        if path == "ocr":
            fields, redaction, quality = _run_ocr_path(filename, file_bytes)
        else:
            fields, redaction, quality = _run_text_native_path(filename, file_bytes)

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
            "error": None,
        }
    except Exception as e:
        return {**_EMPTY_RESULT, "processing_path": path, "error": str(e)}
