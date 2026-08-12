import re

from field_extraction_en import (
    ABN_RE,
    PHONE_RE,
    SALARY_RE,
    LABEL_PATTERNS,
    INCOME_LABEL_PATTERNS,
    _clean_label_value,
)

_REGEX_LIST_FIELDS = {
    "abn": ABN_RE,
    "phone": PHONE_RE,
    "salary": SALARY_RE,
}


def _cleaned_span(match: re.Match) -> tuple[str, int, int] | None:
    """Given a match whose group(1) is a raw label-anchored capture, return
    (cleaned_value, start, end) covering exactly the substring
    _clean_label_value accepts -- not the raw group, which may include
    leading/trailing whitespace _clean_label_value's .strip() discards."""
    raw = match.group(1)
    cleaned = _clean_label_value(raw)
    if cleaned is None:
        return None
    offset = raw.find(cleaned)
    start = match.start(1) + offset
    return cleaned, start, start + len(cleaned)


def find_sensitive_spans(text: str, fields: dict) -> list[dict]:
    spans = []

    for field, pattern in _REGEX_LIST_FIELDS.items():
        if not fields.get(field):
            continue
        for match in pattern.finditer(text):
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
    return cleaned == fields.get(field)


def _box_pct(box: tuple[int, int, int, int], img_h: int, img_w: int) -> dict:
    x1, y1, x2, y2 = box
    return {
        "x_pct": x1 / img_w,
        "y_pct": y1 / img_h,
        "w_pct": (x2 - x1) / img_w,
        "h_pct": (y2 - y1) / img_h,
    }


def find_sensitive_boxes(image, fields: dict) -> list[dict]:
    from module2_ocr_extraction import build_word_reconstruction

    img_h, img_w = image.shape[:2]
    text, word_spans = build_word_reconstruction(image)
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
        text = "ABN: 12 345 978 910\nEmployee: Jo Worker"
        fields = {"abn": ["12 345 978 910"]}
        spans = find_sensitive_spans(text, fields)
        abn_spans = [s for s in spans if s["field"] == "abn"]
        assert len(abn_spans) == 1
        assert abn_spans[0]["value"] == "12 345 978 910"
        assert text[abn_spans[0]["start"]:abn_spans[0]["end"]] == "12 345 978 910"

    def test_multiple_occurrences_regex_field():
        text = "Phone: 0412345678\nOther: 0398765432"
        fields = {"phone": ["0412345678", "0398765432"]}
        spans = find_sensitive_spans(text, fields)
        phone_spans = [s for s in spans if s["field"] == "phone"]
        assert len(phone_spans) == 2
        values = {s["value"] for s in phone_spans}
        assert values == {"0412345678", "0398765432"}

    def test_label_anchored_skips_rejected_candidate():
        # first "Employee Address:" candidate is an angle-bracket
        # placeholder (rejected by _clean_label_value), second is the real
        # address Module 2 would have accepted -- span must land on the
        # second, not the first.
        text = "Employee Address: <insert employee address>\nEmployee Address: 42 Example Street, Melbourne VIC 3000"
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 1
        assert address_spans[0]["value"] == "42 Example Street, Melbourne VIC 3000"
        expected_start = text.index("42 Example Street")
        assert address_spans[0]["start"] == expected_start

    def test_absent_field_produces_no_span():
        text = "Employee: Jo Worker"
        fields = {"bsb": None}
        spans = find_sensitive_spans(text, fields)
        assert [s for s in spans if s["field"] == "bsb"] == []

    def test_income_field_uses_matching_basis_pattern():
        text = "Total gross payment: $718.66\nNET PAY: $625.36"
        fields = {"income": 718.66, "income_basis": "gross"}
        spans = find_sensitive_spans(text, fields)
        income_spans = [s for s in spans if s["field"] == "income"]
        assert len(income_spans) == 1
        assert income_spans[0]["value"] == "$718.66"

    def test_all_spans_satisfy_text_slice_invariant():
        text = (
            "ABN: 12 345 978 910\n"
            "Phone: 0412345678\n"
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Total gross payment: $718.66"
        )
        fields = {
            "abn": ["12 345 978 910"],
            "phone": ["0412345678"],
            "address": "42 Example Street, Melbourne VIC 3000",
            "income": 718.66,
            "income_basis": "gross",
        }
        spans = find_sensitive_spans(text, fields)
        assert len(spans) == 4
        for span in spans:
            assert text[span["start"]:span["end"]] == span["value"]

    from unittest.mock import patch
    import numpy as np

    _FAKE_IMAGE = np.zeros((100, 400, 3), dtype=np.uint8)  # 400x100 (w x h)

    def _fake_word_reconstruction(*args, **kwargs):
        text = "Account: 1234 5678"
        word_spans = [
            {"word": "Account:", "box": (10, 20, 90, 35), "start": 0, "end": 8},
            {"word": "1234", "box": (95, 20, 120, 35), "start": 9, "end": 13},
            {"word": "5678", "box": (125, 20, 150, 35), "start": 14, "end": 18},
        ]
        return text, word_spans

    def test_single_word_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": "1234 5678"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        acct_boxes = [b for b in boxes if b["field"] == "account_number"]
        assert len(acct_boxes) == 1
        assert acct_boxes[0]["value"] == "1234 5678"
        assert abs(acct_boxes[0]["x_pct"] - 95 / 400) < 1e-6
        assert abs(acct_boxes[0]["y_pct"] - 20 / 100) < 1e-6
        assert abs(acct_boxes[0]["w_pct"] - (150 - 95) / 400) < 1e-6
        assert abs(acct_boxes[0]["h_pct"] - (35 - 20) / 100) < 1e-6

    def test_absent_field_no_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": None}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "account_number"] == []

    def test_value_not_in_fields_produces_no_box():
        with patch("module2_ocr_extraction.build_word_reconstruction", side_effect=_fake_word_reconstruction):
            fields = {"account_number": "9999 9999"}
            boxes = find_sensitive_boxes(_FAKE_IMAGE, fields)
        assert [b for b in boxes if b["field"] == "account_number"] == []

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
