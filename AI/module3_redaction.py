import re

from field_extraction import (
    CCCD_RE,
    PHONE_RE,
    TAX_CODE_RE,
    SALARY_RE,
    LABEL_PATTERNS,
    INCOME_LABEL_PATTERNS,
    _clean_label_value,
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

    tests = [
        test_single_occurrence_regex_field,
        test_multiple_occurrences_regex_field,
        test_label_anchored_skips_rejected_candidate,
        test_absent_field_produces_no_span,
        test_income_field_uses_matching_basis_pattern,
        test_all_spans_satisfy_text_slice_invariant,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
