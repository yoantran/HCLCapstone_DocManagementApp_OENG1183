import sys

sys.path.insert(0, ".")

import cv2
import numpy as np

from module2_text_extraction import extract_fields as extract_fields_text
from module2_ocr_extraction import extract_fields as extract_fields_ocr

TEXT_SAMPLE = "samples/en_contract/part-time-employment-contract.docx"
IMAGE_SAMPLE = "samples/en_pay_slip/Screenshot 2026-07-28 152419.png"


def test_text_native_path_exposes_income_keys():
    result = extract_fields_text(TEXT_SAMPLE)
    assert "income" in result["fields"]
    assert "income_basis" in result["fields"]


def test_ocr_path_exposes_income_keys():
    img = cv2.imdecode(np.fromfile(IMAGE_SAMPLE, dtype=np.uint8), cv2.IMREAD_COLOR)
    result = extract_fields_ocr(img)
    assert "income" in result["fields"]
    assert "income_basis" in result["fields"]


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
