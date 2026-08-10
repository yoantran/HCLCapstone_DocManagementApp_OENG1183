from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile

from pipeline import process_document

app = FastAPI()


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    proposed_monthly_repayment: Optional[float] = Form(None),
    existing_monthly_debt: Optional[float] = Form(None),
) -> dict:
    file_bytes = await file.read()
    return process_document(
        filename=file.filename,
        file_bytes=file_bytes,
        proposed_monthly_repayment=proposed_monthly_repayment,
        existing_monthly_debt=existing_monthly_debt,
    )
