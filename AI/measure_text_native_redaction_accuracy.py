"""
Issue #325 -- real accuracy measurement for the text-native redaction
path's pixel-box RESOLUTION step (file_routing.resolve_item_boxes_via_
pdf_text), against human-verified ground truth. Sibling to
measure_redaction_accuracy.py (the image/OCR-path box scorer) -- reuses
its compute_iou directly rather than reimplementing it.

Why this didn't exist until now: measure_redaction_accuracy.py's own
docstring used to say "Text-native redaction is not measured here...
its positional accuracy is exact by construction whenever the field
itself extracts correctly." That's true for the SPAN side only
(find_sensitive_spans's own text[start:end] == value self-check).
It is NOT true for the later, separate PIXEL BOX resolution step a
text-native document's span goes through at preview time
(resolve_item_boxes_via_pdf_text) -- issue #327 found and fixed a real,
confirmed, live case where that step silently produced zero boxes for
every real balance-sheet total on a real docx upload, precisely because
nothing was measuring it. This tool exists so a future regression in
that specific step gets caught automatically instead of by accident.

Ground truth here is real, live-produced output (module2_text_
extraction.extract_fields -> find_sensitive_spans -> convert_docx_to_
pdf_bytes -> resolve_item_boxes_via_pdf_text, the exact real chain
main.py's own /apply-redaction endpoint runs for a .docx upload),
visually spot-checked (crop+zoom, drawn box overlay) against the real
rendered composite image before being trusted, same methodology this
project already uses for every other ground-truth corpus this session
(#310, #316, #317, #323) -- not blind trust in the function's own
output, which would make this scorer circular and useless for catching
a real regression in that same function.
"""

import json

from file_routing import convert_docx_to_pdf_bytes, resolve_item_boxes_via_pdf_text
from measure_redaction_accuracy import compute_iou
from module2_text_extraction import extract_fields
from module3_redaction import find_sensitive_spans

IOU_THRESHOLD = 0.5


def score(ground_truth_path: str = "text_native_redaction_ground_truth.json",
          report_path: str = "accuracy_report_text_native_redaction.txt") -> None:
    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    totals: dict[str, int] = {}
    correct: dict[str, int] = {}
    misses = []

    documents = ground_truth["documents"]
    for doc_idx, doc in enumerate(documents):
        docx_path = doc["docx"]
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()

        text_result = extract_fields(docx_path)
        fields = text_result["fields"]
        gt_by_field: dict[str, list[dict]] = {}
        for box in doc["boxes"]:
            gt_by_field.setdefault(box["field"], []).append(box)

        spans = find_sensitive_spans(text_result["text"], fields)
        items = [s for s in spans if s["field"] in gt_by_field]
        pdf_bytes = convert_docx_to_pdf_bytes(docx_bytes)
        resolved = resolve_item_boxes_via_pdf_text(pdf_bytes, items)
        print(f"[{doc_idx + 1}/{len(documents)}] {docx_path}", flush=True)

        for field, gt_boxes in gt_by_field.items():
            pred_for_field = [b for b in resolved if b["field"] == field]
            for gt_box in gt_boxes:
                totals[field] = totals.get(field, 0) + 1
                best_iou = max((compute_iou(gt_box, p) for p in pred_for_field), default=0.0)
                if best_iou >= IOU_THRESHOLD:
                    correct[field] = correct.get(field, 0) + 1
                else:
                    misses.append((docx_path, field, gt_box, best_iou))

    with open(report_path, "w", encoding="utf-8") as out:
        out.write(f"iou_threshold={IOU_THRESHOLD}\n")
        out.write(f"Documents scored: {len(documents)}\n\n")
        out.write("Per-field accuracy (correct / total ground-truth boxes):\n")
        overall_correct = overall_total = 0
        for field in sorted(totals):
            t, c = totals[field], correct.get(field, 0)
            pct = f"{100 * c / t:.1f}%" if t else "n/a"
            out.write(f"  {field:25s}: {c:3d} / {t:3d}  ({pct})\n")
            overall_correct += c
            overall_total += t
        overall_pct = f"{100 * overall_correct / overall_total:.1f}%" if overall_total else "n/a"
        out.write(f"\nOverall: {overall_correct} / {overall_total}  ({overall_pct})\n")

        out.write(f"\nMisses ({len(misses)}):\n")
        for docx_path, field, gt_box, best_iou in misses:
            out.write(f"  {docx_path}\n    field={field} best_iou={best_iou:.3f} gt_box={gt_box!r}\n")

    print(f"saved {report_path}  overall={overall_correct}/{overall_total} ({overall_pct})")


if __name__ == "__main__":
    def test_compute_iou_catches_a_real_mismatch():
        # Self-check that the scoring logic itself would actually catch
        # a real regression, not just rubber-stamp whatever the live
        # function currently returns -- deliberately mismatched boxes
        # (same field, clearly non-overlapping regions) must score
        # below IOU_THRESHOLD, not silently pass.
        gt_box = {"x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.02}
        wrong_box = {"x_pct": 0.7, "y_pct": 0.7, "w_pct": 0.1, "h_pct": 0.02}
        assert compute_iou(gt_box, wrong_box) < IOU_THRESHOLD

    def test_compute_iou_accepts_a_real_match():
        gt_box = {"x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.02}
        assert compute_iou(gt_box, gt_box) >= IOU_THRESHOLD

    for test in (test_compute_iou_catches_a_real_mismatch, test_compute_iou_accepts_a_real_match):
        test()
        print(f"PASS {test.__name__}")

    score()
