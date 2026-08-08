import sys

sys.path.insert(0, ".")

from field_extraction import extract_income, parse_vnd_amount, extract_fields_from_text


def test_parse_vnd_amount_dot_separator():
    assert parse_vnd_amount("30.000.000 VND") == 30000000.0


def test_parse_vnd_amount_comma_separator():
    assert parse_vnd_amount("5,964,265") == 5964265.0


def test_parse_vnd_amount_no_number():
    assert parse_vnd_amount("...") is None


def test_extract_income_gross_label():
    text = "Mã Nhân Viên: 8888\nTổng thu nhập chính thức: 30.000.000 VND\nPhòng ban: DEPT1"
    amount, basis = extract_income(text)
    assert amount == 30000000.0
    assert basis == "gross"


def test_extract_income_falls_back_to_net_when_no_gross_label():
    text = "Mã BP: XƯỞNG 04-ĐÁ\nThực lĩnh lương (1): 5,964,265\nGhi chú:"
    amount, basis = extract_income(text)
    assert amount == 5964265.0
    assert basis == "net"


def test_extract_income_prefers_gross_over_net_when_both_present():
    text = "Tổng thu nhập chính thức: 30.000.000 VND\nThực lĩnh lương (1): 10.000.000 VND"
    amount, basis = extract_income(text)
    assert amount == 30000000.0
    assert basis == "gross"


def test_extract_income_blank_label_returns_none():
    text = "Tổng thu nhập chính thức: ……………………\nThực lĩnh lương (1): ……"
    amount, basis = extract_income(text)
    assert amount is None
    assert basis is None


def test_extract_income_rejects_generic_tong_cong_label():
    # "Tổng cộng" alone (not "Tổng thu nhập") must NOT be treated as income --
    # it's generic table-total vocabulary shared with balance-sheet documents
    # (e.g. "Tổng cộng tài sản"), a real false-positive risk.
    text = "Tổng cộng tài sản: 500.000.000 VND"
    amount, basis = extract_income(text)
    assert amount is None
    assert basis is None


def test_extract_fields_from_text_includes_income_keys():
    text = "Tổng thu nhập chính thức: 20.000.000 VND"
    fields = extract_fields_from_text(text)
    assert fields["income"] == 20000000.0
    assert fields["income_basis"] == "gross"


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
