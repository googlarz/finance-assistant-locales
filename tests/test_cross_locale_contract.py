"""
Cross-locale contract tests.

Every locale must expose the same public interface via its __init__.py and
return sane output from that interface. This guards the product's core
differentiator: one command works identically in all 6 countries.
"""
import sys
import os
import importlib
import pytest

_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
_LOCALES_ROOT = os.path.join(os.path.dirname(__file__), "..")
for _p in (_PROJECT_ROOT, _LOCALES_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from context import LocaleContext

ALL_LOCALES = ["de", "uk", "fr", "nl", "pl", "us"]

_PROFILES = {
    "de": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=60000.0, tax_class="I"),
    "uk": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=50000.0),
    "fr": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=45000.0),
    "nl": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=50000.0),
    "pl": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=80000.0),
    "us": LocaleContext(tax_year=2024, employment_type="employed", annual_gross=80000.0,
                        extra={"filing_status": "single"}),
}

_GROSS = {"de": 60000, "uk": 50000, "fr": 45000, "nl": 50000, "pl": 80000, "us": 80000}


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_exposes_calculate_tax(code):
    """Every locale __init__.py must export calculate_tax."""
    locale = importlib.import_module(code)
    assert callable(getattr(locale, "calculate_tax", None)), (
        f"Locale '{code}' __init__.py must expose calculate_tax(ctx, year=None)"
    )


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_calculate_tax_returns_dict(code):
    """calculate_tax must return a non-empty dict for a typical employee."""
    locale = importlib.import_module(code)
    ctx = _PROFILES[code]
    result = locale.calculate_tax(ctx, 2024)
    assert isinstance(result, dict), f"{code}: calculate_tax must return dict"
    assert result, f"{code}: calculate_tax returned empty dict"


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_calculate_tax_no_error_key(code):
    """calculate_tax must not return an 'error' key for valid input."""
    locale = importlib.import_module(code)
    ctx = _PROFILES[code]
    result = locale.calculate_tax(ctx, 2024)
    assert "error" not in result, (
        f"{code}: calculate_tax returned error: {result.get('error')}"
    )


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_exposes_get_tax_rules(code):
    """Every locale must expose get_tax_rules(year) returning a dict."""
    locale = importlib.import_module(code)
    fn = getattr(locale, "get_tax_rules", None)
    assert callable(fn), f"{code}: must expose get_tax_rules(year)"
    rules = fn(2024)
    assert isinstance(rules, dict), f"{code}: get_tax_rules must return dict"


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_exposes_get_filing_deadlines(code):
    """Every locale must expose get_filing_deadlines(year) returning a list."""
    locale = importlib.import_module(code)
    fn = getattr(locale, "get_filing_deadlines", None)
    assert callable(fn), f"{code}: must expose get_filing_deadlines(year)"
    deadlines = fn(2024)
    assert isinstance(deadlines, list), f"{code}: get_filing_deadlines must return list"
    assert len(deadlines) >= 1, f"{code}: get_filing_deadlines returned empty list"


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_exposes_generate_tax_claims(code):
    """Every locale must expose generate_tax_claims(ctx, year)."""
    locale = importlib.import_module(code)
    assert callable(getattr(locale, "generate_tax_claims", None)), (
        f"{code}: must expose generate_tax_claims(ctx, year)"
    )


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_exposes_get_social_contributions(code):
    """Every locale must expose get_social_contributions(gross, year)."""
    locale = importlib.import_module(code)
    fn = getattr(locale, "get_social_contributions", None)
    assert callable(fn), f"{code}: must expose get_social_contributions(gross, year)"
    result = fn(_GROSS[code], 2024)
    assert isinstance(result, dict), f"{code}: get_social_contributions must return dict"
    assert "error" not in result, (
        f"{code}: get_social_contributions error: {result.get('error')}"
    )


@pytest.mark.parametrize("code", ALL_LOCALES)
def test_locale_metadata_constants(code):
    """Each locale must define LOCALE_CODE, LOCALE_NAME, SUPPORTED_YEARS, and CURRENCY."""
    locale = importlib.import_module(code)
    assert hasattr(locale, "LOCALE_CODE"), f"{code}: missing LOCALE_CODE"
    assert hasattr(locale, "LOCALE_NAME"), f"{code}: missing LOCALE_NAME"
    assert hasattr(locale, "SUPPORTED_YEARS"), f"{code}: missing SUPPORTED_YEARS"
    assert hasattr(locale, "CURRENCY"), f"{code}: missing CURRENCY"
    assert locale.LOCALE_CODE == code, f"{code}: LOCALE_CODE mismatch"
    assert isinstance(locale.LOCALE_NAME, str) and locale.LOCALE_NAME, f"{code}: LOCALE_NAME must be non-empty str"
    assert isinstance(locale.SUPPORTED_YEARS, list) and locale.SUPPORTED_YEARS, f"{code}: SUPPORTED_YEARS must be non-empty list"
    assert isinstance(locale.CURRENCY, str) and locale.CURRENCY, f"{code}: CURRENCY must be non-empty str"
