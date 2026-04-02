# Finance Assistant Locales

> Country-specific locale plugins for Finance Assistant — tax rules, social contributions, filing deadlines, and deduction discovery.

Part of [Finance Assistant](https://github.com/googlarz/finance-assistant-skill) — the personal finance copilot for Claude Code.

---

## Directory Structure

```
locales/
├── de/     # Germany — bundled, full 2024-2026 support
├── at/     # Austria — not yet implemented
├── ch/     # Switzerland — not yet implemented
├── fr/     # France — not yet implemented
└── nl/     # Netherlands — not yet implemented
```

Each locale lives in its own subdirectory named by ISO 3166-1 alpha-2 country code.

---

## Locale Plugin Interface

Every locale must implement the following in its `__init__.py`:

```python
LOCALE_CODE: str            # e.g. "de"
LOCALE_NAME: str            # e.g. "Germany"
SUPPORTED_YEARS: list[int]  # e.g. [2024, 2025, 2026]


def get_tax_rules(year: int) -> dict:
    """
    Return the raw tax parameters for the given year.

    Required keys (example — adapt to your country):
      grundfreibetrag   (int)   — tax-free allowance
      tax_brackets      (list)  — list of {rate, from, to} dicts
      soli_threshold    (int)   — solidarity surcharge exemption threshold
      ruerup_max_single (int)   — Rürup/equivalent pension ceiling (single)
      riester_max       (int)   — Riester/equivalent ceiling
      ... any other year-specific parameters

    All values for years in SUPPORTED_YEARS must be non-None.
    """


def calculate_tax(profile: dict, year: int) -> dict:
    """
    Calculate full tax liability for the given profile and year.

    Must return a dict with at least:
      gross           (float) — gross annual income used for calculation
      tax             (float) — income tax amount
      soli            (float) — solidarity surcharge (0.0 if not applicable)
      net             (float) — net income after tax and soli
      effective_rate  (float) — effective tax rate as a decimal (e.g. 0.22)
      marginal_rate   (float) — marginal rate on the last euro of income
      confidence      (str)   — one of: "Definitive", "Likely", "Debatable"

    Additional keys (e.g. kirchensteuer, refund_estimate) are welcome.
    """


def get_filing_deadlines(year: int) -> list[dict]:
    """
    Return all relevant tax filing deadlines for the given tax year.

    Each entry must be a dict with:
      label     (str)  — human-readable name, e.g. "Abgabefrist (ohne Berater)"
      deadline  (str)  — ISO 8601 date string, e.g. "2025-07-31"
      notes     (str)  — brief explanation or condition

    Include at least one deadline for the current filing year.
    """


def get_social_contributions(gross: float, year: int) -> dict:
    """
    Return social contribution breakdown for the given gross income and year.

    Each contribution type should be a dict with:
      rate            (float) — total rate as a decimal (employer + employee)
      employee_share  (float) — employee portion as a decimal
      annual_max      (float) — annual contribution ceiling in local currency
                                (use None if uncapped)

    Example keys: rentenversicherung, krankenversicherung,
                  pflegeversicherung, arbeitslosenversicherung
    """


def generate_tax_claims(profile: dict, year: int) -> list[dict]:
    """
    Discover applicable deduction claims for the given profile and year.

    Each claim must be a dict with:
      id               (str)   — stable identifier, e.g. "homeoffice_pauschale"
      title            (str)   — display name
      status           (str)   — one of: "ready", "needs_input",
                                  "needs_evidence", "detected"
      amount_estimate  (float) — estimated deduction amount (0.0 if unknown)
      confidence       (str)   — one of: "Definitive", "Likely", "Debatable"

    "ready" means the claim can be taken as-is from profile data.
    "needs_input" means one more fact is required from the user.
    "needs_evidence" means a receipt or document is required.
    "detected" means a background opportunity was identified, for awareness.
    """
```

---

## provenance.json Format

Every locale must include a `provenance.json` tracking the source and verification date of each rule. This makes it easy to spot outdated parameters when tax laws change.

```json
{
  "locale": "de",
  "last_reviewed": "2025-01-15",
  "rules": {
    "grundfreibetrag_2026": {
      "source_url": "https://www.bundesfinanzministerium.de/...",
      "verified_date": "2025-01-15",
      "confidence": "Definitive",
      "notes": "Published in Jahressteuergesetz 2024, §32a EStG"
    },
    "ruerup_max_single_2026": {
      "source_url": "https://www.deutsche-rentenversicherung.de/...",
      "verified_date": "2025-01-10",
      "confidence": "Likely",
      "notes": "Estimated from 2025 BBG progression (BBG 2026: €101,400)"
    },
    "soli_threshold_2026": {
      "source_url": "https://www.bundesfinanzministerium.de/...",
      "verified_date": "2025-01-15",
      "confidence": "Definitive",
      "notes": "Solidaritätszuschlaggesetz, §3 SolZG"
    }
  }
}
```

Each rule entry should have:
- `source_url` — link to the official government or fiscal authority source
- `verified_date` — ISO date when the rule was last checked against the source
- `confidence` — `"Definitive"`, `"Likely"`, or `"Debatable"`
- `notes` — brief human note (law reference, estimation method, caveat)

---

## Adding a New Locale

1. **Create the directory** for your country code:
   ```bash
   mkdir locales/fr
   ```

2. **Copy the `__init__.py` template** from an existing locale as a starting point:
   ```bash
   cp locales/de/__init__.py locales/fr/__init__.py
   ```
   Alternatively, use `locale_loader.py` in the main skill to scaffold a skeleton automatically:
   ```python
   from scripts.locale_loader import build_locale_on_demand
   build_locale_on_demand("fr")  # creates locales/fr/ skeleton
   ```

3. **Implement all 5 interface functions** for your country's rules. Fill in at least the current year and the next year — no `None` values for years listed in `SUPPORTED_YEARS`.

4. **Add a `provenance.json`** with source URLs and verification dates for every rule you implement.

5. **Write tests** in a file named `tests/test_locale_<country_code>.py`. See the Testing section below for what must pass.

6. **Open a PR** to this repository. See the Contributing section for what a good PR includes.

---

## Bundled Locales

### Germany (`de`)

Full support for tax years 2024, 2025, and 2026. All parameters are filled — no `None` values for any supported year.

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — brackets, Grundfreibetrag, Soli threshold, Rürup/Riester ceilings |
| `tax_calculator.py` | Einkommensteuer (progressive formula), Soli, Kirchensteuer, estimated refund |
| `tax_dates.py` | Filing deadlines, ELSTER advised submission windows by Steuerklasse |
| `social_contributions.py` | Rentenversicherung, Krankenversicherung, Pflegeversicherung, Arbeitslosenversicherung caps 2024-2026 |
| `claim_rules.py` | Deduction discovery: Werbungskosten, Sonderausgaben, Außergewöhnliche Belastungen, Homeoffice, Pendlerpauschale, Kinderfreibetrag |
| `insurance_rules.py` | GKV/PKV thresholds (Versicherungspflichtgrenze) by year |
| `rule_updater.py` | Tax rule provenance tracking and freshness checks |

Key German-specific areas covered:

- **Steuerklassen I–VI** — all tax classes, including married couples (III/V) and single parents
- **Ehegattensplitting** — joint assessment with income splitting for married couples
- **Homeoffice-Pauschale** — €6/day flat deduction, capped at 210 days (2024-2026)
- **Pendlerpauschale** — commuter deduction (€0.30 up to 20 km, €0.38 beyond)
- **Riester / Rürup** — contribution ceilings and deductibility rules per year
- **GKV / PKV thresholds** — Versicherungspflichtgrenze and Beitragsbemessungsgrenze
- **Vorabpauschale awareness** — ETF prepayment tax flag in investment tax context

Sources and verification dates for all 2026 parameters are tracked in `provenance.json`.

---

## Testing

New locales must pass the following tests before merging:

1. **Basic tax calculation for a salaried employee** — given a typical gross income, `calculate_tax()` returns a dict with all required keys and `net < gross`.
2. **Social contributions sum check** — the sum of employee contributions does not exceed gross income, and no individual rate exceeds 1.0.
3. **At least one deduction claim** — `generate_tax_claims()` returns at least one claim with status `"ready"` or `"needs_input"` for a standard employed profile.
4. **Filing deadline present for current year** — `get_filing_deadlines()` returns at least one entry with a deadline date in the current or next calendar year.

Run the locale test suite:

```bash
pytest tests/test_locale_<country_code>.py -v
```

To run all locale tests together:

```bash
pytest tests/ -k "locale" -v
```

---

## Contributing

PRs for new locales are very welcome — each new locale makes Finance Assistant useful for more people.

A good PR includes:

- **Source URLs** for every tax rule — official government sources or the country's fiscal authority (e.g. Bundeszentralamt für Steuern for Germany, HMRC for the UK, Direction Générale des Finances Publiques for France)
- **`provenance.json`** with `source_url`, `verified_date`, `confidence`, and `notes` for each rule
- **Tests** covering at minimum: basic tax calculation, social contributions sum check, at least one deduction claim, and at least one filing deadline for the current year
- **No `None` values** in any parameter for years listed in `SUPPORTED_YEARS` — if a value is estimated, note the estimation method in `provenance.json` and set `confidence` to `"Likely"` or `"Debatable"` accordingly
- A brief note in the PR description about what tax years are covered and any known limitations or assumptions

If you are starting from scratch and find the interface unclear, open an issue — the interface is designed to be extended and feedback from implementers helps improve it.
