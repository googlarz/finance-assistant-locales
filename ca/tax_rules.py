"""
Canadian tax rules and parameters for 2024, 2025, and 2026.

Federal and provincial/territorial income tax brackets, basic personal amounts,
non-refundable tax credit rates, surtaxes, and thresholds.

Sources:
  Canada Revenue Agency (CRA) - Canadian income tax rates for individuals:
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/canadian-income-tax-rates-individuals-current-previous-years.html
  https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/adjustment-personal-income-tax-benefit-amounts.html
  CRA Publication T4127 - Payroll Deductions Formulas (120th, 121st, 122nd, 123rd editions)
"""

from __future__ import annotations
from typing import Optional

SUPPORTED_YEARS = [2024, 2025, 2026]

# Standard province/territory codes and aliases
PROVINCE_CODES = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

PROVINCE_ALIASES = {
    "alberta": "AB",
    "ab": "AB",
    "british columbia": "BC",
    "bc": "BC",
    "manitoba": "MB",
    "mb": "MB",
    "new brunswick": "NB",
    "nb": "NB",
    "newfoundland": "NL",
    "newfoundland and labrador": "NL",
    "nl": "NL",
    "nova scotia": "NS",
    "ns": "NS",
    "northwest territories": "NT",
    "nt": "NT",
    "nwt": "NT",
    "nunavut": "NU",
    "nu": "NU",
    "ontario": "ON",
    "on": "ON",
    "prince edward island": "PE",
    "pei": "PE",
    "pe": "PE",
    "quebec": "QC",
    "québec": "QC",
    "qc": "QC",
    "saskatchewan": "SK",
    "sk": "SK",
    "yukon": "YT",
    "yt": "YT",
}


def normalize_province(region: Optional[str]) -> str:
    """Normalize a region / province string to a 2-letter uppercase postal code (default 'ON')."""
    if not region:
        return "ON"
    cleaned = region.strip().lower()
    return PROVINCE_ALIASES.get(cleaned, "ON")


