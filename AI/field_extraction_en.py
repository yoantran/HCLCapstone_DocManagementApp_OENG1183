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
from difflib import SequenceMatcher

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


# Issue #185 -- a separate function, not an edit to parse_currency_amount
# above. That one is also used for payslip income/salary parsing (already
# benchmarked at 96.2% accuracy) and the validation-corpus scripts --
# loosening its grouping regex for a balance-sheet-specific format risks
# that unrelated, already-proven path. Real balance-sheet cells use
# space-grouped thousands too ("165 000", "1 300 000"), not just commas,
# confirmed on a real spreadsheet-screenshot template -- scoped here only.
# Issue #188 -- real OCR on some cells renders period as the
# thousands-group separator ("$89.000.00") instead of comma/space, while
# OTHER cells in the same real table use comma grouping correctly. Period
# is ALSO the existing decimal/cents separator ("$1,500.00"), so this
# can't just be added to the group-separator character class below --
# that would break real, already-correct cents parsing. Disambiguate
# instead: 2+ periods (one-or-more 3-digit groups, then a final 2-digit
# cents group) is period-grouped thousands; anything with fewer periods
# falls through to the existing comma/space-only logic, unchanged. A
# bare single-period value with no cents suffix ("89.000") turned out
# NOT to be ambiguous after all -- see _DOT_THOUSANDS_NO_CENTS_RE below
# (#186), confirmed real on a different file in the same corpus.
_PERIOD_THOUSANDS_RE = re.compile(r"\d{1,3}(?:\.\d{3})+\.\d{2}")

# Issue #186 -- confirmed on a real spreadsheet-screenshot corpus
# ("images (9).jpg"): the SAME field is rendered 3 different ways across
# its own year-columns in one row -- comma-grouped (already correct), a
# bare digit run with no separator ("165000"), and a dot-grouped value
# with no cents suffix ("120.000"). The bare-single-period case above
# was assumed ambiguous when #188 was fixed; it isn't. Real currency
# decimals are always exactly 2 digits (AUD -- this pipeline's actual
# documented domain, per the Fair Work Ombudsman template corpus), so a
# dot followed by exactly 3 digits can never validly be a decimal point
# -- it's unconditionally a thousands group, regardless of the specific
# digits. Deliberately only matches a SINGLE separator character
# repeated (all dots) -- does NOT accept mixed separators within one
# number (e.g. a real but rare OCR artifact seen in the same corpus,
# "1.459 800", true value 1,459,800 confirmed against two correctly
# space-grouped sibling occurrences of the same total in the same
# table). Extending the character class to also accept comma/space at
# each group boundary was tried and reverted: it corrupts the common,
# already-correct "$435,879,843.89"-style case via regex backtracking
# (matches only "435,879", silently dropping ",843.89") -- verified
# directly, not assumed. Left as a known, narrow limitation rather than
# risk that.
_DOT_THOUSANDS_NO_CENTS_RE = re.compile(r"\d{1,3}(?:\.\d{3})+(?!\.\d{2})(?!\d)")


def parse_currency_amount_balance_sheet(value: str) -> float | None:
    period_match = _PERIOD_THOUSANDS_RE.search(value)
    if period_match is not None:
        digits = period_match.group(0).replace(".", "")
        return float(digits[:-2] + "." + digits[-2:])
    dot_thousands_match = _DOT_THOUSANDS_NO_CENTS_RE.search(value)
    if dot_thousands_match is not None:
        return float(dot_thousands_match.group(0).replace(".", ""))
    # Issue #186 -- a bare digit run with no separator at all ("165000")
    # previously truncated to its first 3 digits, since the grouped
    # alternative requires a literal comma/space to keep matching beyond
    # the first 1-3 digits. Unlike the dot-vs-decimal case above, this
    # one was never really ambiguous: dropping or adding thousands
    # commas never changes the actual numeric value, so reading the
    # whole bare run is always at least as correct as a properly
    # comma-grouped version of the same digits would be.
    match = re.search(r"(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d{2})?", value)
    if match is None:
        return None
    digits = match.group(0).replace(",", "").replace(" ", "")
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
    # Issue #181 -- confirmed on 5 distinct real templates: none of them
    # print a standalone "Total Liabilities" row, only a combined "Total
    # Liabilities and Owner's Equity"/"Total Liabilities & Equity" row.
    # Without the negative lookahead this pattern matches the start of
    # that combined text too, and (when no standalone row exists) wrongly
    # returns the combined assets+equity figure as pure liabilities.
    "total_liabilities": re.compile(r"Total\s*Liabilities(?!\s*(?:and|&))", re.IGNORECASE),
    # Issue #168 -- "Net Assets"/"Net Worth" is a real alternate wording
    # for the same figure (Assets - Liabilities) on simpler small-business
    # templates (real sample: "NET ASSETS (NET WORTH)"), not just "Total
    # (Owner's) Equity" style wording. Issue #177 -- "Shareholders' Equity"
    # is another real alternate, seen on 2 more distinct real templates --
    # apostrophe placement differs from "Owner's" (before the s) vs.
    # "Shareholders'" (plural possessive, after the s), so both orders
    # are covered explicitly rather than a single ".?s?" that only fits one.
    "total_equity": re.compile(
        r"Total\s*(?:(?:Owner|Shareholder)(?:'s|s'|'|s)?\s*)?Equity|Net\s*Assets|Net\s*Worth",
        re.IGNORECASE,
    ),
}

