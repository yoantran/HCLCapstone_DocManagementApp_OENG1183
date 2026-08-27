import sys

sys.path.insert(0, ".")

from module2_ocr_extraction import (
    _line_index_for_offset,
    _repair_line_split_fields,
    find_adjacent_value,
    lines_to_text,
)


def _line(text, box):
    return {"text": text, "box": box}


# Real boxes captured from a live OCR run against samples/en_pay_slip/Payslip.jpg
# (issue #270 class B) -- not synthetic guesses.
PAYSLIP_LINES = [
    _line("MOGO", [0, 0, 72, 30]),
    _line("ABN. 89 002 605 076", [401, 6, 527, 27]),
    _line("ay Slip For:", [0, 48, 66, 70]),
    _line("Rymer, Mark", [107, 52, 184, 75]),
    _line("lassification:", [0, 69, 74, 92]),
    _line("Cheque No:", [400, 60, 471, 79]),
    _line("71", [481, 61, 510, 80]),
    _line("Assembly", [104, 73, 167, 98]),
]


def test_finds_value_to_the_right_on_same_row():
    assert find_adjacent_value(PAYSLIP_LINES, 2) == "Rymer, Mark"  # index 2 = "ay Slip For:"


def test_does_not_cross_into_unrelated_column():
    # "lassification:" and "Cheque No:" overlap vertically (different
    # columns of a 2-column form) but are 326px apart on a 600px-wide
    # page -- must not be treated as the same row.
    assert find_adjacent_value(PAYSLIP_LINES, 4) != "Cheque No:"


def test_line_index_for_offset_maps_back_to_originating_line():
    text = lines_to_text(PAYSLIP_LINES)
    offset = text.index("ay Slip For:")
    assert _line_index_for_offset(PAYSLIP_LINES, offset) == 2


# Synthetic, but representative of Payslip.jpg's real "GROSS PAY:" /
# "$5,837.50" split -- a correctly-worded label (matches LABEL_PATTERNS
# as-is, no wording issue -- that's class A, not this) whose value landed
# in a separate OCR box. This is the pure class-B case for a name-style
# field: "ay Slip For:" (Payslip.jpg's actual wording) doesn't test this,
# since it fails to match LABEL_PATTERNS at all -- a class A gap, not B.
NAME_SPLIT_LINES = [
    _line("Employee:", [0, 100, 70, 122]),
    _line("Jo Worker", [110, 102, 190, 124]),
]


def test_repair_fills_name_split_across_ocr_lines():
    text = lines_to_text(NAME_SPLIT_LINES)
    fields = {"name": None, "address": None, "bsb": None, "account_number": None, "income": None}
    _repair_line_split_fields(NAME_SPLIT_LINES, text, fields)
    assert fields["name"] == "Jo Worker"


# Real boxes from grid4.jpg -- "Net Pay" label and its value "9500" were
# split by OCR into "Net Pay" then a lone "9" then "500" on nearby lines,
# which pre-fix caused income to be parsed as 9.0 instead of 9500 (a
# wrong value, not a miss -- the more dangerous class B failure mode).
GRID4_LINES = [
    _line("Total Deductions", [0, 400, 120, 420]),
    _line("Net Pay", [0, 425, 60, 447]),
    _line("9500", [70, 426, 110, 448]),
]


def test_repair_fills_income_split_across_ocr_lines():
    text = lines_to_text(GRID4_LINES)
    fields = {"name": None, "address": None, "bsb": None, "account_number": None, "income": None}
    _repair_line_split_fields(GRID4_LINES, text, fields)
    assert fields["income"] == 9500.0
    assert fields["income_basis"] == "net"


def test_repair_is_a_noop_when_field_already_found():
    lines = [_line("Employee: Jo Worker", [0, 0, 200, 20])]
    text = lines_to_text(lines)
    fields = {"name": "Jo Worker", "address": None, "bsb": None, "account_number": None, "income": None}
    _repair_line_split_fields(lines, text, fields)
    assert fields["name"] == "Jo Worker"


if __name__ == "__main__":
    test_finds_value_to_the_right_on_same_row()
    test_does_not_cross_into_unrelated_column()
    test_line_index_for_offset_maps_back_to_originating_line()
    test_repair_fills_name_split_across_ocr_lines()
    test_repair_fills_income_split_across_ocr_lines()
    test_repair_is_a_noop_when_field_already_found()
    print("all module2 OCR line-repair self-checks passed")
