"""
Validation runner for the Irish (ie) locale.

Loads cases.json, builds LocaleContext for each case, runs calculate_tax,
and compares results against expected values within tolerance.
"""

import json
import sys
from pathlib import Path

# Add locales root to path
locales_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(locales_root))

from context import LocaleContext
from ie import calculate_tax


def run_cases(verbose: bool = False) -> dict:
    """
    Run all Irish validation cases and return a summary.

    Returns dict with: total, passed, failed, errors, details.
    """
    cases_path = Path(__file__).parent / "cases.json"
    with open(cases_path) as f:
        cases = json.load(f)

    results = {"total": len(cases), "passed": 0, "failed": 0, "errors": [], "details": []}

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
                if abs(actual - exp) > tolerance:
                    failures.append(
                        f"  {key}: expected {exp}, got {actual} "
                        f"(diff {abs(actual - exp):.2f}, tolerance {tolerance})"
                    )

            if failures:
                results["failed"] += 1
                detail = {"id": case_id, "status": "FAIL", "failures": failures}
                results["errors"].append(f"{case_id}: FAIL")
                for f_line in failures:
                    results["errors"].append(f_line)
            else:
                results["passed"] += 1
                detail = {"id": case_id, "status": "PASS"}

            results["details"].append(detail)

            if verbose:
                status = "PASS" if not failures else "FAIL"
                print(f"  [{status}] {case_id}: {case['description']}")
                if failures:
                    for f_line in failures:
                        print(f_line)

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{case_id}: ERROR — {e}")
            results["details"].append({"id": case_id, "status": "ERROR", "error": str(e)})
            if verbose:
                print(f"  [ERROR] {case_id}: {e}")

    return results


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print("Irish (ie) locale validation")
    print("=" * 40)
    results = run_cases(verbose=True)
    print("=" * 40)
    print(f"Total: {results['total']} | Passed: {results['passed']} | Failed: {results['failed']}")
    if results["failed"] > 0:
        sys.exit(1)
