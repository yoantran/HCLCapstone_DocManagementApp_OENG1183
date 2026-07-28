import re

CCCD_RE = re.compile(r"\b\d{12}\b")
PHONE_RE = re.compile(r"(?:\+84|0)(?:3|5|7|8|9)\d{8}\b")
TAX_CODE_RE = re.compile(r"\b\d{10}(?:-\d{3})?\b")
DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
SALARY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")

LABEL_PATTERNS = {
    "name": re.compile(r"H[oọ]?\s*(?:và)?\s*t[eê]n\s*:\s*(.+)"),
    "address": re.compile(r"[ĐD][iị]a\s*ch[iỉ]\s*:\s*(.+)"),
}


def extract_regex_fields(text: str) -> dict:
    phone_matches = PHONE_RE.findall(text)
    # a VN mobile number is 10 digits, same length as a tax code — don't
    # double-count a phone match as a tax code
    tax_code_matches = [m for m in TAX_CODE_RE.findall(text) if m not in phone_matches]
    return {
        "cccd": CCCD_RE.findall(text),
        "phone": phone_matches,
        "tax_code": tax_code_matches,
        "dates": DATE_RE.findall(text),
        "salary": SALARY_RE.findall(text),
    }


def extract_label_anchored(text: str) -> dict:
    result = {}
    for field, pattern in LABEL_PATTERNS.items():
        match = pattern.search(text)
        result[field] = match.group(1).strip() if match else None
    return result


def _ner_fallback(text: str, missing_fields: list[str]) -> dict:
    # ponytail: no reliable pretrained Vietnamese NER model exists (see
    # project_name_extraction_strategy memory) — this tier stays unwired until
    # a real VN NER source is chosen. Upgrade here when Module 2 needs it.
    return {field: None for field in missing_fields}


def extract_fields_from_text(text: str) -> dict:
    fields = extract_regex_fields(text)
    fields.update(extract_label_anchored(text))
    missing = [f for f in ("name", "address") if not fields.get(f)]
    if missing:
        fields.update(_ner_fallback(text, missing))
    return fields
