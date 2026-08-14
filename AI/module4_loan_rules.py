# Issue #139: the pipeline's document/OCR language switched to English
# (#127), and the real validation corpus (#131) is genuinely Australian --
# the Fair Work Ombudsman's own official payslip template, AUD amounts,
# ABN, BSB, superannuation, not just English-language VN documents. Kept
# the Vietnamese min-income floor here after the language switch would
# have been a live bug: a real AU payslip's extracted income (hundreds to
# low thousands of dollars per pay period) compared against 10,000,000
# always fails, regardless of actual income. MAX_REPAYMENT_RATIO/
# MAX_DTI_RATIO are pure ratios and never needed to change for any
# currency -- only the absolute-currency floor did.
#
# AUD 4,000/month is grounded in Australia's real National Minimum Wage
# ($26.44/hr, $1,004.90/week full-time as of 1 July 2026 -- Fair Work
# Ombudsman/Fair Work Commission), rounded down slightly rather than up,
# consistent with a loan-serviceability floor sitting at or near
# full-time minimum wage rather than materially above it.
MIN_MONTHLY_INCOME_AUD = 4_000
MAX_REPAYMENT_RATIO = 0.30
MAX_DTI_RATIO = 0.40


# Issue #163 -- balance-sheet-based readiness, a company's financial
# health rather than a personal repayment-vs-income check. Real AU SME
# lending sources, not invented: current ratio >= 1.0 is the accepted
# minimum (1.5-2.0 considered healthy); debt-to-equity <= 2.0 is where AU
# lenders' "stress zone" starts (below 1.0 = strong, 1.5-2.0 = moderate).
# https://www.crestmontcapital.com/blog/how-financial-ratios-influence-loan-approval
# https://nexist.com.au/blog/debt-to-equity-ratio
MIN_CURRENT_RATIO = 1.0
MAX_DEBT_TO_EQUITY_RATIO = 2.0


def assess_balance_sheet_readiness(
    total_current_assets: float | None,
    total_current_liabilities: float | None,
    total_liabilities: float | None,
    total_equity: float | None,
) -> dict:
    can_check_current_ratio = total_current_assets is not None and total_current_liabilities is not None
    can_check_debt_to_equity = total_liabilities is not None and total_equity is not None

    if not can_check_current_ratio and not can_check_debt_to_equity:
        empty_check = {"pass": None, "value": None}
        return {
            "verdict": "INSUFFICIENT_DATA",
            "checks": {
                "current_ratio": {**empty_check, "threshold": MIN_CURRENT_RATIO},
                "debt_to_equity": {**empty_check, "threshold": MAX_DEBT_TO_EQUITY_RATIO},
            },
        }

    checks = {}
    if can_check_current_ratio:
        current_ratio = total_current_assets / total_current_liabilities if total_current_liabilities else None
        checks["current_ratio"] = {
            "pass": current_ratio is not None and current_ratio >= MIN_CURRENT_RATIO,
            "value": current_ratio,
            "threshold": MIN_CURRENT_RATIO,
        }
    else:
        checks["current_ratio"] = {"pass": None, "value": None, "threshold": MIN_CURRENT_RATIO}

    if can_check_debt_to_equity:
        debt_to_equity = total_liabilities / total_equity if total_equity else None
        checks["debt_to_equity"] = {
            "pass": debt_to_equity is not None and debt_to_equity <= MAX_DEBT_TO_EQUITY_RATIO,
            "value": debt_to_equity,
            "threshold": MAX_DEBT_TO_EQUITY_RATIO,
        }
    else:
        checks["debt_to_equity"] = {"pass": None, "value": None, "threshold": MAX_DEBT_TO_EQUITY_RATIO}

    known_checks = [c for c in checks.values() if c["pass"] is not None]
    verdict = "READY" if known_checks and all(c["pass"] for c in known_checks) else "NOT_READY"
    if not known_checks:
        verdict = "INSUFFICIENT_DATA"

    return {"verdict": verdict, "checks": checks}


def assess_loan_readiness(
    monthly_income: float | None,
    income_basis: str | None,
    proposed_monthly_repayment: float,
    existing_monthly_debt: float | None = None,
) -> dict:
    existing_debt_assumed_zero = existing_monthly_debt is None
    debt = 0.0 if existing_monthly_debt is None else existing_monthly_debt

    if monthly_income is None:
        empty_check = {"pass": None, "value": None}
        return {
            "verdict": "INSUFFICIENT_DATA",
            "income_basis": income_basis,
            "existing_debt_assumed_zero": existing_debt_assumed_zero,
            "checks": {
                "min_income": {**empty_check, "threshold": MIN_MONTHLY_INCOME_AUD},
                "repayment_ratio": {**empty_check, "threshold": MAX_REPAYMENT_RATIO},
                "dti": {**empty_check, "threshold": MAX_DTI_RATIO},
            },
        }

    repayment_ratio = proposed_monthly_repayment / monthly_income
    dti_ratio = (debt + proposed_monthly_repayment) / monthly_income

    checks = {
        "min_income": {
            "pass": monthly_income >= MIN_MONTHLY_INCOME_AUD,
            "value": monthly_income,
            "threshold": MIN_MONTHLY_INCOME_AUD,
        },
        "repayment_ratio": {
            "pass": repayment_ratio <= MAX_REPAYMENT_RATIO,
            "value": repayment_ratio,
            "threshold": MAX_REPAYMENT_RATIO,
        },
        "dti": {
            "pass": dti_ratio <= MAX_DTI_RATIO,
            "value": dti_ratio,
            "threshold": MAX_DTI_RATIO,
        },
    }
    verdict = "READY" if all(c["pass"] for c in checks.values()) else "NOT_READY"

    return {
        "verdict": verdict,
        "income_basis": income_basis,
        "existing_debt_assumed_zero": existing_debt_assumed_zero,
        "checks": checks,
    }


