MIN_MONTHLY_INCOME_VND = 10_000_000
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
                "min_income": {**empty_check, "threshold": MIN_MONTHLY_INCOME_VND},
                "repayment_ratio": {**empty_check, "threshold": MAX_REPAYMENT_RATIO},
                "dti": {**empty_check, "threshold": MAX_DTI_RATIO},
            },
        }

    repayment_ratio = proposed_monthly_repayment / monthly_income
    dti_ratio = (debt + proposed_monthly_repayment) / monthly_income

    checks = {
        "min_income": {
            "pass": monthly_income >= MIN_MONTHLY_INCOME_VND,
            "value": monthly_income,
            "threshold": MIN_MONTHLY_INCOME_VND,
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
            monthly_income=20_000_000,
            income_basis="gross",
            proposed_monthly_repayment=3_000_000,
            existing_monthly_debt=1_000_000,
        )
        assert result["verdict"] == "READY"
        assert result["checks"]["min_income"]["pass"] is True
        assert result["checks"]["repayment_ratio"]["pass"] is True
        assert result["checks"]["dti"]["pass"] is True
        assert result["existing_debt_assumed_zero"] is False

    def test_income_below_floor():
        result = assess_loan_readiness(
            monthly_income=8_000_000,
            income_basis="net",
            proposed_monthly_repayment=1_000_000,
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["min_income"]["pass"] is False

    def test_repayment_ratio_too_high():
        result = assess_loan_readiness(
            monthly_income=20_000_000,
            income_basis="gross",
            proposed_monthly_repayment=7_000_000,  # 35% > 30% cap
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["repayment_ratio"]["pass"] is False
        assert result["checks"]["min_income"]["pass"] is True

    def test_dti_too_high_with_existing_debt():
        result = assess_loan_readiness(
            monthly_income=20_000_000,
            income_basis="gross",
            proposed_monthly_repayment=3_000_000,
            existing_monthly_debt=6_000_000,  # (6M+3M)/20M = 45% > 40% cap
        )
        assert result["verdict"] == "NOT_READY"
        assert result["checks"]["dti"]["pass"] is False
        assert result["checks"]["repayment_ratio"]["pass"] is True

    def test_missing_existing_debt_assumed_zero():
        result = assess_loan_readiness(
            monthly_income=20_000_000,
            income_basis="net",
            proposed_monthly_repayment=3_000_000,
            existing_monthly_debt=None,
        )
        assert result["existing_debt_assumed_zero"] is True
        assert result["checks"]["dti"]["value"] == 3_000_000 / 20_000_000

    def test_missing_income_is_insufficient_data():
        result = assess_loan_readiness(
            monthly_income=None,
            income_basis=None,
            proposed_monthly_repayment=3_000_000,
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
