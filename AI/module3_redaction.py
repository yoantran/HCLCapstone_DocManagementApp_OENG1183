import re

from field_extraction import (
    CCCD_RE,
    PHONE_RE,
    TAX_CODE_RE,
    SALARY_RE,
    LABEL_PATTERNS,
    INCOME_LABEL_PATTERNS,
    _clean_label_value,
    restore_name_diacritics,
)

_REGEX_LIST_FIELDS = {
    "cccd": CCCD_RE,
    "phone": PHONE_RE,
    "tax_code": TAX_CODE_RE,
    "salary": SALARY_RE,
}


def _cleaned_span(match: re.Match) -> tuple[str, int, int] | None:
    """Given a match whose group(1) is a raw label-anchored capture, return
    (cleaned_value, start, end) covering exactly the substring
    _clean_label_value accepts -- not the raw group, which may include
    leading/trailing whitespace _clean_label_value's .strip() discards.
    Deliberately does NOT apply any further display cleanup (e.g. name's
    diacritic restoration) -- a redaction span must match what's literally
    printed in the source text at that position, not a display-enhanced
    version of it."""
    raw = match.group(1)
    cleaned = _clean_label_value(raw)
    if cleaned is None:
        return None
    offset = raw.find(cleaned)
    start = match.start(1) + offset
    return cleaned, start, start + len(cleaned)


def find_sensitive_spans(text: str, fields: dict) -> list[dict]:
    spans = []

    # a VN mobile number is 10 digits, same length as a tax code -- exclude
    # phone-shaped matches from tax_code spans, same dedup
    # extract_regex_fields() already applies to the fields dict itself.
    phone_matches = set(PHONE_RE.findall(text))

    for field, pattern in _REGEX_LIST_FIELDS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            if field == "tax_code" and match.group(0) in phone_matches:
                continue
            spans.append(
                {
                    "field": field,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "detection_method": "regex",
                }
            )

    for field, pattern in LABEL_PATTERNS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            spans.append(
                {
                    "field": field,
                    "value": cleaned,
                    "start": start,
                    "end": end,
                    "detection_method": "regex",
                }
            )
            break

    if fields.get("income") is not None:
        pattern = INCOME_LABEL_PATTERNS.get(fields.get("income_basis"))
        if pattern is not None:
            for match in pattern.finditer(text):
                result = _cleaned_span(match)
                if result is None:
                    continue
                cleaned, start, end = result
                spans.append(
                    {
                        "field": "income",
                        "value": cleaned,
                        "start": start,
                        "end": end,
                        "detection_method": "regex",
                    }
                )
                break

    return spans


def _words_overlapping_span(word_spans: list[dict], start: int, end: int) -> list[dict]:
    return [w for w in word_spans if w["start"] < end and w["end"] > start]


def _union_box(words: list[dict]) -> tuple[int, int, int, int]:
    x1 = min(w["box"][0] for w in words)
    y1 = min(w["box"][1] for w in words)
    x2 = max(w["box"][2] for w in words)
    y2 = max(w["box"][3] for w in words)
    return x1, y1, x2, y2


def _matches_accepted_value(field: str, cleaned: str, fields: dict) -> bool:
    # fields["name"] is post-restore_name_diacritics(); the reconstruction's
    # raw cleaned match is not -- comparing them directly would reject
    # every correct name match. Apply the same transform before comparing.
    target = fields.get(field)
    if field == "name":
        return restore_name_diacritics(cleaned) == target
    return cleaned == target


def _box_pct(box: tuple[int, int, int, int], img_h: int, img_w: int) -> dict:
    x1, y1, x2, y2 = box
    return {
        "x_pct": x1 / img_w,
        "y_pct": y1 / img_h,
        "w_pct": (x2 - x1) / img_w,
        "h_pct": (y2 - y1) / img_h,
    }


def find_sensitive_boxes(image, fields: dict) -> list[dict]:
    from module2_ocr_tesseract import _word_data, _build_word_reconstruction

    img_h, img_w = image.shape[:2]
    data = _word_data(image)
    text, word_spans = _build_word_reconstruction(data)
    boxes = []

    for field, pattern in _REGEX_LIST_FIELDS.items():
        accepted = set(fields.get(field) or [])
        if not accepted:
            continue
        for match in pattern.finditer(text):
            value = match.group(0)
            if value not in accepted:
                continue
            overlapping = _words_overlapping_span(word_spans, match.start(), match.end())
            if not overlapping:
                continue
            boxes.append(
                {
                    "field": field,
                    "value": value,
                    **_box_pct(_union_box(overlapping), img_h, img_w),
                    "detection_method": "regex",
                }
            )

    for field, pattern in LABEL_PATTERNS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
            result = _cleaned_span(match)
            if result is None:
                continue
            cleaned, start, end = result
            if not _matches_accepted_value(field, cleaned, fields):
                continue
            overlapping = _words_overlapping_span(word_spans, start, end)
            if not overlapping:
                break
            boxes.append(
                {
                    "field": field,
                    "value": cleaned,
                    **_box_pct(_union_box(overlapping), img_h, img_w),
                    "detection_method": "regex",
                }
            )
            break

    if fields.get("income") is not None:
        # income's fields value is a parsed float, not the raw printed
        # string -- unlike the other label-anchored fields, there's no
        # string form to cross-check the reconstruction's match against
        # without changing Module 2's return contract (out of scope).
        # Accept the first clean match, same limitation find_sensitive_spans
        # already has for this field.
        pattern = INCOME_LABEL_PATTERNS.get(fields.get("income_basis"))
        if pattern is not None:
            for match in pattern.finditer(text):
                result = _cleaned_span(match)
                if result is None:
                    continue
                cleaned, start, end = result
                overlapping = _words_overlapping_span(word_spans, start, end)
                if overlapping:
                    boxes.append(
                        {
                            "field": "income",
                            "value": cleaned,
                            **_box_pct(_union_box(overlapping), img_h, img_w),
                            "detection_method": "regex",
                        }
                    )
                break

    return boxes


