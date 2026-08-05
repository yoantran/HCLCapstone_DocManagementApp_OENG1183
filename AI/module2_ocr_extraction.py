# NOTE: superseded as the production image-path engine by module2_ocr_tesseract.py
# (58.8% vs 23.8% on the 38-doc accuracy benchmark -- see issue #116). Kept as
# a reference implementation: real PPStructureV3 table-structure detection,
# which no PaddleOCR/PaddleX model pairs with usable Vietnamese diacritic
# recognition (checked 3 lineages, all near-zero coverage, see issue #116).
# A future FastAPI endpoint should import from module2_ocr_tesseract, not here.

from html.parser import HTMLParser

import cv2
import numpy as np
from paddleocr import PPStructureV3

from field_extraction import extract_fields_from_text


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
# pair rather than PPStructureV3's own default — its default auto-selects a
# lighter latin_PP-OCRv5_mobile_rec model that drops far more Vietnamese
# diacritics than PP-OCRv6_medium_rec does.
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


def ocr_document(image, lang: str = "vi") -> dict:
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


def extract_fields(image, lang: str = "vi") -> dict:
    doc = ocr_document(image, lang=lang)
    text = lines_to_text(doc["lines"])
    table_rows = [row for html in doc["tables"] for row in html_table_to_rows(html)]
    fields = extract_fields_from_text(text, table_rows=table_rows or None)
    return {"fields": fields, "line_boxes": doc["lines"], "tables": doc["tables"], "text": text}


if __name__ == "__main__":
    from module1_opencv import enhance

    with open("module2_selfcheck_output.txt", "w", encoding="utf-8") as out:
        for path in ("samples/pay_slip/image-94-600x414.png", "samples/pay_slip/mau-phieu-luong-02.png"):
            img = cv2.imread(path)
            assert img is not None, f"could not load {path}"
            enhanced = enhance(img)["image"]
            result = extract_fields(enhanced)
            out.write(f"--- {path} ---\n")
            for field, value in result["fields"].items():
                out.write(f"  {field}: {value}\n")
            out.write(f"  line_boxes: {len(result['line_boxes'])} lines\n")
            out.write(f"  tables: {len(result['tables'])}\n")
    print("saved module2_selfcheck_output.txt")
