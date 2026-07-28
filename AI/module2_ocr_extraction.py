import cv2
import numpy as np
from paddleocr import PPStructureV3

from field_extraction import extract_fields_from_text

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
    fields = extract_fields_from_text(text)
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
