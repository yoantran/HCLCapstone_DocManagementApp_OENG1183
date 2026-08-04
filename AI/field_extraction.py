import re

CCCD_RE = re.compile(r"\b\d{12}\b")
PHONE_RE = re.compile(r"(?:\+84|0)(?:3|5|7|8|9)\d{8}\b")
TAX_CODE_RE = re.compile(r"\b\d{10}(?:-\d{3})?\b")
DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
# Vietnamese locale properly uses "." as the thousands separator (not ","),
# but real payslip templates found in the wild use either -- e.g. a real
# sample used "5.000.000" while another used "5,964,265" for the same kind
# of figure. Match both rather than assuming one convention.
SALARY_RE = re.compile(r"\b\d{1,3}(?:[,.]\d{3})+\b")

# ponytail: labor contracts and payslips use several different real
# conventions for identifying the employee ("Họ tên", "BÊN B", "Tên NV") —
# this list grows as new templates surface, it's not a closed set.
# Deliberately NOT matching bare "tên:" (or "Người lao động") as a label —
# both recur in unrelated contexts ("Tên công ty:" = company name, "Tên
# đơn vị:" = unit name; "Người lao động" appears constantly in contract body
# prose) and would fire on the wrong thing, returning a nonsense "value"
# instead of the real one. A wrong value is worse than a missing one — only
# add label variants actually observed on a real document, not a maximally
# generic pattern.
LABEL_PATTERNS = {
    # [ \t]* (not \s*) right before the capture group — \s also matches
    # newlines, which let a blank field's label swallow the next unrelated
    # line as its "value" (e.g. a blank "Địa chỉ:" grabbing a page title on
    # the following line). Same-line whitespace only, so a genuinely blank
    # field correctly fails to match instead of bleeding into the next line.
    "name": re.compile(
        r"(?:H[oọ]?\s*(?:và)?\s*t[eê]n|BÊN\s*B|T[eê]n\s*NV)\s*:[ \t]*(.+)",
        re.IGNORECASE,
    ),
    "address": re.compile(r"[ĐD][iị]a\s*ch[iỉ]\s*:[ \t]*(.+)", re.IGNORECASE),
}

# a captured value that *starts* with placeholder/filler characters (dots,
# ellipsis, dashes) means the field is blank — whatever follows on the same
# line (a parenthetical note, the next field's label) is unrelated adjacent
# text, not the real value. Simpler and more robust than trying to detect
# where legitimate content ends.
_STARTS_WITH_FILLER_RE = re.compile(r"^[.…_\-]")

# some real templates use bracket-enclosed placeholder tokens instead of
# dots/ellipsis -- e.g. "Họ và tên: [member_name]" from a mail-merge-style
# template. If the whole captured value is exactly one bracketed token,
# it's a placeholder, not real data.
_BRACKET_PLACEHOLDER_RE = re.compile(r"^\[[^\[\]]*\]$")

# unfilled contract templates often follow a label directly with the role
# descriptor itself ("Bên B : Người lao động" = "Party B: [is] the
# employee"), not an actual name — only a filled contract replaces this with
# a real name. Treat these known generic-role phrases as blank too.
_GENERIC_ROLE_VALUES = {"người lao động", "người sử dụng lao động", "nlđ", "nsdlđ"}


def _clean_label_value(value: str) -> str | None:
    value = value.strip()
    if not value or _STARTS_WITH_FILLER_RE.match(value):
        return None
    if _BRACKET_PLACEHOLDER_RE.match(value):
        return None
    if value.lower() in _GENERIC_ROLE_VALUES:
        return None
    return value


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
        result[field] = _clean_label_value(match.group(1)) if match else None
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
