import sys

sys.path.insert(0, ".")

import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

import module1_opencv
from main import app

client = TestClient(app)

with open("samples/en_contract/part-time-employment-contract.docx", "rb") as f:
    _DOCX_BYTES = f.read()

with open("samples/en_pay_slip/Screenshot 2026-07-28 152419.png", "rb") as f:
    _IMAGE_BYTES = f.read()

with open("samples/en_balance_sheet/Machias_Balance-sheet-template.pdf", "rb") as f:
    _PDF_BYTES = f.read()


def test_docx_upload_returns_text_native_result():
    response = client.post(
        "/process",
        files={"file": ("payslip.docx", _DOCX_BYTES, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["processing_path"] == "text_native"
    assert body["redaction"]["type"] == "spans"
    assert body["loan_readiness"] is None


def test_image_upload_returns_ocr_result():
    response = client.post(
        "/process",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["processing_path"] == "ocr"
    assert body["redaction"]["type"] == "boxes"


def test_unsupported_file_returns_200_with_error():
    response = client.post(
        "/process",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is not None
    assert body["fields"] is None


def test_missing_file_field_is_a_real_4xx():
    # FastAPI's own request validation, not pipeline error handling --
    # this is the one case that's NOT a 200-with-error, per Decision 6.
    response = client.post("/process")
    assert response.status_code == 422


def test_repayment_amount_populates_loan_readiness():
    response = client.post(
        "/process",
        files={"file": ("payslip.docx", _DOCX_BYTES, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"proposed_monthly_repayment": "1000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["loan_readiness"] is not None
    assert body["loan_readiness"]["verdict"] in ("READY", "NOT_READY", "INSUFFICIENT_DATA")


def test_apply_redaction_blacks_out_region():
    items = json.dumps([{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.3, "h_pct": 0.1}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
        data={"items": items},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    arr = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    h, w = arr.shape[:2]
    y, x = int(0.15 * h), int(0.2 * w)
    assert arr[y, x].tolist() == [0, 0, 0]


def test_apply_redaction_empty_items_is_422():
    response = client.post(
        "/apply-redaction",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
        data={"items": "[]"},
    )
    assert response.status_code == 422


def test_apply_redaction_uses_enhanced_not_raw_dimensions():
    raw = cv2.imdecode(np.frombuffer(_IMAGE_BYTES, dtype=np.uint8), cv2.IMREAD_COLOR)
    expected = module1_opencv.enhance(raw)["image"]

    response = client.post(
        "/apply-redaction",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
        data={"items": '[{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1}]'},
    )
    assert response.status_code == 200
    arr = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert arr.shape[:2] == expected.shape[:2]
    # sanity: this must actually be a DIFFERENT shape than the raw upload,
    # or this test can't tell enhanced from raw at all on this fixture
    assert arr.shape[:2] != raw.shape[:2]


def test_apply_redaction_bad_items_json_is_422():
    response = client.post(
        "/apply-redaction",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
        data={"items": "not json"},
    )
    assert response.status_code == 422


def test_apply_redaction_accepts_pdf_via_render_first_page():
    # Issue #207 -- a scanned PDF already has real box coordinates
    # (computed via the same OCR path an image takes), so the endpoint
    # must render and redact it too, not just PNG/JPG/JPEG. This fixture
    # happens to route "text_native" in file_routing's own classification
    # (no genuinely scanned PDF exists in the current sample corpus), but
    # that distinction is BE's gate to enforce -- this endpoint itself
    # doesn't discriminate scanned vs text-native PDFs, it just renders
    # whatever PDF bytes it's given and draws boxes on page 1.
    items = json.dumps([{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("balance-sheet.pdf", _PDF_BYTES, "application/pdf")},
        data={"items": items},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    arr = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert arr.shape[0] > 0 and arr.shape[1] > 0


def test_apply_redaction_undecodable_pdf_is_422():
    response = client.post(
        "/apply-redaction",
        files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")},
        data={"items": '[{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1}]'},
    )
    assert response.status_code == 422


def test_apply_redaction_undecodable_file_is_422():
    response = client.post(
        "/apply-redaction",
        files={"file": ("fake.png", b"not a real image", "image/png")},
        data={"items": "[]"},
    )
    assert response.status_code == 422


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
