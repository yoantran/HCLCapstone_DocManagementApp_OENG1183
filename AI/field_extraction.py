import re
import unicodedata

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
        r"(?:H[oọ]?\s*(?:và)?\s*t[eê]n|BÊN\s*B|T[eê]n\s*NV|[ÔO]ng\s*/\s*[Bb][àa])\s*:[ \t]*(.+)",
        re.IGNORECASE,
    ),
    "address": re.compile(r"[ĐD][iị]a\s*ch[iỉ]\s*:[ \t]*(.+)", re.IGNORECASE),
    # VN bank account numbers have no fixed digit count (8-15 digits,
    # bank-dependent) -- anchoring on the label rather than a digit-count
    # regex avoids colliding with CCCD (fixed 12 digits) or phone (fixed
    # VN mobile pattern). "STK" is a common single-token abbreviation of
    # "Số tài khoản", not just "Số" + "TK" separately.
    "bank_account": re.compile(
        r"(?:S[oố]\s*t[àa]i\s*kho[aả]n|S[oố]\s*TK|STK)\s*:[ \t]*(.+)",
        re.IGNORECASE,
    ),
}

# Income for Module 4 (loan-readiness rules engine). CLAUDE.md's thresholds
# are stated in terms of gross income, but real payslip templates print net
# take-home ("Thực lĩnh") far more reliably than an explicit gross line --
# try gross first, fall back to net, and let the caller know which basis
# was actually used (see extract_income). Deliberately NOT anchoring on
# "Tổng cộng" for net income -- that label is generic table-total
# vocabulary shared with balance-sheet documents ("Tổng cộng tài sản"),
# and field_extraction.py is shared across the payslip/contract/balance-
# sheet branches, so it's a real false-positive risk. "Thực lĩnh" is
# payslip-specific vocabulary and safe to anchor on alone.
INCOME_LABEL_PATTERNS = {
    "gross": re.compile(r"T[oổ]ng\s*thu\s*nh[aậ]p[^:\n]*:[ \t]*(.+)", re.IGNORECASE),
    "net": re.compile(r"Th[uự]c\s*l[iĩ]nh[^:\n]*:[ \t]*(.+)", re.IGNORECASE),
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

# Vietnamese legal/administrative boilerplate ("Ban hành kèm theo Thông tư
# số .../2021...", "Mẫu số 01/BTC") sitting physically close to a real field
# on the source document -- when OCR merges two visually-adjacent lines
# (real value + nearby footer citation) into one captured value, or a
# proximity search's nearest candidate line turns out to be this footer
# text, a real value never contains this vocabulary. Reject rather than try
# to salvage a partial value, since the merge typically also lost the real
# value's own tail (e.g. district/city dropped, not just glued together).
_BOILERPLATE_RE = re.compile(
    r"ban\s*hành|th[oô]ng\s*t[uư]\s*s[oố]|m[aẫ]u\s*s[oố]|ngh[iị]\s*đ[iị]nh|ph[uụ]\s*l[uụ]c",
    re.IGNORECASE,
)

# "Nguyễn Văn A" / "Nguyễn Văn B" / "Nguyễn Thị A" etc -- the standard
# Vietnamese legal-template placeholder name (equivalent to "John Doe"), a
# single trailing capital letter instead of a real given name. A real given
# name is never a single letter. Matched against the diacritic-stripped form
# -- hand-enumerating every accented variant of "Nguyễn"/"Văn"/"Thị" (ễ vs ê
# vs e, ă vs a, etc) is fragile and easy to miss a real one.
_PLACEHOLDER_NAME_STRIPPED_RE = re.compile(r"^(?:nguyen\s+)?(?:van|thi)\s+[a-z]$", re.IGNORECASE)


def _is_shouty_title(value: str) -> bool:
    # Vietnamese official-document titles/headers are conventionally
    # rendered in full caps ("BẢNG THANH TOÁN TIỀN LƯƠNG...", "PHIẾU
    # LƯƠNG", "HỢP ĐỒNG LAO ĐỘNG") -- a real name/address value never is.
    # A cheap, general reject for whichever specific title text a proximity
    # search happens to land on, rather than blacklisting each one by name.
    letters = [c for c in value if c.isalpha()]
    return len(letters) > 6 and all(c.isupper() for c in letters)

# same label vocabulary as LABEL_PATTERNS, minus the trailing ":[ \t]*(.+)" --
# for table cells where the whole cell IS just the label with no colon at
# all, and the real value lives in the adjacent cell (see
# extract_from_table_rows). This is the dominant miss class flattened-text
# regex can't reach (measured: 14/16 misses in accuracy_report.txt).
_BARE_LABEL_RE = {
    "name": re.compile(
        r"H[oọ]?\s*(?:và)?\s*t[eê]n|BÊN\s*B|T[eê]n\s*NV|[ÔO]ng\s*/\s*[Bb][àa]",
        re.IGNORECASE,
    ),
    "address": re.compile(r"[ĐD][iị]a\s*ch[iỉ]", re.IGNORECASE),
}


def _clean_label_value(value: str) -> str | None:
    value = value.strip()
    if not value or _STARTS_WITH_FILLER_RE.match(value):
        return None
    if _BRACKET_PLACEHOLDER_RE.match(value):
        return None
    if value.lower() in _GENERIC_ROLE_VALUES:
        return None
    if _PLACEHOLDER_NAME_STRIPPED_RE.match(_strip_diacritics(value)):
        return None
    if _BOILERPLATE_RE.search(value):
        return None
    if _is_shouty_title(value):
        return None
    # a colon anywhere in the captured value means we've bled into another
    # label's text (e.g. a merged/duplicated table cell producing "ÔNG/BÀ:
    # Quốc tịch: Quốc tịch:") -- a real name/address never contains one, so
    # this is a safe, reliable "not real data" signal.
    if ":" in value:
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
    # try every match for a field's pattern, not just the first -- a single
    # .search() stops at the first regex hit even if it's a known-blank
    # value (e.g. a "Bên B: Người lao động" section header matches before a
    # real "Ông/bà: <name>" line later in the same document), silently
    # missing the real value that comes after it.
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


def extract_from_table_rows(rows: list[list[str]]) -> dict:
    """Pair a bare label cell with its adjacent value cell. Table rows keep
    real cell boundaries (from python-docx's own table API or PPStructureV3's
    table HTML), so this recovers name/address on colon-less label/value
    layouts the flattened-text regex path never sees."""
    result: dict[str, str] = {}
    for row in rows:
        for i, cell in enumerate(row):
            cell = cell.strip()
            if not cell:
                continue
            for field, pattern in _BARE_LABEL_RE.items():
                if result.get(field) or not pattern.search(cell):
                    continue
                colon_idx = cell.find(":")
                candidate = _clean_label_value(cell[colon_idx + 1:]) if colon_idx != -1 else None
                if candidate is None and i + 1 < len(row):
                    candidate = _clean_label_value(row[i + 1])
                if candidate is not None:
                    result[field] = candidate
    return result


def parse_vnd_amount(value: str) -> float | None:
    """Pull the numeric amount out of a captured income value like
    '30.000.000 VND' or '5,964,265 (1)' -- strips currency suffix/trailing
    notes and normalizes either '.' or ',' as the thousands separator (see
    SALARY_RE's comment: real templates use both conventions)."""
    match = re.search(r"\d{1,3}(?:[.,]\d{3})+|\d+", value)
    if match is None:
        return None
    digits = re.sub(r"[.,]", "", match.group(0))
    return float(digits)


def extract_income(text: str) -> tuple[float | None, str | None]:
    """Try every gross-income label match first, then every net-income
    label match -- same finditer-not-first-search approach as
    extract_label_anchored, so a known-blank label earlier in the document
    doesn't shadow a real value later on."""
    for basis in ("gross", "net"):
        for match in INCOME_LABEL_PATTERNS[basis].finditer(text):
            cleaned = _clean_label_value(match.group(1))
            if cleaned is None:
                continue
            amount = parse_vnd_amount(cleaned)
            if amount is not None:
                return amount, basis
    return None, None


# the ~30 most common Vietnamese surnames cover the vast majority of real
# names (a genuinely closed, well-known set) -- given names are open-ended
# and far riskier to "correct" this way (a wrong correction on a rare-but-
# real given name is worse than leaving an OCR-garbled one alone), so this
# stays scoped to surnames only.
_VN_SURNAMES = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ",
    "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Đoàn",
    "Vương", "Trương", "Mai", "Đào", "Lương", "Tô", "Tăng", "Chu", "Cao",
    "Trịnh", "Đàm", "Kiều", "Lâm",
]


