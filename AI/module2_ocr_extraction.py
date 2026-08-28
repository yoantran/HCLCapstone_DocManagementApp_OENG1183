# Production image-path OCR engine (issue #129). PPStructureV3 (PaddleOCR),
# chosen over Tesseract for the English pipeline after a real head-to-head
# test on a real English payslip: PPStructureV3 transcribed every value
# correctly and recovered real table structure (3 correctly-separated HTML
# tables matching the document's actual layout); Tesseract's raw output on
# the same table was unreadable garbage.
#
# This module was originally built and measured against Vietnamese (see
# issue #116) -- PaddleOCR/PaddleX has no model with usable Vietnamese
# diacritic coverage (checked 3 lineages, all near-zero), which is why the
# Vietnamese pipeline uses Tesseract instead (module2_ocr_tesseract.py).
# That finding doesn't apply to English -- English is exactly where this
# engine's table-structure win matters, so it's the production engine here.

from html.parser import HTMLParser

import cv2
import numpy as np
from paddleocr import PaddleOCR, PPStructureV3

from field_extraction_en import (
    INCOME_LABEL_PATTERNS,
    LABEL_PATTERNS,
    _clean_label_value,
    _get_nlp_en,
    _has_person_entity,
    _looks_like_bsb_or_account,
    _looks_like_name,
    extract_fields_from_text_en,
    parse_currency_amount,
)


