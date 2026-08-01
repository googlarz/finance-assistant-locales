"""
Validation runner for the Irish (ie) locale.

Loads cases.json, builds LocaleContext for each case, runs calculate_tax,
and compares results against expected values within tolerance.

run_cases() returns a list of per-case dicts matching the shared runner contract:
  [{"id": str, "locale": "ie", "status": "pass"|"fail"|"skip", "failures": [...], "result": ...}]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add locales root to path
locales_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(locales_root))

from context import LocaleContext
from ie import calculate_tax


def run_cases(verbose: bool = False) -> list[dict]:
    """
    Run all Irish validation cases.

    Returns a list of result dicts (one per case) with:
      id, locale, status ("pass"|"fail"|"skip"), failures, result
    """
    cases_path = Path(__file__).parent / "cases.json"
    with open(cases_path) as f:
        cases = json.load(f)

    results = []

    for case in cases:
        case_id = case["id"]
        inputs = case["inputs"]
        expected = case["expected"]
        tolerance = expected.get("tolerance_abs", 50)

        try:
            ctx = LocaleContext(
                tax_year=case["year"],
                employment_type=inputs["employment_type"],
                annual_gross=inputs["gross_annual_income"],
                married=(inputs.get("marital_status") == "married"),
            )

            result = calculate_tax(ctx)

            failures = []
            for key in ["income_tax", "usc", "prsi_employee"]:
                if key not in expected:
                    continue
                actual = result.get(key, 0)
                exp = expected[key]
                diff = abs(actual - exp)
                if diff > tolerance:
                    failures.append({
                        "field": key,
                        "expected": exp,
                        "actual": actual,
                        "diff": diff,
                    })

            results.append({
                "id": case_id,
                "locale": "ie",
                "status": "fail" if failures else "pass",
                "failures": failures,
                "result": result,
            })

            if verbose:
                status = "PASS" if not failures else "FAIL"
                print(f"  [{status}] {case_id}: {case['description']}")
                for f_ in failures:
                    print(f"         {f_['field']}: expected={f_['expected']}, actual={f_['actual']:.2f}, diff={f_['diff']:.2f}")

        except Exception as e:
            results.append({
                "id": case_id,
                "locale": "ie",
                "status": "skip",
                "failures": [],
                "error": str(e),
                "result": None,
            })
            if verbose:
                print(f"  [SKIP] {case_id}: {e}")

    return results


if __name__ == "__main__":
    print("Irish (ie) locale validation")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nIE: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
    if failed > 0:
        sys.exit(1)
