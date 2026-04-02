"""Tests for German social contribution calculations."""
from de.social_contributions import (
    estimate_employee_social_contributions,
    get_full_contribution_picture,
    SOCIAL_CAPS,
)
from de.insurance_rules import get_pkv_eligible


def test_employee_contributions_sum_correctly():
    result = estimate_employee_social_contributions(65000, 2025)
    total_from_parts = round(
        result["pension"] + result["unemployment"] + result["health"] + result["care"], 2
    )
    assert result["total"] == total_from_parts


def test_contributions_cap_at_bbg():
    caps = SOCIAL_CAPS[2025]
    high_gross = caps["rv_alv"] * 2  # well above both caps

    result_high = estimate_employee_social_contributions(high_gross, 2025)
    result_at_cap = estimate_employee_social_contributions(caps["rv_alv"], 2025)

    # Pension and unemployment should be identical (both capped at rv_alv)
    assert result_high["pension"] == result_at_cap["pension"]
    assert result_high["unemployment"] == result_at_cap["unemployment"]


def test_full_picture_has_employer_share():
    result = get_full_contribution_picture(65000, 2025, has_children=True)
    assert result["totals"]["employer_annual"] > 0
    assert result["totals"]["employee_annual"] > 0
    assert result["totals"]["combined_annual"] > result["totals"]["employee_annual"]


def test_childless_pv_higher():
    result_parent = get_full_contribution_picture(65000, 2025, has_children=True)
    result_childless = get_full_contribution_picture(65000, 2025, has_children=False)
    parent_pv = result_parent["branches"]["care_pv"]["employee"]
    childless_pv = result_childless["branches"]["care_pv"]["employee"]
    assert childless_pv > parent_pv


def test_pkv_eligible():
    # Gross above JAEG 2025 (73_800) → eligible
    assert get_pkv_eligible(80000, 2025) is True
    # Gross below JAEG 2025 → not eligible
    assert get_pkv_eligible(60000, 2025) is False
