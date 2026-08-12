"""
Real accuracy measurement for Module 2's IMAGE path (module2_ocr_extraction.py
-- PaddleOCR/PPStructureV3), reusing the exact same ground-truth mechanism as
measure_accuracy.py (the text-native path): fill_docx() with a fixed seed
tells us exactly which value it inserted for which field.

Each -FILLED.docx is rendered to a PNG (soffice -> PDF -> pdfium page render)
so the OCR path actually has to read pixels, not structured XML -- this is
the missing measurement flagged after the text-native branch hit 100%.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np
import pypdfium2 as pdfium

from _fill_templates import fill_docx
from field_extraction_en import extract_fields_from_text_en, parse_currency_amount
from measure_accuracy import build_manifest
from module1_opencv import enhance

SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
RENDER_DIR = Path("samples/_rendered_for_ocr_scoring")

SCALAR_FIELDS = {"name", "address", "bsb", "account_number"}
LIST_FIELDS = {"abn", "salary"}


def docx_to_pngs(docx_path: str, out_dir: Path, scale: float) -> list[Path]:
    """Renders every page of the docx, not just the first -- the real Fair
    Work payslip template runs to 4 PDF pages (instructional preamble +
    example on pages 0-1, the actual form split across pages 2-3), and a
    single production image upload is always one page anyway, so a real
    multi-page document isn't a case the production pipeline needs to
    handle -- this exists purely because the benchmark's source material
    is a multi-page instructional template, not a single scanned photo."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), docx_path],
        check=True, capture_output=True,
    )
    pdf_path = out_dir / (Path(docx_path).stem + ".pdf")
    pdf = pdfium.PdfDocument(str(pdf_path))
    png_paths = []
    for i, page in enumerate(pdf):
        png_path = out_dir / f"{Path(docx_path).stem}_p{i}.png"
        bitmap = page.render(scale=scale)
        bitmap.to_pil().save(png_path)
        png_paths.append(png_path)
    pdf.close()
    pdf_path.unlink()
    return png_paths


def _extract_fields_for_pages(png_paths: list[Path], lang: str = "en") -> list[dict]:
    """Runs each page's OCR in a completely fresh, isolated OS subprocess
    (_ocr_worker.py) -- no shared pipeline object, no shared native memory
    buffers between pages. Confirmed empirically this session: even a
    single, correctly *batched* predict() call within one process can
    occasionally surface a stale/wrong result for one page in the batch
    while the other pages are correct (e.g. name/bsb genuinely correct on
    3 of 4 pages, but one page returns coherent, real-looking data copied
    from a completely different, previously-processed image) -- a real,
    non-deterministic race in the third-party CPU inference engine's
    internal buffer handling (PaddleOCR/PaddleX PPStructureV3), not
    something closeable with a Python-level code change (looping vs.
    batching, with/without image preprocessing, and several other
    variables were each tested and ruled out individually). Process
    isolation closes it by construction: there is no memory left to share
    across separate OS processes. Slower (a fresh pipeline construction
    per page) but correct, which matters more for a benchmark whose whole
    purpose is producing a trustworthy number."""
    page_fields = []
    for png_path in png_paths:
        proc = subprocess.run(
            [sys.executable, "_ocr_worker.py", str(png_path), lang],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )
        payload = json.loads(proc.stdout)
        page_fields.append(extract_fields_from_text_en(payload["text"], table_rows=payload["table_rows"] or None))
    return page_fields


def _merge_page_fields(page_fields_list: list[dict]) -> dict:
    """Combines each rendered page's independently-extracted fields into
    one dict -- list fields (abn, salary, ...) concatenate across pages
    (each page can carry different real values, e.g. entitlements on page
    2 and deductions/superannuation on page 3 of the payslip template);
    scalar fields (name, bsb, ...) take the first page that actually found
    a value, since a given scalar field only ever appears on one page."""
    merged: dict = {}
    for fields in page_fields_list:
        for key, value in fields.items():
            if isinstance(value, list):
                merged[key] = merged.get(key, []) + value
            elif key not in merged or merged[key] in (None, ""):
                if value not in (None, ""):
                    merged[key] = value
                elif key not in merged:
                    merged[key] = value
    return merged


