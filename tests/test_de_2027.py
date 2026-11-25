"""Tests for the 2026 corrections and 2027 (enacted-only) German parameters.

2027 income-tax parameters (Grundfreibetrag 12,564, tariff, Kinderfreibetrag,
Kindergeld 267, Arbeitnehmer-Pauschbetrag 1,430) are only a draft
(BT-Drs. 21/8235) and must NOT be applied.
"""
import json
import os

import pytest

from context import LocaleContext
from de import calculate_tax
from de.insurance_rules import (
    GKV_BBG,
    GKV_ZUSATZBEITRAG,
    JAEG,
    get_gkv_contribution_estimate,
    get_insurance_thresholds,
)
from de.social_contributions import (
    BEZUGSGROESSE,
    GKV_ZUSATZBEITRAG_AVG,
    PV_RATES,
    SOCIAL_CAPS,
    estimate_employee_social_contributions,
    get_full_contribution_picture,
)
from de.tax_rules import TAX_YEAR_RULES, calculate_income_tax

WARNING = "2027 income tax reform not yet enacted; using 2026 tariff"
PROVENANCE = os.path.join(os.path.dirname(__file__), "..", "de", "provenance.json")


# ── 2026 corrections ──────────────────────────────────────────────────────

def test_2026_pendlerpauschale_038_from_first_km():
    rules = TAX_YEAR_RULES[2026]
    assert rules["pendlerpauschale_short"] == 0.38
    assert rules["pendlerpauschale_long"] == 0.38


def test_2026_pendlerpauschale_applied_in_calculator():
    ctx = LocaleContext(tax_year=2026, employment_type="employed", annual_gross=60000.0,
                        tax_class="I", commute_km=10, commute_days_per_year=200)
    result = calculate_tax(ctx)
    # 10 km x 200 days x 0.38 (old split rate would give 600)
    assert result["breakdown"]["werbungskosten_detail"]["pendlerpauschale"] == 760.0


def test_2025_pendlerpauschale_unchanged():
    assert TAX_YEAR_RULES[2025]["pendlerpauschale_short"] == 0.30


def test_2026_zusatzbeitrag_avg_29():
    assert GKV_ZUSATZBEITRAG_AVG[2026] == 0.029
    assert GKV_ZUSATZBEITRAG[2026] == 0.029


def test_2026_jaeg_77400():
    assert JAEG[2026] == 77_400


def test_2026_ruerup_30826():
    assert TAX_YEAR_RULES[2026]["ruerup_max_single"] == 30_826


@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_pv_childless_surcharge_06(year):
    rates = PV_RATES[year]
    assert rates["childless_total"] == 0.042
    assert rates["childless_employee"] == 0.024
    assert rates["childless_employer"] == 0.018
    assert rates["with_children_total"] == 0.036


def test_pv_childless_picture_uses_24_percent_employee():
    result = get_full_contribution_picture(50_000, 2026, has_children=False)
    pv = result["branches"]["care_pv"]
    assert pv["rate_employee"] == 0.024
    assert pv["employee"] == round(50_000 * 0.024, 2)


def test_2026_bav_tax_free_limit_is_8_percent_of_bbg():
    rules = TAX_YEAR_RULES[2026]
    assert rules["bav_tax_free_limit"] == 8_112  # 8% x 101,400
    ctx = LocaleContext(tax_year=2026, employment_type="employed", annual_gross=90000.0,
                        tax_class="I", bav=True, bav_contribution=20_000.0)
    result = calculate_tax(ctx)
    assert result["breakdown"]["bav_deductible"] == 8_112.0


# ── 2027 social / insurance values (enacted) ──────────────────────────────

def test_2027_caps_split_kv_and_pv():
    caps = SOCIAL_CAPS[2027]
    assert caps["rv_alv"] == 106_200
    assert caps["gkv"] == 76_500
    assert caps["pv"] == 72_900
    assert "gkv_pv" not in caps


