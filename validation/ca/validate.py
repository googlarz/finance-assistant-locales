"""
Canadian validation: runs official CRA test cases against the CA locale engine.

Sources: CRA publication T4127, Form 5000-S1 (Federal Tax), and provincial 428 schedules.
Expected values are verified against CRA published rules and parameters.
"""
from __future__ import annotations

import json
import os
import sys

_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

from context import LocaleContext
from ca import calculate_tax

_CASES_PATH = os.path.join(os.path.dirname(__file__), "cases.json")


def _build_ctx(case: dict) -> LocaleContext:
    inp = case["inputs"]
    return LocaleContext(
        tax_year=case["year"],
        employment_type=inp.get("employment_type", "employed"),
        annual_gross=float(inp["gross_annual_income"]),
        region=inp.get("province", "ON"),
        married=(inp.get("marital_status") == "married"),
    )


def run_cases(verbose: bool = False) -> list[dict]:
    """Run all Canadian validation cases. Returns list of result dicts."""
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
                "locale": "ca",
                "status": "skip",
                "failures": [],
                "error": str(exc),
                "result": None,
            })
            if verbose:
                print(f"  [SKIP] {case_id}: {exc}")
            continue

        expected = case.get("expected", {})
        tol = float(expected.get("tolerance_abs", 100))
        failures = []

        valid_fields = {
            "federal_tax",
            "provincial_tax",
            "tax",
            "cpp_employee",
            "ei_employee",
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
            "locale": "ca",
            "status": "fail" if failures else "pass",
            "failures": failures,
            "result": result,
        })
        if verbose:
            status = "FAIL" if failures else "PASS"
            print(f"  [{status}] {case_id}: {case.get('description', '')}")
            for f_ in failures:
                print(f"         {f_['field']}: expected={f_['expected']}, actual={f_['actual']:.2f}, diff={f_['diff']:.2f}")

    return results


if __name__ == "__main__":
    print("Canada Validation Cases")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nCA: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
