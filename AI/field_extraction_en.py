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
from datetime import datetime

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

# Real line on the Fair Work template: "*Annual salary: [if applicable]
# $67,000" -- a bracketed aside sits BETWEEN the label and the value,
# which would break LABEL_PATTERNS's bracket-bounded "rest of line"
# convention (issue #138) since that stops at the FIRST "[", which here
# precedes the real value. Anchored to the $-shape itself instead of a
# generic "rest of line" capture, with an optional bracketed aside
# skipped in between.
ANNUAL_SALARY_RE = re.compile(
    r"Annual\s*salary\s*:[ \t]*(?:\[[^\[\]]*\]\s*)?(\$[\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)

# Real line once a document is filled: "*Pay period: 16/07/2026 to
# 22/07/2026" -- the blank template's own placeholders ("<insert date>")
# are gone once fill_docx_payslip() runs, leaving clean DD/MM/YYYY dates
# with no bracket noise, unlike ANNUAL_SALARY_RE's label line.
PAY_PERIOD_RE = re.compile(
    r"Pay\s*period\s*:[ \t]*(\d{2}/\d{2}/\d{4})\s*to\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

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


def extract_annual_salary_en(text: str) -> float | None:
    match = ANNUAL_SALARY_RE.search(text)
    if match is None:
        return None
    return parse_currency_amount(match.group(1))


def extract_pay_period_days_en(text: str) -> int | None:
    match = PAY_PERIOD_RE.search(text)
    if match is None:
        return None
    start = datetime.strptime(match.group(1), "%d/%m/%Y")
    end = datetime.strptime(match.group(2), "%d/%m/%Y")
    return (end - start).days


# Issue #163 -- balance-sheet totals. Checked all 8 real templates in
# samples/en_balance_sheet/ directly: every one is a category-label-cell +
# adjacent-value-cell grid (never a colon-anchored single line like the
# payslip's "Total gross payment: $X"), which is why this pairs table
# cells rather than extending LABEL_PATTERNS. "Total Assets" deliberately
# won't match inside "Total Current Assets" -- \s* only matches
# whitespace, "Current" sits between them -- so these four patterns don't
# collide despite three sharing a "Total ... Assets/Liabilities" shape.
_BALANCE_SHEET_LABEL_RE = {
    "total_current_assets": re.compile(r"Total\s*Current\s*Assets", re.IGNORECASE),
    "total_assets": re.compile(r"Total\s*Assets", re.IGNORECASE),
    "total_current_liabilities": re.compile(r"Total\s*Current\s*Liabilities", re.IGNORECASE),
    "total_liabilities": re.compile(r"Total\s*Liabilities", re.IGNORECASE),
    # Issue #168 -- "Net Assets"/"Net Worth" is a real alternate wording
    # for the same figure (Assets - Liabilities) on simpler small-business
    # templates (real sample: "NET ASSETS (NET WORTH)"), not just "Total
    # (Owner's) Equity" style wording.
    "total_equity": re.compile(r"Total\s*(?:Owner.?s?\s*)?Equity|Net\s*Assets|Net\s*Worth", re.IGNORECASE),
}


def _last_numeric_cell(cells: list[str]) -> float | None:
    """Issue #172 -- several real templates have more than one value
    column (e.g. PRIOR YEAR / CURRENT YEAR, FY1 / FY2). The rightmost
    parseable cell is the most recent period, which is what a
    loan-readiness check actually wants -- take the LAST match, not the
    first, so a multi-period row doesn't silently return stale data."""
    result = None
    for cell in cells:
        amount = parse_currency_amount(cell)
        if amount is not None:
            result = amount
    return result


def _next_nonempty_row(table_rows: list[list[str]], start_idx: int) -> list[str] | None:
    """Issue #171 -- PPStructureV3's table recovery sometimes inserts a
    genuinely empty spacer row between a header-labels row and its real
    values row (the docx source of #165's original fix had them
    adjacent, with no such gap). Skip past empty rows instead of only
    ever checking exactly one row down."""
    for row in table_rows[start_idx:]:
        if any(cell.strip() for cell in row):
            return row
    return None


def extract_balance_sheet_fields_en(table_rows: list[list[str]]) -> dict:
    """Pair a bare label cell with its adjacent value cell(s) -- same
    algorithm as field_extraction.py's extract_from_table_rows (VN era),
    ported to English balance-sheet labels. Real templates put the label
    and its number(s) in adjacent cells of the same row, no colon.

    Issue #165 -- one real template (IC-Simple-Small-Business-Balance-Sheet)
    has a summary header row bunching several labels together (adjacent
    cell is another label, not a value), with the real numbers sitting in
    the SAME column index on the row directly below instead. Fall back
    there before giving up.

    Issue #171 -- on the OCR/image path, PPStructureV3 sometimes recovers
    that same header row as ONE merged cell containing all the label text
    concatenated ("TOTAL CURRENT ASSETS TOTAL CURRENT LIABILITIES TOTAL
    CURRENT EQUITY" as a single string), unlike docx's separate <td> per
    label -- so every label in the group shares the same cell index and a
    naive same-column lookup can't tell them apart. Find every field a
    cell matches, in left-to-right order of appearance, and use each
    field's RANK within that group (not the cell's own index) as the
    column position in the values row below -- first label found maps to
    the first value column, second to the second, etc., matching the
    real left-to-right visual layout."""
    result: dict[str, float | None] = {field: None for field in _BALANCE_SHEET_LABEL_RE}
    for row_idx, row in enumerate(table_rows):
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            matches_in_cell = sorted(
                (match.start(), field)
                for field, pattern in _BALANCE_SHEET_LABEL_RE.items()
                if result.get(field) is None
                for match in [pattern.search(cell)]
                if match is not None
            )
            for within_cell_rank, (_, field) in enumerate(matches_in_cell):
                if result.get(field) is not None:
                    continue
                # Same-row cells are all the same field across time periods
                # (e.g. "TOTAL ASSETS | $4,900 | $7,850") -- take the last
                # (most recent). The next-row fallback (#165) is different:
                # that row typically holds DIFFERENT fields at different
                # column positions, so it must stay a single-column
                # lookup, not a rightmost-scan -- scanning there would
                # grab a neighboring field's value.
                candidate = _last_numeric_cell(row[i + 1:])
                if candidate is None:
                    next_row = _next_nonempty_row(table_rows, row_idx + 1)
                    if next_row is not None:
                        col = i + within_cell_rank if len(matches_in_cell) > 1 else i
                        if col < len(next_row):
                            candidate = parse_currency_amount(next_row[col])
                if candidate is not None:
                    result[field] = candidate
    return result


def extract_fields_from_text_en(text: str, table_rows: list[list[str]] | None = None) -> dict:
    fields = extract_regex_fields_en(text)
    fields.update(extract_label_anchored_en(text))
    fields["income"], fields["income_basis"] = extract_income_en(text)
    fields["annual_salary"] = extract_annual_salary_en(text)
    fields["pay_period_days"] = extract_pay_period_days_en(text)
    if table_rows:
        fields.update(extract_balance_sheet_fields_en(table_rows))
    return fields
