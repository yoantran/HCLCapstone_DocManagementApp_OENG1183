import sys

sys.path.insert(0, ".")

from field_extraction_en import (
    extract_balance_sheet_fields_en,
    extract_fields_from_text_en,
    extract_name_via_ner_en,
    parse_currency_amount,
    parse_currency_amount_balance_sheet,
)


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


def test_extracts_name_and_address_when_ocr_drops_leading_e():
    # Real confirmed case (#272): rendering a real tracked FILLED contract
    # through the actual OCR pipeline (docx -> pdf -> image -> PPStructureV3,
    # not a hand-picked corpus file) produced "mployee Name:"/"mployee
    # Address:" -- OCR dropped the leading "E" on both labels, same
    # left-edge character-drop artifact already confirmed on Payslip.jpg.
    text = (
        "mployer Name: Jesse Townsend\n"
        "mployer Address: 681/1 Jillian Flat, South Matthewport QLD 2672\n"
        "mployee Name: Steven Wood\n"
        "mployee Address: Unit 67 4 Martin Spur, West Adamfurt NT 2639"
    )
    fields = extract_fields_from_text_en(text)
    assert fields["name"] == "Steven Wood"
    assert fields["address"] == "Unit 67 4 Martin Spur, West Adamfurt NT 2639"


def test_extracts_bsb_and_account_when_ocr_drops_leading_letter():
    # Issue #272 -- proactive fix, checked (not assumed) for false-positive
    # risk: searched the whole corpus for a standalone "SB:"/"ccount:" not
    # preceded by "B"/"A", zero collisions found before applying this.
    text = "Bank details: A Pretend Bank\nSB: 123-456\nccount: 1234 5678"
    fields = extract_fields_from_text_en(text)
    assert fields["bsb"] == "123-456"
    assert fields["account_number"] == "1234 5678"


def test_extracts_gross_and_net_when_ocr_drops_leading_letter():
    # Issue #272 -- same proactive fix, but "gross" specifically needed
    # real corpus checking first: a bare dropped-G "ross" collides with
    # real unrelated text (a real employer surname "Christopher Ross",
    # "Crossing", "Crossroad") -- requiring the trailing "Pay" to stay
    # mandatory is what makes this safe, confirmed against the corpus.
    text = "ross Pay: $718.66\nET PAY: $625.36"
    fields = extract_fields_from_text_en(text)
    assert fields["income"] == 718.66
    assert fields["income_basis"] == "gross"


def test_does_not_match_bare_ross_without_trailing_pay():
    # The real collision this design specifically avoids.
    text = "Employer Name: Christopher Ross\nEmployer Address: 1 Crossing St"
    fields = extract_fields_from_text_en(text)
    assert fields["income"] is None


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


def test_balance_sheet_picks_current_column_when_current_is_leftmost():
    # Issue #182's real template: header reads "CURRENT YR." then "[PRIOR",
    # current year FIRST -- rightmost would silently return the older figure.
    rows = [
        ["", "CURRENT YR.", "[PRIOR"],
        ["Total current assets", "$120,000.00", "$100,000.00"],
    ]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_current_assets"] == 120000.0


def test_balance_sheet_picks_current_column_when_current_is_rightmost():
    # #172's original real template: "PRIOR YEAR" then "CURRENT YEAR" --
    # rightmost happens to be correct here, must still work.
    rows = [
        ["", "PRIOR YEAR", "CURRENT YEAR"],
        ["Total Assets", "$100,000.00", "$120,000.00"],
    ]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_assets"] == 120000.0


def test_balance_sheet_picks_highest_numbered_period_column():
    # A third real convention: FY1/FY2/FY3, ascending -- no "current"/
    # "prior" wording at all, only period numbers.
    rows = [
        ["", "FY1", "FY2", "FY3"],
        ["Total Liabilities", "$50,000.00", "$60,000.00", "$70,000.00"],
    ]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_liabilities"] == 70000.0


def test_salary_field_suppressed_on_balance_sheet_input():
    # Issue #219 -- SALARY_RE previously ran unconditionally and matched
    # every dollar figure in a balance-sheet table as spurious "salary".
    text = "Total Current Assets $7,850.00\nTotal Assets $4,900.00"
    rows = [["Total Current Assets", "$7,850.00"], ["Total Assets", "$4,900.00"]]
    fields = extract_fields_from_text_en(text, table_rows=rows)
    assert fields["salary"] == []


def test_salary_field_still_populated_on_payslip_input():
    text = "Total gross payment: $27.81"
    fields = extract_fields_from_text_en(text)
    assert fields["salary"] == ["$27.81"]


