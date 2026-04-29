"""
US federal income tax rules — brackets, standard deductions, contribution limits.

Sources: IRS Rev. Proc. 2023-34 (2024), IRS Rev. Proc. 2024-40 (2025)
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
}

# ── 2025 ─────────────────────────────────────────────────────────────────────

_2025 = {
    "year": 2025,
    "standard_deduction": {
        "single": 15_000,
        "married_filing_jointly": 30_000,
        "married_filing_separately": 15_000,
        "head_of_household": 22_500,
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
}

TAX_YEAR_RULES: dict[int, dict] = {
    2024: _2024,
    2025: _2025,
}


def get_tax_year_rules(year: int) -> dict:
    if year in TAX_YEAR_RULES:
        return TAX_YEAR_RULES[year]
    # Fall back to most recent known year
    latest = max(TAX_YEAR_RULES)
    return TAX_YEAR_RULES[latest]