def score(render_scale: float = 2.0, use_enhance: bool = True, limit: int | None = None,
          report_path: str = "accuracy_report_image.txt") -> None:
    manifest = build_manifest()[:limit]
    totals = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    correct = {f: 0 for f in SCALAR_FIELDS | LIST_FIELDS}
    income_total = income_correct = 0
    misses = []

    for i, (src, dst, seed) in enumerate(manifest, 1):
        _, ground_truth = fill_docx(src, dst, seed=seed)

        png_paths = docx_to_pngs(dst, RENDER_DIR, render_scale)

        pipeline_input_paths = []
        for png_path in png_paths:
            if not use_enhance:
                pipeline_input_paths.append(png_path)
                continue
            # cv2.imread silently returns None on Unicode/bracket paths on
            # Windows (real filenames here, e.g. "[Mẫu tham khảo] HĐ lao
            # động-FILLED.png") -- imdecode from a manually-read buffer
            # sidesteps its path handling entirely.
            img = cv2.imdecode(np.fromfile(str(png_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            enhanced = enhance(img)["image"]
            enhanced_path = png_path.parent / f"{png_path.stem}_enhanced.png"
            cv2.imencode(".png", enhanced)[1].tofile(str(enhanced_path))
            pipeline_input_paths.append(enhanced_path)
        page_fields_list = _extract_fields_for_pages(pipeline_input_paths, lang="en")
        extracted = _merge_page_fields(page_fields_list)

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

        gt_income = ground_truth.get("income")
        if gt_income:
            income_total += 1
            expected = parse_currency_amount(gt_income[0])
            expected_basis = ground_truth["income_basis"][0]
            got = extracted.get("income")
            got_basis = extracted.get("income_basis")
            if got is not None and abs(got - expected) < 0.01 and got_basis == expected_basis:
                income_correct += 1
            else:
                misses.append((dst, "income", [gt_income[0]], (got, got_basis)))

    with open(report_path, "w", encoding="utf-8") as out:
        out.write(f"render_scale={render_scale} use_enhance={use_enhance}\n")
        out.write(f"Documents scored: {len(manifest)}\n\n")
        out.write("Per-field accuracy (correct / total ground-truth values):\n")
        overall_correct = overall_total = 0
        for field in ("name", "address", "bsb", "account_number", "abn", "salary"):
            t, c = totals[field], correct[field]
            pct = f"{100 * c / t:.1f}%" if t else "n/a (no ground truth)"
            out.write(f"  {field:15s}: {c:3d} / {t:3d}  ({pct})\n")
            overall_correct += c
            overall_total += t
        income_pct = f"{100 * income_correct / income_total:.1f}%" if income_total else "n/a"
        out.write(f"  {'income':15s}: {income_correct:3d} / {income_total:3d}  ({income_pct})\n")
        overall_correct += income_correct
        overall_total += income_total
        overall_pct = f"{100 * overall_correct / overall_total:.1f}%" if overall_total else "n/a"
        out.write(f"\nOverall: {overall_correct} / {overall_total}  ({overall_pct})\n")

        out.write(f"\nMisses ({len(misses)}):\n")
        for dst, field, expected, got in misses:
            out.write(f"  {dst}\n    field={field} expected={expected!r} got={got!r}\n")

    print(f"saved {report_path}  overall={overall_correct}/{overall_total} ({overall_pct})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--no-enhance", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report", default="accuracy_report_image.txt")
    args = ap.parse_args()
    score(render_scale=args.scale, use_enhance=not args.no_enhance, limit=args.limit, report_path=args.report)
