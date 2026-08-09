import sys

sys.path.insert(0, ".")

from field_extraction import extract_fields_from_text


def test_extracts_so_tk_label():
    text = "Họ và tên: Nguyễn Văn Long\nSố TK: 0631000449323\nMST TNCN: 8396543222"
    fields = extract_fields_from_text(text)
    assert fields["bank_account"] == "0631000449323"


def test_extracts_so_tai_khoan_label():
    text = "Số tài khoản: 19036789012345\nNgân hàng: Vietcombank"
    fields = extract_fields_from_text(text)
    assert fields["bank_account"] == "19036789012345"


def test_extracts_stk_label():
    text = "STK: 0123456789\nChủ tài khoản: Trần Thị B"
    fields = extract_fields_from_text(text)
    assert fields["bank_account"] == "0123456789"


def test_blank_bank_account_returns_none():
    text = "Số TK: ……………………\nGhi chú:"
    fields = extract_fields_from_text(text)
    assert fields["bank_account"] is None


def test_absent_bank_account_returns_none():
    text = "Họ và tên: Nguyễn Văn Long"
    fields = extract_fields_from_text(text)
    assert fields["bank_account"] is None


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
