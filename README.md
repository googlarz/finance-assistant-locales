# Finance Assistant Locales

Country-specific locale plugins for [Finance Assistant](https://github.com/googlarz/finance-assistant-skill) — tax rules, social contributions, filing deadlines, and deduction logic.

## Structure

Each locale lives in its own subdirectory named by ISO 3166-1 alpha-2 country code:

```
locales/
├── de/     # Germany — bundled, full 2024-2026 support
├── at/     # Austria — not yet implemented
├── ch/     # Switzerland — not yet implemented
└── ...
```

## Locale Plugin Interface

Every locale must export the following from its `__init__.py`:

```python
LOCALE_CODE: str          # e.g. "de"
LOCALE_NAME: str          # e.g. "Germany"
SUPPORTED_YEARS: list[int]  # e.g. [2024, 2025, 2026]

def get_tax_rules(year: int) -> dict
def calculate_tax(profile: dict, year: int) -> dict
def get_filing_deadlines(year: int) -> list[dict]
def get_social_contributions(gross: float, year: int) -> dict
def generate_tax_claims(profile: dict, year: int) -> list[dict]
```

## Adding a New Locale

1. Create a new directory: `mkdir <country_code>/`
2. Copy `de/__init__.py` as a starting template
3. Implement all 5 interface functions for your country's rules
4. Add `SUPPORTED_YEARS` for the years your rules cover
5. Test with `pytest tests/test_locale_<country_code>.py`
6. Open a PR

Alternatively, use `locale_loader.py` in the main skill to scaffold a skeleton automatically:

```python
from scripts.locale_loader import build_locale_on_demand
build_locale_on_demand("at")  # creates locales/at/ skeleton
```

## Bundled Locales

### 🇩🇪 Germany (`de`)

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — brackets, Grundfreibetrag, Soli threshold, Rürup/Riester ceilings |
| `tax_calculator.py` | Einkommensteuer (progressive formula), Soli, Kirchensteuer, estimated refund |
| `tax_dates.py` | Filing deadlines, ELSTER advised submission windows by Steuerklasse |
| `social_contributions.py` | Rentenversicherung, Krankenversicherung, Pflegeversicherung, Arbeitslosenversicherung caps 2024-2026 |
| `claim_rules.py` | Deduction discovery: Werbungskosten, Sonderausgaben, Außergewöhnliche Belastungen, Homeoffice, Pendlerpauschale, Kinderfreibetrag |

All 2026 parameters are filled (no `None` values). Sources and verification dates are tracked in `provenance.json`.

## Contributing

PRs for new locales are welcome. Please include:
- Source URLs for every tax rule (official government or fiscal authority)
- A `provenance.json` with rule sources and verification dates
- Tests covering at least: basic tax calculation, social contributions, one deduction claim
