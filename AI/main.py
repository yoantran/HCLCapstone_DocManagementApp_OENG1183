import asyncio
import json
import threading
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

import file_routing
import module1_opencv
import module3_redaction
from demo import DEMO_HTML
from pipeline import process_document

app = FastAPI()

# Issue #195 -- /process is declared async but calls process_document()
# synchronously with no await/offload, blocking uvicorn's single event
# loop for the whole OCR-bound duration; confirmed via docker logs that a
# second request isn't even accepted/logged until the first finishes.
# Offloading to a thread (asyncio.to_thread) frees the event loop so
# FastAPI accepts/queues other requests instead of stalling at the
# connection level -- the real fix this unblocks without any GPU/budget
# decision. The lock below keeps actual processing serialized: module2_
# ocr_extraction.py caches ONE shared PPStructureV3/PaddleOCR instance per
# language at module scope, reused across every call, and there's no
# confirmed evidence Paddle's inference predictors are safe for
# concurrent .predict() calls on the same instance from multiple threads
# -- getting that wrong risks silent wrong OCR output, not just a crash,
# so this doesn't add real throughput (matches the issue's own "doesn't
# add true parallelism" framing) until that's verified safe to remove.
#
# Issue #341 -- this lock (originally scoped to /process's own OCR model
# safety) is also the ONLY thing standing between a real crash/corruption
# risk on /apply-redaction, which was found to have never received #195's
# fix at all: it ran its entire pdfium/LibreOffice/cv2 pipeline directly
# in the coroutine body, with no offload and no lock. pypdfium2 (and the
# underlying PDFium C library it wraps) is explicitly documented as not
# thread-safe -- "not allowed to call pdfium functions simultaneously
# across different threads, not even with different documents" (pdfium
# upstream guidance; see also pypdfium2-team/pypdfium2#303). /process's
# own pipeline (pipeline.py, module2_text_extraction.py) also calls
# pdfium, so a /process call already dispatched to its background thread
# and a concurrent /apply-redaction call running synchronously on the
# event loop could genuinely call pdfium from two different OS threads
# at the same real moment under real concurrent usage -- a live hazard,
# not just a slowness one. Renamed from _process_lock (misleadingly
# implied /process-only scope) since it now guards both endpoints against
# the same real shared constraint: PDFium's global, not per-endpoint or
# per-document, thread-safety limitation.
_native_library_lock = threading.Lock()


def _process_document_serialized(**kwargs) -> dict:
    with _native_library_lock:
        return process_document(**kwargs)

# Permissive local-dev CORS -- lets a standalone local HTML demo page (or
# any other local tool) call this API from a different origin (including
# file:// pages, which send Origin: null). Fine for local/dev use; BE's
# real caller doesn't need this since server-to-server calls aren't
# subject to CORS at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/demo", response_class=HTMLResponse)
async def demo() -> str:
    return DEMO_HTML


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    proposed_monthly_repayment: Optional[float] = Form(None),
    existing_monthly_debt: Optional[float] = Form(None),
    include_preview: bool = Form(False),
) -> dict:
    file_bytes = await file.read()
    return await asyncio.to_thread(
        _process_document_serialized,
        filename=file.filename,
        file_bytes=file_bytes,
        proposed_monthly_repayment=proposed_monthly_repayment,
        existing_monthly_debt=existing_monthly_debt,
        include_preview=include_preview,
    )


@app.post("/apply-redaction", responses={200: {"content": {"image/png": {}}}})
async def apply_redaction(
    file: UploadFile = File(...),
    items: str = Form(...),
) -> Response:
    file_bytes = await file.read()
    png_bytes = await asyncio.to_thread(
        _apply_redaction_serialized, file_bytes, items, file.filename or ""
    )
    return Response(content=png_bytes, media_type="image/png")


def _apply_redaction_serialized(file_bytes: bytes, items: str, filename: str) -> bytes:
    with _native_library_lock:
        return _apply_redaction_sync(file_bytes, items, filename)


