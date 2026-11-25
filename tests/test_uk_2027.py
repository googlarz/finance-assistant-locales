"""
Tests for the UK 2027/28 entry and the 2025-2027 corrections
(employer NI 15% above £5,000, SSP, LEL, data-driven confidence).

Only legislated values drive the 2027 entry; announced-only values are carried
forward from 2026/27 and the result is flagged "Likely" with a note.
"""

import json
from pathlib import Path

import pytest
from context import LocaleContext
from uk import SUPPORTED_YEARS, calculate_tax
from uk.insurance_rules import (
    NI_LOWER_EARNINGS_LIMIT_WEEKLY,
    SSP_WEEKLY,
    get_income_protection_guidance,
)
from uk.pension import calculate_salary_sacrifice
from uk.social_contributions import NI_THRESHOLDS, get_social_contributions
from uk.tax_rules import TAX_YEAR_RULES, get_tax_year_rules, resolve_supported_year

PROVENANCE = Path(__file__).resolve().parent.parent / "uk" / "provenance.json"


def _employed(year, gross=50_000.0, **kw):
    return calculate_tax(
        LocaleContext(tax_year=year, employment_type="employed", annual_gross=gross, **kw)
    )


# ── Year registered ───────────────────────────────────────────────────────────

def test_2027_supported_and_resolves_exactly():
    assert 2027 in SUPPORTED_YEARS
    assert resolve_supported_year(2027) == (2027, None)


# ── Enacted 2027/28 values ────────────────────────────────────────────────────

def test_2027_enacted_values():
    r = TAX_YEAR_RULES[2027]
    assert r["personal_allowance"] == 12_570
    assert r["basic_rate_limit"] - r["personal_allowance"] == 37_700
    assert r["ni_employer_rate"] == 0.15
    assert r["dividend_allowance"] == 500
    assert r["dividend_ordinary_rate"] == 0.1075
    assert r["dividend_upper_rate"] == 0.3575
    assert r["cgt_rate_basic"] == 0.18
    assert r["cgt_rate_higher"] == 0.24
    assert r["capital_gains_allowance"] == 3_000
    assert r["isa_allowance"] == 20_000
    assert r["pension_annual_allowance"] == 60_000
    assert r["savings_starting_rate_limit"] == 5_000


def test_2027_savings_property_rates_use_enacted_not_announced():
    r = TAX_YEAR_RULES[2027]
    for kind in ("savings", "property"):
        assert (r[f"{kind}_basic_rate"], r[f"{kind}_higher_rate"], r[f"{kind}_additional_rate"]) == (
            0.22, 0.42, 0.47,
        )


def test_2027_announced_only_values_not_adopted():
    """SSP 127.55 and LEL 133 are announced only; 2026/27 values are carried forward."""
    assert SSP_WEEKLY[2027] == SSP_WEEKLY[2026] == 123.25
    assert NI_LOWER_EARNINGS_LIMIT_WEEKLY[2027] == NI_LOWER_EARNINGS_LIMIT_WEEKLY[2026] == 129
    assert NI_THRESHOLDS[2027]["employee_lower_threshold"] == NI_THRESHOLDS[2026]["employee_lower_threshold"]


# ── Employer NI correction ────────────────────────────────────────────────────

@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_employer_ni_15_percent_above_5000(year):
    assert NI_THRESHOLDS[year]["employer_rate"] == 0.15
    assert NI_THRESHOLDS[year]["employer_secondary_threshold"] == 5_000
    assert TAX_YEAR_RULES[year]["ni_employer_rate"] == 0.15
    assert TAX_YEAR_RULES[year]["ni_employer_secondary_threshold"] == 5_000
    ni = get_social_contributions(55_000, year)
    assert ni["ni_employer"] == pytest.approx(7_500.0)
    assert "15%" in ni["note"] and "£5,000" in ni["note"]


def test_employer_ni_2024_unchanged():
    assert NI_THRESHOLDS[2024]["employer_rate"] == 0.138
    assert NI_THRESHOLDS[2024]["employer_secondary_threshold"] == 9_100
    assert "13.8%" in get_social_contributions(50_000, 2024)["note"]


def test_tax_rules_and_ni_tables_agree_on_employer_ni():
    for year in (2024, 2025, 2026, 2027):
        assert TAX_YEAR_RULES[year]["ni_employer_rate"] == NI_THRESHOLDS[year]["employer_rate"]
        assert (
            TAX_YEAR_RULES[year]["ni_employer_secondary_threshold"]
            == NI_THRESHOLDS[year]["employer_secondary_threshold"]
        )


