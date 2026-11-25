"""
US federal income tax rules — brackets, standard deductions, contribution limits.

Sources: IRS Rev. Proc. 2023-34 (2024), IRS Rev. Proc. 2024-40 (2025), IRS Rev. Proc. 2025-32 (2026),
IRS Rev. Proc. 2026-35 (2027)
All dollar amounts are for the federal return only; state taxes are handled separately.
"""

from __future__ import annotations

# ── 2024 ─────────────────────────────────────────────────────────────────────

_2024 = {
    "year": 2024,
    "standard_deduction": {
        "single": 14_600,
        "married_filing_jointly": 29_200,
        "married_filing_separately": 14_600,
        "head_of_household": 21_900,
    },
    # (rate, min_income, max_income) — max_income=None means no ceiling
    "brackets": {
        "single": [
            (0.10,  0,       11_600),
            (0.12,  11_600,  47_150),
            (0.22,  47_150,  100_525),
            (0.24,  100_525, 191_950),
            (0.32,  191_950, 243_725),
            (0.35,  243_725, 609_350),
            (0.37,  609_350, None),
        ],
        "married_filing_jointly": [
            (0.10,  0,       23_200),
            (0.12,  23_200,  94_300),
            (0.22,  94_300,  201_050),
            (0.24,  201_050, 383_900),
            (0.32,  383_900, 487_450),
            (0.35,  487_450, 731_200),
            (0.37,  731_200, None),
        ],
    },
    "long_term_capital_gains": {
        "single": [(0.0, 0, 47_025), (0.15, 47_025, 518_900), (0.20, 518_900, None)],
        "married_filing_jointly": [(0.0, 0, 94_050), (0.15, 94_050, 583_750), (0.20, 583_750, None)],
    },
    "contribution_limits": {
        "401k_employee": 23_000,
        "401k_catchup_50plus": 7_500,
        "ira": 7_000,
        "ira_catchup_50plus": 1_000,
        "hsa_individual": 4_150,
        "hsa_family": 8_300,
        "sep_ira_max": 69_000,   # IRC §415(c)(1)(A)
    },
    "fica": {
        "social_security_rate": 0.062,
        "social_security_wage_base": 168_600,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,   # on wages > $200k single / $250k MFJ
        "additional_medicare_threshold_single": 200_000,
        "additional_medicare_threshold_mfj": 250_000,
        "additional_medicare_threshold_mfs": 125_000,
    },
    "amt": {
        "exemption_single": 85_700,
        "exemption_mfj": 133_300,
        "phase_out_single": 609_350,
        "phase_out_mfj": 1_218_700,
    },
    # §199A QBI deduction — source: IRS Rev. Proc. 2023-34
    "qbi": {
        "rate": 0.20,
        "threshold_single": 182_050,
        "threshold_mfj": 364_100,
        "phase_out_range_single": 50_000,   # phase-out completes at threshold + range
        "phase_out_range_mfj": 100_000,
    },
    # Estimated tax quarterly deadlines — source: IRS Publication 505
    "quarterly_deadlines": [
        {"quarter": 1, "period": "Jan 1 – Mar 31", "due": "2024-04-15"},
        {"quarter": 2, "period": "Apr 1 – May 31", "due": "2024-06-17"},
        {"quarter": 3, "period": "Jun 1 – Aug 31", "due": "2024-09-16"},
        {"quarter": 4, "period": "Sep 1 – Dec 31", "due": "2025-01-15"},
    ],
}

# ── 2025 ─────────────────────────────────────────────────────────────────────

_2025 = {
    "year": 2025,
    "standard_deduction": {
        # Raised by the OBBBA after Rev. Proc. 2024-40 (15,000 / 30,000 / 22,500);
        # amounts per IRS IR-2025-103.
        "single": 15_750,
        "married_filing_jointly": 31_500,
        "married_filing_separately": 15_750,
        "head_of_household": 23_625,
    },
    "brackets": {
        "single": [
            (0.10,  0,       11_925),
            (0.12,  11_925,  48_475),
            (0.22,  48_475,  103_350),
            (0.24,  103_350, 197_300),
            (0.32,  197_300, 250_525),
            (0.35,  250_525, 626_350),
            (0.37,  626_350, None),
        ],
        "married_filing_jointly": [
            (0.10,  0,       23_850),
            (0.12,  23_850,  96_950),
            (0.22,  96_950,  206_700),
            (0.24,  206_700, 394_600),
            (0.32,  394_600, 501_050),
            (0.35,  501_050, 751_600),
            (0.37,  751_600, None),
        ],
    },
    "long_term_capital_gains": {
        "single": [(0.0, 0, 48_350), (0.15, 48_350, 533_400), (0.20, 533_400, None)],
        "married_filing_jointly": [(0.0, 0, 96_700), (0.15, 96_700, 600_050), (0.20, 600_050, None)],
    },
    "contribution_limits": {
        "401k_employee": 23_500,
        "401k_catchup_50plus": 7_500,
        "ira": 7_000,
        "ira_catchup_50plus": 1_000,
        "hsa_individual": 4_300,
        "hsa_family": 8_550,
        "sep_ira_max": 70_000,
    },
    "fica": {
        "social_security_rate": 0.062,
        "social_security_wage_base": 176_100,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,
        "additional_medicare_threshold_single": 200_000,
        "additional_medicare_threshold_mfj": 250_000,
        "additional_medicare_threshold_mfs": 125_000,
    },
    "amt": {
        "exemption_single": 88_100,
        "exemption_mfj": 137_000,
        "phase_out_single": 626_350,
        "phase_out_mfj": 1_252_700,
    },
    # §199A QBI deduction — source: IRS Rev. Proc. 2024-40
    "qbi": {
        "rate": 0.20,
        "threshold_single": 197_300,
        "threshold_mfj": 394_600,
        "phase_out_range_single": 50_000,
        "phase_out_range_mfj": 100_000,
    },
    # Estimated tax quarterly deadlines — source: IRS Publication 505
    "quarterly_deadlines": [
        {"quarter": 1, "period": "Jan 1 – Mar 31", "due": "2025-04-15"},
        {"quarter": 2, "period": "Apr 1 – May 31", "due": "2025-06-16"},
        {"quarter": 3, "period": "Jun 1 – Aug 31", "due": "2025-09-15"},
        {"quarter": 4, "period": "Sep 1 – Dec 31", "due": "2026-01-15"},
    ],
}

