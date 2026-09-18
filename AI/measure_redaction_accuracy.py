"""
Real accuracy measurement for Module 3's redaction box positioning
(find_sensitive_boxes(), the image-path track) against human-annotated
ground truth -- issue #81's own stated, never-measured success criteria.

Text-native redaction's SPAN correctness (find_sensitive_spans's own
self-check enforcing text[start:end] == value as a hard invariant) is
not measured here -- that's exact by construction whenever the field
itself extracts correctly (#131 already measured that at 100%). Issue
#325/#327 -- that invariant does NOT cover the separate, later PIXEL
BOX resolution step a text-native document's span goes through at
preview time (file_routing.resolve_item_boxes_via_pdf_text): #327 found
and fixed a real, confirmed, live case where that step silently
produced zero boxes for every real balance-sheet total on a real docx
upload, because nothing was measuring it -- this docstring's own
earlier, now-corrected claim ("exact by construction") was itself part
of why that real defect went unnoticed. See
measure_text_native_redaction_accuracy.py, the sibling scorer for that
specific step.
"""

import json
import re
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

# Issue #297 -- every ground-truth filename follows <doc_id>_p<N>.ext,
# including single-page documents (always "_p0"), confirmed against the
# real redaction_ground_truth.json.
_PAGE_FILENAME_RE = re.compile(r"^(?P<doc_id>.+)_p(?P<page_num>\d+)\.[A-Za-z0-9]+$")


def _group_by_document(docs: list[dict]) -> list[list[dict]]:
    """Groups per-page-image ground-truth entries back into their real
    multi-page documents, pages sorted in order within each group, so
    score() can thread extract_fields's balance_sheet_section across
    pages the same way pipeline.py's real _run_ocr_path loop does.
    Scoring each page image in total isolation (the original behavior)
    can never demonstrate a fix whose whole point is carrying state
    ACROSS pages -- confirmed real: total_current_liabilities stayed at
    0/18 in that mode even after #297's fix, purely because this
    scorer never simulated the real multi-page call chain, not because
    the fix didn't work (verified separately via a direct two-call
    test on Balance-sheet-template-FILLED-300_p1.png/_p2.png). Preserves
    each doc_id's first-appearance order so report output stays stable."""
    groups: dict[str, list[tuple[int, dict]]] = {}
    order: list[str] = []
    for doc in docs:
        match = _PAGE_FILENAME_RE.match(doc["filename"])
        doc_id, page_num = match.group("doc_id"), int(match.group("page_num"))
        if doc_id not in groups:
            groups[doc_id] = []
            order.append(doc_id)
        groups[doc_id].append((page_num, doc))
    return [[d for _, d in sorted(groups[doc_id])] for doc_id in order]


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
    import sys
    import time

    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    totals = {f: 0 for f in FIELDS}
    correct = {f: 0 for f in FIELDS}
    misses = []

    docs = ground_truth["documents"]
    document_groups = _group_by_document(docs)
    page_count = 0
    for group in document_groups:
        # Issue #297 -- reset per real document (not per page): a
        # section header carried in from an unrelated PRECEDING
        # document would be a real bug of its own, same class as the
        # one this carry-through exists to fix.
        balance_sheet_section: str | None = None
        for doc in group:
            filename = doc["filename"]
            page_count += 1
            t0 = time.monotonic()
            image_path = IMAGE_DIR / filename
            img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)

            extracted = extract_fields(img, lang="en", initial_section=balance_sheet_section)
            balance_sheet_section = extracted["balance_sheet_section"]
            ocr_fields = extracted["fields"]
            predicted_boxes = find_sensitive_boxes(img, ocr_fields, table_ocr_preds=extracted["table_ocr_preds"])
            elapsed = time.monotonic() - t0
            print(f"[{page_count}/{len(docs)}] {filename} ({elapsed:.1f}s)", file=sys.stderr, flush=True)

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

    def test_group_by_document_sorts_pages_and_preserves_doc_order():
        # Issue #297 -- pages fed out of order, across two documents
        # interleaved, must regroup correctly: each doc's own pages
        # sorted p0/p1/p2, doc B first (its p0 appeared first).
        docs = [
            {"filename": "DocB_p0.png"},
            {"filename": "DocA_p2.png"},
            {"filename": "DocA_p0.png"},
            {"filename": "DocA_p1.png"},
            {"filename": "DocB_p1.png"},
        ]
        groups = _group_by_document(docs)
        assert [d["filename"] for d in groups[0]] == ["DocB_p0.png", "DocB_p1.png"]
        assert [d["filename"] for d in groups[1]] == ["DocA_p0.png", "DocA_p1.png", "DocA_p2.png"]

    def test_group_by_document_single_page_doc_is_its_own_group():
        docs = [{"filename": "SoloContract_p0.png"}]
        groups = _group_by_document(docs)
        assert len(groups) == 1
        assert len(groups[0]) == 1

    tests = [
        test_identical_boxes_iou_is_one,
        test_disjoint_boxes_iou_is_zero,
        test_partial_overlap_hand_computed,
        test_group_by_document_sorts_pages_and_preserves_doc_order,
        test_group_by_document_single_page_doc_is_its_own_group,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")

    score()
