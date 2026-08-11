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
from paddleocr import PPStructureV3

from field_extraction_en import extract_fields_from_text_en


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
    return {"fields": fields, "line_boxes": doc["lines"], "tables": doc["tables"], "text": text}


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