# ── 2026 ─────────────────────────────────────────────────────────────────────

_2026 = {
    "year": 2026,
    # Source: IRS Rev. Proc. 2025-32 (2026 inflation adjustments, as amended by the OBBBA)
    "standard_deduction": {
        "single": 16_100,
        "married_filing_jointly": 32_200,
        "married_filing_separately": 16_100,
        "head_of_household": 24_150,
    },
    "brackets": {
        "single": [
            (0.10,  0,       12_400),
            (0.12,  12_400,  50_400),
            (0.22,  50_400,  105_700),
            (0.24,  105_700, 201_775),
            (0.32,  201_775, 256_225),
            (0.35,  256_225, 640_600),
            (0.37,  640_600, None),
        ],
        "married_filing_jointly": [
            (0.10,  0,       24_800),
            (0.12,  24_800,  100_800),
            (0.22,  100_800, 211_400),
            (0.24,  211_400, 403_550),
            (0.32,  403_550, 512_450),
            (0.35,  512_450, 768_700),
            (0.37,  768_700, None),
        ],
    },
    "long_term_capital_gains": {
        "single": [(0.0, 0, 49_450), (0.15, 49_450, 545_500), (0.20, 545_500, None)],
        "married_filing_jointly": [(0.0, 0, 98_900), (0.15, 98_900, 613_700), (0.20, 613_700, None)],
    },
    # Retirement limits: IRS Notice 2025-67; HSA limits: IRS Rev. Proc. 2025-19
    "contribution_limits": {
        "401k_employee": 24_500,
        "401k_catchup_50plus": 8_000,
        "ira": 7_500,
        "ira_catchup_50plus": 1_100,
        "hsa_individual": 4_400,
        "hsa_family": 8_750,
        "sep_ira_max": 72_000,
    },
    # Wage base: SSA 2026 COLA fact sheet
    "fica": {
        "social_security_rate": 0.062,
        "social_security_wage_base": 184_500,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,
        "additional_medicare_threshold_single": 200_000,
        "additional_medicare_threshold_mfj": 250_000,
        "additional_medicare_threshold_mfs": 125_000,
    },
    "amt": {
        "exemption_single": 90_100,
        "exemption_mfj": 140_200,
        "phase_out_single": 500_000,
        "phase_out_mfj": 1_000_000,
    },
    # §199A QBI deduction — source: IRS Rev. Proc. 2025-32 (OBBBA widened the phase-in range)
    "qbi": {
        "rate": 0.20,
        "threshold_single": 201_750,
        "threshold_mfj": 403_500,
        "phase_out_range_single": 75_000,
        "phase_out_range_mfj": 150_000,
    },
    # Estimated tax quarterly deadlines for tax year 2026 (Form 1040-ES).
    # Source: IRS Publication 505 calendar rules; no weekend adjustments needed.
    "quarterly_deadlines": [
        {"quarter": 1, "period": "Jan 1 – Mar 31", "due": "2026-04-15"},
        {"quarter": 2, "period": "Apr 1 – May 31", "due": "2026-06-15"},
        {"quarter": 3, "period": "Jun 1 – Aug 31", "due": "2026-09-15"},
        {"quarter": 4, "period": "Sep 1 – Dec 31", "due": "2027-01-15"},
    ],
}

# ── 2027 ─────────────────────────────────────────────────────────────────────

