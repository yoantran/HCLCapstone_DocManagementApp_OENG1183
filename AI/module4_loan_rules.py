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

    tests = [
        test_ready_case,
        test_income_below_floor,
        test_repayment_ratio_too_high,
        test_dti_too_high_with_existing_debt,
        test_missing_existing_debt_assumed_zero,
        test_missing_income_is_insufficient_data,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
