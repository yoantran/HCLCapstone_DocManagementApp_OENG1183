from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from demo import DEMO_HTML
from pipeline import process_document

app = FastAPI()

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
    return process_document(
        filename=file.filename,
        file_bytes=file_bytes,
        proposed_monthly_repayment=proposed_monthly_repayment,
        existing_monthly_debt=existing_monthly_debt,
        include_preview=include_preview,
    )