TAX_YEAR_RULES = {
    2024: {
        "confidence": "Definitive",
        "indexation_factor": 0.047,
        # Federal Brackets: (from, to, rate)
        "federal_brackets": [
            {"from": 0.0, "to": 55867.0, "rate": 0.15},
            {"from": 55867.0, "to": 111733.0, "rate": 0.205},
            {"from": 111733.0, "to": 173205.0, "rate": 0.26},
            {"from": 173205.0, "to": 246752.0, "rate": 0.29},
            {"from": 246752.0, "to": None, "rate": 0.33},
        ],
        # Federal Basic Personal Amount: maximum $15,705, minimum $14,156
        "federal_bpa_max": 15705.0,
        "federal_bpa_min": 14156.0,
        "federal_bpa_taper_start": 173205.0,
        "federal_bpa_taper_end": 246752.0,
        "federal_nrtc_rate": 0.15,
        "canada_employment_amount_max": 1433.0,
        "tfsa_limit": 7000.0,
        "rrsp_dollar_limit": 31560.0,
        "rrsp_earned_income_rate": 0.18,
        # Provincial rules
        "provinces": {
            "AB": {
                "name": "Alberta",
                "brackets": [
                    {"from": 0.0, "to": 148269.0, "rate": 0.10},
                    {"from": 148269.0, "to": 177922.0, "rate": 0.12},
                    {"from": 177922.0, "to": 237230.0, "rate": 0.13},
                    {"from": 237230.0, "to": 355845.0, "rate": 0.14},
                    {"from": 355845.0, "to": None, "rate": 0.15},
                ],
                "bpa": 21885.0,
                "nrtc_rate": 0.10,
            },
            "BC": {
                "name": "British Columbia",
                "brackets": [
                    {"from": 0.0, "to": 47937.0, "rate": 0.0506},
                    {"from": 47937.0, "to": 95875.0, "rate": 0.077},
                    {"from": 95875.0, "to": 110076.0, "rate": 0.105},
                    {"from": 110076.0, "to": 133664.0, "rate": 0.1229},
                    {"from": 133664.0, "to": 181232.0, "rate": 0.147},
                    {"from": 181232.0, "to": 252752.0, "rate": 0.168},
                    {"from": 252752.0, "to": None, "rate": 0.205},
                ],
                "bpa": 12580.0,
                "nrtc_rate": 0.0506,
                "tax_reduction": {"max_reduction": 547.0, "phase_out_start": 24230.0, "phase_out_rate": 0.0356},
            },
            "MB": {
                "name": "Manitoba",
                "brackets": [
                    {"from": 0.0, "to": 47000.0, "rate": 0.108},
                    {"from": 47000.0, "to": 100000.0, "rate": 0.1275},
                    {"from": 100000.0, "to": None, "rate": 0.174},
                ],
                "bpa": 15780.0,
                "nrtc_rate": 0.108,
            },
            "NB": {
                "name": "New Brunswick",
                "brackets": [
                    {"from": 0.0, "to": 49958.0, "rate": 0.094},
                    {"from": 49958.0, "to": 99916.0, "rate": 0.14},
                    {"from": 99916.0, "to": 185064.0, "rate": 0.16},
                    {"from": 185064.0, "to": None, "rate": 0.195},
                ],
                "bpa": 13044.0,
                "nrtc_rate": 0.094,
            },
            "NL": {
                "name": "Newfoundland and Labrador",
                "brackets": [
                    {"from": 0.0, "to": 43198.0, "rate": 0.087},
                    {"from": 43198.0, "to": 86395.0, "rate": 0.145},
                    {"from": 86395.0, "to": 154244.0, "rate": 0.158},
                    {"from": 154244.0, "to": 215943.0, "rate": 0.178},
                    {"from": 215943.0, "to": 275870.0, "rate": 0.198},
                    {"from": 275870.0, "to": 551739.0, "rate": 0.208},
                    {"from": 551739.0, "to": 1103478.0, "rate": 0.213},
                    {"from": 1103478.0, "to": None, "rate": 0.218},
                ],
                "bpa": 10818.0,
                "nrtc_rate": 0.087,
            },
            "NS": {
                "name": "Nova Scotia",
                "brackets": [
                    {"from": 0.0, "to": 29590.0, "rate": 0.0879},
                    {"from": 29590.0, "to": 59180.0, "rate": 0.1495},
                    {"from": 59180.0, "to": 93000.0, "rate": 0.1667},
                    {"from": 93000.0, "to": 150000.0, "rate": 0.175},
                    {"from": 150000.0, "to": None, "rate": 0.21},
                ],
                "bpa": 11481.0,
                "nrtc_rate": 0.0879,
            },
            "NT": {
                "name": "Northwest Territories",
                "brackets": [
                    {"from": 0.0, "to": 50597.0, "rate": 0.059},
                    {"from": 50597.0, "to": 101198.0, "rate": 0.086},
                    {"from": 101198.0, "to": 164525.0, "rate": 0.122},
                    {"from": 164525.0, "to": None, "rate": 0.1405},
                ],
                "bpa": 17373.0,
                "nrtc_rate": 0.059,
            },
            "NU": {
                "name": "Nunavut",
                "brackets": [
                    {"from": 0.0, "to": 53268.0, "rate": 0.04},
                    {"from": 53268.0, "to": 106537.0, "rate": 0.07},
                    {"from": 106537.0, "to": 173205.0, "rate": 0.09},
                    {"from": 173205.0, "to": None, "rate": 0.115},
                ],
                "bpa": 18767.0,
                "nrtc_rate": 0.04,
            },
            "ON": {
                "name": "Ontario",
                "brackets": [
                    {"from": 0.0, "to": 51446.0, "rate": 0.0505},
                    {"from": 51446.0, "to": 102894.0, "rate": 0.0915},
                    {"from": 102894.0, "to": 150000.0, "rate": 0.1116},
                    {"from": 150000.0, "to": 220000.0, "rate": 0.1216},
                    {"from": 220000.0, "to": None, "rate": 0.1316},
                ],
                "bpa": 12399.0,
                "nrtc_rate": 0.0505,
                "surtax": {
                    "threshold_1": 5554.0,
                    "rate_1": 0.20,
                    "threshold_2": 7108.0,
                    "rate_2": 0.36,
                },
                "health_premium": True,
                "tax_reduction": {"basic": 286.0},
            },
            "PE": {
                "name": "Prince Edward Island",
                "brackets": [
                    {"from": 0.0, "to": 32656.0, "rate": 0.0965},
                    {"from": 32656.0, "to": 64313.0, "rate": 0.1363},
                    {"from": 64313.0, "to": 105000.0, "rate": 0.1665},
                    {"from": 105000.0, "to": 140000.0, "rate": 0.1800},
                    {"from": 140000.0, "to": None, "rate": 0.1875},
                ],
                "bpa": 13500.0,
                "nrtc_rate": 0.0965,
            },
            "QC": {
                "name": "Quebec",
                "brackets": [
                    {"from": 0.0, "to": 51780.0, "rate": 0.14},
                    {"from": 51780.0, "to": 103545.0, "rate": 0.19},
                    {"from": 103545.0, "to": 126000.0, "rate": 0.24},
                    {"from": 126000.0, "to": None, "rate": 0.2575},
                ],
                "bpa": 18056.0,
                "nrtc_rate": 0.14,
                "federal_abatement_rate": 0.165,
                "separate_filing": True,
            },
            "SK": {
                "name": "Saskatchewan",
                "brackets": [
                    {"from": 0.0, "to": 52057.0, "rate": 0.105},
                    {"from": 52057.0, "to": 148734.0, "rate": 0.125},
                    {"from": 148734.0, "to": None, "rate": 0.145},
                ],
                "bpa": 18491.0,
                "nrtc_rate": 0.105,
            },
            "YT": {
                "name": "Yukon",
                "brackets": [
                    {"from": 0.0, "to": 55867.0, "rate": 0.064},
                    {"from": 55867.0, "to": 111733.0, "rate": 0.09},
                    {"from": 111733.0, "to": 173205.0, "rate": 0.109},
                    {"from": 173205.0, "to": 500000.0, "rate": 0.128},
                    {"from": 500000.0, "to": None, "rate": 0.15},
                ],
                "bpa": 15705.0,
                "nrtc_rate": 0.064,
            },
        },
    },
    2025: {
        "confidence": "Definitive",
        "indexation_factor": 0.027,
        # Federal: Lowest rate dropped to 14.5% (effective July 2025 blended 14.5% annual)
        "federal_brackets": [
            {"from": 0.0, "to": 57375.0, "rate": 0.145},
            {"from": 57375.0, "to": 114750.0, "rate": 0.205},
            {"from": 114750.0, "to": 177882.0, "rate": 0.26},
            {"from": 177882.0, "to": 253414.0, "rate": 0.29},
            {"from": 253414.0, "to": None, "rate": 0.33},
        ],
        "federal_bpa_max": 16129.0,
        "federal_bpa_min": 14538.0,
        "federal_bpa_taper_start": 177882.0,
        "federal_bpa_taper_end": 253414.0,
        "federal_nrtc_rate": 0.145,
        "canada_employment_amount_max": 1471.0,
        "tfsa_limit": 7000.0,
        "rrsp_dollar_limit": 32490.0,
        "rrsp_earned_income_rate": 0.18,
        "provinces": {
            "AB": {
                "name": "Alberta",
                "brackets": [
                    {"from": 0.0, "to": 60000.0, "rate": 0.08},
                    {"from": 60000.0, "to": 151234.0, "rate": 0.10},
                    {"from": 151234.0, "to": 181481.0, "rate": 0.12},
                    {"from": 181481.0, "to": 241974.0, "rate": 0.13},
                    {"from": 241974.0, "to": 362961.0, "rate": 0.14},
                    {"from": 362961.0, "to": None, "rate": 0.15},
                ],
                "bpa": 22323.0,
                "nrtc_rate": 0.08,
            },
            "BC": {
                "name": "British Columbia",
                "brackets": [
                    {"from": 0.0, "to": 49279.0, "rate": 0.0506},
                    {"from": 49279.0, "to": 98560.0, "rate": 0.077},
                    {"from": 98560.0, "to": 113158.0, "rate": 0.105},
                    {"from": 113158.0, "to": 137407.0, "rate": 0.1229},
                    {"from": 137407.0, "to": 186306.0, "rate": 0.147},
                    {"from": 186306.0, "to": 259829.0, "rate": 0.168},
                    {"from": 259829.0, "to": None, "rate": 0.205},
                ],
                "bpa": 12932.0,
                "nrtc_rate": 0.0506,
                "tax_reduction": {"max_reduction": 562.0, "phase_out_start": 24900.0, "phase_out_rate": 0.0356},
            },
            "MB": {
                "name": "Manitoba",
                "brackets": [
                    {"from": 0.0, "to": 47000.0, "rate": 0.108},
                    {"from": 47000.0, "to": 100000.0, "rate": 0.1275},
                    {"from": 100000.0, "to": None, "rate": 0.174},
                ],
                "bpa": 15780.0,
                "nrtc_rate": 0.108,
            },
            "NB": {
                "name": "New Brunswick",
                "brackets": [
                    {"from": 0.0, "to": 51306.0, "rate": 0.094},
                    {"from": 51306.0, "to": 102614.0, "rate": 0.14},
                    {"from": 102614.0, "to": 190060.0, "rate": 0.16},
                    {"from": 190060.0, "to": None, "rate": 0.195},
                ],
                "bpa": 13396.0,
                "nrtc_rate": 0.094,
            },
            "NL": {
                "name": "Newfoundland and Labrador",
                "brackets": [
                    {"from": 0.0, "to": 44192.0, "rate": 0.087},
                    {"from": 44192.0, "to": 88382.0, "rate": 0.145},
                    {"from": 88382.0, "to": 157792.0, "rate": 0.158},
                    {"from": 157792.0, "to": 220910.0, "rate": 0.178},
                    {"from": 220910.0, "to": 282214.0, "rate": 0.198},
                    {"from": 282214.0, "to": 564429.0, "rate": 0.208},
                    {"from": 564429.0, "to": 1128858.0, "rate": 0.213},
                    {"from": 1128858.0, "to": None, "rate": 0.218},
                ],
                "bpa": 11067.0,
                "nrtc_rate": 0.087,
            },
            "NS": {
                "name": "Nova Scotia",
                "brackets": [
                    {"from": 0.0, "to": 30507.0, "rate": 0.0879},
                    {"from": 30507.0, "to": 61015.0, "rate": 0.1495},
                    {"from": 61015.0, "to": 95883.0, "rate": 0.1667},
                    {"from": 95883.0, "to": 154650.0, "rate": 0.175},
                    {"from": 154650.0, "to": None, "rate": 0.21},
                ],
                "bpa": 11744.0,
                "nrtc_rate": 0.0879,
            },
            "NT": {
                "name": "Northwest Territories",
                "brackets": [
                    {"from": 0.0, "to": 51964.0, "rate": 0.059},
                    {"from": 51964.0, "to": 103930.0, "rate": 0.086},
                    {"from": 103930.0, "to": 168967.0, "rate": 0.122},
                    {"from": 168967.0, "to": None, "rate": 0.1405},
                ],
                "bpa": 17842.0,
                "nrtc_rate": 0.059,
            },
            "NU": {
                "name": "Nunavut",
                "brackets": [
                    {"from": 0.0, "to": 54707.0, "rate": 0.04},
                    {"from": 54707.0, "to": 109413.0, "rate": 0.07},
                    {"from": 109413.0, "to": 177881.0, "rate": 0.09},
                    {"from": 177881.0, "to": None, "rate": 0.115},
                ],
                "bpa": 19274.0,
                "nrtc_rate": 0.04,
            },
            "ON": {
                "name": "Ontario",
                "brackets": [
                    {"from": 0.0, "to": 52886.0, "rate": 0.0505},
                    {"from": 52886.0, "to": 105775.0, "rate": 0.0915},
                    {"from": 105775.0, "to": 150000.0, "rate": 0.1116},
                    {"from": 150000.0, "to": 220000.0, "rate": 0.1216},
                    {"from": 220000.0, "to": None, "rate": 0.1316},
                ],
                "bpa": 12747.0,
                "nrtc_rate": 0.0505,
                "surtax": {
                    "threshold_1": 5710.0,
                    "rate_1": 0.20,
                    "threshold_2": 7307.0,
                    "rate_2": 0.36,
                },
                "health_premium": True,
                "tax_reduction": {"basic": 294.0},
            },
            "PE": {
                "name": "Prince Edward Island",
                "brackets": [
                    {"from": 0.0, "to": 33328.0, "rate": 0.095},
                    {"from": 33328.0, "to": 64656.0, "rate": 0.1347},
                    {"from": 64656.0, "to": 105000.0, "rate": 0.166},
                    {"from": 105000.0, "to": 140000.0, "rate": 0.1762},
                    {"from": 140000.0, "to": None, "rate": 0.190},
                ],
                "bpa": 14650.0,
                "nrtc_rate": 0.095,
            },
            "QC": {
                "name": "Quebec",
                "brackets": [
                    {"from": 0.0, "to": 53255.0, "rate": 0.14},
                    {"from": 53255.0, "to": 106495.0, "rate": 0.19},
                    {"from": 106495.0, "to": 129590.0, "rate": 0.24},
                    {"from": 129590.0, "to": None, "rate": 0.2575},
                ],
                "bpa": 18571.0,
                "nrtc_rate": 0.14,
                "federal_abatement_rate": 0.165,
                "separate_filing": True,
            },
            "SK": {
                "name": "Saskatchewan",
                "brackets": [
                    {"from": 0.0, "to": 53463.0, "rate": 0.105},
                    {"from": 53463.0, "to": 152750.0, "rate": 0.125},
                    {"from": 152750.0, "to": None, "rate": 0.145},
                ],
                "bpa": 19491.0,
                "nrtc_rate": 0.105,
            },
            "YT": {
                "name": "Yukon",
                "brackets": [
                    {"from": 0.0, "to": 57375.0, "rate": 0.064},
                    {"from": 57375.0, "to": 114750.0, "rate": 0.09},
                    {"from": 114750.0, "to": 177882.0, "rate": 0.109},
                    {"from": 177882.0, "to": 500000.0, "rate": 0.128},
                    {"from": 500000.0, "to": None, "rate": 0.15},
                ],
                "bpa": 16129.0,
                "nrtc_rate": 0.064,
            },
        },
    },
    2026: {
        "confidence": "Definitive",
        "indexation_factor": 0.02,
        # Federal: Lowest rate is 14.0%
        "federal_brackets": [
            {"from": 0.0, "to": 58523.0, "rate": 0.14},
            {"from": 58523.0, "to": 117045.0, "rate": 0.205},
            {"from": 117045.0, "to": 181440.0, "rate": 0.26},
            {"from": 181440.0, "to": 258482.0, "rate": 0.29},
            {"from": 258482.0, "to": None, "rate": 0.33},
        ],
        "federal_bpa_max": 16452.0,
        "federal_bpa_min": 14829.0,
        "federal_bpa_taper_start": 181440.0,
        "federal_bpa_taper_end": 258482.0,
        "federal_nrtc_rate": 0.14,
        "canada_employment_amount_max": 1501.0,
        "tfsa_limit": 7000.0,
        "rrsp_dollar_limit": 33140.0,
        "rrsp_earned_income_rate": 0.18,
        "provinces": {
            "AB": {
                "name": "Alberta",
                "brackets": [
                    {"from": 0.0, "to": 61200.0, "rate": 0.08},
                    {"from": 61200.0, "to": 154259.0, "rate": 0.10},
                    {"from": 154259.0, "to": 185111.0, "rate": 0.12},
                    {"from": 185111.0, "to": 246813.0, "rate": 0.13},
                    {"from": 246813.0, "to": 370220.0, "rate": 0.14},
                    {"from": 370220.0, "to": None, "rate": 0.15},
                ],
                "bpa": 22769.0,
                "nrtc_rate": 0.08,
            },
            "BC": {
                "name": "British Columbia",
                # Budget 2026: lowest rate 5.60%
                "brackets": [
                    {"from": 0.0, "to": 50363.0, "rate": 0.056},
                    {"from": 50363.0, "to": 100728.0, "rate": 0.077},
                    {"from": 100728.0, "to": 115648.0, "rate": 0.105},
                    {"from": 115648.0, "to": 140430.0, "rate": 0.1229},
                    {"from": 140430.0, "to": 190405.0, "rate": 0.147},
                    {"from": 190405.0, "to": 265545.0, "rate": 0.168},
                    {"from": 265545.0, "to": None, "rate": 0.205},
                ],
                "bpa": 13216.0,
                "nrtc_rate": 0.056,
                "tax_reduction": {"max_reduction": 690.0, "phase_out_start": 25570.0, "phase_out_rate": 0.0356},
            },
            "MB": {
                "name": "Manitoba",
                "brackets": [
                    {"from": 0.0, "to": 47000.0, "rate": 0.108},
                    {"from": 47000.0, "to": 100000.0, "rate": 0.1275},
                    {"from": 100000.0, "to": None, "rate": 0.174},
                ],
                "bpa": 15780.0,
                "nrtc_rate": 0.108,
            },
            "NB": {
                "name": "New Brunswick",
                "brackets": [
                    {"from": 0.0, "to": 52333.0, "rate": 0.094},
                    {"from": 52333.0, "to": 104666.0, "rate": 0.14},
                    {"from": 104666.0, "to": 193861.0, "rate": 0.16},
                    {"from": 193861.0, "to": None, "rate": 0.195},
                ],
                "bpa": 13664.0,
                "nrtc_rate": 0.094,
            },
            "NL": {
                "name": "Newfoundland and Labrador",
                "brackets": [
                    {"from": 0.0, "to": 44678.0, "rate": 0.087},
                    {"from": 44678.0, "to": 89354.0, "rate": 0.145},
                    {"from": 89354.0, "to": 159528.0, "rate": 0.158},
                    {"from": 159528.0, "to": 223340.0, "rate": 0.178},
                    {"from": 223340.0, "to": 285319.0, "rate": 0.198},
                    {"from": 285319.0, "to": 570638.0, "rate": 0.208},
                    {"from": 570638.0, "to": 1141275.0, "rate": 0.213},
                    {"from": 1141275.0, "to": None, "rate": 0.218},
                ],
                "bpa": 15000.0,
                "nrtc_rate": 0.087,
            },
            "NS": {
                "name": "Nova Scotia",
                "brackets": [
                    {"from": 0.0, "to": 30995.0, "rate": 0.0879},
                    {"from": 30995.0, "to": 61991.0, "rate": 0.1495},
                    {"from": 61991.0, "to": 97417.0, "rate": 0.1667},
                    {"from": 97417.0, "to": 157124.0, "rate": 0.175},
                    {"from": 157124.0, "to": None, "rate": 0.21},
                ],
                "bpa": 11932.0,
                "nrtc_rate": 0.0879,
            },
            "NT": {
                "name": "Northwest Territories",
                "brackets": [
                    {"from": 0.0, "to": 53003.0, "rate": 0.059},
                    {"from": 53003.0, "to": 106009.0, "rate": 0.086},
                    {"from": 106009.0, "to": 172346.0, "rate": 0.122},
                    {"from": 172346.0, "to": None, "rate": 0.1405},
                ],
                "bpa": 18198.0,
                "nrtc_rate": 0.059,
            },
            "NU": {
                "name": "Nunavut",
                "brackets": [
                    {"from": 0.0, "to": 55801.0, "rate": 0.04},
                    {"from": 55801.0, "to": 111602.0, "rate": 0.07},
                    {"from": 111602.0, "to": 181439.0, "rate": 0.09},
                    {"from": 181439.0, "to": None, "rate": 0.115},
                ],
                "bpa": 19659.0,
                "nrtc_rate": 0.04,
            },
            "ON": {
                "name": "Ontario",
                "brackets": [
                    {"from": 0.0, "to": 53891.0, "rate": 0.0505},
                    {"from": 53891.0, "to": 107785.0, "rate": 0.0915},
                    {"from": 107785.0, "to": 150000.0, "rate": 0.1116},
                    {"from": 150000.0, "to": 220000.0, "rate": 0.1216},
                    {"from": 220000.0, "to": None, "rate": 0.1316},
                ],
                "bpa": 12989.0,
                "nrtc_rate": 0.0505,
                "surtax": {
                    "threshold_1": 5818.0,
                    "rate_1": 0.20,
                    "threshold_2": 7446.0,
                    "rate_2": 0.36,
                },
                "health_premium": True,
                "tax_reduction": {"basic": 300.0},
            },
            "PE": {
                "name": "Prince Edward Island",
                # Budget 2026: New top bracket at 20% over 200,000
                "brackets": [
                    {"from": 0.0, "to": 33928.0, "rate": 0.095},
                    {"from": 33928.0, "to": 65820.0, "rate": 0.1347},
                    {"from": 65820.0, "to": 106890.0, "rate": 0.166},
                    {"from": 106890.0, "to": 142520.0, "rate": 0.1762},
                    {"from": 142520.0, "to": 200000.0, "rate": 0.190},
                    {"from": 200000.0, "to": None, "rate": 0.200},
                ],
                "bpa": 15000.0,
                "nrtc_rate": 0.095,
            },
            "QC": {
                "name": "Quebec",
                "brackets": [
                    {"from": 0.0, "to": 54320.0, "rate": 0.14},
                    {"from": 54320.0, "to": 108625.0, "rate": 0.19},
                    {"from": 108625.0, "to": 132180.0, "rate": 0.24},
                    {"from": 132180.0, "to": None, "rate": 0.2575},
                ],
                "bpa": 18942.0,
                "nrtc_rate": 0.14,
                "federal_abatement_rate": 0.165,
                "separate_filing": True,
            },
            "SK": {
                "name": "Saskatchewan",
                "brackets": [
                    {"from": 0.0, "to": 54532.0, "rate": 0.105},
                    {"from": 54532.0, "to": 155805.0, "rate": 0.125},
                    {"from": 155805.0, "to": None, "rate": 0.145},
                ],
                "bpa": 20381.0,
                "nrtc_rate": 0.105,
            },
            "YT": {
                "name": "Yukon",
                "brackets": [
                    {"from": 0.0, "to": 58523.0, "rate": 0.064},
                    {"from": 58523.0, "to": 117045.0, "rate": 0.09},
                    {"from": 117045.0, "to": 181440.0, "rate": 0.109},
                    {"from": 181440.0, "to": 500000.0, "rate": 0.128},
                    {"from": 500000.0, "to": None, "rate": 0.15},
                ],
                "bpa": 16452.0,
                "nrtc_rate": 0.064,
            },
        },
    },
}


def resolve_supported_year(year: int) -> tuple[int, Optional[str]]:
    """Resolve tax year to supported years (2024-2026) with note if clamped."""
    if year in SUPPORTED_YEARS:
        return year, None
    if year < SUPPORTED_YEARS[0]:
        return SUPPORTED_YEARS[0], f"Year {year} is prior to supported range; using {SUPPORTED_YEARS[0]} rules."
    return SUPPORTED_YEARS[-1], f"Year {year} exceeds supported range; using {SUPPORTED_YEARS[-1]} rules."


def get_tax_year_rules(year: int) -> dict:
    """Return raw tax rules for given year, falling back to supported range."""
    resolved_year, _ = resolve_supported_year(year)
    return TAX_YEAR_RULES[resolved_year]
