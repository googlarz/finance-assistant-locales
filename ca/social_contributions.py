"""
Canada social contributions: CPP / QPP, CPP2 / QPP2, and Employment Insurance (EI).

Rules for 2024, 2025, and 2026.

Sources:
  Canada Revenue Agency (CRA):
  - CPP contribution rates, maximums and exemptions:
    https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/canada-pension-plan-cpp/cpp-contribution-rates-maximums-exemptions.html
  - EI premium rates and maximums:
    https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/payroll/payroll-deductions-contributions/employment-insurance-ei/ei-premium-rates-maximums.html
  - CRA T4127 Table 8.3 & Table 8.7 (2024-2026 editions)
"""

from __future__ import annotations
from typing import Optional
from .tax_rules import normalize_province, resolve_supported_year

CPP_EI_RULES = {
    2024: {
        # CPP (Canada except QC)
        "cpp_ympe": 68500.0,
        "cpp_basic_exemption": 3500.0,
        "cpp_employee_rate": 0.0595,
        "cpp_employer_rate": 0.0595,
        "cpp_max_contribution": 3867.50,
        # CPP2 (Second additional CPP)
        "cpp2_yampe": 73200.0,
        "cpp2_employee_rate": 0.04,
        "cpp2_employer_rate": 0.04,
        "cpp2_max_contribution": 188.00,
        # QPP (QC)
        "qpp_employee_rate": 0.0640,
        "qpp_employer_rate": 0.0640,
        "qpp_max_contribution": 4160.00,
        "qpp2_yampe": 73200.0,
        "qpp2_employee_rate": 0.04,
        "qpp2_employer_rate": 0.04,
        "qpp2_max_contribution": 188.00,
        # EI (Canada except QC)
        "ei_max_insurable": 63200.0,
        "ei_employee_rate": 0.0166,
        "ei_employer_rate": 0.02324,  # 1.4x employee rate
        "ei_max_employee_premium": 1049.12,
        "ei_max_employer_premium": 1468.77,
        # EI (QC - reduced for QPIP)
        "ei_qc_employee_rate": 0.0132,
        "ei_qc_employer_rate": 0.01848,
        "ei_qc_max_employee_premium": 834.24,
        "ei_qc_max_employer_premium": 1167.94,
        # QPIP (QC only)
        "qpip_max_insurable": 94000.0,
        "qpip_employee_rate": 0.00494,
        "qpip_employer_rate": 0.00692,
        "qpip_max_employee_premium": 464.36,
        "qpip_max_employer_premium": 650.48,
    },
    2025: {
        # CPP (Canada except QC)
        "cpp_ympe": 71300.0,
        "cpp_basic_exemption": 3500.0,
        "cpp_employee_rate": 0.0595,
        "cpp_employer_rate": 0.0595,
        "cpp_max_contribution": 4034.10,
        # CPP2
        "cpp2_yampe": 81200.0,
        "cpp2_employee_rate": 0.04,
        "cpp2_employer_rate": 0.04,
        "cpp2_max_contribution": 396.00,
        # QPP (QC)
        "qpp_employee_rate": 0.0640,
        "qpp_employer_rate": 0.0640,
        "qpp_max_contribution": 4339.20,
        "qpp2_yampe": 81200.0,
        "qpp2_employee_rate": 0.04,
        "qpp2_employer_rate": 0.04,
        "qpp2_max_contribution": 396.00,
        # EI (Canada except QC)
        "ei_max_insurable": 65700.0,
        "ei_employee_rate": 0.0164,
        "ei_employer_rate": 0.02296,
        "ei_max_employee_premium": 1077.48,
        "ei_max_employer_premium": 1508.47,
        # EI (QC)
        "ei_qc_employee_rate": 0.0131,
        "ei_qc_employer_rate": 0.01834,
        "ei_qc_max_employee_premium": 860.67,
        "ei_qc_max_employer_premium": 1204.94,
        # QPIP (QC)
        "qpip_max_insurable": 98000.0,
        "qpip_employee_rate": 0.00494,
        "qpip_employer_rate": 0.00692,
        "qpip_max_employee_premium": 484.12,
        "qpip_max_employer_premium": 678.16,
    },
    2026: {
        # CPP (Canada except QC)
        "cpp_ympe": 74600.0,
        "cpp_basic_exemption": 3500.0,
        "cpp_employee_rate": 0.0595,
        "cpp_employer_rate": 0.0595,
        "cpp_max_contribution": 4230.45,
        # CPP2
        "cpp2_yampe": 85000.0,
        "cpp2_employee_rate": 0.04,
        "cpp2_employer_rate": 0.04,
        "cpp2_max_contribution": 416.00,
        # QPP (QC)
        "qpp_employee_rate": 0.0630,
        "qpp_employer_rate": 0.0630,
        "qpp_max_contribution": 4479.30,
        "qpp2_yampe": 85000.0,
        "qpp2_employee_rate": 0.04,
        "qpp2_employer_rate": 0.04,
        "qpp2_max_contribution": 416.00,
        # EI (Canada except QC)
        "ei_max_insurable": 68900.0,
        "ei_employee_rate": 0.0163,
        "ei_employer_rate": 0.02282,
        "ei_max_employee_premium": 1123.07,
        "ei_max_employer_premium": 1572.30,
        # EI (QC)
        "ei_qc_employee_rate": 0.0130,
        "ei_qc_employer_rate": 0.01820,
        "ei_qc_max_employee_premium": 895.70,
        "ei_qc_max_employer_premium": 1253.98,
        # QPIP (QC)
        "qpip_max_insurable": 103000.0,
        "qpip_employee_rate": 0.0043,
        "qpip_employer_rate": 0.00602,
        "qpip_max_employee_premium": 442.90,
        "qpip_max_employer_premium": 620.06,
    },
}


