"""
One-off measurement (see docs/superpowers/specs/2026-08-10-module3-
redaction-image-path-design.md Decision 2): does matching field regexes
against a word-level reconstruction of image_to_data's output, instead of
image_to_string's text, change the existing 38-doc accuracy baseline
(58.8%, 47/80, accuracy_report_tesseract_baseline.txt)? The result decides
whether module2_ocr_tesseract.py's production text source gets swapped
(Task 2 of the implementation plan) or stays as-is.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np

from _fill_templates import fill_docx
from measure_accuracy import build_manifest
from measure_accuracy_image import RENDER_DIR, docx_to_png
from field_extraction import extract_fields_from_text, restore_name_diacritics
from module2_ocr_tesseract import _word_data, _build_word_reconstruction, extract_by_proximity, _group_lines

SCALAR_FIELDS = {"name", "address"}
LIST_FIELDS = {"cccd", "phone", "salary"}


def extract_fields_reconstructed(image, lang: str = "vie") -> dict:
    data = _word_data(image, lang=lang)
    text, _ = _build_word_reconstruction(data)
    fields = extract_fields_from_text(text)
    missing = [f for f in ("name", "address") if not fields.get(f)]
    if missing:
        lines = _group_lines(data)
        proximity_fields = extract_by_proximity(lines)
        for f in missing:
            if proximity_fields.get(f):
                fields[f] = proximity_fields[f]
        fields["name"] = restore_name_diacritics(fields.get("name"))
    return {"fields": fields, "text": text}


def score(render_scale: float = 3.5, limit: int | None = None,
          report_path: str = "accuracy_report_tesseract_reconstructed.txt") -> None:
    manifest = build_manifest()[:limit]
    totals = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    correct = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    misses = []

    for i, (src, dst, seed) in enumerate(manifest, 1):
        _, ground_truth = fill_docx(src, dst, seed=seed)
        png_path = RENDER_DIR / f"{Path(dst).stem}.png"
        docx_to_png(dst, png_path, render_scale)
        img = cv2.imdecode(np.fromfile(str(png_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        extracted = extract_fields_reconstructed(img, lang="vie")["fields"]

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
        out.write(f"engine=tesseract-reconstructed render_scale={render_scale}\n")
        out.write(f"Documents scored: {len(manifest)}\n\n")
        overall_correct = overall_total = 0
        for field in ("name", "address", "cccd", "phone", "salary"):
            t, c = totals[field], correct[field]
            pct = f"{100 * c / t:.1f}%" if t else "n/a"
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
    score()