_2027 = {
    "year": 2027,
    # Source: IRS Rev. Proc. 2026-35 (2027 inflation adjustments); the PDF still
    # carries a "[Release Date, 2026]" placeholder, see also IR-2026-133.
    "standard_deduction": {
        "single": 16_600,
        "married_filing_jointly": 33_200,
        "married_filing_separately": 16_600,
        "head_of_household": 24_925,
    },
    "brackets": {
        "single": [
            (0.10,  0,       12_800),
            (0.12,  12_800,  52_025),
            (0.22,  52_025,  109_125),
            (0.24,  109_125, 208_325),
            (0.32,  208_325, 264_550),
            (0.35,  264_550, 661_375),
            (0.37,  661_375, None),
        ],
        "married_filing_jointly": [
            (0.10,  0,       25_600),
            (0.12,  25_600,  104_050),
            (0.22,  104_050, 218_250),
            (0.24,  218_250, 416_650),
            (0.32,  416_650, 529_100),
            (0.35,  529_100, 793_650),
            (0.37,  793_650, None),
        ],
        "head_of_household": [
            (0.10,  0,       18_250),
            (0.12,  18_250,  69_650),
            (0.22,  69_650,  109_100),
            (0.24,  109_100, 208_300),
            (0.32,  208_300, 264_550),
            (0.35,  264_550, 661_350),
            (0.37,  661_350, None),
        ],
        "married_filing_separately": [
            (0.10,  0,       12_800),
            (0.12,  12_800,  52_025),
            (0.22,  52_025,  109_125),
            (0.24,  109_125, 208_325),
            (0.32,  208_325, 264_550),
            (0.35,  264_550, 396_825),
            (0.37,  396_825, None),
        ],
    },
    "long_term_capital_gains": {
        "single": [(0.0, 0, 51_050), (0.15, 51_050, 563_200), (0.20, 563_200, None)],
        "married_filing_jointly": [(0.0, 0, 102_100), (0.15, 102_100, 633_600), (0.20, 633_600, None)],
        "head_of_household": [(0.0, 0, 68_350), (0.15, 68_350, 598_400), (0.20, 598_400, None)],
        "married_filing_separately": [(0.0, 0, 51_050), (0.15, 51_050, 316_800), (0.20, 316_800, None)],
    },
    # Retirement limits: IRS Notice 2026-66; HSA limits: IRS Rev. Proc. 2026-24
    "contribution_limits": {
        "401k_employee": 25_500,
        "401k_catchup_50plus": 8_500,
        "401k_catchup_60_63": 11_750,
        "ira": 7_500,
        "ira_catchup_50plus": 1_100,
        "hsa_individual": 4_500,
        "hsa_family": 9_000,
        "sep_ira_max": 75_000,   # §415(c)(1)(A), Notice 2026-66
    },
    # Wage base: SSA OACT contribution and benefit base; rates/thresholds per statute
    "fica": {
        "social_security_rate": 0.062,
        "social_security_wage_base": 192_300,
        "medicare_rate": 0.0145,
        "additional_medicare_rate": 0.009,
        "additional_medicare_threshold_single": 200_000,
        "additional_medicare_threshold_mfj": 250_000,
        "additional_medicare_threshold_mfs": 125_000,
    },
    "amt": {
        "exemption_single": 93_000,
        "exemption_mfj": 144_700,
        "phase_out_single": 515_950,
        "phase_out_mfj": 1_031_900,
    },
    # §199A QBI deduction — source: IRS Rev. Proc. 2026-35; phase-in ranges per P.L. 119-21
    "qbi": {
        "rate": 0.20,
        "threshold_single": 208_300,
        "threshold_mfj": 416_600,
        "phase_out_range_single": 75_000,
        "phase_out_range_mfj": 150_000,
    },
    # Not used by the calculator yet (credits/estate/gift are not modelled)
    "child_tax_credit": {
        "max_per_child": 2_300,
        "refundable_portion": 1_800,
    },
    "estate_gift": {
        "estate_basic_exclusion": 15_480_000,
        "gift_annual_exclusion": 20_000,
    },
    # Estimated tax quarterly deadlines for tax year 2027 (Form 1040-ES).
    # Q4: Jan 15 2028 is a Saturday and Jan 17 2028 is Martin Luther King Jr. Day.
    "quarterly_deadlines": [
        {"quarter": 1, "period": "Jan 1 – Mar 31", "due": "2027-04-15"},
        {"quarter": 2, "period": "Apr 1 – May 31", "due": "2027-06-15"},
        {"quarter": 3, "period": "Jun 1 – Aug 31", "due": "2027-09-15"},
        {"quarter": 4, "period": "Sep 1 – Dec 31", "due": "2028-01-18"},
    ],
}

TAX_YEAR_RULES: dict[int, dict] = {
    2024: _2024,
    2025: _2025,
    2026: _2026,
    2027: _2027,
}


def get_tax_year_rules(year: int) -> dict:
    if year in TAX_YEAR_RULES:
        return TAX_YEAR_RULES[year]
    # No table for this year: fall back to the most recent known year, but say so
    # loudly — the figures are NOT the rules for `year`.
    latest = max(TAX_YEAR_RULES)
    return {
        **TAX_YEAR_RULES[latest],
        "confidence": "low",
        "fallback_for_year": year,
        "warnings": [
            f"No US tax table for {year}; using {latest} figures as a low-confidence estimate."
        ],
    }
