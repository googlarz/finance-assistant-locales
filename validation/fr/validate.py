"""
FR validation: runs official impots.gouv.fr test cases against the FR locale engine.
"""
from __future__ import annotations

import json
import os
import sys

_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

from context import LocaleContext
from fr import calculate_tax

_CASES_PATH = os.path.join(os.path.dirname(__file__), "cases.json")

_AE_TYPE_MAP = {
    "commerce": "commerce",
    "services": "services",
    "bnc": "bnc",
}


def _build_ctx(case: dict) -> LocaleContext:
    inp = case["inputs"]
    extra = {}
    if inp.get("ae_type"):
        extra["ae_type"] = _AE_TYPE_MAP.get(inp["ae_type"], inp["ae_type"])
        extra["auto_entrepreneur"] = True

    emp_type = inp.get("employment_type", "employed")
    if emp_type == "auto_entrepreneur":
        # FR engine detects AE via employment_type in (freelancer, self_employed) + extra flag
        emp_type = "freelancer"
        extra["auto_entrepreneur"] = True

    children = []
    children_count = inp.get("children_count", 0)
    if children_count:
        # Create placeholder ChildInfo objects for count
        from context import ChildInfo
        for i in range(children_count):
            children.append(ChildInfo(birth_year=2015 - i))

    return LocaleContext(
        tax_year=case["year"],
        employment_type=emp_type,
        annual_gross=float(inp["gross_annual_income"]),
        married=(inp.get("marital_status") == "married"),
        children=children,
        extra=extra,
    )


def run_cases(verbose: bool = False) -> list[dict]:
    """Run all FR validation cases. Returns list of result dicts."""
    with open(_CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    for case in cases:
        case_id = case["id"]
        try:
            ctx = _build_ctx(case)
            result = calculate_tax(ctx)
        except Exception as exc:
            results.append({
                "id": case_id,
                "locale": "fr",
                "status": "skip",
                "failures": [],
                "error": str(exc),
                "result": None,
            })
            if verbose:
                print(f"  [SKIP] {case_id}: {exc}")
            continue

        expected = case.get("expected", {})
        tol = float(expected.get("tolerance_abs", 150))
        failures = []

        field_map = {
            "income_tax": "income_tax",
            "prelevements_sociaux": "prelevements_sociaux",
        }

        for field, exp_val in expected.items():
            if field == "tolerance_abs":
                continue
            if field == "income_tax_max":
                actual = result.get("income_tax", 0.0)
                if actual > float(exp_val):
                    failures.append({
                        "field": field,
                        "expected": f"<= {exp_val}",
                        "actual": actual,
                        "diff": actual - float(exp_val),
                    })
                continue
            if field in field_map:
                actual = result.get(field_map[field])
                if actual is None:
                    continue
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({
                        "field": field,
                        "expected": float(exp_val),
                        "actual": actual,
                        "diff": diff,
                    })

        results.append({
            "id": case_id,
            "locale": "fr",
            "status": "fail" if failures else "pass",
            "failures": failures,
            "result": result,
        })
        if verbose:
            status = "FAIL" if failures else "PASS"
            print(f"  [{status}] {case_id}")
            for f_ in failures:
                print(f"         {f_['field']}: expected={f_['expected']}, actual={f_['actual']:.2f}, diff={f_['diff']:.2f}")

    return results


if __name__ == "__main__":
    print("FR Validation Cases")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nFR: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
