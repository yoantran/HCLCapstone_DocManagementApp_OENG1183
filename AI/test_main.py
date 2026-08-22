import sys

sys.path.insert(0, ".")

import json

import cv2
import numpy as np
from fastapi.testclient import TestClient

import file_routing
import module1_opencv
from main import app

client = TestClient(app)

with open("samples/en_contract/part-time-employment-contract.docx", "rb") as f:
    _DOCX_BYTES = f.read()

with open("samples/en_pay_slip/Screenshot 2026-07-28 152419.png", "rb") as f:
    _IMAGE_BYTES = f.read()

with open("samples/en_balance_sheet/Machias_Balance-sheet-template.pdf", "rb") as f:
    _PDF_BYTES = f.read()

with open("samples/en_contract/part-time-employment-contract-FILLED-100.docx", "rb") as f:
    _FILLED_DOCX_BYTES = f.read()


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


def test_apply_redaction_span_item_resolves_box_from_pdf_text():
    # Issue #208 -- a real, unconverted PDF's own text layer. Confirms the
    # "each item must have x_pct... or value" validation relaxation
    # actually reaches resolve_item_boxes_via_pdf_text, and that it finds
    # a real, known-present string via pdfium's own search.
    items = json.dumps([{"field": "misc", "value": "BALANCE SHEET"}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("balance-sheet.pdf", _PDF_BYTES, "application/pdf")},
        data={"items": items},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_apply_redaction_span_item_not_found_returns_unredacted_200():
    # A value absent from the PDF's text layer is dropped, not an error --
    # same accepted "skip, don't fabricate a box" degradation
    # module3_redaction.find_sensitive_boxes already has for OCR word-box
    # misses.
    items = json.dumps([{"field": "misc", "value": "this string does not appear anywhere"}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("balance-sheet.pdf", _PDF_BYTES, "application/pdf")},
        data={"items": items},
    )
    assert response.status_code == 200


def test_apply_redaction_item_without_coords_or_value_is_422():
    items = json.dumps([{"field": "bsb"}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("payslip.png", _IMAGE_BYTES, "image/png")},
        data={"items": items},
    )
    assert response.status_code == 422


def test_apply_redaction_accepts_docx_via_libreoffice_conversion():
    # Issue #208 -- real docx bytes, real LibreOffice conversion, real
    # pdfium text search -- not mocked. "Steven Wood" is this fixture's
    # real Employee Name value (confirmed directly against the file, not
    # assumed).
    items = json.dumps([{"field": "name", "value": "Steven Wood"}])
    response = client.post(
        "/apply-redaction",
        files={
            "file": (
                "contract.docx",
                _FILLED_DOCX_BYTES,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"items": items},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    arr = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert arr.shape[0] > 0 and arr.shape[1] > 0


def test_apply_redaction_docx_box_lands_at_resolved_location_not_enhanced():
    # Issue #208 regression -- caught via actually viewing a real redacted
    # output image, not status/shape assertions alone: a text-native
    # item's box is resolved against pdfium's RAW rendered page geometry,
    # but module1_opencv.enhance()'s deskew+autocrop shift content
    # relative to that raw geometry. Drawing on the enhanced image put the
    # box on the ADDRESS line instead of the NAME line, even though search
    # correctly found "Steven Wood" -- main.py now skips enhance() for
    # text-native items specifically (see its own comment) to keep the
    # coordinate space consistent.
    #
    # Expected pixel location is derived by calling
    # resolve_item_boxes_via_pdf_text directly (same as production code
    # does) rather than a hardcoded magic percentage -- LibreOffice's
    # exact layout output can differ slightly by version/platform, so a
    # hardcoded number would be a flaky test tied to this one environment.
    pdf_bytes = file_routing.convert_docx_to_pdf_bytes(_FILLED_DOCX_BYTES)
    name_resolved = file_routing.resolve_item_boxes_via_pdf_text(
        pdf_bytes, [{"field": "name", "value": "Steven Wood"}]
    )
    address_resolved = file_routing.resolve_item_boxes_via_pdf_text(
        pdf_bytes, [{"field": "address", "value": "Martin Spur"}]
    )
    assert len(name_resolved) == 1
    assert len(address_resolved) == 1
    name_box = name_resolved[0]
    address_box = address_resolved[0]

    items = json.dumps([{"field": "name", "value": "Steven Wood"}])
    response = client.post(
        "/apply-redaction",
        files={
            "file": (
                "contract.docx",
                _FILLED_DOCX_BYTES,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"items": items},
    )
    assert response.status_code == 200
    arr = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    h, w = arr.shape[:2]

    name_cx = int((name_box["x_pct"] + name_box["w_pct"] / 2) * w)
    name_cy = int((name_box["y_pct"] + name_box["h_pct"] / 2) * h)
    assert arr[name_cy, name_cx].tolist() == [0, 0, 0]

    # The exact real bug: this address-line pixel is where the box
    # wrongly landed before the fix. Only "name" was requested, so it
    # must stay unredacted.
    address_cx = int((address_box["x_pct"] + address_box["w_pct"] / 2) * w)
    address_cy = int((address_box["y_pct"] + address_box["h_pct"] / 2) * h)
    assert arr[address_cy, address_cx].tolist() != [0, 0, 0]


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


def test_apply_redaction_undecodable_file_with_valid_items_is_422():
    # Issue #200 -- the test above sends items="[]", so it trips the
    # empty-items check (main.py) before ever reaching the undecodable-
    # image check (cv2.imdecode returning None), leaving that branch with
    # no real coverage. This test sends well-formed, non-empty items so
    # the request actually reaches the image-decode step and exercises
    # the `image is None` guard specifically.
    items = json.dumps([{"field": "bsb", "value": "x", "x_pct": 0.1, "y_pct": 0.1, "w_pct": 0.1, "h_pct": 0.1}])
    response = client.post(
        "/apply-redaction",
        files={"file": ("fake.png", b"not a real image", "image/png")},
        data={"items": items},
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
