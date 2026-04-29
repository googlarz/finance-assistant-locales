"""
NL validation: runs official belastingdienst.nl test cases against the NL locale engine.
"""
from __future__ import annotations

import json
import os
import sys

_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

from context import LocaleContext
from nl import calculate_tax

_CASES_PATH = os.path.join(os.path.dirname(__file__), "cases.json")


def _build_ctx(case: dict) -> LocaleContext:
    inp = case["inputs"]
    extra = {}
    if inp.get("savings") is not None:
        extra["savings"] = float(inp["savings"])
    if inp.get("investments") is not None:
        extra["investments"] = float(inp["investments"])
    if inp.get("debts") is not None:
        extra["debts"] = float(inp["debts"])

    return LocaleContext(
        tax_year=case["year"],
        employment_type=inp.get("employment_type", "employed"),
        annual_gross=float(inp.get("gross_annual_income", 0)),
        married=(inp.get("marital_status") == "married"),
        extra=extra,
    )


def run_cases(verbose: bool = False) -> list[dict]:
    """Run all NL validation cases. Returns list of result dicts."""
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
                "locale": "nl",
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
            if field == "box1_tax":
                actual = result.get("box1_tax", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "box1_tax_min":
                actual = result.get("box1_tax", 0.0)
                if actual < float(exp_val):
                    failures.append({"field": field, "expected": f">= {exp_val}", "actual": actual, "diff": float(exp_val) - actual})
            elif field == "box3_tax":
                actual = result.get("box3_tax", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > tol:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})
            elif field == "marginal_rate":
                actual = result.get("marginal_rate", 0.0)
                diff = abs(actual - float(exp_val))
                if diff > 0.01:
                    failures.append({"field": field, "expected": float(exp_val), "actual": actual, "diff": diff})

        results.append({
            "id": case_id,
            "locale": "nl",
            "status": "fail" if failures else "pass",
            "failures": failures,
            "result": result,
        })
        if verbose:
            status = "FAIL" if failures else "PASS"
            print(f"  [{status}] {case_id}")
            for f_ in failures:
                actual_fmt = f_['actual'] if isinstance(f_['actual'], str) else f"{f_['actual']:.2f}"
                print(f"         {f_['field']}: expected={f_['expected']}, actual={actual_fmt}, diff={f_['diff']:.4f}")

    return results


if __name__ == "__main__":
    print("NL Validation Cases")
    print("=" * 60)
    results = run_cases(verbose=True)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"\nNL: {passed}/{len(results)} passed ({failed} failed, {skipped} skipped)")
