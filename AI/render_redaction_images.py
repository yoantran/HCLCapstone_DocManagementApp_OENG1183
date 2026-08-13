"""
Renders #131's 36-document corpus to persistent, enhanced PNGs for manual
redaction ground-truth annotation. One-off utility -- not part of the AI
service itself, not imported by anything else.

Skips payslip pages 0-1 (the Fair Work template's own fixed instructional
preamble + "EXAMPLE PAY SLIP" section -- confirmed in issue #131's
investigation to contain no real filled data), matching the same skip
measure_accuracy_image.py applies when scoring field extraction. Also
skips contract pages 1-4 (confirmed via direct text-page inspection:
page 0 has the real "Employee Name:"/"Employee Address:" fields; pages
1-2 are legal boilerplate clauses, page 3 is a blank signature block,
page 4 is a footer/source-attribution page -- none of them contain any
field find_sensitive_boxes() would ever emit a box for). Images are
enhanced the same way (module1_opencv.enhance()) as the real production
/process endpoint and the accuracy benchmarks apply it, so box
coordinates the annotator draws match exactly what find_sensitive_boxes()
will later see when re-run against these same files.
"""

from pathlib import Path

import cv2
import numpy as np

from _fill_templates import fill_docx
from measure_accuracy import build_manifest
from measure_accuracy_image import docx_to_pngs
from module1_opencv import enhance

OUT_DIR = Path("samples/_redaction_annotation")
RENDER_SCALE = 2.0


def render_corpus() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    saved = []

    for src, dst, seed in manifest:
        fill_docx(src, dst, seed=seed)
        png_paths = docx_to_pngs(dst, OUT_DIR, RENDER_SCALE)
        normalized_src = src.replace("\\", "/")
        if "en_pay_slip" in normalized_src:
            png_paths = png_paths[2:4]
        elif "en_contract" in normalized_src:
            png_paths = png_paths[0:1]

        for png_path in png_paths:
            img = cv2.imdecode(np.fromfile(str(png_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            enhanced = enhance(img)["image"]
            cv2.imencode(".png", enhanced)[1].tofile(str(png_path))
            saved.append(png_path)

    return saved


if __name__ == "__main__":
    paths = render_corpus()
    print(f"rendered {len(paths)} annotation images to {OUT_DIR}/")