class _TableRowParser(HTMLParser):
    """Reads <tr>/<td>/<th> cell text out of PPStructureV3's pred_html,
    keeping real cell boundaries -- same table-cell-pairing input as the
    DOCX branch, sourced from OCR's own table-structure output instead of
    python-docx (see extract_from_table_rows in field_extraction.py)."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell_parts = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell_parts is not None:
            self._row.append("".join(self._cell_parts).strip())
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell_parts is not None:
            self._cell_parts.append(data)


def html_table_to_rows(html: str) -> list[list[str]]:
    parser = _TableRowParser()
    parser.feed(html)
    return parser.rows

# ponytail: PaddlePaddle's oneDNN CPU path throws
# "ConvertPirAttribute2RuntimeAttribute ... not support" on this machine —
# enable_mkldnn=False works around it. Root-cause before relying on this in
# production (see project_ocr_table_form_finding memory).
#
# text_detection/recognition model names are forced to the PP-OCRv6 medium
# pair -- originally forced to fix Vietnamese diacritic coverage (PPStructureV3's
# own auto-selected default is a lighter latin_PP-OCRv5_mobile_rec model),
# but also already confirmed to work well for English in the real head-to-line
# test that selected this engine -- no need to re-tune for English specifically.
_pipelines: dict[str, PPStructureV3] = {}


def _get_pipeline(lang: str) -> PPStructureV3:
    if lang not in _pipelines:
        _pipelines[lang] = PPStructureV3(
            lang=lang,
            use_table_recognition=True,
            # PPStructureV3 loads formula recognition by default -- real
            # model weights loaded on every cold start for zero benefit,
            # none of this pipeline's document types (payslip, balance
            # sheet, contract) ever contain math formulas. Disabling cuts
            # real weight-loading time off every cold start (local CPU and
            # Modal GPU both), found while chasing Modal cold-start latency
            # for the live demo.
            use_formula_recognition=False,
            text_detection_model_name="PP-OCRv6_medium_det",
            text_recognition_model_name="PP-OCRv6_medium_rec",
            enable_mkldnn=False,
        )
    return _pipelines[lang]


def ocr_document(image, lang: str = "en") -> dict:
    if isinstance(image, np.ndarray) and image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    result = _get_pipeline(lang).predict(image)[0]

    ocr_res = result.get("overall_ocr_res", {})
    texts = ocr_res.get("rec_texts", [])
    scores = ocr_res.get("rec_scores", [])
    boxes = ocr_res.get("rec_boxes", [])
    lines = [
        {"text": t, "score": float(s), "box": (b.tolist() if hasattr(b, "tolist") else list(b))}
        for t, s, b in zip(texts, scores, boxes)
    ]

    tables = [t["pred_html"] for t in result.get("table_res_list", []) if t.get("pred_html")]

    return {"lines": lines, "tables": tables}


def lines_to_text(lines: list[dict]) -> str:
    return "\n".join(line["text"] for line in lines)


def extract_fields(image, lang: str = "en") -> dict:
    doc = ocr_document(image, lang=lang)
    text = lines_to_text(doc["lines"])
    table_rows = [row for html in doc["tables"] for row in html_table_to_rows(html)]
    fields = extract_fields_from_text_en(text, table_rows=table_rows or None)
    _repair_line_split_fields(doc["lines"], text, fields)
    return {"fields": fields, "line_boxes": doc["lines"], "tables": doc["tables"], "text": text}


# Issue #270 class B -- PPStructureV3 detects a label and its value as
# separate OCR spans whenever they're visually adjacent but not drawn as
# one contiguous text run (common on non-tabular/photographed layouts,
# e.g. Payslip.jpg's "Pay Slip For:" / "Rymer, Mark" or "GROSS PAY:" /
# "$5,837.50" each landing in their own detected box). lines_to_text()
# joins every detected span onto its own "\n"-separated line, so a
# label-anchored regex expecting "label: value" on ONE line finds the
# label with nothing after it -- and worse, if the regex's capture
# crosses onto the wrong nearby line, it can grab a truncated, WRONG
# number instead of correctly missing (the grid4.jpg "income: 9.0"
# case -- OCR split "9500" as "9" then "500" on separate lines/cells,
# and the pre-fix regex's within-line capture silently accepted the "9").
#
# This repairs it via the OCR lines' own real spatial boxes rather than
# guessing at more label wording -- when a label matched but its
# same-line capture came back empty, look up which OCR line the label
# text came from and search for the value by real position: directly to
# the right on the same visual row first (true reading order), directly
# below in the same column second (a value that wrapped under its
# label). Never widens the search past adjacent spans, so it can't
# reach across into an unrelated field's row/column the way a naive
# "nearest number anywhere on the page" search could.
_REPAIRABLE_LABEL_FIELDS = ("name", "address", "bsb", "account_number")


def _line_index_for_offset(lines: list[dict], offset: int) -> int:
    """lines_to_text() joins line["text"] with "\n" in order, so a match
    offset into that joined string maps back to exactly one line index."""
    pos = 0
    for i, line in enumerate(lines):
        end = pos + len(line["text"])
        if offset <= end:
            return i
        pos = end + 1  # +1 for the "\n" separator
    return len(lines) - 1


def _overlap_ratio(a_lo: float, a_hi: float, b_lo: float, b_hi: float) -> float:
    overlap = min(a_hi, b_hi) - max(a_lo, b_lo)
    smaller = min(a_hi - a_lo, b_hi - b_lo)
    return overlap / smaller if overlap > 0 and smaller > 0 else 0.0


def find_adjacent_value(lines: list[dict], label_line_idx: int) -> str | None:
    lx1, ly1, lx2, ly2 = lines[label_line_idx]["box"]
    label_h = ly2 - ly1

    # Real confirmed case (Payslip.jpg): "lassification:" and "Cheque No:"
    # sit in genuinely different columns of a 2-column form but still
    # overlap vertically by >50% (69-92 vs 60-79) -- a bare overlap-ratio
    # check alone would wrongly treat them as the same row. Capping the
    # rightward gap at a fraction of the page's own width (max x2 seen
    # across all lines, the only page-width signal available here) is
    # what actually rejects that case (326px gap on a 600px-wide page)
    # while still allowing the real same-row case (41px gap).
    page_width = max((line["box"][2] for line in lines), default=0)
    max_right_gap = page_width * 0.3

    best_right = None  # (x_gap, index)
    best_below = None  # (y_gap, index)
    for i, line in enumerate(lines):
        if i == label_line_idx:
            continue
        x1, y1, x2, y2 = line["box"]
        if x1 >= lx2 and _overlap_ratio(ly1, ly2, y1, y2) >= 0.6:
            gap = x1 - lx2
            if gap <= max_right_gap and (best_right is None or gap < best_right[0]):
                best_right = (gap, i)
        elif y1 >= ly2 and _overlap_ratio(lx1, lx2, x1, x2) >= 0.6:
            gap = y1 - ly2
            if gap <= label_h * 2 and (best_below is None or gap < best_below[0]):
                best_below = (gap, i)

    if best_right is not None:
        return lines[best_right[1]]["text"].strip()
    if best_below is not None:
        return lines[best_below[1]]["text"].strip()
    return None


def _repair_line_split_fields(lines: list[dict], text: str, fields: dict) -> None:
    for field in _REPAIRABLE_LABEL_FIELDS:
        if fields.get(field) is not None:
            continue
        match = LABEL_PATTERNS[field].search(text)
        if match is None:
            continue
        value = find_adjacent_value(lines, _line_index_for_offset(lines, match.start()))
        cleaned = _clean_label_value(value) if value else None
        if cleaned is None:
            continue
        # Real confirmed false positive (audited on Salary Slip Format
        # Basic.jpg): unlike LABEL_PATTERNS's own same-line capture, this
        # function's spatial box lookup has no idea WHAT it's grabbing --
        # it took the box nearest to a bare "Employee:" label and returned
        # "Bank Detals" (an unrelated field on the same form) uncritically.
        # `name` needs the same semantic check class A's NER fallback
        # already applies (spaCy confirms PERSON, not just "some
        # non-blank text was nearby"). `bsb`/`account_number` get a
        # cheap numeric-shape gate too (#272) -- same unguarded code
        # path, no confirmed real failure yet, but proactive since it's
        # low-risk. `address` is deliberately left as tolerant as
        # before -- no safe, cheap "looks like an address" shape check
        # exists, and there's no real failing case to design one against.
        if field == "name" and not (_looks_like_name(cleaned) and _has_person_entity(_get_nlp_en(), cleaned)):
            continue
        if field in ("bsb", "account_number") and not _looks_like_bsb_or_account(cleaned):
            continue
        fields[field] = cleaned

    if fields.get("income") is None:
        for basis in ("gross", "net"):
            match = INCOME_LABEL_PATTERNS[basis].search(text)
            if match is None:
                continue
            value = find_adjacent_value(lines, _line_index_for_offset(lines, match.start()))
            cleaned = _clean_label_value(value) if value else None
            amount = parse_currency_amount(cleaned) if cleaned is not None else None
            if amount is not None:
                fields["income"] = amount
                fields["income_basis"] = basis
                break


# Word-box source for module3_redaction.find_sensitive_boxes() (issue #130).
# PPStructureV3 does not support return_word_box -- confirmed empirically by
# passing it through predict()'s kwargs and observing overall_ocr_res still
# reports return_word_box=False. Only the plain (non-structure) PaddleOCR
# pipeline honors it, giving per-line lists of tokens (text_word) with
# parallel per-token boxes (text_word_boxes) -- finer than Tesseract's
# image_to_data even, since punctuation is split into its own token. This is
# necessarily a second, separate model pass: nothing folds PPStructureV3's
# table-aware pipeline and return_word_box into one call.
_word_pipelines: dict[str, PaddleOCR] = {}


def _get_word_pipeline(lang: str) -> PaddleOCR:
    if lang not in _word_pipelines:
        _word_pipelines[lang] = PaddleOCR(
            lang=lang,
            text_detection_model_name="PP-OCRv6_medium_det",
            text_recognition_model_name="PP-OCRv6_medium_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _word_pipelines[lang]


def build_word_reconstruction(image, lang: str = "en") -> tuple[str, list[dict]]:
    """Concatenates return_word_box=True's per-line tokens in order (they
    already include their own inter-word whitespace/punctuation as separate
    tokens, so no extra join character is needed to reproduce the original
    spacing), returning the joined text plus a parallel list recording each
    non-blank token's exact character span -- the offset map
    find_sensitive_boxes() (module3_redaction.py) uses to locate a regex
    match's box(es). Same shape as module2_ocr_tesseract._build_word_reconstruction()."""
    if isinstance(image, np.ndarray) and image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    result = _get_word_pipeline(lang).predict(image, return_word_box=True)[0]

    text_parts = []
    word_spans = []
    pos = 0
    for tokens, boxes in zip(result.get("text_word", []), result.get("text_word_boxes", [])):
        for token, box in zip(tokens, boxes):
            if token.strip():
                x1, y1, x2, y2 = (int(v) for v in box)
                word_spans.append({"word": token, "box": (x1, y1, x2, y2), "start": pos, "end": pos + len(token)})
            text_parts.append(token)
            pos += len(token)
        text_parts.append("\n")
        pos += 1

    return "".join(text_parts), word_spans


if __name__ == "__main__":
    from module1_opencv import enhance

    with open("module2_selfcheck_output.txt", "w", encoding="utf-8") as out:
        for path in ("samples/en_pay_slip/Payslip.jpg", "samples/en_pay_slip/Screenshot 2026-07-28 152419.png"):
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            assert img is not None, f"could not load {path}"
            enhanced = enhance(img)["image"]
            result = extract_fields(enhanced)
            out.write(f"--- {path} ---\n")
            for field, value in result["fields"].items():
                out.write(f"  {field}: {value}\n")
            out.write(f"  line_boxes: {len(result['line_boxes'])} lines\n")
            out.write(f"  tables: {len(result['tables'])}\n")
    print("saved module2_selfcheck_output.txt")
