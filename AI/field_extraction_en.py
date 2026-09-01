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

import spacy

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
    #
    # Issue #272 -- leading "E?" confirmed real: rendering
    # part-time-employment-contract-FILLED-100.docx through the actual
    # OCR pipeline (docx -> pdf -> image -> PPStructureV3, not a
    # hand-picked corpus file) produced "mployee Name: Steven Wood" and
    # "mployee Address: ...NT 2639" -- OCR dropped the leading "E" on
    # BOTH labels, same left-edge character-drop artifact already seen
    # on Payslip.jpg ("ay Slip For:", "lassification:"). Making the "E"
    # optional doesn't risk matching "Employer" -- "mployee" and
    # "mployer" still diverge at the last letter (ee vs er).
    "name": re.compile(r"E?mployee(?:\s*Name)?\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    "address": re.compile(r"E?mployee\s*Address\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    # Issue #272 -- same leading-character-drop artifact, checked
    # proactively this time rather than waiting for a real repro. Real
    # false-positive risk was checked, not assumed: searched the whole
    # corpus for a standalone "SB:" (not preceded by "B") and a
    # standalone "ccount:" (not preceded by "A") -- zero collisions
    # found, so making the first letter optional is safe here too.
    "bsb": re.compile(r"B?SB\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
    "account_number": re.compile(r"A?ccount\s*:[ \t]*([^\[\n]*)", re.IGNORECASE),
}

# Issue #272 -- same recurring leading-character-drop artifact patched
# for name/address/bsb/account_number, applied here too (no confirmed
# real repro for income specifically yet, but the mechanism is already
# proven recurring on 4 other real documents). "gross" needed real
# checking, not the same blind "make the first letter optional" move --
# a bare "ross" (dropped "G") is genuinely unsafe: found 4 real
# collisions in the corpus, including a real employer's SURNAME
# ("Christopher Ross"). Requiring the trailing "Pay"/"payment" to stay
# mandatory (only the leading letter is optional) avoids all of them --
# verified directly, not assumed: re-ran the exact final patterns
# against the whole corpus and got zero matches that weren't the real,
# fully-spelled label. "net"/"Total"'s dropped-letter forms ("et Pay",
# "ET PAY", "otal ...") had zero real collisions either way.
INCOME_LABEL_PATTERNS = {
    "gross": re.compile(r"(?:T?otal\s*g?ross\s*payment|G?ross\s*Pay)\s*:?[ \t]*([^\[\n]*)", re.IGNORECASE),
    "net": re.compile(r"(?:N?ET\s*PAY|T?otal\s*n?et\s*payment|N?et\s*Pay)\s*:?[ \t]*([^\[\n]*)", re.IGNORECASE),
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
    # Issue #270 -- same bare-digit-run bug #186 already fixed in
    # parse_currency_amount_balance_sheet, just never ported here: the old
    # `\d{1,3}(?:,\d{3})*` accepts ZERO repetitions of the comma group, so
    # a plain unformatted number with no thousands separator at all (real
    # case: grid/list payslip templates literally show "9500", not
    # "9,500") matched only its first 3 digits ("950"), silently
    # truncating a real income value by 10x. Requiring `+` (at least one
    # comma-group) on the first alternative and falling through to a bare
    # `\d+` otherwise is the exact fix #186 already validated for the
    # balance-sheet parser -- same technique, ported.
    match = re.search(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?", value)
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
# NOT to be ambiguous after all -- #186 added a dedicated branch for
# this shape, since removed (#271, see below) after its real dependency
# turned out smaller than believed.
_PERIOD_THOUSANDS_RE = re.compile(r"\d{1,3}(?:\.\d{3})+\.\d{2}")

# Issue #186 added a dot-grouped-thousands-no-cents branch here
# ("120.000" -> 120000.0), grounded in a real case (images (9).jpg).
# Issue #271 -- removed on explicit request after measuring its real
# blast radius across the full corpus: instrumenting the function
# showed this branch only ever fired on 3 cells total. Re-running the
# ENTIRE corpus with it removed (not just simulating the 3 cells in
# isolation, which is what first suggested a regression) confirmed
# zero change to any file's final extracted result, including
# images (9).jpg -- its own row has other, unaffected cells further
# right that "last cell wins" already resolves to instead. The only
# real effect anywhere: images.jpg's already-broken total_assets
# (the #271 adversarial stray-digit-noise bug, "3 203,200.00 3") swaps
# from one wrong number (200003.0) to a different wrong number
# (3203.0) -- not a regression (already wrong), not a fix either.
#
# Correction, checked directly rather than assumed: the OLD #186 branch
# never actually fixed the "1.459 800" mixed-separator case its own
# comment used to cite as a reason to leave that class of input broken.
# Ran the pre-removal code against that exact string and got 1.45, not
# 1459800.0 -- despacing (this function's first step, for the unrelated
# "$106 ,000" word-wrap case) merges "459" and "800" into one run before
# the old regex ever saw it, so its own "(?!\d)" guard (stop right after
# a clean 3-digit group) never matched. That branch was solving a
# different, narrower shape ("120.000" with nothing after) than the one
# its comment credited it with. Separately, re-checked the real source
# (images (9).jpg, still in the corpus) fresh: its "1.459 800" cell sits
# alongside two other, correctly space-grouped occurrences of the same
# total in the same row, and this document's real extracted
# total_assets has been confirmed correct (1459800.0) throughout this
# whole session -- the garbled cell never actually reaches the final
# result, rescued by the same "last parseable cell wins" mechanism that
# already covers other unrelated garbled cells elsewhere in this
# corpus. Real, still-open parsing bug in isolation; zero measured
# real-world impact on anything extracted so far.


def parse_currency_amount_balance_sheet(value: str) -> float | None:
    # Issue #226 -- despace first so OCR's mid-number word-wrap artifacts
    # ("$106 ,000") parse the same as their clean docx-native equivalent
    # ("$106,000"); a no-op on already-clean input.
    value = _despace(value)
    # Issue #271 -- real confirmed bug: a table cell that's actually prose
    # with an incidental number in it ("in 12 months", from an
    # instructional worksheet template, not a real balance-sheet figure)
    # was accepted as a valid dollar amount because nothing here checked
    # whether the CELL looked like a number at all, only whether a number
    # could be found somewhere inside it. Every real currency cell seen
    # across the entire corpus (docx-native or OCR) is pure digits/
    # currency-symbols/separators -- zero letters, confirmed against
    # every existing test case this function has. A run of 2+ letters
    # anywhere in the (despaced) cell means it's prose, not an amount.
    if re.search(r"[A-Za-z]{2,}", value):
        return None
    period_match = _PERIOD_THOUSANDS_RE.search(value)
    if period_match is not None:
        digits = period_match.group(0).replace(".", "")
        return float(digits[:-2] + "." + digits[-2:])
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

# Issue #214 -- balance-sheet totals were never redacted: no value-capture
# pattern existed for them, only the label-only regexes above (built for
# extract_balance_sheet_fields_en's table-cell pairing, which doesn't need
# one). Same shape problem as income (float value, no fixed printed string
# form) -- same fix, a "trailing value" suffix like INCOME_LABEL_PATTERNS
# uses. Verified reliable for the docx path: module2_text_extraction.py
# space-joins each table row onto one line ("Total Assets  $87,500.00", no
# colon needed since \s* already matches it), so label and value are
# always adjacent in `text`. NOT verified for the image/OCR path --
# module2_ocr_extraction.py's `text` comes from PPStructureV3's own line
# detection (lines_to_text), independent of its table HTML/table_rows, so
# whether a wide table's label and value land on the same OCR-detected
# line is unconfirmed; a miss there degrades to no box (same failure mode
# find_sensitive_boxes already accepts for income). Wrapping each label
# regex in a non-capturing group before appending the suffix matters:
# total_equity's pattern is `A|B|C` with no grouping of its own, so
# appending unwrapped would silently apply the value capture only to the
# last alternative ("Net Worth"), losing it on "Total Equity"/"Net Assets"
# matches. Verified against a real filled template (#215): its equity row
# prints "NET ASSETS (NET WORTH) $135,000 ... $45,000" -- a parenthetical
# alternate-name aside sits between the matched label ("Net Assets") and
# the value, same shape as ANNUAL_SALARY_RE's bracketed-aside case above.
# Without skipping it, the value capture starts with "(NET WORTH) ...",
# which _clean_label_value rejects as bracket-cruft and the whole span is
# silently dropped -- caught by running this against real data, not
# assumed safe from the regex alone.
#
# Swept all 30 real docx files in samples/en_balance_sheet/ after the fix:
# total_assets, total_liabilities, total_equity redact 30/30 whenever
# fields[key] is set. total_current_assets redacts 0/15, and
# total_current_liabilities 15/30 -- both misses are the SAME real
# structural gap: the #167-family templates print a bare "Total" row
# under a "Current assets"/"Current liabilities" section header instead
# of literal "Total Current Assets" text, which _BALANCE_SHEET_LABEL_RE
# (by design -- see #167 below) can't match directly; extraction only
# gets these via _SECTION_HEADER_TO_FIELD's section tracking, which this
# regex-only approach doesn't replicate. Same accepted degradation class
# as income above (falls back to no span/box, not a wrong one) --
# SENSITIVE_FIELD_KEYS still strips both fields from aiResult.fields for
# non-owners unconditionally regardless. Porting section-tracking into
# this module is real, separate scope, not taken on here.
BALANCE_SHEET_VALUE_PATTERNS = {
    key: re.compile(rf"(?:{pattern.pattern})\s*:?[ \t]*(?:\([^()]*\)\s*)?([^\[\n]*)", re.IGNORECASE)
    for key, pattern in _BALANCE_SHEET_LABEL_RE.items()
}

# Issue #167 -- one real template (samples/en_balance_sheet/Balance sheet
# template.docx) never writes "Total Current Assets"/"Total Current
# Liabilities" as combined literal text at all. "Current" only appears in
# a section-header row ("Current assets"), with a bare, unlabeled "Total"
# row following later in that same section -- the same bare "Total" text
# also appears for Fixed Assets/Long-Term Liabilities subtotals we don't
# want, so which section we're currently in has to be tracked.
# Issue #226 -- `\s*` not `\s+`: matched against a DESPACED cell (see
# `_despace`/its call sites below), which has zero internal whitespace by
# construction. PPStructureV3 word-wraps this template's narrow label
# column mid-word ("Current assets" -> "Curr ent asset S"), which no
# amount of wording-alternative regex can survive -- despacing both the
# cell and the pattern's separator (`\s+` -> `\s*`, matching zero spaces)
# is what makes "CurrentassetS" match "^CurrentAssets$" case-insensitively.
#
# Issue #297 -- the liabilities pattern's "/short-term" required a
# literal hyphen, but this real template's actual wording is "short
# term" (a space, not a hyphen) -- _despace() only strips whitespace,
# so that becomes "shortterm" with NO separator at all, never matching
# the hardcoded "-". Confirmed real on Balance-sheet-template-FILLED-
# 300_p1.png's own OCR'd header cell. "-?" makes the hyphen optional,
# matching both the hyphenated and despaced-space real wordings.
_SECTION_HEADER_TO_FIELD = {
    re.compile(r"^Current\s*Assets$", re.IGNORECASE): "total_current_assets",
    re.compile(r"^Current(?:/short-?term)?\s*Liabilities$", re.IGNORECASE): "total_current_liabilities",
}
# Other section headers seen in the real template -- encountering one of
# these resets the tracked section so ITS bare "Total" row isn't
# misattributed to whichever current-asset/liability section came before.
_OTHER_SECTION_HEADER_RE = re.compile(
    r"^(?:Fixed\s*Assets|Long-Term\s*Liabilities|Intermediate\s*Liabilities)$",
    re.IGNORECASE,
)
_BARE_TOTAL_RE = re.compile(r"^Total$", re.IGNORECASE)


def _despace(cell: str) -> str:
    """Issue #226 -- PPStructureV3 recovers this template's narrow label
    column with mid-word spaces from its own word-wrap ("Bala nce shee t
    for..." for "Balance sheet for..."), including inside numbers
    ("$106 ,000" for "$106,000"). Removing all whitespace before matching
    is safe for `_BALANCE_SHEET_LABEL_RE`'s own patterns unchanged (they
    already use `\\s*`, tolerating the fully-concatenated result), and for
    parse_currency_amount_balance_sheet's separator regexes (which never
    expect a literal space mid-number on the clean docx-native path this
    despacing is a no-op for)."""
    return re.sub(r"\s+", "", cell)

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


# Issue #271 -- confirmed real on IC-Small-Business-Pro-Forma-Balance-Sheet-
# Template.jpg: an entire row there is nothing but "$"/"5"/"S"/"s" tokens
# (a different row's own currency-symbol column, real evidence this
# document's OCR genuinely confuses "$" with these specific characters,
# not a guess). Deliberately narrow -- a real label is never JUST one of
# these characters repeated, but a real value legitimately CAN be a bare
# "5" (five dollars) or similar short digit run, so this only matches
# cells with ZERO digits at all.
_BARE_CURRENCY_SYMBOL_RE = re.compile(r"^[\$Ss]+$")


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
    "Total Long-Term Assets" itself doesn't match any of them.

    Issue #271 -- real confirmed bug: a standalone currency-symbol cell
    with zero digits in it ("$" split into its own cell, ahead of the
    real value in the next cell -- confirmed real on
    IC-Small-Business-Pro-Forma-Balance-Sheet-Template.jpg, where OCR
    also misreads "$" as a bare "s"/"S" elsewhere in the very same
    table) was wrongly treated as the #184 stop signal, halting the scan
    before it ever reached the real number 1-2 cells later. Unlike a
    real label ("Total Long-Term Assets"), a cell that's PURELY a
    currency symbol can never be a different field's label -- safe to
    skip over it and keep scanning, not stop."""
    result = None
    preferred = None
    for offset, cell in enumerate(cells):
        stripped = cell.strip()
        amount = parse_currency_amount_balance_sheet(cell)
        if amount is not None:
            result = amount
            if prefer_col is not None and start_col + offset == prefer_col:
                preferred = amount
        elif stripped and not _BARE_CURRENCY_SYMBOL_RE.match(stripped):
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
        # Issue #298 -- some real templates put the bare "Total" label
        # LAST in its row, values BEFORE it (reversed from the assumed
        # "label first, values after" shape the forward search above
        # expects) -- confirmed real on 3 independent documents, e.g.
        # ['$78,000', '$80,000', '$55,000', '$94,000', '$129,000',
        # 'Total']. start_col=0 since row[:i]'s own indices already are
        # the row's real absolute column positions, no offset needed.
        candidate = _last_numeric_cell(row[:i], start_col=0, prefer_col=prefer_col)
    if candidate is None:
        next_row = _next_nonempty_row(table_rows, row_idx + 1)
        if next_row is not None:
            col = i + col_offset
            if col < len(next_row):
                candidate = parse_currency_amount_balance_sheet(next_row[col])
    return candidate


def extract_balance_sheet_fields_en(
    table_rows: list[list[str]], initial_section: str | None = None
) -> tuple[dict, str | None]:
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
    scanning; a bare "Total" row is attributed to it.

    Issue #297 -- on a real multi-page document, a section header can
    land on one page with its bare "Total" row on the next -- each
    page gets OCR'd and extracted independently (pipeline.py's own
    per-page loops, both the OCR and text-native paths), so
    current_section_field being reset to None at the top of every call
    meant this NEVER resolved: the page with the header has no Total
    row yet, and the page with the Total row has no section context
    (confirmed real: Balance-sheet-template-FILLED-300_p2.png alone
    resolves total_current_liabilities to None). initial_section lets
    a caller carry the section state in from wherever the previous
    page's call left off; the returned final section lets it carry
    that state OUT to seed the next page's call -- the same "only the
    first bare Total after a header counts" reset logic below already
    applies identically whether the header came from this page or was
    carried in from the previous one."""
    result: dict[str, float | None] = {field: None for field in _BALANCE_SHEET_LABEL_RE}
    current_section_field: str | None = initial_section
    prefer_col = _detect_current_period_column(table_rows)
    for row_idx, row in enumerate(table_rows):
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            despaced_cell = _despace(cell)

            if not _row_has_other_numeric_cell(row, i):
                section_field = next(
                    (f for p, f in _SECTION_HEADER_TO_FIELD.items() if p.match(despaced_cell)), None
                )
                if section_field is not None:
                    current_section_field = section_field
                    continue
                if _OTHER_SECTION_HEADER_RE.match(despaced_cell):
                    current_section_field = None
                    continue

            if _BARE_TOTAL_RE.match(despaced_cell) and current_section_field is not None:
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
                for match in [pattern.search(despaced_cell)]
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

    return result, current_section_field


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
            despaced_cell = _despace(cell)
            if _BARE_TOTAL_RE.match(despaced_cell):
                continue
            if any(p.match(despaced_cell) for p in _SECTION_HEADER_TO_FIELD) or _OTHER_SECTION_HEADER_RE.match(despaced_cell):
                continue
            field = _fuzzy_match_label(cell)
            if field is None or result.get(field) is not None:
                continue
            candidate = _resolve_value(table_rows, row_idx, row, i, 0, prefer_col)
            if candidate is not None:
                result[field] = candidate


# Issue #270 class A -- LABEL_PATTERNS["name"] only matches label wording
# actually observed in the corpus ("*Employee:", "Employee Name:"). A real
# payslip using different wording (confirmed real case: "Pay Slip For:",
# OCR-garbled to "ay Slip For:") is never caught by regex alone, however
# clean the underlying text -- and real-world payslip templates are far
# more varied than the 2 template families in this corpus. This is a
# bounded, keyword-anchored spaCy fallback, deliberately NOT a generic
# "grab any PERSON entity found anywhere in the document" search -- a
# real payslip can have multiple names (employee, approving manager,
# payroll officer), and undisambiguated NER can't tell which one is the
# employee. Only fires when LABEL_PATTERNS found nothing at all (checked
# by the caller) -- never overrides a working regex match, and only
# considers text adjacent to a small set of real, observed name-context
# words, not the whole document.
# "slip for" not "pay slip for", and "mployee" alongside "employee" --
# real OCR drops the leading character of some lines (Payslip.jpg's
# "ay Slip For:"/"lassification:"; a real end-to-end render of
# part-time-employment-contract-FILLED-100.docx through the actual OCR
# pipeline produced "mployee Name:"/"mployee Address:"), a confirmed
# recurring artifact, not a hypothetical -- matching the dropped-letter
# form directly survives it. Defense in depth here specifically:
# LABEL_PATTERNS's own "E?mployee" fix already covers this exact case,
# this is a backstop for wording this list hasn't anticipated yet.
_NAME_CONTEXT_KEYWORDS = ("employee", "mployee", "slip for", "full name", "worker", "staff", "candidate")

_nlp_en = None


def _get_nlp_en():
    global _nlp_en
    if _nlp_en is None:
        _nlp_en = spacy.load("en_core_web_sm")
    return _nlp_en


def _has_person_entity(nlp, text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    return any(ent.label_ == "PERSON" for ent in nlp(text).ents)


# Real false positives found verifying this against the actual corpus (not
# hypothetical): en_core_web_sm tags the bare section header "RECITALS" as
# PERSON in isolation, and a "next line" that's really a full boilerplate
# sentence ("On behalf of [Company Name] trading as...") passed the old
# bare PERSON-tag check too, since a long sentence full of proper nouns
# gives spaCy plenty of chances to mistag something. A real name in every
# sample seen (docx-native or OCR) is 2-5 short words, never uppercase,
# never sentence punctuation -- this rejects both real failure cases
# while still accepting "Rymer, Mark", "Jo Worker", "Sally Harley".
def _looks_like_name(text: str) -> bool:
    if not text or len(text) > 60 or text.isupper():
        return False
    if any(ch in text for ch in ".;:"):
        return False
    return 2 <= len(text.split()) <= 5


# Issue #272 -- proactive hardening, not a confirmed-bug fix: no real
# corpus document has been found where bsb/account_number's Class B
# repair (module2_ocr_extraction._repair_line_split_fields) actually
# misfires, but that repair uses the exact same blind "nearest spatial
# box, no semantic check" mechanism that DID misfire for `name` (the
# real "Bank Detals" case). A real bsb/account_number is always short
# and mostly digits ("123-456", "1234 5678") -- confirmed against the
# one real example in the corpus (Screenshot 2026-07-28...png). Cheap,
# safe insurance on an already-proven-unsafe code path.
def _looks_like_bsb_or_account(text: str) -> bool:
    if not text or len(text) > 20:
        return False
    digit_count = sum(ch.isdigit() for ch in text)
    return digit_count >= 4 and not re.search(r"[A-Za-z]", text)


# Issue #272 -- the "no safe cheap shape check exists for free-text
# address" concern turned out wrong once real evidence was checked:
# every real address across 8 sampled real FILLED contracts ends with
# an AU state abbreviation directly followed by a 4-digit postcode
# ("...West Adamfurt NT 2639", "...Perezshire WA 0831", "...Lake Scott
# NSW 9494") -- 8/8, no exceptions. Requiring BOTH together (not the
# state code alone) is what makes this safe: a bare "VIC"/"WA"/"SA"/
# "ACT" risks colliding with an unrelated real English word, but
# state-code-immediately-followed-by-4-digits is a virtually
# unambiguous real-address signal. Case-sensitive on purpose -- every
# real sample has the state code fully uppercase.
_AU_ADDRESS_RE = re.compile(r"\b(?:NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+\d{4}\b")


def _looks_like_address(text: str) -> bool:
    if not text or len(text) > 100:
        return False
    return bool(_AU_ADDRESS_RE.search(text))


def extract_name_via_ner_en(text: str) -> str | None:
    lines = text.split("\n")
    nlp = _get_nlp_en()
    for i, line in enumerate(lines):
        low = line.lower()
        if not any(kw in low for kw in _NAME_CONTEXT_KEYWORDS):
            continue
        # Same line, after a colon -- real for the docx-native / clean-OCR
        # case where label and value weren't split onto separate lines.
        if ":" in line:
            same_line_value = line.split(":", 1)[1].strip()
            cleaned = _clean_label_value(same_line_value)
            if cleaned and _looks_like_name(cleaned) and _has_person_entity(nlp, cleaned):
                return cleaned
        # Next line -- real for the OCR-split case (Payslip.jpg's actual
        # "ay Slip For:\nRymer, Mark"). Whole line, not spaCy's own PERSON
        # span -- confirmed empirically that en_core_web_sm's span
        # boundary drops "Rymer" from "Rymer, Mark" (tags only "Mark"),
        # so the span itself is an unreliable value; PERSON-tagged is used
        # only as a yes/no signal that this line is a name, and the full
        # adjacent line is taken as the value to avoid that truncation.
        if i + 1 < len(lines):
            cleaned = _clean_label_value(lines[i + 1].strip())
            if cleaned and _looks_like_name(cleaned) and _has_person_entity(nlp, cleaned):
                return cleaned
    return None


def extract_fields_from_text_en(
    text: str, table_rows: list[list[str]] | None = None, initial_section: str | None = None
) -> dict:
    fields = extract_regex_fields_en(text)
    fields.update(extract_label_anchored_en(text))
    if fields.get("name") is None:
        fields["name"] = extract_name_via_ner_en(text)
    fields["income"], fields["income_basis"] = extract_income_en(text)
    fields["annual_salary"] = extract_annual_salary_en(text)
    fields["pay_period_days"] = extract_pay_period_days_en(text)
    # Issue #297 -- carries the balance-sheet section-tracking state
    # (see extract_balance_sheet_fields_en's own docstring) through this
    # layer for a caller that needs to thread it across pages (module2_
    # ocr_extraction.extract_fields does, and pops this back out before
    # returning -- never meant to reach a real consumer of `fields`).
    final_section = initial_section
    if table_rows:
        balance_sheet_fields, final_section = extract_balance_sheet_fields_en(table_rows, initial_section)
        # Issue #219 -- SALARY_RE is payslip-domain (a single colon-anchored
        # dollar figure); a table containing real balance-sheet totals means
        # this is balance-sheet-shaped, where every dollar amount is a false
        # "salary" match. Gating on `table_rows` presence alone (any table)
        # over-suppressed: a DOCX payslip's own line-item table has no
        # balance-sheet labels, so this checks the actual detection result,
        # not merely a table's existence -- caught auditing #219 itself,
        # real repro on Pay-slip-template-sts-FILLED-118.docx.
        if any(v is not None for v in balance_sheet_fields.values()):
            fields["salary"] = []
        fields.update(balance_sheet_fields)
    fields["_balance_sheet_section"] = final_section
    return fields