if __name__ == "__main__":
    def test_single_occurrence_regex_field():
        text = "MST TNCN: 8396543222\nHọ tên: Nguyễn Văn A"
        fields = {"tax_code": ["8396543222"]}
        spans = find_sensitive_spans(text, fields)
        tax_spans = [s for s in spans if s["field"] == "tax_code"]
        assert len(tax_spans) == 1
        assert tax_spans[0]["value"] == "8396543222"
        assert text[tax_spans[0]["start"]:tax_spans[0]["end"]] == "8396543222"

    def test_multiple_occurrences_regex_field():
        text = "SĐT: 0912345678\nSố khác: 0987654321"
        fields = {"phone": ["0912345678", "0987654321"]}
        spans = find_sensitive_spans(text, fields)
        phone_spans = [s for s in spans if s["field"] == "phone"]
        assert len(phone_spans) == 2
        values = {s["value"] for s in phone_spans}
        assert values == {"0912345678", "0987654321"}

    def test_label_anchored_skips_rejected_candidate():
        # first "Địa chỉ:" candidate is a filler placeholder (rejected by
        # _clean_label_value), second is the real address that Module 2
        # would have accepted -- span must land on the second, not the first.
        text = "Địa chỉ: ……………………\nĐịa chỉ: 123 Lê Lợi, Quận 1, TP.HCM"
        fields = {"address": "123 Lê Lợi, Quận 1, TP.HCM"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 1
        assert address_spans[0]["value"] == "123 Lê Lợi, Quận 1, TP.HCM"
        expected_start = text.index("123 Lê Lợi")
        assert address_spans[0]["start"] == expected_start

    def test_absent_field_produces_no_span():
        text = "Họ tên: Nguyễn Văn A"
        fields = {"bank_account": None}
        spans = find_sensitive_spans(text, fields)
        assert [s for s in spans if s["field"] == "bank_account"] == []

    def test_income_field_uses_matching_basis_pattern():
        text = "Tổng thu nhập chính thức: 30.000.000 VND\nThực lĩnh lương (1): 10.000.000 VND"
        fields = {"income": 30000000.0, "income_basis": "gross"}
        spans = find_sensitive_spans(text, fields)
        income_spans = [s for s in spans if s["field"] == "income"]
        assert len(income_spans) == 1
        assert income_spans[0]["value"] == "30.000.000 VND"

    def test_all_spans_satisfy_text_slice_invariant():
        text = (
            "MST TNCN: 8396543222\n"
            "SĐT: 0912345678\n"
            "Số TK: 0631000449323\n"
            "Địa chỉ: 123 Lê Lợi, Quận 1, TP.HCM\n"
            "Tổng thu nhập chính thức: 30.000.000 VND"
        )
        fields = {
            "tax_code": ["8396543222"],
            "phone": ["0912345678"],
            "bank_account": "0631000449323",
            "address": "123 Lê Lợi, Quận 1, TP.HCM",
            "income": 30000000.0,
            "income_basis": "gross",
        }
        spans = find_sensitive_spans(text, fields)
        assert len(spans) == 5
        for span in spans:
            assert text[span["start"]:span["end"]] == span["value"]

    from unittest.mock import patch
    import numpy as np

    _FAKE_IMAGE = np.zeros((100, 400, 3), dtype=np.uint8)  # 400x100 (w x h)

    def _fake_word_data(*args, **kwargs):
        return {
            "text": ["Số", "TK:", "0631000449323"],
            "conf": [90, 88, 95],
            "block_num": [1, 1, 1],
            "par_num": [1, 1, 1],
            "line_num": [1, 1, 1],
            "left": [10, 40, 90],
            "top": [20, 20, 20],
            "width": [25, 25, 120],
            "height": [15, 15, 15],
        }

    def test_single_word_box():
        with patch("module2_ocr_tesseract._word_data", side_effect=_fake_word_data):
            fields = {"bank_account": "0631000449323"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        bank_boxes = [b for b in boxes if b["field"] == "bank_account"]
        assert len(bank_boxes) == 1
        assert bank_boxes[0]["value"] == "0631000449323"
        assert abs(bank_boxes[0]["x_pct"] - 0.225) < 1e-6
        assert abs(bank_boxes[0]["y_pct"] - 0.20) < 1e-6
        assert abs(bank_boxes[0]["w_pct"] - 0.30) < 1e-6
        assert abs(bank_boxes[0]["h_pct"] - 0.15) < 1e-6

    def test_absent_field_no_box():
        with patch("module2_ocr_tesseract._word_data", side_effect=_fake_word_data):
            fields = {"bank_account": None}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "bank_account"] == []

    def test_value_not_in_fields_produces_no_box():
        with patch("module2_ocr_tesseract._word_data", side_effect=_fake_word_data):
            fields = {"bank_account": "9999999999999"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "bank_account"] == []

    tests = [
        test_single_occurrence_regex_field,
        test_multiple_occurrences_regex_field,
        test_label_anchored_skips_rejected_candidate,
        test_absent_field_produces_no_span,
        test_income_field_uses_matching_basis_pattern,
        test_all_spans_satisfy_text_slice_invariant,
        test_single_word_box,
        test_absent_field_no_box,
        test_value_not_in_fields_produces_no_box,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