@pytest.mark.parametrize("year", [2024, 2025, 2026])
def test_earlier_years_kv_and_pv_caps_equal(year):
    assert SOCIAL_CAPS[year]["gkv"] == SOCIAL_CAPS[year]["pv"]


def test_2027_kv_and_pv_use_separate_caps():
    gross = 200_000  # above every cap
    result = get_full_contribution_picture(gross, 2027, has_children=True)
    zb = 0.029
    assert result["branches"]["health_gkv"]["employee"] == round(76_500 * (0.073 + zb / 2), 2)
    assert result["branches"]["care_pv"]["employee"] == round(72_900 * 0.018, 2)
    assert result["branches"]["pension_rv"]["employee"] == round(106_200 * 0.093, 2)
    assert result["caps"] == {"rv_alv": 106_200, "gkv": 76_500, "pv": 72_900}


def test_2027_legacy_estimate_uses_separate_caps():
    result = estimate_employee_social_contributions(200_000, 2027)
    assert result["care"] == round(72_900 * 0.018, 2)
    assert result["health"] == round(76_500 * 0.0815, 2)


def test_2027_jaeg_and_gkv_bbg():
    assert JAEG[2027] == 84_150
    assert GKV_BBG[2027] == 76_500


def test_2027_zusatzbeitrag_avg_29():
    assert GKV_ZUSATZBEITRAG_AVG[2027] == 0.029
    assert GKV_ZUSATZBEITRAG[2027] == 0.029
    assert get_gkv_contribution_estimate(100_000, 2027)["bbg"] == 76_500


def test_2027_bezugsgroesse():
    assert BEZUGSGROESSE[2027] == 49_560


def test_2027_insurance_thresholds_no_unpublished_pkv_value():
    t = get_insurance_thresholds(2027)
    assert t["year"] == 2027
    assert t["jaeg"] == 84_150
    assert t["pkv_mindestbeitrag_monthly"] is None


# ── 2027 tax rules: enacted changes applied, draft NOT applied ────────────

def test_2027_riester_new_cap_1800():
    assert TAX_YEAR_RULES[2027]["riester_max"] == 1_800
    assert TAX_YEAR_RULES[2026]["riester_max"] == 2_100


def test_2027_bav_limits():
    rules = TAX_YEAR_RULES[2027]
    assert rules["bav_tax_free_limit"] == 8_496  # 8% x 106,200
    assert rules["bav_4pct_bbg"] == 4_248


def test_2027_ruerup_not_published():
    assert TAX_YEAR_RULES[2027]["ruerup_max_single"] is None


def test_2027_unchanged_statutory_values_match_2026():
    r26, r27 = TAX_YEAR_RULES[2026], TAX_YEAR_RULES[2027]
    for key in ("soli_freigrenze_single", "sonderausgaben_pauschbetrag", "homeoffice_tagespauschale",
                "homeoffice_max_days", "homeoffice_max_annual", "pendlerpauschale_short",
                "pendlerpauschale_long", "sparer_pauschbetrag_single", "sparer_pauschbetrag_married",
                "kinderbetreuung_pct", "kinderbetreuung_max", "ausbildungsfreibetrag",
                "entlastungsbetrag_alleinerziehende", "pflegepauschbetrag_pf1",
                "pflegepauschbetrag_pf2", "pflegepauschbetrag_pf3", "gwg_threshold_net",
                "gwg_threshold_gross", "behindertenpauschbetrag"):
        assert r27[key] == r26[key], key


def test_2027_draft_income_tax_values_not_applied():
    r = TAX_YEAR_RULES[2027]
    assert r["grundfreibetrag"] == 12_348 != 12_564
    assert r["zone1_coeff"] == 914.51
    assert r["zone2_upper"] == 69_878
    assert r["reichensteuersatz_threshold"] == 277_826
    assert r["kinderfreibetrag_child"] == 3_414 != 3_564
    assert r["kindergeld_per_child"] == 259 != 267
    assert r["arbeitnehmer_pauschbetrag"] == 1_230 != 1_430