# Issue #167 -- one real template (samples/en_balance_sheet/Balance sheet
# template.docx) never writes "Total Current Assets"/"Total Current
# Liabilities" as combined literal text at all. "Current" only appears in
# a section-header row ("Current assets"), with a bare, unlabeled "Total"
# row following later in that same section -- the same bare "Total" text
# also appears for Fixed Assets/Long-Term Liabilities subtotals we don't
# want, so which section we're currently in has to be tracked.
_SECTION_HEADER_TO_FIELD = {
    re.compile(r"^Current\s+Assets$", re.IGNORECASE): "total_current_assets",
    re.compile(r"^Current(?:/short-term)?\s+Liabilities$", re.IGNORECASE): "total_current_liabilities",
}
# Other section headers seen in the real template -- encountering one of
# these resets the tracked section so ITS bare "Total" row isn't
# misattributed to whichever current-asset/liability section came before.
_OTHER_SECTION_HEADER_RE = re.compile(
    r"^(?:Fixed\s+Assets|Long-Term\s+Liabilities|Intermediate\s+Liabilities)$",
    re.IGNORECASE,
)
_BARE_TOTAL_RE = re.compile(r"^Total$", re.IGNORECASE)

# Issue #179 -- OCR sometimes recovers a table's STRUCTURE correctly but
# misreads individual characters in the label text itself ("Total cument
# ossets" for "Total current assets"). No amount of wording-alternative
# regex (#168, #177) can close this -- it's character-level noise, not
# wording/structure variance. Fuzzy fallback only, tried after every exact
# match in the table has already been attempted (see the second pass in
# extract_balance_sheet_fields_en) so an exact match anywhere always wins.
_FUZZY_CANONICAL_LABELS = {
    "total_current_assets": "Total Current Assets",
    "total_assets": "Total Assets",
    "total_current_liabilities": "Total Current Liabilities",
    "total_liabilities": "Total Liabilities",
    "total_equity": "Total Equity",
}
# Tuned against #179's real typos ("Total cument ossets" ~0.87, "Total
# current lablttes" ~0.89, "Total Liabililies" ~0.94) while staying above
# real distractor labels that must NOT match (a bare section header like
# "Current Liabilities" scores ~0.86 against total_current_liabilities --
# excluded structurally below, not by threshold alone; "Total Fixed
# Assets" scores exactly 0.80 against total_assets, which is why the
# threshold sits at 0.85, not 0.80 as first proposed).
_FUZZY_THRESHOLD = 0.85
_FUZZY_MARGIN = 0.05


def _fuzzy_match_label(cell: str) -> str | None:
    scores = sorted(
        (
            (SequenceMatcher(None, cell.lower(), canonical.lower()).ratio(), field)
            for field, canonical in _FUZZY_CANONICAL_LABELS.items()
        ),
        reverse=True,
    )
    candidates = [(score, field) for score, field in scores if score >= _FUZZY_THRESHOLD]
    if not candidates:
        return None
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < _FUZZY_MARGIN:
        return None  # ambiguous between two tracked fields -- skip rather than guess
    return candidates[0][1]