def test_salary_sacrifice_uses_15_percent_employer_ni():
    res = calculate_salary_sacrifice(60_000, 10_000, tax_year=2026)
    assert res["employer_ni_saving"] == pytest.approx(1_500.0)


# ── SSP / LEL corrections ─────────────────────────────────────────────────────

def test_ssp_and_lel_current_values():
    assert SSP_WEEKLY[2024] == 116.75
    assert SSP_WEEKLY[2025] == 118.75
    assert SSP_WEEKLY[2026] == 123.25
    assert NI_LOWER_EARNINGS_LIMIT_WEEKLY[2026] == 129


def test_income_protection_guidance_confidence_and_warning():
    g26 = get_income_protection_guidance(40_000, 2026)
    assert g26["ssp_context"]["ssp_weekly_gbp"] == 123.25
    assert g26["confidence"] == "Definitive" and g26["warning"] is None
    g27 = get_income_protection_guidance(40_000, 2027)
    assert g27["ssp_context"]["ssp_weekly_gbp"] == 123.25
    assert g27["confidence"] == "Likely"
    assert "127.55" in g27["warning"]


# ── Data-driven confidence in calculate_tax ──────────────────────────────────

def test_2027_result_is_low_confidence_with_warning():
    res = _employed(2027)
    assert res["tax_year"] == 2027
    assert res["confidence"] == "Likely"
    assert "2027/28" in res["year_note"] and "not yet legislated" in res["year_note"]
    assert res["tax"] == pytest.approx(7_486.0)  # (50,000 - 12,570) * 20%
    assert res["ni_detail"]["ni_employer"] == pytest.approx(6_750.0)


def test_confidence_follows_rules_data_not_hardcoded_year(monkeypatch):
    import uk.tax_rules as tr

    patched = dict(TAX_YEAR_RULES[2025], confidence="Likely", note="test caveat")
    monkeypatch.setitem(tr.TAX_YEAR_RULES, 2025, patched)
    res = _employed(2025)
    assert res["confidence"] == "Likely"
    assert res["year_note"] == "test caveat"


def test_definitive_years_unchanged():
    for year in (2024, 2025):
        res = _employed(year)
        assert res["confidence"] == "Definitive"
        assert res["year_note"] is None


def test_year_beyond_bundled_rules_falls_back_to_2027_with_both_notes():
    res = _employed(2029)
    assert res["tax_year"] == 2027
    assert res["confidence"] == "Likely"
    assert "newer than bundled rules" in res["year_note"]
    assert "not yet legislated" in res["year_note"]


def test_scottish_taxpayer_2027_uses_scottish_bands():
    res = _employed(2027, 50_000.0, region="Scotland")
    assert res["tax_system"] == "Scottish"
    assert res["confidence"] == "Likely"


# ── Docstring claim / provenance ──────────────────────────────────────────────

def test_no_frozen_until_april_2028_claim():
    import uk.tax_rules as tr

    assert "until April 2028" not in (tr.__doc__ or "")
    assert "2030-31" in tr.__doc__
    assert "until April 2028" not in PROVENANCE.read_text()


def test_provenance_records_2027_and_discrepancies():
    prov = json.loads(PROVENANCE.read_text())
    assert prov["last_reviewed"] == "2026-11-24"
    rules = prov["rules"]
    for rule in rules.values():
        assert {"source_url", "verified_date", "confidence", "notes"} <= set(rule)
    assert "22%/42%/47%" in rules["savings_property_rates_2027_28"]["notes"]
    assert "24%/44%/49%" in rules["savings_property_rates_2027_28"]["notes"]
    assert rules["scottish_bands_2026_27"]["confidence"] == "Unconfirmed"
    assert "proposed" in rules["scottish_bands_2026_27"]["notes"]
    assert rules["announced_not_legislated_2027_28"]["confidence"] == "Announced, not legislated"
    assert "127.55" in rules["ssp_weekly_rate_2027_28"]["notes"]
    assert "£500,000" in rules["announced_not_legislated_2027_28"]["notes"]
    # repo Scottish 2026 bands deliberately unchanged
    assert get_tax_year_rules(2026)["scottish_bands"][0] == (0.19, 0, 2_827)