@pytest.mark.parametrize("zve", [10_000, 30_000, 60_000, 120_000, 300_000])
def test_2027_income_tax_equals_2026_tariff(zve):
    assert calculate_income_tax(zve, 2027) == calculate_income_tax(zve, 2026)


# ── 2027 low-confidence warning ───────────────────────────────────────────

def _ctx(year):
    return LocaleContext(tax_year=year, employment_type="employed", annual_gross=60000.0,
                         tax_class="I", homeoffice_days_per_week=2, commute_km=10,
                         commute_days_per_year=200)


def test_2027_result_has_warning_and_low_confidence():
    result = calculate_tax(_ctx(2027))
    assert WARNING in result["confidence_detractors"]
    assert result["confidence_label"] == "Low Confidence"
    assert result["confidence_pct"] < 50


def test_2026_result_has_no_2027_warning():
    result = calculate_tax(_ctx(2026))
    assert WARNING not in result["confidence_detractors"]
    assert result["confidence_label"] != "Low Confidence"


def test_2027_breakdown_uses_2026_tariff():
    r26 = calculate_tax(_ctx(2026))["breakdown"]
    r27 = calculate_tax(_ctx(2027))["breakdown"]
    assert r27["estimated_tax"] == r26["estimated_tax"]
    assert r27["zu_versteuerndes_einkommen"] == r26["zu_versteuerndes_einkommen"]


def test_2027_riester_cap_applied_in_calculator():
    ctx = LocaleContext(tax_year=2027, employment_type="employed", annual_gross=60000.0,
                        tax_class="I", riester=True, riester_contribution=2_100.0)
    base = LocaleContext(tax_year=2027, employment_type="employed", annual_gross=60000.0, tax_class="I")
    delta = (calculate_tax(ctx)["breakdown"]["total_sonderausgaben"]
             - calculate_tax(base)["breakdown"]["total_sonderausgaben"])
    assert delta == 1_800


# ── provenance.json ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def provenance():
    with open(PROVENANCE, encoding="utf-8") as fh:
        return json.load(fh)


def test_provenance_draft_values_recorded_not_applied(provenance):
    rules = provenance["rules"]
    expected = {
        "grundfreibetrag": ("value", 12564),
        "arbeitnehmer_pauschbetrag": ("value", 1430),
        "kindergeld": ("value_per_child_monthly", 267),
        "kinderfreibetrag": ("child_freibetrag", 3564),
    }
    for rule, (field, value) in expected.items():
        entry = rules[rule]["2027"]
        assert entry[field] == value
        assert entry["status"] == "draft, unconfirmed"
        assert entry["source_url"].startswith("https://")
        assert entry["verified_date"] == "2026-11-24"
        assert entry["applied_in_code"] is False
    assert rules["einkommensteuertarif"]["2027"]["status"] == "draft, unconfirmed"


def test_provenance_corrected_values(provenance):
    rules = provenance["rules"]
    assert rules["ruerup_max"]["2026"]["value_single"] == 30826
    assert rules["riester_max"]["2027"]["value"] == 1800
    assert rules["riester_max"]["2027"]["status"] == "enacted"
    caps = rules["social_contribution_caps"]["2027"]
    assert (caps["rv_alv_bbg"], caps["gkv_bbg"], caps["pv_bbg"]) == (106200, 76500, 72900)
    assert caps["jaeg"] == 84150 and caps["bezugsgroesse_annual"] == 49560
    assert rules["social_contribution_caps"]["2026"]["jaeg"] == 77400
    assert rules["gkv_zusatzbeitrag_avg"]["2026"]["value"] == 0.029
    assert rules["gkv_zusatzbeitrag_avg"]["2027"]["value"] == 0.029
    assert rules["pendlerpauschale"]["2026"]["value_short"] == 0.38
    assert rules["bav_limits"]["2027"]["value_tax_free_8pct_of_bbg"] == 8496
    assert rules["pv_childless_rates"]["2026"]["childless_total"] == 0.042
    assert rules["pv_childless_rates"]["2027_draft_pnog"]["status"] == "draft, unconfirmed"
    assert provenance["last_verified"] == "2026-11-24"