# Issue #182 -- #172's "rightmost = most recent" assumption is only true
# for SOME real templates ("PRIOR YEAR" then "CURRENT YEAR", left to
# right). At least one real template does the opposite ("CURRENT YR."
# then "PRIOR YR."), and a third convention (Year 1/Year 2/Year 3,
# ascending) happens to agree with rightmost by coincidence, not by the
# same rule. Column position alone can't tell these apart -- the actual
# header text can. "CURRENT"/"THIS" beats "PRIOR"/"PREVIOUS"/"LAST";
# among "FYn"/"Year n" cells, the highest n wins.
_CURRENT_PERIOD_RE = re.compile(r"\bCURRENT\b|\bTHIS\s*Y", re.IGNORECASE)
_PRIOR_PERIOD_RE = re.compile(r"\bPRIOR\b|\bPREVIOUS\b|\bLAST\s*Y", re.IGNORECASE)
# Issue #192 -- the original pattern only matched "FYn"/"Y n" style
# headers, not the literal "Year N" text real templates actually use
# (confirmed on images (9).jpg and Balance sheet template.docx's "[Year
# 1]".."[Year 5]" headers) -- "Year" starts with "Y" too, so the old
# `F?Y` branch matched just the leading "Y" and then failed on the "ear"
# that followed, never falling through to try the literal word.
_NUMBERED_PERIOD_RE = re.compile(r"\b(?:F?Y|Year)\s*(\d+)\b", re.IGNORECASE)


def _detect_current_period_column(table_rows: list[list[str]]) -> int | None:
    """Scan for a header row (>=2 cells matching a period keyword) and
    return the absolute column index of whichever cell represents the
    most recent period. None if no real header is found -- callers fall
    back to the old rightmost-wins behavior unchanged, so tables without
    a recognizable header (most docx tables, single-value-column rows)
    see no behavior change at all."""
    for row in table_rows:
        current_idx: int | None = None
        prior_idx: int | None = None
        numbered: list[tuple[int, int]] = []  # (period number, column index)
        matches = 0
        for idx, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            if _CURRENT_PERIOD_RE.search(cell):
                current_idx = idx
                matches += 1
            elif _PRIOR_PERIOD_RE.search(cell):
                prior_idx = idx
                matches += 1
            elif (m := _NUMBERED_PERIOD_RE.search(cell)) is not None:
                numbered.append((int(m.group(1)), idx))
                matches += 1
        if matches < 2:
            continue
        if current_idx is not None:
            return current_idx
        if numbered:
            return max(numbered)[1]  # highest period number = most recent
        if prior_idx is not None:
            continue  # a "prior" cell alone, no "current" counterpart -- ambiguous
    return None


def _last_numeric_cell(cells: list[str], start_col: int = 0, prefer_col: int | None = None) -> float | None:
    """Issue #172 -- several real templates have more than one value
    column (e.g. PRIOR YEAR / CURRENT YEAR, FY1 / FY2). Take the LAST
    parseable cell by default (rightmost -- the safe fallback when no
    header was detected), so a multi-period row doesn't silently return
    stale data.

    Issue #182 -- when the caller HAS detected which absolute column is
    the current period (prefer_col), that value wins over rightmost --
    rightmost is only a proxy for "most recent," and a real template
    exists where the proxy is backwards.

    Issue #184 -- stop at the first non-empty, non-numeric cell. A real
    2-panel row ("Total Current Assets | $105,000 | | Total Long-Term
    Assets | $320,000") has a genuinely different field's label and
    value sitting later in the same row -- without stopping, this
    would scan straight past the empty spacer into the OTHER field's
    value. The stop check is deliberately generic (any real label
    text, not just cells matching the 5 tracked patterns), since
    "Total Long-Term Assets" itself doesn't match any of them."""
    result = None
    preferred = None
    for offset, cell in enumerate(cells):
        stripped = cell.strip()
        amount = parse_currency_amount_balance_sheet(cell)
        if amount is not None:
            result = amount
            if prefer_col is not None and start_col + offset == prefer_col:
                preferred = amount
        elif stripped:
            break
    return preferred if preferred is not None else result


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


def _row_has_other_numeric_cell(row: list[str], skip_index: int) -> bool:
    """A real section-header row (e.g. "Current assets" alone) has no
    other cell with any digit/currency content. A line-item row that
    happens to share the same text (e.g. IC-Simple's "Current Assets"
    line item, "['Current Assets', '$', '$', '$', '$', '$']") does --
    even blank "$" placeholder cells count, distinguishing a header from
    a line item that just hasn't been filled in yet."""
    return any(re.search(r"[$\d]", c) for j, c in enumerate(row) if j != skip_index)


