"""
Standalone single-image OCR worker, run as a fresh subprocess per page by
measure_accuracy_image.py -- see _extract_fields_for_pages() there for why.
Confirmed empirically this session: even a single, correctly batched
predict() call within one process can occasionally surface a stale/wrong
result for one page in the batch while the others are correct -- a real,
non-deterministic race in the third-party CPU inference engine's internal
buffer handling (PaddleOCR/PaddleX PPStructureV3), not something closeable
with a Python-level code change. Running every single predict() call in
its own OS process closes it by construction: there is no memory left to
share across separate processes.

Usage: python _ocr_worker.py <image_path> <lang>
Prints one line of JSON to stdout: {"text": str, "table_rows": [[str, ...], ...]}
"""

import json
import sys

import cv2
import numpy as np
from paddleocr import PPStructureV3

from module2_ocr_extraction import html_table_to_rows


def main() -> None:
    image_path = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"

    image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    pipeline = PPStructureV3(
        lang=lang,
        use_table_recognition=True,
        text_detection_model_name="PP-OCRv6_medium_det",
        text_recognition_model_name="PP-OCRv6_medium_rec",
        enable_mkldnn=False,
    )
    result = pipeline.predict(image)[0]

    ocr_res = result.get("overall_ocr_res", {})
    text = "\n".join(ocr_res.get("rec_texts", []))
    tables = [t["pred_html"] for t in result.get("table_res_list", []) if t.get("pred_html")]
    table_rows = [row for html in tables for row in html_table_to_rows(html)]

    print(json.dumps({"text": text, "table_rows": table_rows}))


if __name__ == "__main__":
    main()
