"""
US validation: runs official IRS test cases against the US locale engine.

Sources: IRS Rev. Proc. 2023-34 (2024 brackets / standard deduction) and
IRS Schedule SE (self-employment tax). Expected values are computed
independently from published IRS figures, not from this engine.
"""
from __future__ import annotations

import json
import os
import sys

_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

from context import LocaleContext
from us import calculate_tax

_CASES_PATH = os.path.join(os.path.dirname(__file__), "cases.json")


def _build_ctx(case: dict) -> LocaleContext:
    inp = case["inputs"]
    return LocaleContext(
        tax_year=case["year"],
        employment_type=inp.get("employment_type", "employed"),
        annual_gross=float(inp["gross_annual_income"]),
        married=(inp.get("marital_status") == "married"),
    )


def run_cases(verbose: bool = False) -> list[dict]:
    """Run all US validation cases. Returns list of result dicts."""
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
                "id": case_id, "locale": "us", "status": "skip",
                "failures": [], "error": str(exc), "result": None,
            })
            if verbose:
                print(f"  [SKIP] {case_id}: {exc}")
            continue

        expected = case.get("expected", {})
        tol = float(expected.get("tolerance_abs", 100))
        failures = []

        # US calculator returns these keys directly
        valid_fields = {
            "federal_income_tax", "social_security_tax",
            "medicare_tax", "self_employment_tax",
        }

        for field, exp_val in expected.items():
            if field == "tolerance_abs":
                continue
            if field in valid_fields:
                actual = result.get(field)
                if actual is None:
                    continue
                diff = abs(float(actual) - float(exp_val))
                if diff > tol:
                    failures.append({
                        "field": field,
                        "expected": float(exp_val),
                        "actual": float(actual),
                        "diff": diff,
                    })

        results.append({
            "id": case_id,
            "locale": "us",
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
    print("US Validation Cases")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nUS: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