def _strip_diacritics(s: str) -> str:
    # Đ/đ don't decompose via NFD (they're their own codepoints, not a
    # base letter + combining mark) -- map explicitly before stripping.
    s = s.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


_SURNAME_LOOKUP = {_strip_diacritics(s).lower(): s for s in _VN_SURNAMES}


def restore_name_diacritics(name: str | None) -> str | None:
    """OCR frequently drops diacritics on an otherwise-correctly-positioned
    name (e.g. "Duong Vu" for "Dương Vũ") -- restore them token-by-token
    where a word's diacritic-stripped form matches a known surname exactly."""
    if not name:
        return name
    words = name.split()
    restored = [_SURNAME_LOOKUP.get(_strip_diacritics(w).lower(), w) for w in words]
    return " ".join(restored)


def _ner_fallback(text: str, missing_fields: list[str]) -> dict:
    # ponytail: no reliable pretrained Vietnamese NER model exists (see
    # project_name_extraction_strategy memory) — this tier stays unwired until
    # a real VN NER source is chosen. Upgrade here when Module 2 needs it.
    return {field: None for field in missing_fields}


def extract_fields_from_text(text: str, table_rows: list[list[str]] | None = None) -> dict:
    fields = extract_regex_fields(text)
    fields.update(extract_label_anchored(text))
    if table_rows:
        for field, value in extract_from_table_rows(table_rows).items():
            if not fields.get(field):
                fields[field] = value
    missing = [f for f in ("name", "address") if not fields.get(f)]
    if missing:
        fields.update(_ner_fallback(text, missing))
    fields["name"] = restore_name_diacritics(fields.get("name"))
    fields["income"], fields["income_basis"] = extract_income(text)
    return fields
