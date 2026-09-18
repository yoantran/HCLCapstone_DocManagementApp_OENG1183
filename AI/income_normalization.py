"""
Converts Module 2's extracted income figure into a standardized monthly
value before it reaches Module 4's loan-readiness rules -- issue #141.
Module 2 only extracts what's printed on the document (a period-gross
figure, an optional annual salary, an optional pay-period date range);
it deliberately does no unit-conversion math. Module 4 is a pure rules
engine that expects an already-normalized monthly figure and was never
meant to know about pay periods. This sits between the two.
"""

WEEKLY_DAYS_RANGE = (6, 8)
FORTNIGHTLY_DAYS_RANGE = (12, 16)
MONTHLY_DAYS_RANGE = (27, 32)

# Standard AU payroll annualization factors, not invented figures.
WEEKLY_TO_MONTHLY = 52 / 12
FORTNIGHTLY_TO_MONTHLY = 26 / 12


def normalize_monthly_income(fields: dict) -> dict:
    income = fields.get("income")
    income_basis = fields.get("income_basis")
    annual_salary = fields.get("annual_salary")
    pay_period_days = fields.get("pay_period_days")

    if annual_salary is not None:
        return {
            "monthly_income": annual_salary / 12,
            "income_basis": income_basis,
            "income_source": "annual_salary",
            "pay_period_days": pay_period_days,
        }

    if income is None:
        return {
            "monthly_income": None,
            "income_basis": income_basis,
            "income_source": "insufficient_data",
            "pay_period_days": pay_period_days,
        }

    if pay_period_days is None:
        return {
            "monthly_income": income,
            "income_basis": income_basis,
            "income_source": "already_monthly",
            "pay_period_days": None,
        }

    if WEEKLY_DAYS_RANGE[0] <= pay_period_days <= WEEKLY_DAYS_RANGE[1]:
        return {
            "monthly_income": income * WEEKLY_TO_MONTHLY,
            "income_basis": income_basis,
            "income_source": "period_gross",
            "pay_period_days": pay_period_days,
        }
    if FORTNIGHTLY_DAYS_RANGE[0] <= pay_period_days <= FORTNIGHTLY_DAYS_RANGE[1]:
        return {
            "monthly_income": income * FORTNIGHTLY_TO_MONTHLY,
            "income_basis": income_basis,
            "income_source": "period_gross",
            "pay_period_days": pay_period_days,
        }
    if MONTHLY_DAYS_RANGE[0] <= pay_period_days <= MONTHLY_DAYS_RANGE[1]:
        return {
            "monthly_income": income,
            "income_basis": income_basis,
            "income_source": "period_gross",
            "pay_period_days": pay_period_days,
        }

    return {
        "monthly_income": None,
        "income_basis": income_basis,
        "income_source": "insufficient_data",
        "pay_period_days": pay_period_days,
    }


if __name__ == "__main__":
    def test_annual_salary_preferred_over_period_gross():
        fields = {"income": 718.66, "income_basis": "gross", "annual_salary": 60_000, "pay_period_days": 6}
        result = normalize_monthly_income(fields)
        assert result["monthly_income"] == 5_000.0
        assert result["income_source"] == "annual_salary"

    def test_weekly_period_gross_converted():
        fields = {"income": 718.66, "income_basis": "gross", "annual_salary": None, "pay_period_days": 6}
        result = normalize_monthly_income(fields)
        assert abs(result["monthly_income"] - 718.66 * (52 / 12)) < 1e-6
        assert result["income_source"] == "period_gross"

    def test_fortnightly_period_gross_converted():
        fields = {"income": 1_400.0, "income_basis": "gross", "annual_salary": None, "pay_period_days": 14}
        result = normalize_monthly_income(fields)
        assert abs(result["monthly_income"] - 1_400.0 * (26 / 12)) < 1e-6
        assert result["income_source"] == "period_gross"

    def test_no_period_data_treated_as_already_monthly():
        fields = {"income": 8_000.0, "income_basis": "gross", "annual_salary": None, "pay_period_days": None}
        result = normalize_monthly_income(fields)
        assert result["monthly_income"] == 8_000.0
        assert result["income_source"] == "already_monthly"

    def test_unclassifiable_period_is_honest_none():
        fields = {"income": 2_000.0, "income_basis": "gross", "annual_salary": None, "pay_period_days": 10}
        result = normalize_monthly_income(fields)
        assert result["monthly_income"] is None
        assert result["income_source"] == "insufficient_data"

    def test_missing_income_is_insufficient_data():
        fields = {"income": None, "income_basis": None, "annual_salary": None, "pay_period_days": None}
        result = normalize_monthly_income(fields)
        assert result["monthly_income"] is None
        assert result["income_source"] == "insufficient_data"

    tests = [
        test_annual_salary_preferred_over_period_gross,
        test_weekly_period_gross_converted,
        test_fortnightly_period_gross_converted,
        test_no_period_data_treated_as_already_monthly,
        test_unclassifiable_period_is_honest_none,
        test_missing_income_is_insufficient_data,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"\n{len(tests)} tests passed")