def test_salary_field_not_suppressed_by_non_balance_sheet_table():
    # Real regression found auditing #219 on Pay-slip-template-sts-FILLED-118.docx:
    # a DOCX payslip's own line-item table has table_rows but no balance-sheet
    # labels, so gating on table_rows presence alone wrongly zeroed out salary.
    text = "Ordinary hours $798.36\nOvertime $551.28\nTotal gross payment: $798.36"
    rows = [["Ordinary hours", "$798.36"], ["Overtime", "$551.28"]]
    fields = extract_fields_from_text_en(text, table_rows=rows)
    assert fields["salary"] == ["$798.36", "$551.28", "$798.36"]


def test_balance_sheet_picks_highest_year_n_column():
    # Issue #192 -- images (9).jpg's ACTUAL real header text is "Year N"
    # (spelled out), not "FYn". The original #182 regex only matched
    # "FYn" and silently never detected this real header at all.
    rows = [
        ["", "Year 1", "Year 2", "Year 3"],
        ["Total Assets", "$100,000.00", "$110,000.00", "$120,000.00"],
    ]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_assets"] == 120000.0


def test_parse_currency_amount_balance_sheet_period_separated_thousands():
    # Issue #188 -- real OCR on some cells uses period as the
    # thousands-group separator instead of comma/space.
    assert parse_currency_amount_balance_sheet("$89.000.00") == 89000.0
    assert parse_currency_amount_balance_sheet("$41.000.00") == 41000.0


def test_parse_currency_amount_balance_sheet_period_thousands_does_not_break_cents():
    # Must not regress real, already-correct comma/space parsing.
    assert parse_currency_amount_balance_sheet("$1,500.00") == 1500.0
    assert parse_currency_amount_balance_sheet("89 000.00") == 89000.0


def test_parse_currency_amount_balance_sheet_dot_thousands_no_cents_removed():
    # Issue #186 originally added a dedicated branch for this shape
    # ("120.000" -> 120000.0). Issue #271 removed it on explicit request
    # after measuring its real blast radius: instrumenting the function
    # showed it only ever fired on 3 cells across the whole corpus, and
    # re-running every file with it removed confirmed zero change to any
    # file's final extracted result -- including images (9).jpg, whose
    # own row has other, unaffected cells that "last cell wins" already
    # resolves to instead. A bare dot-grouped value with no cents suffix
    # now falls through to the plain fallback parse -- documented here
    # as the current, intentional behavior, not a bug.
    assert parse_currency_amount_balance_sheet("120.000") == 120.0
    assert parse_currency_amount_balance_sheet("165.000") == 165.0


def test_parse_currency_amount_balance_sheet_bare_digit_run_not_truncated():
    # Issue #186 -- previously truncated to the first 3 digits since the
    # grouped alternative requires a literal comma/space to keep matching.
    assert parse_currency_amount_balance_sheet("165000") == 165000.0
    assert parse_currency_amount_balance_sheet("45000") == 45000.0
    assert parse_currency_amount_balance_sheet("614800") == 614800.0
    assert parse_currency_amount_balance_sheet("5234202.00") == 5234202.0


def test_parse_currency_amount_balance_sheet_dot_and_bare_do_not_regress_existing_cases():
    # Must not regress real, already-correct comma/space/period-with-cents
    # parsing, or the plain 2-digit-cents case.
    assert parse_currency_amount_balance_sheet("$1,500.00") == 1500.0
    assert parse_currency_amount_balance_sheet("89 000.00") == 89000.0
    assert parse_currency_amount_balance_sheet("$89.000.00") == 89000.0
    assert parse_currency_amount_balance_sheet("$637.89") == 637.89
    # Confirmed unsafe to fix generally (regex backtracking corrupts this
    # common case if the dot-thousands regex's separator class is widened
    # to also accept comma/space) -- must keep parsing correctly as-is.
    assert parse_currency_amount_balance_sheet("$435,879,843.89") == 435879843.89


def test_balance_sheet_falls_back_to_rightmost_when_no_header_detected():
    # No recognizable header row at all (most real docx tables) -- must
    # keep #172's original rightmost behavior unchanged, no regression.
    rows = [["Total Equity", "$1", "$2", "$3"]]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_equity"] == 3.0


def test_balance_sheet_section_carries_across_two_calls():
    # Issue #297 -- a section header on one page with its bare "Total"
    # row on the next needs the section-tracking state threaded across
    # two separate calls (real multi-page pipeline.py loops call this
    # once per page, independently). Page 1's rows only contain the
    # header; page 2's only contain the bare Total row -- neither call
    # alone can resolve total_current_liabilities without the carry.
    page1_rows = [["Current/short-term Liabilities"]]
    page2_rows = [["Total", "$45,000"]]

    page1_fields, section = extract_balance_sheet_fields_en(page1_rows)
    assert page1_fields["total_current_liabilities"] is None
    assert section == "total_current_liabilities"

    page2_fields, _ = extract_balance_sheet_fields_en(page2_rows, section)
    assert page2_fields["total_current_liabilities"] == 45000.0

    # Confirm the carry is actually necessary -- without it, page 2
    # alone still can't resolve it, matching the real bug's shape.
    page2_fields_nocarry, _ = extract_balance_sheet_fields_en(page2_rows)
    assert page2_fields_nocarry["total_current_liabilities"] is None


