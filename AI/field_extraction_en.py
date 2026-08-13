"""
English/Australian (en_AU) field extraction -- parallel to field_extraction.py,
not a modification of it. Kept as a separate module deliberately: the
Vietnamese pipeline stays untouched and independently correct; this one is
built and grounded against real downloaded Australian document templates
(samples/en_pay_slip, en_contract, en_balance_sheet), not translated
guesses. See issue #128.

Real evidence this module's patterns are grounded in:
- Pay-slip-template-sts.docx: the actual Fair Work Ombudsman (Australia's
  labor authority) official pay slip template -- "*Employer:", "*ABN:",
  "*Employee:", "BSB:", "Account:", "Total gross payment", "NET PAY" are
  the legally-required label conventions, not invented.
- part-time-employment-contract.docx: "Employee Name:", "Employee Address:"
  as colon-anchored inline labels, same structure as the Vietnamese
  LABEL_PATTERNS convention.
- A real filled English payslip (tested this session): dollar amounts use
  cents ("$27.81", "$417.15"), not thousands-grouped round numbers like
  Vietnamese salary figures -- SALARY_RE here is genuinely different from
  field_extraction.py's, not a copy.
- Searched the full downloaded corpus for a personal national-ID or phone
  field (TFN, Medicare Number, Phone, Mobile) -- found none. Australian
  payslips don't print Tax File Numbers (privacy-sensitive by law).
  cccd/tax_code have no equivalent here and are dropped, not renamed.
"""
import re

from field_extraction import _clean_label_value as _clean_label_value_base

DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")  # DD/MM/YYYY -- same convention as Vietnamese, confirmed on a real sample

# $ prefix required -- real payslip tables have bare hour counts ("15.0",
# "8.0") in the same rows as dollar amounts ("$27.81"); without requiring
# "$", hours would be misread as salary values.
SALARY_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b")

# 11 digits, grouped 2-3-3-3 with spaces -- confirmed on every real ABN
# seen ("12 345 978 910", "89 002 605 076"). This is a business
# registration number, not a personal ID -- closest real equivalent to
# field_extraction.py's tax_code, not to cccd (no personal-ID equivalent
# exists in this document set at all).
ABN_RE = re.compile(r"\b\d{2}[ ]\d{3}[ ]\d{3}[ ]\d{3}\b")

# Best-effort -- zero real samples in the downloaded corpus show a phone
# field at all (searched all templates directly). Kept cheap/low-risk
# rather than dropped, in case a real document does include one.
PHONE_RE = re.compile(r"\b0[2-478](?:[ ]?\d){8}\b")

# Capture groups stop at a literal "[" as well as a real newline (not just
# "\n" like a bare ".+" would) -- issue #138: module2_text_extraction.py
# joins a docx table row's cells with a space, not a newline, so a label
# that's the last paragraph in a merged/duplicated table cell (e.g. real
# Fair Work template "Account: <value>") runs straight into the next
# cell's bracketed instructional aside ("[This is the amount paid...")
# with nothing to stop ".+"'s capture. Every real instructional aside in
# the downloaded corpus is "[...]"-delimited (confirmed directly), so
# bounding the capture there is a targeted fix, not a guess -- and a
# no-op for every field that was already passing, since none of their
# real values legitimately contain a "[".
LABEL_PATTERNS = {
    # "Employee" and "Employer" are different words (not substrings of each
    # other) -- safe to anchor on "Employee" alone without accidentally
    # matching "Employer" lines.
    "name": re.compile(r"Employee(?:\s*Name)?\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    "address": re.compile(r"Employee\s*Address\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    "bsb": re.compile(r"BSB\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    "account_number": re.compile(r"Account\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
}

INCOME_LABEL_PATTERNS = {
    "gross": re.compile(r"(?:Total\s*gross\s*payment|Gross\s*Pay)\s*:?[ \t]*([^\[\n]*)", re.IGNORECASE),
    "net": re.compile(r"(?:NET\s*PAY|Total\s*net\s*payment|Net\s*Pay)\s*:?[ \t]*([^\[\n]*)", re.IGNORECASE),
}

# Real placeholder conventions found in the downloaded corpus that
# field_extraction.py's _clean_label_value doesn't cover -- Vietnamese
# templates use dots/underscores/square brackets; these Australian
# templates use angle brackets ("<insert employee name>") and curly
# braces ("{insert full name}") too.
_ANGLE_BRACKET_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")
_CURLY_BRACE_PLACEHOLDER_RE = re.compile(r"^\{[^{}]*\}$")


def _clean_label_value(value: str) -> str | None:
    value = value.strip()
    if _ANGLE_BRACKET_PLACEHOLDER_RE.match(value) or _CURLY_BRACE_PLACEHOLDER_RE.match(value):
        return None
    # reuses field_extraction.py's filler/bracket/colon-bleed/shouty-title
    # checks -- all format-based, not Vietnamese-language-based, so they
    # apply correctly here too. Its Vietnamese-specific checks (placeholder
    # name stripping, legal-boilerplate rejection) simply never match
    # English text -- harmless no-ops, not incorrectly-applied logic.
    return _clean_label_value_base(value)


def parse_currency_amount(value: str) -> float | None:
    match = re.search(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})?", value)
    if match is None:
        return None
    digits = match.group(0).replace(",", "")
    return float(digits)


def extract_regex_fields_en(text: str) -> dict:
    return {
        "abn": ABN_RE.findall(text),
        "phone": PHONE_RE.findall(text),
        "dates": DATE_RE.findall(text),
        "salary": SALARY_RE.findall(text),
    }


def extract_label_anchored_en(text: str) -> dict:
    result = {}
    for field, pattern in LABEL_PATTERNS.items():
        value = None
        for match in pattern.finditer(text):
            cleaned = _clean_label_value(match.group(1))
            if cleaned is not None:
                value = cleaned
                break
        result[field] = value
    return result


def extract_income_en(text: str) -> tuple[float | None, str | None]:
    for basis in ("gross", "net"):
        for match in INCOME_LABEL_PATTERNS[basis].finditer(text):
            cleaned = _clean_label_value(match.group(1))
            if cleaned is None:
                continue
            amount = parse_currency_amount(cleaned)
            if amount is not None:
                return amount, basis
    return None, None


def extract_fields_from_text_en(text: str, table_rows: list[list[str]] | None = None) -> dict:
    fields = extract_regex_fields_en(text)
    fields.update(extract_label_anchored_en(text))
    fields["income"], fields["income_basis"] = extract_income_en(text)
    return fields
