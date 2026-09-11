import base64
import os
import re
import tempfile

import cv2
import numpy as np

import module1_opencv
import module2_ocr_extraction
import module2_text_extraction
import module3_redaction
import module4_loan_rules
import income_normalization
from field_extraction_en import (
    _BALANCE_SHEET_LABEL_RE,
    extract_balance_sheet_fields_en,
    parse_currency_amount_balance_sheet,
)
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
    # Issue #297 -- a balance-sheet section header can land on one page
    # with its bare "Total" row on the next; carrying this across
    # iterations lets extract_balance_sheet_fields_en's section-tracking
    # (see its own docstring) survive the page boundary instead of
    # resetting to None on every page's independent call.
    balance_sheet_section: str | None = None
    # Issue #345 -- same page-boundary gap, for the period-column header
    # ("[Year1]".."[Year5]") that #182's column-detection needs -- see
    # extract_balance_sheet_fields_en's own docstring.
    balance_sheet_prefer_col: int | None = None

    for page_index, raw_image in enumerate(raw_pages):
        enhanced = module1_opencv.enhance(raw_image)
        enhanced_image = enhanced["image"]
        enhanced_pages.append(enhanced_image)

        if worst_blur is None or enhanced["blur_score"] < worst_blur:
            worst_blur = enhanced["blur_score"]
        if worst_contrast is None or enhanced["contrast_score"] < worst_contrast:
            worst_contrast = enhanced["contrast_score"]
        any_low_quality = any_low_quality or enhanced["low_quality"]

        ocr_result = module2_ocr_extraction.extract_fields(
            enhanced_image, initial_section=balance_sheet_section, initial_prefer_col=balance_sheet_prefer_col
        )
        balance_sheet_section = ocr_result["balance_sheet_section"]
        balance_sheet_prefer_col = ocr_result["balance_sheet_prefer_col"]
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


_BARE_TOTAL_RE = re.compile(r"Total", re.IGNORECASE)


def _plain_text_balance_sheet_value(text: str, field: str) -> float | None:
    """Issue #345 -- a balance-sheet total's OWN table row can get
    corrupted by table-structure recognition independently of whether the
    header's period column was detected correctly (confirmed real on
    Balance-sheet-template-FILLED-300.pdf: a duplicated label token split
    into its own spurious cell, displacing the real rightmost value out of
    the carried column index entirely). The raw pdfium TEXT layer for the
    same row -- already extracted for this whole document regardless --
    reads the real values in genuine left-to-right order with none of that
    corruption, since it never goes through OCR table-structure recovery
    at all. Finds the label, then every dollar-shaped amount between it
    and the next recognized balance-sheet label (or end of text), and
    returns the LAST one -- same "rightmost is current period" convention
    #295/#296's own table_rows-based detection already uses, just applied
    to a linear reading-order text run instead of a table row.

    pdfium's raw text wraps mid-WORD too, not just mid-number (real dump:
    "TOT\\r\\nAL \\r\\nASSE\\r\\nTS" for "TOTAL ASSETS") -- neither label
    regex can match a literal "Total"/"Assets" substring split like that.
    Same #327-established discipline: strip ONLY \\r/\\n (not real spaces,
    which stay genuine word separators) before matching."""
    label_re = _BALANCE_SHEET_LABEL_RE.get(field)
    if label_re is None:
        return None
    text = text.replace("\r", "").replace("\n", "")
    label_match = label_re.search(text)
    if label_match is None:
        return None
    # Issue #345 -- bounding the window at only the 5 fully-qualified
    # labels is too permissive: a real template (this exact document,
    # same #167/#297 shape) writes its OTHER subtotals as a bare "Total"
    # with no "Current"/"Liabilities"/etc. after it, so a section header
    # + bare "Total" row can sit entirely BETWEEN this label and the next
    # fully-qualified one -- confirmed real: an earlier version of this
    # window bled past "Current/short-term liabilities" into that
    # section's own bare "Total" row and picked up ITS last value
    # ($45,000, current liabilities) instead of stopping at the end of
    # THIS row's real 5 values. Any bare "Total" (case-insensitive) is a
    # reliable row boundary regardless of what follows it.
    window_end = len(text)
    for other_re in list(_BALANCE_SHEET_LABEL_RE.values()) + [_BARE_TOTAL_RE]:
        other_match = other_re.search(text, label_match.end())
        if other_match is not None:
            window_end = min(window_end, other_match.start())
    window = text[label_match.end():window_end]
    amounts = [
        parse_currency_amount_balance_sheet(m.group(0))
        for m in module3_redaction._BALANCE_SHEET_BARE_AMOUNT_RE.finditer(window)
    ]
    amounts = [a for a in amounts if a is not None]
    return amounts[-1] if len(amounts) > 1 else None


