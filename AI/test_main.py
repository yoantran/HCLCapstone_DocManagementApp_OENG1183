import sys

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

with open("samples/en_contract/part-time-employment-contract.docx", "rb") as f:
    _DOCX_BYTES = f.read()

with open("samples/en_pay_slip/Screenshot 2026-07-28 152419.png", "rb") as f:
    _IMAGE_BYTES = f.read()


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


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
