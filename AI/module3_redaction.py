import re
import cv2
import numpy as np

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

# Field keys Module 3 is configured to detect and redact -- derived from
# the detectors themselves (not detection results), so a real detection
# miss on a given document degrades to a missing black box rather than
# silently reporting the field as "safe to show raw." annual_salary has
# no dedicated regex/label detector but is still a real sensitive field
# extracted by field_extraction_en.py -- included explicitly so it's
# never silently omitted.
SENSITIVE_FIELD_KEYS = sorted(set(_REGEX_LIST_FIELDS) | set(LABEL_PATTERNS) | {"income", "annual_salary"})


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
            # Issue #205 -- redact every occurrence of the real value (a
            # repeated name/address/bsb/account_number on a payslip header
            # AND footer both need a box), not just the first. Safe because
            # _matches_accepted_value is an exact string compare against
            # fields[field] -- a different real value that happens to match
            # the same label pattern elsewhere in the document is rejected,
            # not redacted.
            if not _matches_accepted_value(field, cleaned, fields):
                continue
            spans.append(
                {
                    "field": field,
                    "value": cleaned,
                    "start": start,
                    "end": end,
                    "detection_method": "regex",
                }
            )

    if fields.get("income") is not None:
        # income's fields value is a parsed float, not the raw printed
        # string, so (unlike the fields above) there's no exact-match check
        # available to safely redact every occurrence -- a different dollar
        # figure elsewhere in the document (a subtotal, a prior period) can
        # match the same label pattern and would be false-positive-redacted
        # without one. Keep the existing first-match-only behavior here
        # deliberately; fixing this for real needs Module 2 to expose which
        # match it actually parsed the accepted value from, out of scope
        # for #205.
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
                # No OCR word boxes overlap this occurrence specifically --
                # continue, not break: a LATER occurrence of the same real
                # value (#205) may still have overlapping word boxes even
                # though this one doesn't.
                continue
            boxes.append(
                {
                    "field": field,
                    "value": cleaned,
                    **_box_pct(_union_box(overlapping), img_h, img_w),
                    "detection_method": "regex",
                }
            )

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


def apply_redaction_image(image: np.ndarray, items: list[dict]) -> np.ndarray:
    """Burns filled black rectangles over each item's box. Coordinates are
    percentages of `image`'s own dimensions -- caller must pass the same
    enhanced image the coordinates were originally computed against
    (module1_opencv.enhance() output), never the raw upload."""
    img_h, img_w = image.shape[:2]
    redacted = image.copy()
    for item in items:
        x1 = int(item["x_pct"] * img_w)
        y1 = int(item["y_pct"] * img_h)
        x2 = int((item["x_pct"] + item["w_pct"]) * img_w)
        y2 = int((item["y_pct"] + item["h_pct"]) * img_h)
        cv2.rectangle(redacted, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    return redacted


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

    def test_label_anchored_field_redacts_every_occurrence():
        # Issue #205 -- a repeated address (header + footer) must get a
        # span for BOTH occurrences, not just the first.
        text = (
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Some other line in between.\n"
            "Employee Address: 42 Example Street, Melbourne VIC 3000"
        )
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 2
        starts = {s["start"] for s in address_spans}
        assert starts == {text.index("42 Example Street"), text.rindex("42 Example Street")}

    def test_label_anchored_field_does_not_redact_a_different_value():
        # A second "Employee Address:" line with a genuinely different
        # address (not the accepted fields.address value) must NOT get a
        # span -- _matches_accepted_value is what keeps #205's fix from
        # over-redacting a different real value that happens to match the
        # same label pattern elsewhere in the document.
        text = (
            "Employee Address: 42 Example Street, Melbourne VIC 3000\n"
            "Employee Address: 1 Other Street, Sydney NSW 2000"
        )
        fields = {"address": "42 Example Street, Melbourne VIC 3000"}
        spans = find_sensitive_spans(text, fields)
        address_spans = [s for s in spans if s["field"] == "address"]
        assert len(address_spans) == 1
        assert address_spans[0]["value"] == "42 Example Street, Melbourne VIC 3000"

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

    def test_apply_redaction_image_blacks_out_region_only():
        image = np.full((100, 200, 3), 255, dtype=np.uint8)  # all white
        items = [{"field": "bsb", "value": "x", "x_pct": 0.25, "y_pct": 0.25, "w_pct": 0.25, "h_pct": 0.25}]
        redacted = apply_redaction_image(image, items)
        # inside the box (x in [50,100), y in [25,50)) -> black
        assert redacted[35, 70].tolist() == [0, 0, 0]
        # outside the box -> untouched white
        assert redacted[5, 5].tolist() == [255, 255, 255]
        # input not mutated
        assert image[35, 70].tolist() == [255, 255, 255]

    def test_apply_redaction_image_no_items_returns_unchanged_copy():
        image = np.full((50, 50, 3), 200, dtype=np.uint8)
        redacted = apply_redaction_image(image, [])
        assert np.array_equal(redacted, image)

    tests = [
        test_single_occurrence_regex_field,
        test_multiple_occurrences_regex_field,
        test_label_anchored_skips_rejected_candidate,
        test_label_anchored_field_redacts_every_occurrence,
        test_label_anchored_field_does_not_redact_a_different_value,
        test_absent_field_produces_no_span,
        test_income_field_uses_matching_basis_pattern,
        test_all_spans_satisfy_text_slice_invariant,
        test_single_word_box,
        test_absent_field_no_box,
        test_value_not_in_fields_produces_no_box,
        test_apply_redaction_image_blacks_out_region_only,
        test_apply_redaction_image_no_items_returns_unchanged_copy,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
