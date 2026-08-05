"""
Same measurement as measure_accuracy_image.py, swapping PaddleOCR for
Tesseract (module2_ocr_tesseract.py) to test whether its `vie` trained-data
language pack has better Vietnamese diacritic coverage than any PaddleOCR
model does (see issue #116 -- checked 3 PaddleOCR lineages, all near-zero
Vietnamese-specific character support in their output vocabulary).
"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np

from _fill_templates import fill_docx
from measure_accuracy import build_manifest
from measure_accuracy_image import RENDER_DIR, docx_to_png
from module1_opencv import enhance
from module2_ocr_tesseract import extract_fields

SCALAR_FIELDS = {"name", "address"}
LIST_FIELDS = {"cccd", "phone", "salary"}


def score(render_scale: float = 3.5, use_enhance: bool = False, limit: int | None = None,
          report_path: str = "accuracy_report_tesseract.txt") -> None:
    manifest = build_manifest()[:limit]
    totals = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    correct = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    misses = []

    for i, (src, dst, seed) in enumerate(manifest, 1):
        _, ground_truth = fill_docx(src, dst, seed=seed)

        png_path = RENDER_DIR / f"{Path(dst).stem}.png"
        docx_to_png(dst, png_path, render_scale)

        img = cv2.imdecode(np.fromfile(str(png_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        pipeline_input = enhance(img)["image"] if use_enhance else img
        extracted = extract_fields(pipeline_input, lang="vie")["fields"]

        print(f"[{i}/{len(manifest)}] {dst}", flush=True)

        for field in SCALAR_FIELDS:
            gt_values = set(ground_truth.get(field, []))
            if not gt_values:
                continue
            totals[field] += 1
            value = extracted.get(field)
            if value is not None and value in gt_values:
                correct[field] += 1
            else:
                misses.append((dst, field, sorted(gt_values), value))

        for field in LIST_FIELDS:
            gt_values = ground_truth.get(field, [])
            if not gt_values:
                continue
            extracted_set = set(extracted.get(field) or [])
            for v in gt_values:
                totals[field] += 1
                if v in extracted_set:
                    correct[field] += 1
                else:
                    misses.append((dst, field, [v], sorted(extracted_set)))

    with open(report_path, "w", encoding="utf-8") as out:
        out.write(f"engine=tesseract render_scale={render_scale} use_enhance={use_enhance}\n")
        out.write(f"Documents scored: {len(manifest)}\n\n")
        out.write("Per-field accuracy (correct / total ground-truth values):\n")
        overall_correct = overall_total = 0
        for field in ("name", "address", "cccd", "phone", "salary"):
            t, c = totals[field], correct[field]
            pct = f"{100 * c / t:.1f}%" if t else "n/a (no ground truth)"
            out.write(f"  {field:8s}: {c:3d} / {t:3d}  ({pct})\n")
            overall_correct += c
            overall_total += t
        overall_pct = f"{100 * overall_correct / overall_total:.1f}%" if overall_total else "n/a"
        out.write(f"\nOverall: {overall_correct} / {overall_total}  ({overall_pct})\n")

        out.write(f"\nMisses ({len(misses)}):\n")
        for dst, field, expected, got in misses:
            out.write(f"  {dst}\n    field={field} expected={expected!r} got={got!r}\n")

    print(f"saved {report_path}  overall={overall_correct}/{overall_total} ({overall_pct})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=3.5)
    ap.add_argument("--enhance", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report", default="accuracy_report_tesseract.txt")
    args = ap.parse_args()
    score(render_scale=args.scale, use_enhance=args.enhance, limit=args.limit, report_path=args.report)
