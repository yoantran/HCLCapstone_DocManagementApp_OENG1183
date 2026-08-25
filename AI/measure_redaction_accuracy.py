"""
Real accuracy measurement for Module 3's redaction box positioning
(find_sensitive_boxes(), the image-path track) against human-annotated
ground truth -- issue #81's own stated, never-measured success criteria.

Text-native redaction is not measured here: find_sensitive_spans()'s own
self-check already enforces text[start:end] == value as a hard invariant,
so its positional accuracy is exact by construction whenever the field
itself extracts correctly (#131 already measured that at 100%).
"""

import json
from pathlib import Path

import cv2
import numpy as np

from module2_ocr_extraction import extract_fields
from module3_redaction import find_sensitive_boxes

IOU_THRESHOLD = 0.5
IMAGE_DIR = Path("samples/_redaction_annotation")
FIELDS = (
    "name", "address", "abn", "bsb", "account_number", "income", "salary",
    # Issue #216 -- balance-sheet totals, ground-truth boxes not yet drawn.
    "total_current_assets", "total_assets",
    "total_current_liabilities", "total_liabilities", "total_equity",
)


def compute_iou(box_a: dict, box_b: dict) -> float:
    ax1, ay1 = box_a["x_pct"], box_a["y_pct"]
    ax2, ay2 = ax1 + box_a["w_pct"], ay1 + box_a["h_pct"]
    bx1, by1 = box_b["x_pct"], box_b["y_pct"]
    bx2, by2 = bx1 + box_b["w_pct"], by1 + box_b["h_pct"]

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = box_a["w_pct"] * box_a["h_pct"]
    area_b = box_b["w_pct"] * box_b["h_pct"]
    union_area = area_a + area_b - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def score(ground_truth_path: str = "redaction_ground_truth.json",
          report_path: str = "accuracy_report_redaction.txt") -> None:
    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    totals = {f: 0 for f in FIELDS}
    correct = {f: 0 for f in FIELDS}
    misses = []

    for doc in ground_truth["documents"]:
        filename = doc["filename"]
        image_path = IMAGE_DIR / filename
        img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)

        ocr_fields = extract_fields(img, lang="en")["fields"]
        predicted_boxes = find_sensitive_boxes(img, ocr_fields)

        gt_by_field: dict[str, list[dict]] = {}
        for box in doc["boxes"]:
            gt_by_field.setdefault(box["field"], []).append(box)

        for field, gt_boxes in gt_by_field.items():
            pred_for_field = [b for b in predicted_boxes if b["field"] == field]
            for gt_box in gt_boxes:
                totals[field] += 1
                best_iou = max((compute_iou(gt_box, p) for p in pred_for_field), default=0.0)
                if best_iou >= IOU_THRESHOLD:
                    correct[field] += 1
                else:
                    misses.append((filename, field, gt_box, best_iou))

    with open(report_path, "w", encoding="utf-8") as out:
        out.write(f"iou_threshold={IOU_THRESHOLD}\n")
        out.write(f"Documents scored: {len(ground_truth['documents'])}\n\n")
        out.write("Per-field accuracy (correct / total ground-truth boxes):\n")
        overall_correct = overall_total = 0
        for field in FIELDS:
            t, c = totals[field], correct[field]
            pct = f"{100 * c / t:.1f}%" if t else "n/a (no ground truth)"
            out.write(f"  {field:15s}: {c:3d} / {t:3d}  ({pct})\n")
            overall_correct += c
            overall_total += t
        overall_pct = f"{100 * overall_correct / overall_total:.1f}%" if overall_total else "n/a"
        out.write(f"\nOverall: {overall_correct} / {overall_total}  ({overall_pct})\n")

        out.write(f"\nMisses ({len(misses)}):\n")
        for filename, field, gt_box, best_iou in misses:
            out.write(f"  {filename}\n    field={field} best_iou={best_iou:.3f} gt_box={gt_box!r}\n")

    print(f"saved {report_path}  overall={overall_correct}/{overall_total} ({overall_pct})")


if __name__ == "__main__":
    def test_identical_boxes_iou_is_one():
        box = {"x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.2, "h_pct": 0.05}
        assert abs(compute_iou(box, box) - 1.0) < 1e-9

    def test_disjoint_boxes_iou_is_zero():
        a = {"x_pct": 0.0, "y_pct": 0.0, "w_pct": 0.1, "h_pct": 0.1}
        b = {"x_pct": 0.5, "y_pct": 0.5, "w_pct": 0.1, "h_pct": 0.1}
        assert compute_iou(a, b) == 0.0

    def test_partial_overlap_hand_computed():
        # a: [0.0, 0.0] to [0.2, 0.1] -- area 0.02
        # b: [0.1, 0.0] to [0.3, 0.1] -- area 0.02
        # intersection: [0.1, 0.0] to [0.2, 0.1] -- area 0.01
        # union: 0.02 + 0.02 - 0.01 = 0.03
        # iou: 0.01 / 0.03 = 0.3333...
        a = {"x_pct": 0.0, "y_pct": 0.0, "w_pct": 0.2, "h_pct": 0.1}
        b = {"x_pct": 0.1, "y_pct": 0.0, "w_pct": 0.2, "h_pct": 0.1}
        assert abs(compute_iou(a, b) - (1 / 3)) < 1e-9

    tests = [
        test_identical_boxes_iou_is_one,
        test_disjoint_boxes_iou_is_zero,
        test_partial_overlap_hand_computed,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")

    score()
