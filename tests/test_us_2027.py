"""Tests for the US 2027 tax table, holiday-aware deadlines and fallback warnings."""
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from us.tax_rules import TAX_YEAR_RULES, get_tax_year_rules
from us.tax_dates import _shift_weekend, get_estimated_tax_deadlines
from us.tax_calculator import calculate_liability
from us.claim_rules import generate_us_claims


# ── 2027 table ───────────────────────────────────────────────────────────────

def test_2027_is_in_table_and_not_a_fallback():
    rules = get_tax_year_rules(2027)
    assert rules is TAX_YEAR_RULES[2027]
    assert rules["year"] == 2027
    assert "warnings" not in rules and "confidence" not in rules
    assert rules["standard_deduction"]["single"] != get_tax_year_rules(2026)["standard_deduction"]["single"]


def test_2027_standard_deduction():
    sd = get_tax_year_rules(2027)["standard_deduction"]
    assert sd == {
        "single": 16_600,
        "married_filing_jointly": 33_200,
        "married_filing_separately": 16_600,
        "head_of_household": 24_925,
    }


def test_2027_brackets_values_and_contiguity():
    b = get_tax_year_rules(2027)["brackets"]
    assert set(b) == {"single", "married_filing_jointly", "head_of_household", "married_filing_separately"}
    assert b["single"][0] == (0.10, 0, 12_800)
    assert b["single"][-2] == (0.35, 264_550, 661_375)
    assert b["married_filing_jointly"][-2] == (0.35, 529_100, 793_650)
    assert b["head_of_household"][0] == (0.10, 0, 18_250)
    assert b["married_filing_separately"][-2] == (0.35, 264_550, 396_825)
    for status, brackets in b.items():
        assert [r for r, _, _ in brackets] == [0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37]
        assert brackets[0][1] == 0 and brackets[-1][2] is None
        for (_, _, upper), (_, lower, _) in zip(brackets, brackets[1:]):
            assert upper == lower, status


def test_2027_other_parameters():
    r = get_tax_year_rules(2027)
    assert r["fica"]["social_security_wage_base"] == 192_300
    lim = r["contribution_limits"]
    assert (lim["401k_employee"], lim["401k_catchup_50plus"], lim["401k_catchup_60_63"]) == (25_500, 8_500, 11_750)
    assert (lim["ira"], lim["hsa_individual"], lim["hsa_family"], lim["sep_ira_max"]) == (7_500, 4_500, 9_000, 75_000)
    assert r["amt"] == {
        "exemption_single": 93_000, "exemption_mfj": 144_700,
        "phase_out_single": 515_950, "phase_out_mfj": 1_031_900,
    }
    assert r["qbi"]["threshold_single"] == 208_300 and r["qbi"]["threshold_mfj"] == 416_600
    assert r["child_tax_credit"] == {"max_per_child": 2_300, "refundable_portion": 1_800}
    assert r["estate_gift"] == {"estate_basic_exclusion": 15_480_000, "gift_annual_exclusion": 20_000}
    ltcg = r["long_term_capital_gains"]
    assert ltcg["single"][0][2] == 51_050 and ltcg["married_filing_jointly"][1][2] == 633_600
    assert ltcg["head_of_household"][1][2] == 598_400 and ltcg["married_filing_separately"][1][2] == 316_800


def test_2027_hoh_uses_hoh_brackets_in_calculator():
    base = {"employment": {"annual_gross": 100_000, "type": "employed"},
            "tax_profile": {"filing_status": "head_of_household", "tax_year": 2027}}
    hoh = calculate_liability(base)
    single = calculate_liability(
        {**base, "tax_profile": {"filing_status": "single", "tax_year": 2027}})
    # HoH: wider 10%/12% bands but a bigger standard deduction -> strictly less federal tax
    assert hoh["federal_income_tax"] < single["federal_income_tax"]
    taxable = 100_000 - 24_925
    expected = 18_250 * 0.10 + (69_650 - 18_250) * 0.12 + (taxable - 69_650) * 0.22
    assert hoh["federal_income_tax"] == pytest.approx(expected, abs=1)


# ── Fallback must be explicit ────────────────────────────────────────────────

def test_future_year_fallback_is_flagged_low_confidence():
    r = get_tax_year_rules(2099)
    assert r["year"] == max(TAX_YEAR_RULES)          # data from latest table
    assert r["fallback_for_year"] == 2099
    assert r["confidence"] == "low"
    assert r["warnings"] and "2099" in r["warnings"][0]
    # the shared table must not be mutated
    assert "warnings" not in TAX_YEAR_RULES[max(TAX_YEAR_RULES)]


def test_2028_does_not_silently_return_2027_as_if_known():
    assert get_tax_year_rules(2028)["confidence"] == "low"


# ── Holiday-aware deadlines ──────────────────────────────────────────────────

def test_q4_2027_skips_saturday_and_mlk_day():
    assert date(2028, 1, 15).weekday() == 5
    assert _shift_weekend(date(2028, 1, 15)) == date(2028, 1, 18)
    q = {d["quarter"]: d["deadline"] for d in get_estimated_tax_deadlines(2027)}
    assert q == {"Q1": "2027-04-15", "Q2": "2027-06-15", "Q3": "2027-09-15", "Q4": "2028-01-18"}


def test_2027_table_deadlines_match_computed_deadlines():
    table = [d["due"] for d in get_tax_year_rules(2027)["quarterly_deadlines"]]
    assert table == [d["deadline"] for d in get_estimated_tax_deadlines(2027)]


@pytest.mark.parametrize("d, expected", [
    (date(2026, 1, 15), date(2026, 1, 15)),    # Thursday, not a holiday
    (date(2025, 6, 15), date(2025, 6, 16)),    # Sunday -> Monday
    (date(2025, 9, 15), date(2025, 9, 15)),    # Monday, not a holiday
    (date(2028, 6, 17), date(2028, 6, 20)),    # Sat -> Mon Jun 19 (Juneteenth) -> Tue
    (date(2027, 12, 31), date(2028, 1, 3)),    # Fri: New Year's 2028 observed -> Mon Jan 3
    (date(2026, 11, 26), date(2026, 11, 27)),  # Thanksgiving -> Friday
    (date(2026, 7, 3), date(2026, 7, 6)),      # Fri: July 4 (Sat) observed -> Mon
])
def test_shift_weekend_skips_holidays(d, expected):
    assert _shift_weekend(d) == expected


def test_existing_deadlines_unchanged():
    q = [d["deadline"] for d in get_estimated_tax_deadlines(2024)]
    assert q == ["2024-04-15", "2024-06-17", "2024-09-16", "2025-01-15"]


# ── SEP-IRA text is year-driven ──────────────────────────────────────────────

def _sep_detail(year):
    ctx = {"employment": {"type": "self_employed", "annual_gross": 90_000}, "tax_profile": {}}
    return next(c["detail"] for c in generate_us_claims(ctx, year) if c["id"] == "sep_ira")


def test_sep_ira_text_follows_year():
    assert "$75,000 for 2027" in _sep_detail(2027)
    assert "$69,000 for 2024" in _sep_detail(2024)
    assert "$72,000 for 2026" in _sep_detail(2026)
