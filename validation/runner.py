"""
Validation runner: executes all locale validation suites and aggregates results.

Usage:
    from validation.runner import run_all_validations, format_validation_report
    result = run_all_validations()
    print(format_validation_report(result))

Or from the command line:
    cd locales && python -m validation.runner
"""
from __future__ import annotations

import os
import sys

# Ensure locales/ root is on path when run as a script or imported
_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _LOCALES_ROOT not in sys.path:
    sys.path.insert(0, _LOCALES_ROOT)

_ALL_LOCALES = ["de", "uk", "fr", "nl", "pl"]


def _load_locale_runner(locale: str):
    """Dynamically import the validate module for the given locale."""
    import importlib.util as _ilu
    path = os.path.join(os.path.dirname(__file__), locale, "validate.py")
    spec = _ilu.spec_from_file_location(f"validation_{locale}", path)
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_all_validations(locales: list[str] | None = None, verbose: bool = False) -> dict:
    """
    Run all validation cases for the specified locales (default: all).

    Returns:
        {
            "summary": {"total": int, "passed": int, "failed": int, "skipped": int},
            "by_locale": {
                "de": {"total": int, "passed": int, "failed": int, "skipped": int},
                ...
            },
            "failures": [
                {"id": str, "locale": str, "field": str,
                 "expected": float, "actual": float, "diff": float}
            ]
        }
    """
    if locales is None:
        locales = _ALL_LOCALES

    total = 0
    passed = 0
    failed = 0
    skipped = 0
    by_locale: dict[str, dict] = {}
    all_failures: list[dict] = []

    for locale in locales:
        try:
            module = _load_locale_runner(locale)
            case_results = module.run_cases(verbose=verbose)
        except Exception as exc:
            by_locale[locale] = {
                "total": 0, "passed": 0, "failed": 0, "skipped": 0,
                "error": str(exc),
            }
            continue

        loc_total = len(case_results)
        loc_passed = sum(1 for r in case_results if r["status"] == "pass")
        loc_failed = sum(1 for r in case_results if r["status"] == "fail")
        loc_skipped = sum(1 for r in case_results if r["status"] == "skip")

        by_locale[locale] = {
            "total": loc_total,
            "passed": loc_passed,
            "failed": loc_failed,
            "skipped": loc_skipped,
        }

        for r in case_results:
            for f in r.get("failures", []):
                all_failures.append({
                    "id": r["id"],
                    "locale": locale,
                    "field": f.get("field", "unknown"),
                    "expected": f.get("expected"),
                    "actual": f.get("actual"),
                    "diff": f.get("diff"),
                })

        total += loc_total
        passed += loc_passed
        failed += loc_failed
        skipped += loc_skipped

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "by_locale": by_locale,
        "failures": all_failures,
    }


def format_validation_report(result: dict) -> str:
    """
    Produce a plain-text validation report.

    Example:
        DE: 8/8 passed
        UK: 5/6 passed (1 failed: uk_2024_taper_110k — income_tax off by £142)
        FR: 5/5 passed
        NL: 4/5 passed (1 failed: nl_2024_box3_partners — box3_tax off by €12)
        PL: 5/5 passed
        Total: 27/29 passed
    """
    lines = []
    by_locale = result.get("by_locale", {})
    failures_by_locale: dict[str, list[dict]] = {}
    for f in result.get("failures", []):
        failures_by_locale.setdefault(f["locale"], []).append(f)

    for locale in _ALL_LOCALES:
        if locale not in by_locale:
            continue
        stats = by_locale[locale]
        if "error" in stats:
            lines.append(f"{locale.upper()}: ERROR — {stats['error']}")
            continue

        loc_total = stats["total"]
        loc_passed = stats["passed"]
        loc_failed = stats["failed"]
        loc_skipped = stats["skipped"]

        if loc_failed == 0:
            skip_note = f" ({loc_skipped} skipped)" if loc_skipped else ""
            lines.append(f"{locale.upper()}: {loc_passed}/{loc_total} passed{skip_note}")
        else:
            loc_failures = failures_by_locale.get(locale, [])
            failure_details = []
            # Group by case id
            seen = set()
            for f in loc_failures:
                case_id = f["id"]
                if case_id in seen:
                    continue
                seen.add(case_id)
                field = f["field"]
                diff = f.get("diff")
                if diff is not None and isinstance(diff, (int, float)):
                    failure_details.append(f"{case_id} — {field} off by {diff:.0f}")
                else:
                    failure_details.append(f"{case_id} — {field}: expected {f['expected']}, got {f['actual']}")
            detail_str = "; ".join(failure_details)
            skip_note = f", {loc_skipped} skipped" if loc_skipped else ""
            lines.append(
                f"{locale.upper()}: {loc_passed}/{loc_total} passed"
                f" ({loc_failed} failed{skip_note}: {detail_str})"
            )

    summary = result.get("summary", {})
    total = summary.get("total", 0)
    total_passed = summary.get("passed", 0)
    total_failed = summary.get("failed", 0)
    total_skipped = summary.get("skipped", 0)

    skip_note = f" ({total_skipped} skipped)" if total_skipped else ""
    lines.append(f"Total: {total_passed}/{total} passed ({total_failed} failed){skip_note}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run locale validation suites")
    parser.add_argument("--locales", nargs="*", help="Locales to validate (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-case results")
    args = parser.parse_args()

    result = run_all_validations(locales=args.locales, verbose=args.verbose)
    print(format_validation_report(result))

    # Exit non-zero if any failures
    if result["summary"]["failed"] > 0:
        sys.exit(1)