def _resolve_value(
    table_rows: list[list[str]],
    row_idx: int,
    row: list[str],
    i: int,
    col_offset: int,
    prefer_col: int | None = None,
) -> float | None:
    candidate = _last_numeric_cell(row[i + 1:], start_col=i + 1, prefer_col=prefer_col)
    if candidate is None:
        next_row = _next_nonempty_row(table_rows, row_idx + 1)
        if next_row is not None:
            col = i + col_offset
            if col < len(next_row):
                candidate = parse_currency_amount_balance_sheet(next_row[col])
    return candidate


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
    real left-to-right visual layout.

    Issue #167 -- one real template never writes "Total Current Assets"/
    "Total Current Liabilities" as combined text at all -- see
    _SECTION_HEADER_TO_FIELD's comment. Track the current section while
    scanning; a bare "Total" row is attributed to it."""
    result: dict[str, float | None] = {field: None for field in _BALANCE_SHEET_LABEL_RE}
    current_section_field: str | None = None
    prefer_col = _detect_current_period_column(table_rows)
    for row_idx, row in enumerate(table_rows):
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue

            if not _row_has_other_numeric_cell(row, i):
                section_field = next(
                    (f for p, f in _SECTION_HEADER_TO_FIELD.items() if p.match(cell)), None
                )
                if section_field is not None:
                    current_section_field = section_field
                    continue
                if _OTHER_SECTION_HEADER_RE.match(cell):
                    current_section_field = None
                    continue

            if _BARE_TOTAL_RE.match(cell) and current_section_field is not None:
                field = current_section_field
                current_section_field = None  # only the first bare Total after a header counts
                if result.get(field) is None:
                    candidate = _resolve_value(table_rows, row_idx, row, i, 0, prefer_col)
                    if candidate is not None:
                        result[field] = candidate
                continue

            # Issue #180 -- real templates' own "Common Financial Ratio"
            # section has formula-description labels like "Debt Ratio
            # (Total Liabilities / Total Assets)". That literal substring
            # matches _BALANCE_SHEET_LABEL_RE too, and picks up the RATIO
            # VALUE (0.71, 0.91...) sitting next to it as if it were a
            # dollar total -- worse than missing data, since it silently
            # poisons the result with a plausible-looking wrong number.
            # No real dollar-total label cell checked so far contains a
            # "/" (division symbol); every formula description does.
            if "/" in cell:
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
                col_offset = within_cell_rank if len(matches_in_cell) > 1 else 0
                candidate = _resolve_value(table_rows, row_idx, row, i, col_offset, prefer_col)
                if candidate is not None:
                    result[field] = candidate

    if any(v is None for v in result.values()):
        _fuzzy_fill_remaining_fields(table_rows, result, prefer_col)

    return result


def _fuzzy_fill_remaining_fields(table_rows: list[list[str]], result: dict, prefer_col: int | None = None) -> None:
    """Issue #179's fallback pass. Runs only after every exact match in the
    table has already been tried, so an exact match anywhere always wins
    over a fuzzy guess. Skips section-header and bare-"Total" cells (same
    patterns pass one already carves out) -- those are structurally
    different from a mislabeled totals cell and fuzzy-scoring them risks
    exactly the false-positive collision #180/#181 already had to guard
    against with exact matching. Only handles the single-label-per-cell
    layout #179 was found on (col_offset=0) -- #171's merged-cell,
    multi-label-per-cell ranking is exact-match-only, deliberately not
    extended here."""
    for row_idx, row in enumerate(table_rows):
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell or "/" in cell:
                continue
            if _BARE_TOTAL_RE.match(cell):
                continue
            if any(p.match(cell) for p in _SECTION_HEADER_TO_FIELD) or _OTHER_SECTION_HEADER_RE.match(cell):
                continue
            field = _fuzzy_match_label(cell)
            if field is None or result.get(field) is not None:
                continue
            candidate = _resolve_value(table_rows, row_idx, row, i, 0, prefer_col)
            if candidate is not None:
                result[field] = candidate


def extract_fields_from_text_en(text: str, table_rows: list[list[str]] | None = None) -> dict:
    fields = extract_regex_fields_en(text)
    fields.update(extract_label_anchored_en(text))
    fields["income"], fields["income_basis"] = extract_income_en(text)
    fields["annual_salary"] = extract_annual_salary_en(text)
    fields["pay_period_days"] = extract_pay_period_days_en(text)
    if table_rows:
        fields.update(extract_balance_sheet_fields_en(table_rows))
    return fields
