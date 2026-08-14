import sys

sys.path.insert(0, ".")

from field_extraction_en import extract_fields_from_text_en, parse_currency_amount


def test_parse_currency_amount_with_cents():
    assert parse_currency_amount("$27.81") == 27.81


def test_parse_currency_amount_with_thousands_and_cents():
    assert parse_currency_amount("$1,234.56") == 1234.56


def test_extracts_employee_name_not_employer():
    # real Fair Work Ombudsman template convention -- "Employee:"/"Employer:"
    # are parallel labels, must not cross-match ("Employer" doesn't contain
    # "Employee" as a substring, but worth a real regression test anyway)
    text = "*Employer: Acme Pty Ltd\n*ABN: 12 345 978 910\n*Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] == "Jo Worker"


def test_extracts_employee_name_and_address_real_contract_convention():
    # real label convention from part-time-employment-contract.docx
    text = (
        "Employer Name: Acme Pty Ltd\n"
        "Employer Address: 1 Business St, Melbourne VIC\n"
        "Employee Name: Sam Employee\n"
        "Employee Address: 22 Home St, Melbourne VIC 3000"
    )
    fields = extract_fields_from_text_en(text)
    assert fields["name"] == "Sam Employee"
    assert fields["address"] == "22 Home St, Melbourne VIC 3000"


def test_extracts_abn():
    text = "*Employer: Acme Pty Ltd\n*ABN: 12 345 978 910"
    fields = extract_fields_from_text_en(text)
    assert fields["abn"] == ["12 345 978 910"]


def test_extracts_bsb_and_account_number():
    # real values confirmed from the tested English payslip sample
    text = "Bank details: A Pretend Bank\nBSB: 123-456\nAccount: 1234 5678"
    fields = extract_fields_from_text_en(text)
    assert fields["bsb"] == "123-456"
    assert fields["account_number"] == "1234 5678"


def test_extracts_gross_and_net_income():
    text = "Total gross payment: $718.66\nNET PAY: $625.36"
    fields = extract_fields_from_text_en(text)
    assert fields["income"] == 718.66
    assert fields["income_basis"] == "gross"


def test_falls_back_to_net_when_no_gross_label():
    text = "NET PAY: $625.36"
    fields = extract_fields_from_text_en(text)
    assert fields["income"] == 625.36
    assert fields["income_basis"] == "net"


def test_salary_regex_requires_dollar_sign_not_bare_hours():
    # real payslip table has both dollar amounts ($27.81) and bare hour
    # counts (15.0) in the same row -- must not treat hours as salary
    text = "Ordinary hours 15.0 $27.81 $417.15"
    fields = extract_fields_from_text_en(text)
    assert set(fields["salary"]) == {"$27.81", "$417.15"}


def test_angle_bracket_placeholder_rejected():
    # real Fair Work template convention
    text = "*Employee: <insert employee name>"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] is None


def test_curly_brace_placeholder_rejected():
    # real convention from Template_Contract-full-time-or-part-time-Federal_Award.docx
    text = "{insert full name}, also referred to as “you”"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] is None


def test_underscore_blank_rejected():
    # real convention from part-time-employment-contract.docx
    text = "Employee Name: ____________________________________________________________"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] is None


def test_phone_field_present_but_absent_on_typical_documents():
    text = "Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert fields["phone"] == []


def test_no_cccd_or_vietnamese_fields_in_schema():
    text = "Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert "cccd" not in fields
    assert "tax_code" not in fields
    assert "bank_account" not in fields


def test_extracts_annual_salary_with_bracketed_aside():
    text = "*Annual salary: [if applicable] $67,000"
    fields = extract_fields_from_text_en(text)
    assert fields["annual_salary"] == 67000.0


def test_extracts_annual_salary_without_bracketed_aside():
    text = "Annual salary: $50,000"
    fields = extract_fields_from_text_en(text)
    assert fields["annual_salary"] == 50000.0


def test_no_annual_salary_returns_none():
    text = "Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert fields["annual_salary"] is None


def test_extracts_pay_period_days():
    text = "*Pay period: 16/07/2026 to 22/07/2026"
    fields = extract_fields_from_text_en(text)
    assert fields["pay_period_days"] == 6


def test_no_pay_period_returns_none():
    text = "Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert fields["pay_period_days"] is None


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
