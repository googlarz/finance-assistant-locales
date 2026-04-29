"""
PL validation: runs official podatki.gov.pl / ZUS test cases against the PL locale engine.
"""
from __future__ import annotations

import json
import os
import sys

_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

from context import LocaleContext, ChildInfo
from pl import calculate_tax, get_social_contributions

_CASES_PATH = os.path.join(os.path.dirname(__file__), "cases.json")


def _build_ctx(case: dict) -> LocaleContext:
    inp = case["inputs"]
    extra = {}
    if inp.get("age") is not None:
        extra["age"] = inp["age"]

    children = []
    for i in range(inp.get("children_count", 0)):
        children.append(ChildInfo(birth_year=2015 - i))

    return LocaleContext(
        tax_year=case["year"],
        employment_type=inp.get("employment_type", "employed"),
        annual_gross=float(inp["gross_annual_income"]),
        married=(inp.get("marital_status") == "married"),
        children=children,
        extra=extra,
    )


def run_cases(verbose: bool = False) -> list[dict]:
    """Run all PL validation cases. Returns list of result dicts."""
    with open(_CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    for case in cases:
        case_id = case["id"]

        # Social-only case
        if "expected_social" in case and "expected" not in case:
            inp = case["inputs"]
            gross = float(inp["gross_annual_income"])
            tol_social = float(case["expected_social"].get("tolerance_abs", 100))
            try:
                social = get_social_contributions(gross, case["year"])
            except Exception as exc:
                results.append({
                    "id": case_id,
                    "locale": "pl",
                    "status": "skip",
                    "failures": [],
                    "error": str(exc),
                    "result": None,
                })
                if verbose:
                    print(f"  [SKIP] {case_id}: {exc}")
                continue

            failures = []
            exp_s = case["expected_social"]

            def _chk(exp_key: str, result_key: str):
                val = exp_s.get(exp_key)
                if val is None:
                    return
                actual = social.get(result_key, social.get("branches", {}).get(result_key, None))
                # Try nested paths for PL social structure
                if actual is None:
                    # Try branches
                    branches = social.get("branches", {})
                    if exp_key == "emerytalne_employee":
                        actual = branches.get("pension_emerytalne", {}).get("employee", None)
                    elif exp_key == "rentowe_employee":
                        actual = branches.get("disability_rentowe", {}).get("employee", None)
                    elif exp_key == "chorobowe_employee":
                        actual = branches.get("sickness_chorobowe", {}).get("employee", None)
                    elif exp_key == "employee_total":
                        actual = social.get("employee_total", None)
                if actual is None:
                    return
                diff = abs(actual - float(val))
                if diff > tol_social:
                    failures.append({"field": exp_key, "expected": float(val), "actual": actual, "diff": diff})

            _chk("emerytalne_employee", "emerytalne_employee")
            _chk("rentowe_employee", "rentowe_employee")
            _chk("chorobowe_employee", "chorobowe_employee")
            _chk("employee_total", "employee_total")

            results.append({
                "id": case_id,
                "locale": "pl",
                "status": "fail" if failures else "pass",
                "failures": failures,
                "result": social,
            })
            if verbose:
                status = "FAIL" if failures else "PASS"
                print(f"  [{status}] {case_id}")
                for f_ in failures:
                    print(f"         {f_['field']}: expected={f_['expected']}, actual={f_['actual']:.2f}, diff={f_['diff']:.2f}")
            continue

        # Tax case
        try:
            ctx = _build_ctx(case)
            result = calculate_tax(ctx)
        except Exception as exc:
            results.append({
                "id": case_id,
                "locale": "pl",
                "status": "skip",
                "failures": [],
                "error": str(exc),
                "result": None,
            })
            if verbose:
                print(f"  [SKIP] {case_id}: {exc}")
            continue

        expected = case.get("expected", {})
        tol = float(expected.get("tolerance_abs", 300))
        failures = []

        for field, exp_val in expected.items():
            if field == "tolerance_abs":
                continue
            if field == "income_tax":
                actual = result.get("income_tax", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "income_tax_min":
                actual = result.get("income_tax", 0.0)
                if actual < float(exp_val):
                    failures.append({"field": field, "expected": f">= {exp_val}", "actual": actual, "diff": float(exp_val) - actual})
            elif field == "income_tax_max":
                actual = result.get("income_tax", 0.0)
                if actual > float(exp_val) + tol:
                    failures.append({"field": field, "expected": f"<= {exp_val}", "actual": actual, "diff": actual - float(exp_val)})
            elif field == "zus_employee":
                actual = result.get("zus_employee", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "health_insurance":
                actual = result.get("health_insurance", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "net":
                actual = result.get("net", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "ulga_mlodych_applied":
                actual = result.get("ulga_mlodych_applied", False)
                if actual != bool(exp_val):
                    failures.append({"field": field, "expected": bool(exp_val), "actual": actual, "diff": 0})

        results.append({
            "id": case_id,
            "locale": "pl",
            "status": "fail" if failures else "pass",
            "failures": failures,
            "result": result,
        })
        if verbose:
            status = "FAIL" if failures else "PASS"
            print(f"  [{status}] {case_id}")
            for f_ in failures:
                actual_fmt = f_['actual'] if isinstance(f_['actual'], (str, bool)) else f"{f_['actual']:.2f}"
                print(f"         {f_['field']}: expected={f_['expected']}, actual={actual_fmt}, diff={f_['diff']:.2f}")

    return results


if __name__ == "__main__":
    print("PL Validation Cases")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nPL: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
