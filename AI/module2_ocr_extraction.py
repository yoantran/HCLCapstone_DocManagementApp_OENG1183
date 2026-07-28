import re

import cv2
import numpy as np
from paddleocr import PPStructureV3

CCCD_RE = re.compile(r"\b\d{12}\b")
PHONE_RE = re.compile(r"(?:\+84|0)(?:3|5|7|8|9)\d{8}\b")
TAX_CODE_RE = re.compile(r"\b\d{10}(?:-\d{3})?\b")
DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
SALARY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")

LABEL_PATTERNS = {
    "name": re.compile(r"H[oọ]?\s*(?:và)?\s*t[eê]n\s*:\s*(.+)"),
    "address": re.compile(r"[ĐD][iị]a\s*ch[iỉ]\s*:\s*(.+)"),
}

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


def extract_regex_fields(text: str) -> dict:
    phone_matches = PHONE_RE.findall(text)
    # a VN mobile number is 10 digits, same length as a tax code — don't
    # double-count a phone match as a tax code
    tax_code_matches = [m for m in TAX_CODE_RE.findall(text) if m not in phone_matches]
    return {
        "cccd": CCCD_RE.findall(text),
        "phone": phone_matches,
        "tax_code": tax_code_matches,
        "dates": DATE_RE.findall(text),
        "salary": SALARY_RE.findall(text),
    }


def extract_label_anchored(text: str) -> dict:
    result = {}
    for field, pattern in LABEL_PATTERNS.items():
        match = pattern.search(text)
        result[field] = match.group(1).strip() if match else None
    return result


def _ner_fallback(text: str, missing_fields: list[str]) -> dict:
    # ponytail: no reliable pretrained Vietnamese NER model exists (see
    # project_name_extraction_strategy memory) — this tier stays unwired until
    # a real VN NER source is chosen. Upgrade here when Module 2 needs it.
    return {field: None for field in missing_fields}


def extract_fields(image, lang: str = "vi") -> dict:
    doc = ocr_document(image, lang=lang)
    text = lines_to_text(doc["lines"])
    fields = extract_regex_fields(text)
    fields.update(extract_label_anchored(text))
    missing = [f for f in ("name", "address") if not fields.get(f)]
    if missing:
        fields.update(_ner_fallback(text, missing))
    return {"fields": fields, "line_boxes": doc["lines"], "tables": doc["tables"], "text": text}


if __name__ == "__main__":
    from module1_opencv import enhance

    with open("module2_selfcheck_output.txt", "w", encoding="utf-8") as out:
        for path in ("sample_payslip.png", "sample_payslip_degraded.jpg"):
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