def calculate_social_contributions(gross: float, year: int, province: Optional[str] = None, self_employed: bool = False) -> dict:
    """
    Calculate employee/self-employed social contributions (CPP/QPP, CPP2/QPP2, EI, QPIP).

    Args:
        gross: Gross annual earnings.
        year: Tax year (2024-2026).
        province: Province code (e.g. 'ON', 'BC', 'QC').
        self_employed: True if self-employed (pays both employee and employer CPP/QPP; EI is optional).

    Returns:
        Dict with total employee and employer contributions and granular breakdown.
    """
    resolved_year, _ = resolve_supported_year(year)
    rules = CPP_EI_RULES[resolved_year]
    prov = normalize_province(province)
    is_qc = (prov == "QC")

    # 1. Pension plan (CPP vs QPP)
    ympe = rules["cpp_ympe"]
    basic_exemption = rules["cpp_basic_exemption"]
    pensionable_earnings = max(0.0, min(gross, ympe) - basic_exemption)

    if is_qc:
        pension_rate_ee = rules["qpp_employee_rate"]
        pension_rate_er = rules["qpp_employer_rate"]
        pension_max_ee = rules["qpp_max_contribution"]
        plan_name = "QPP"
    else:
        pension_rate_ee = rules["cpp_employee_rate"]
        pension_rate_er = rules["cpp_employer_rate"]
        pension_max_ee = rules["cpp_max_contribution"]
        plan_name = "CPP"

    cpp_ee = min(round(pensionable_earnings * pension_rate_ee, 2), pension_max_ee)
    cpp_er = cpp_ee if not self_employed else 0.0
    if self_employed:
        cpp_ee = round(cpp_ee * 2, 2)  # Self-employed pays both portions

    # 2. Second Additional CPP / QPP (CPP2 / QPP2)
    yampe = rules["cpp2_yampe"]
    if gross > ympe:
        cpp2_earnings = min(gross, yampe) - ympe
        cpp2_rate = rules["cpp2_employee_rate"]
        cpp2_max = rules["cpp2_max_contribution"]
        cpp2_ee = min(round(cpp2_earnings * cpp2_rate, 2), cpp2_max)
        cpp2_er = cpp2_ee if not self_employed else 0.0
        if self_employed:
            cpp2_ee = round(cpp2_ee * 2, 2)
    else:
        cpp2_ee = 0.0
        cpp2_er = 0.0

    # 3. Employment Insurance (EI)
    if self_employed:
        # Standard self-employed filers are exempt from EI unless opted into special benefits
        ei_ee = 0.0
        ei_er = 0.0
    else:
        ei_max_insurable = rules["ei_max_insurable"]
        insurable_earnings = min(gross, ei_max_insurable)
        if is_qc:
            ei_rate_ee = rules["ei_qc_employee_rate"]
            ei_rate_er = rules["ei_qc_employer_rate"]
            ei_max_ee = rules["ei_qc_max_employee_premium"]
            ei_max_er = rules["ei_qc_max_employer_premium"]
        else:
            ei_rate_ee = rules["ei_employee_rate"]
            ei_rate_er = rules["ei_employer_rate"]
            ei_max_ee = rules["ei_max_employee_premium"]
            ei_max_er = rules["ei_max_employer_premium"]

        ei_ee = min(round(insurable_earnings * ei_rate_ee, 2), ei_max_ee)
        ei_er = min(round(insurable_earnings * ei_rate_er, 2), ei_max_er)

    # 4. QPIP (Quebec Parental Insurance Plan - QC only)
    qpip_ee = 0.0
    qpip_er = 0.0
    if is_qc and not self_employed:
        qpip_max_ins = rules["qpip_max_insurable"]
        qpip_ins = min(gross, qpip_max_ins)
        qpip_ee = min(round(qpip_ins * rules["qpip_employee_rate"], 2), rules["qpip_max_employee_premium"])
        qpip_er = min(round(qpip_ins * rules["qpip_employer_rate"], 2), rules["qpip_max_employer_premium"])

    total_employee = round(cpp_ee + cpp2_ee + ei_ee + qpip_ee, 2)
    total_employer = round(cpp_er + cpp2_er + ei_er + qpip_er, 2)

    return {
        "annual_gross": round(gross, 2),
        "year": resolved_year,
        "province": prov,
        "self_employed": self_employed,
        "plan": plan_name,
        "cpp_employee": cpp_ee,
        "cpp_employer": cpp_er,
        "cpp2_employee": cpp2_ee,
        "cpp2_employer": cpp2_er,
        "ei_employee": ei_ee,
        "ei_employer": ei_er,
        "qpip_employee": qpip_ee,
        "qpip_employer": qpip_er,
        "total_employee": total_employee,
        "total_employer": total_employer,
        # Standard interface breakdown keys expected by cross-locale checks
        "cpp": {
            "rate": (pension_rate_ee * 2) if not self_employed else pension_rate_ee,
            "employee_share": pension_rate_ee,
            "annual_max": pension_max_ee * (2 if self_employed else 1),
            "amount": cpp_ee,
        },
        "ei": {
            "rate": round(rules["ei_employee_rate"] + rules["ei_employer_rate"], 5),
            "employee_share": rules["ei_employee_rate"],
            "annual_max": rules["ei_max_employee_premium"],
            "amount": ei_ee,
        },
    }