def test_balance_sheet_bare_total_resolves_when_values_precede_it():
    # Issue #298 -- confirmed real on 3 independent documents
    # (Balance-sheet-template-FILLED-302/307/312_p2.png): some
    # templates put "Total" as the LAST cell in its row, with every
    # value BEFORE it -- reversed from the assumed "label first,
    # values after" shape _resolve_value's forward search expects.
    # Rightmost value wins (no header detected here), same convention
    # as the forward-order case.
    rows = [
        ["Current/short term liabilities"],
        ["$78,000", "$80,000", "$55,000", "$94,000", "$129,000", "Total"],
    ]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_current_liabilities"] == 129000.0


def test_balance_sheet_section_header_tolerates_despaced_short_term():
    # Issue #297 -- real OCR on Balance-sheet-template-FILLED-300_p1.png
    # recovers this header as "Curr ent/ short term liabil ities" --
    # _despace() strips the internal spaces (no hyphen to begin with),
    # leaving "Current/shorttermLiabilities". The original regex
    # required a literal "-" in "/short-term", which this despaced text
    # never has -- confirmed real, this exact cell never matched before.
    rows = [["Current/short term liabilities"], ["Total", "$45,000"]]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_current_liabilities"] == 45000.0


def test_parse_currency_amount_balance_sheet_rejects_prose_with_incidental_number():
    # Real confirmed bug (#271, images (2).jpg): a genuinely blank
    # worksheet template's own instructional sentence ("...in 12
    # months...") sat in the cell adjacent to a real "Total current
    # assets" label, and got accepted as if "12" were a dollar figure.
    assert parse_currency_amount_balance_sheet("in12 months") is None
    assert parse_currency_amount_balance_sheet("in 12 months") is None
    # Must not regress a real amount that happens to be short.
    assert parse_currency_amount_balance_sheet("$12.00") == 12.0


def test_balance_sheet_does_not_match_prose_cell_adjacent_to_real_label():
    # Same bug, full pipeline: "Total current assets" is a real exact
    # label match, but its neighboring cell is prose, not a value --
    # must stay None, not silently populate with a wrong number.
    rows = [["Total current assets", "in12 months"]]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_current_assets"] is None


def test_last_numeric_cell_skips_bare_currency_symbol_not_stops():
    # Real confirmed bug (#271, IC-Small-Business-Pro-Forma-Balance-Sheet-
    # Template.jpg): OCR split "$" into its own cell (and elsewhere in the
    # same real table misreads "$" as bare "s"/"S") ahead of the real
    # value -- the #184 stop-at-first-unparseable-cell guard treated it
    # as a different field's label and gave up before ever reaching the
    # real number 2 cells later.
    row = ["TOTAL ASSETS", "s", "558.00", "$", "1,848.00"]
    fields, _ = extract_balance_sheet_fields_en([row])
    assert fields["total_assets"] is not None


def test_last_numeric_cell_still_stops_at_a_real_label():
    # Must not regress #184's original case -- a real OTHER field's label
    # (not a bare currency symbol) still has to stop the scan.
    rows = [["Total Current Assets", "$105,000", "", "Total Long-Term Assets", "$320,000"]]
    fields, _ = extract_balance_sheet_fields_en(rows)
    assert fields["total_current_assets"] == 105000.0


def test_ner_fallback_finds_name_with_real_unrecognized_label_wording():
    # Real confirmed case (#270 class A): Payslip.jpg's actual OCR text --
    # "Pay Slip For:" garbled to "ay Slip For:", label+value split across
    # lines. LABEL_PATTERNS["name"] doesn't match this wording at all.
    text = "ay Slip For:\nRymer, Mark\nCheque No:\n71\nlassification:\nAssembly"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] == "Rymer, Mark"


def test_ner_fallback_does_not_override_a_working_regex_match():
    text = "*Employer: Acme Pty Ltd\n*Employee: Jo Worker"
    fields = extract_fields_from_text_en(text)
    assert fields["name"] == "Jo Worker"


def test_ner_fallback_ignores_unrelated_person_names():
    # No name-context keyword anywhere -- must not grab a name from
    # unrelated text just because spaCy tags it PERSON somewhere.
    text = "Approved by the finance team.\nJohn Smith reviewed this document."
    assert extract_name_via_ner_en(text) is None


def test_ner_fallback_same_line_after_colon():
    text = "Full Name: Priya Chandra\nDate: 01/01/2026"
    assert extract_name_via_ner_en(text) == "Priya Chandra"


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
