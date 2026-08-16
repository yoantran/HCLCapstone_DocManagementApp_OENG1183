"""
Real accuracy measurement for balance-sheet field extraction (text-native
docx path), against a synthetic filled validation batch -- same shape as
measure_accuracy.py's payslip/contract corpus (#131), applied to #6.

Ground truth comes from re-running the same deterministic (seed, template)
pairs used to generate the batch -- fill_docx() returns exactly which
value it inserted for which field, so there's no need to hand-annotate
anything. This rewrites the already-committed -FILLED files with
byte-identical content (same seed + same source = same output), it does
not change them.

Two source templates, not one (matching payslip/contract's 2-template
precedent):
- CIC-Balance-Sheet-Template.docx: lettered A-S rows, single value column.
  Only 4 of 5 tracked fields are fillable -- this real template's own
  "Total Current Assets" row has no blank cell at all, confirmed by
  direct inspection. total_current_assets has no ground truth from this
  source and is correctly never counted against it.
- Balance sheet template.docx: 5 year-columns per row, real "Year N"
  header text (#182/#192 period-selection is what makes this template's
  ground truth resolvable at all -- Year 5, the rightmost/highest-
  numbered column, is what's scored). All 5 fields fillable.
"""

from _fill_templates import fill_docx
from field_extraction_en import parse_currency_amount_balance_sheet
from module2_text_extraction import extract_fields

BALANCE_SHEET_FIELDS = (
    "total_current_assets",
    "total_assets",
    "total_current_liabilities",
    "total_liabilities",
    "total_equity",
)

CIC_SRC = "samples/en_balance_sheet/CIC-Balance-Sheet-Template.docx"
YEARS_SRC = "samples/en_balance_sheet/Balance sheet template.docx"
REPS_PER_TEMPLATE = 15


def build_manifest() -> list[tuple[str, str, int]]:
    manifest = []
    seed = 200

    for _ in range(REPS_PER_TEMPLATE):
        dst = f"samples/en_balance_sheet/CIC-Balance-Sheet-Template-FILLED-{seed}.docx"
        manifest.append((CIC_SRC, dst, seed))
        seed += 1

    for _ in range(REPS_PER_TEMPLATE):
        dst = f"samples/en_balance_sheet/Balance-sheet-template-FILLED-{seed}.docx"
        manifest.append((YEARS_SRC, dst, seed))
        seed += 1

    return manifest


def score() -> None:
    manifest = build_manifest()
    totals = {f: 0 for f in BALANCE_SHEET_FIELDS}
    correct = {f: 0 for f in BALANCE_SHEET_FIELDS}
    misses = []

    for src, dst, seed in manifest:
        _, ground_truth = fill_docx(src, dst, seed=seed)
        extracted = extract_fields(dst)["fields"]

        for field in BALANCE_SHEET_FIELDS:
            gt_values = ground_truth.get(field)
            if not gt_values:
                continue
            expected = parse_currency_amount_balance_sheet(gt_values[0])
            totals[field] += 1
            got = extracted.get(field)
            if got is not None and abs(got - expected) < 0.01:
                correct[field] += 1
            else:
                misses.append((dst, field, expected, got))

    with open("balance_sheet_accuracy_report.txt", "w", encoding="utf-8") as out:
        out.write(f"Documents scored: {len(manifest)}\n\n")
        out.write("Per-field accuracy (correct / total ground-truth values):\n")
        overall_correct = overall_total = 0
        for field in BALANCE_SHEET_FIELDS:
            t, c = totals[field], correct[field]
            pct = f"{100 * c / t:.1f}%" if t else "n/a (no ground truth)"
            out.write(f"  {field:25s}: {c:3d} / {t:3d}  ({pct})\n")
            overall_correct += c
            overall_total += t
        overall_pct = f"{100 * overall_correct / overall_total:.1f}%" if overall_total else "n/a"
        out.write(f"\nOverall: {overall_correct} / {overall_total}  ({overall_pct})\n")

        out.write(f"\nMisses ({len(misses)}):\n")
        for dst, field, expected, got in misses:
            out.write(f"  {dst}\n    field={field} expected={expected!r} got={got!r}\n")

    print("saved balance_sheet_accuracy_report.txt")


if __name__ == "__main__":
    score()