if __name__ == "__main__":
    def test_ready_case():
        result = assess_loan_readiness(
            monthly_income=8_000,
            income_basis="gross",
            proposed_monthly_repayment=1_200,
            existing_monthly_debt=400,
        )
        assert result["verdict"] == "READY"
        assert result["checks"]["min_income"]["pass"] is True
        assert result["checks"]["repayment_ratio"]["pass"] is True
        assert result["checks"]["dti"]["pass"] is True
        assert result["existing_debt_assumed_zero"] is False

    def test_income_below_floor():
        result = assess_loan_readiness(
            monthly_income=3_000,
            income_basis="net",
            proposed_monthly_repayment=400,
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["min_income"]["pass"] is False

    def test_repayment_ratio_too_high():
        result = assess_loan_readiness(
            monthly_income=8_000,
            income_basis="gross",
            proposed_monthly_repayment=2_800,  # 35% > 30% cap
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["repayment_ratio"]["pass"] is False
        assert result["checks"]["min_income"]["pass"] is True

    def test_dti_too_high_with_existing_debt():
        result = assess_loan_readiness(
            monthly_income=8_000,
            income_basis="gross",
            proposed_monthly_repayment=1_200,
            existing_monthly_debt=2_400,  # (2400+1200)/8000 = 45% > 40% cap
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["dti"]["pass"] is False
        assert result["checks"]["repayment_ratio"]["pass"] is True

    def test_missing_existing_debt_assumed_zero():
        result = assess_loan_readiness(
            monthly_income=8_000,
            income_basis="net",
            proposed_monthly_repayment=1_200,
            existing_monthly_debt=None,
        )
        assert result["existing_debt_assumed_zero"] is True
        assert result["checks"]["dti"]["value"] == 1_200 / 8_000

    def test_missing_income_is_insufficient_data():
        result = assess_loan_readiness(
            monthly_income=None,
            income_basis=None,
            proposed_monthly_repayment=1_200,
        )
        assert result["verdict"] == "INSUFFICIENT_DATA"
        assert result["checks"]["min_income"]["pass"] is None
        assert result["checks"]["min_income"]["value"] is None

    def test_balance_sheet_ready_case():
        result = assess_balance_sheet_readiness(
            total_current_assets=200_000,
            total_current_liabilities=100_000,  # current ratio 2.0
            total_liabilities=150_000,
            total_equity=100_000,  # debt-to-equity 1.5
        )
        assert result["verdict"] == "READY"
        assert result["checks"]["current_ratio"]["pass"] is True
        assert result["checks"]["debt_to_equity"]["pass"] is True

    def test_balance_sheet_current_ratio_too_low():
        result = assess_balance_sheet_readiness(
            total_current_assets=50_000,
            total_current_liabilities=100_000,  # current ratio 0.5 < 1.0
            total_liabilities=100_000,
            total_equity=100_000,
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["current_ratio"]["pass"] is False

    def test_balance_sheet_debt_to_equity_too_high():
        result = assess_balance_sheet_readiness(
            total_current_assets=200_000,
            total_current_liabilities=100_000,
            total_liabilities=300_000,
            total_equity=100_000,  # debt-to-equity 3.0 > 2.0
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["debt_to_equity"]["pass"] is False
        assert result["checks"]["current_ratio"]["pass"] is True

    def test_balance_sheet_missing_all_data_is_insufficient():
        result = assess_balance_sheet_readiness(
            total_current_assets=None,
            total_current_liabilities=None,
            total_liabilities=None,
            total_equity=None,
        )
        assert result["verdict"] == "INSUFFICIENT_DATA"
        assert result["checks"]["current_ratio"]["pass"] is None
        assert result["checks"]["debt_to_equity"]["pass"] is None

    def test_balance_sheet_partial_data_checks_what_it_can():
        # only current-ratio fields present -- debt-to-equity stays
        # unknown (None), doesn't block the verdict on what IS known
        result = assess_balance_sheet_readiness(
            total_current_assets=200_000,
            total_current_liabilities=100_000,
            total_liabilities=None,
            total_equity=None,
        )
        assert result["verdict"] == "READY"
        assert result["checks"]["current_ratio"]["pass"] is True
        assert result["checks"]["debt_to_equity"]["pass"] is None

    tests = [
        test_ready_case,
        test_income_below_floor,
        test_repayment_ratio_too_high,
        test_dti_too_high_with_existing_debt,
        test_missing_existing_debt_assumed_zero,
        test_missing_income_is_insufficient_data,
        test_balance_sheet_ready_case,
        test_balance_sheet_current_ratio_too_low,
        test_balance_sheet_debt_to_equity_too_high,
        test_balance_sheet_missing_all_data_is_insufficient,
        test_balance_sheet_partial_data_checks_what_it_can,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
