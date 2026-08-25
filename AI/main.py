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
_process_lock = threading.Lock()


def _process_document_serialized(**kwargs) -> dict:
    with _process_lock:
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

    filename = (file.filename or "").lower()
    if filename.endswith(".docx"):
        try:
            file_bytes = file_routing.convert_docx_to_pdf_bytes(file_bytes)
        except Exception:
            raise HTTPException(status_code=422, detail="file is not a convertible docx") from None
        filename = filename[:-len(".docx")] + ".pdf"

    if filename.endswith(".pdf"):
        try:
            image = file_routing.render_pdf_first_page(file_bytes)
        except Exception:
            raise HTTPException(status_code=422, detail="file is not a decodable PDF") from None
        redaction_items = file_routing.resolve_item_boxes_via_pdf_text(file_bytes, redaction_items)
    else:
        image = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="file is not a decodable image")

    if is_text_native_item_shape and filename.endswith(".pdf"):
        final_image = image
    else:
        final_image = module1_opencv.enhance(image)["image"]
    redacted = module3_redaction.apply_redaction_image(final_image, redaction_items)
    ok, buf = cv2.imencode(".png", redacted)
    if not ok:
        raise HTTPException(status_code=500, detail="failed to encode redacted image")

    return Response(content=buf.tobytes(), media_type="image/png")