def _cross_check_balance_sheet_fields_against_plain_text(fields: dict, text: str) -> None:
    """Issue #345 -- only OVERRIDES a table-row-derived value when the
    plain-text reading independently disagrees with it. `len(amounts) > 1`
    inside _plain_text_balance_sheet_value already guards against a single
    ambiguous match; requiring disagreement here (not just "plain text has
    an opinion") means an already-correct table-row result is never
    second-guessed just because a differently-scoped plain-text window
    happens to exist -- this only fires when the two sources genuinely
    conflict, which is what the corrupted-row case actually looks like."""
    for field in _BALANCE_SHEET_LABEL_RE:
        table_value = fields.get(field)
        if table_value is None:
            continue
        plain_value = _plain_text_balance_sheet_value(text, field)
        if plain_value is not None and abs(plain_value - table_value) >= 0.01:
            fields[field] = plain_value


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
    #
    # Issue #297 -- that section-tracking still needs to survive a
    # header landing on one page with its bare "Total" row on the next
    # (confirmed real, total_current_liabilities resolving to None on
    # every document in samples/_redaction_annotation/) -- threading
    # initial_section/the returned final section across iterations
    # carries just that one piece of state forward without touching the
    # per-page table_rows themselves, so the corruption risk above still
    # doesn't apply.
    balance_sheet_section: str | None = None
    # Issue #345 -- same page-boundary gap #297 already carries
    # balance_sheet_section across, for the period-column header (see
    # extract_balance_sheet_fields_en's own docstring) -- confirmed real
    # on Balance-sheet-template-FILLED-300.pdf, whose header is on page 0
    # while the Total Assets row it labels is on page 1.
    balance_sheet_prefer_col: int | None = None
    if ext == ".pdf":
        for page_image in render_pdf_all_pages(file_bytes):
            enhanced = module1_opencv.enhance(page_image)
            ocr_doc = module2_ocr_extraction.ocr_document(enhanced["image"])
            table_rows = [
                row for html in ocr_doc["tables"] for row in module2_ocr_extraction.html_table_to_rows(html)
            ]
            if not table_rows:
                continue
            page_fields, balance_sheet_section, balance_sheet_prefer_col = extract_balance_sheet_fields_en(
                table_rows, balance_sheet_section, balance_sheet_prefer_col
            )
            for key, value in page_fields.items():
                if value is not None and fields.get(key) is None:
                    fields[key] = value

    # Issue #345 -- the table-row-derived value above can come from a row
    # independently corrupted by table-structure recognition even when
    # the header's own period column was detected correctly (see
    # _plain_text_balance_sheet_value's own docstring); cross-check
    # against the plain pdfium text before this function's own remaining
    # steps (salary suppression, span detection) run against `fields`.
    _cross_check_balance_sheet_fields_against_plain_text(fields, text_result["text"])

    # Issue #347 -- extract_fields_from_text_en's own #219 suppression ("a
    # balance-sheet-shaped table means every dollar figure is a false
    # salary match") only fires when ITS OWN table_rows argument is
    # populated -- module2_text_extraction.extract_fields(path) never
    # passes one for a standalone .pdf (only the .docx path builds it), so
    # `fields` above starts from an unsuppressed call. The per-page OCR-
    # table loop just above discovers balance-sheet fields entirely
    # separately and never re-applies that check -- confirmed real on
    # Balance-sheet-template-FILLED-300.pdf: all 25 real dollar figures on
    # the page got spuriously redacted as "salary" on top of the genuine
    # totals. Same condition #219 already uses, just re-checked here once
    # this loop's own detection result is known.
    if any(fields.get(key) is not None for key in _BALANCE_SHEET_LABEL_RE):
        fields["salary"] = []

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