def _apply_redaction_sync(file_bytes: bytes, items: str, filename: str) -> bytes:
    try:
        redaction_items = json.loads(items)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="items must be valid JSON") from None

    if not isinstance(redaction_items, list) or not redaction_items:
        raise HTTPException(status_code=422, detail="items must be a non-empty list of redaction boxes")
    # Issue #208 -- a text-native document's stored items are spans (no
    # x_pct/etc, see pipeline.py's _run_text_native_path), resolved to real
    # boxes below via resolve_item_boxes_via_pdf_text. Only `value` is
    # required for those; the OCR/scanned-PDF shape (#207) still requires
    # real coordinates since nothing here re-resolves them.
    if not all(isinstance(item, dict) and (
        {"x_pct", "y_pct", "w_pct", "h_pct"} <= item.keys() or "value" in item
    ) for item in redaction_items):
        raise HTTPException(status_code=422, detail="each item must have x_pct/y_pct/w_pct/h_pct or a value")

    # Issue #207 -- a scanned PDF (no real text layer) already went
    # through the OCR/image path at upload time and has real box
    # coordinates, so it deserves a preview too, not just PNG/JPG/JPEG.
    # Issue #208 -- a genuinely text-native PDF, or a docx (converted to
    # PDF first via LibreOffice so it can reuse the exact same render +
    # text-search machinery), also gets one now: resolve_item_boxes_via_
    # pdf_text finds each span's box by searching the rendered page's own
    # text layer, so no coordinates need to have existed ahead of time.
    # Caught by actually viewing a real redacted output image, not just a
    # 200 status code: a text-native item's box (below) is computed
    # against pdfium's RAW rendered page geometry. module1_opencv.enhance()
    # deskews (rotates) and autocrops (trims to content, non-uniformly)
    # -- either one shifts content relative to a percentage computed
    # against the pre-enhance image, so drawing a text-native box onto the
    # enhanced image silently redacts the wrong region. The #207
    # scanned-PDF/OCR path doesn't have this problem: its box percentages
    # are computed by find_sensitive_boxes AFTER enhance() already ran, at
    # upload time -- enhance() is deterministic, so re-running it here on
    # the same bytes reproduces the same crop/rotation those percentages
    # already assume. A vector-rendered PDF page also has no real scan
    # skew/noise to correct in the first place, so skipping enhance() for
    # a text-native item isn't a workaround, it's the correct behavior.
    is_text_native_item_shape = any("x_pct" not in item for item in redaction_items)

    filename = filename.lower()
    if filename.endswith(".docx"):
        try:
            file_bytes = file_routing.convert_docx_to_pdf_bytes(file_bytes)
        except Exception:
            raise HTTPException(status_code=422, detail="file is not a convertible docx") from None
        filename = filename[:-len(".docx")] + ".pdf"

    if filename.endswith(".pdf"):
        try:
            if is_text_native_item_shape:
                # Issue #283 -- a text-native item's box isn't known to be
                # on page 1, so render every page and let
                # resolve_item_boxes_via_pdf_text search all of them,
                # against this same composite image's coordinate space.
                final_image = file_routing.stack_pages_vertically(file_routing.render_pdf_all_pages(file_bytes))
            else:
                # Issue #286 -- an x_pct item's coordinates were baked at
                # upload time against a composite of each page's OWN
                # enhanced image (pipeline.py::_run_ocr_path's
                # boxes_to_composite_pct), not the raw rendered pages --
                # reproduce that here identically (enhance() is
                # deterministic per page, same invariant the single-page
                # case already relies on below). Compositing the raw
                # pages first and enhancing the whole stack afterward
                # would be wrong: deskew/autocrop would run across page
                # boundaries as if it were one image, not one call per
                # real page.
                pages = file_routing.render_pdf_all_pages(file_bytes)
                enhanced_pages = [module1_opencv.enhance(p)["image"] for p in pages]
                final_image = file_routing.stack_pages_vertically(enhanced_pages)
        except Exception:
            raise HTTPException(status_code=422, detail="file is not a decodable PDF") from None
        redaction_items = file_routing.resolve_item_boxes_via_pdf_text(file_bytes, redaction_items)
    else:
        image = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=422, detail="file is not a decodable image")
        final_image = image if is_text_native_item_shape else module1_opencv.enhance(image)["image"]

    redacted = module3_redaction.apply_redaction_image(final_image, redaction_items)
    ok, buf = cv2.imencode(".png", redacted)
    if not ok:
        raise HTTPException(status_code=500, detail="failed to encode redacted image")

    return buf.tobytes()
