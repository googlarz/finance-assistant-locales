# Finance Assistant Locales

> Country-specific locale plugins for Finance Assistant — tax rules, social contributions, filing deadlines, and deduction discovery.

Part of [Finance Assistant](https://github.com/googlarz/finance-assistant) — the personal finance copilot for Claude Code.

---

## Directory Structure

```
locales/
├── de/     # Germany — bundled, full 2024-2026 support
├── uk/     # United Kingdom — bundled, full 2024-2026 support
├── fr/     # France — bundled, full 2024-2026 support
├── nl/     # Netherlands — bundled, full 2024-2026 support
├── pl/     # Poland — bundled, full 2024-2026 support
├── at/     # Austria — not yet implemented
└── ch/     # Switzerland — not yet implemented
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

### United Kingdom (`uk`)

Full support for tax years 2024, 2025, and 2026. All parameters are filled — no `None` values for any supported year. All income tax thresholds are frozen at 2024/25 levels until April 2028 (Autumn Budget 2022). NI rates reflect the Spring Budget 2024 reductions effective 6 January 2024.

Tax year convention: `year=2024` → 2024/25 tax year (6 April 2024 – 5 April 2025).

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — personal allowance, rate bands, NI thresholds, ISA/pension allowances |
| `tax_calculator.py` | Income tax with personal allowance taper, NI (Class 1/Class 4), net pay, effective and marginal rates |
| `tax_dates.py` | Self Assessment filing deadlines (paper, online, payment on account), PAYE coding review |
| `social_contributions.py` | Class 1 NI employee (8%/2%) and employer (13.8%); Class 4 NI self-employed (6%/2%) |
| `claim_rules.py` | Deduction discovery: personal allowance, marriage allowance, pension relief, Gift Aid, ISA, WFH flat rate, professional subscriptions, mileage allowance, CGT exemption |

Key UK-specific areas covered:

- **Personal allowance taper** — £1 lost per £2 of income over £100,000; effective 60% marginal rate in the £100k–£125,140 band
- **Marriage allowance** — up to £1,260 transferable between spouses where lower earner is below basic rate threshold
- **NI (Class 1 employee)** — 8% on £12,570–£50,270, 2% above (reduced from 12% effective Jan 2024)
- **NI (Class 4 self-employed)** — 6% on £12,570–£50,270, 2% above (Class 2 abolished April 2024)
- **ISA allowance** — £20,000 annual, flagged if under-utilised
- **Pension annual allowance** — £60,000 (raised from £40,000 in April 2023)
- **Working from home** — HMRC flat rate £6/week (£312/year) for employees required to work from home
- **Gift Aid** — 25% uplift flagged; higher-rate reclaim via Self Assessment noted

Sources and verification dates for all parameters are tracked in `provenance.json`.

---

### France (`fr`)

Full support for tax years 2024, 2025, and 2026. All parameters are filled — no `None` values for any supported year. Tax year = calendar year. 2025 and 2026 parameters are estimated by indexation and marked `"Likely"`.

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — IR brackets, abattement forfaitaire, quotient familial parts and plafonnement, décote thresholds, CSG/CRDS rates, PASS |
| `tax_calculator.py` | IR (progressive brackets with quotient familial), abattement 10%, décote, prélèvements sociaux (CSG + CRDS = 9.7%), confidence |
| `tax_dates.py` | Online declaration openings, Zone 1/2/3 online deadlines, paper deadline, solde payment deadline, prélèvement à la source note |
| `social_contributions.py` | Assurance maladie, CNAV retraite de base, AGIRC-ARRCO retraite complémentaire (tranche 1 & 2), chômage, CSG, CRDS — employee and employer shares |
| `claim_rules.py` | Abattement forfaitaire 10%, frais réels, pension alimentaire, dons aux associations (66%/75%), emploi à domicile (50% credit), PER déductibility, micro-entrepreneur abattement and CA threshold alert, quotient familial note |

Key French-specific areas covered:

- **Quotient familial** — 1 part per adult, 0.5 per child for first two, 1 per child from third onwards; benefit capped at plafond du quotient familial per half-part
- **Abattement forfaitaire 10%** — automatic for salaried workers; can be replaced by frais réels if higher
- **Décote** — low-income tax reduction applied when IR falls below the ceiling (single ~€1,929; couple ~€3,191)
- **Prélèvement à la source** — monthly withholding throughout the year; spring declaration adjusts final balance
- **Micro-entrepreneur** — micro-BIC (50%) and micro-BNC (34%) abattements; CA threshold alerts
- **PER (Plan d'Épargne Retraite)** — contributions deductible up to 10% of income, capped at 8× PASS

Sources and verification dates for all parameters are tracked in `provenance.json`.

---

### Netherlands (`nl`)

Full support for tax years 2024, 2025, and 2026. All parameters are filled — no `None` values for any supported year. Tax year = calendar year. 2025 rates reflect the Belastingplan 2025 reduction of the first Box 1 bracket to 35.82%. 2026 parameters are estimated and marked `"Likely"`.

**Important:** Box 3 (savings and investments) is under ongoing legal challenge following the Kerstarrest (HR 24-12-2021). Box 3 results are returned with `"Debatable"` confidence when significant assets are present.

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — Box 1 rates and threshold, heffingskorting, arbeidskorting, Box 2 rates, Box 3 deemed returns and exemption, ZVW |
| `tax_calculator.py` | Box 1 tax with heffingskorting + arbeidskorting; Box 2 (DGA/BV) if flagged; Box 3 deemed-return tax; confidence scoring |
| `tax_dates.py` | Aangifte deadline (1 May), extension option (1 Sept), M-form deadline, voorlopige aanslag, Box 3 peildatum (1 Jan), payment deadline |
| `social_contributions.py` | Volksverzekeringen (AOW, ANW, WLZ) split out from Box 1 rate; ZVW employer contribution; WW and WAO/WIA employer premiums; embedded-in-Box-1 note |
| `claim_rules.py` | Heffingskorting, arbeidskorting, hypotheekrenteaftrek, alimentatie, zorgkosten, giftenaftrek, lijfrentepremies, Box 3 vrijstelling alert, 30%-regeling (expat ruling) |

Key Dutch-specific areas covered:

- **Three-box system** — Box 1 (work/home), Box 2 (substantial shareholding ≥5%), Box 3 (savings/investments)
- **Heffingskorting** — general tax credit; phases out above the taper threshold
- **Arbeidskorting** — employment credit; phases in then phases out; higher-income earners receive less
- **Volksverzekeringen embedded** — AOW (17.90%), ANW (0.10%), WLZ (9.65%) are included in the Box 1 first-bracket rate; not double-counted
- **Box 3 deemed return** — fixed rates on savings (1.44%) and other investments (6.04%); rate 36%; exemption €57,000 per person; marked `"Debatable"` due to Kerstarrest
- **Box 2** — DGA/BV owner substantial-shareholding income taxed at 24.5%/33%
- **30%-regeling** — expat ruling detected from profile; up to 30% of salary paid tax-free as ET cost reimbursement

Sources and verification dates for all parameters are tracked in `provenance.json`.

---

### Poland (`pl`)

Full support for tax years 2024, 2025, and 2026. All parameters are filled — no `None` values for any supported year. Tax year = calendar year. The **Polski Ład** reform (effective 1 January 2022) introduced the current 12%/32% bracket structure, a 30,000 PLN tax-free amount, and removed the health insurance deductibility from PIT. 2025 parameters (IKZE limit) are estimated by indexation and marked `"Likely"`. 2026 parameters are projected and calculations are marked `"Debatable"`.

| Module | Content |
|--------|---------|
| `tax_rules.py` | `TAX_YEAR_RULES` for 2024, 2025, 2026 — PIT brackets, tax-free amount (kwota wolna), work cost deductions, IKZE/ulga limits, ZUS rates, ZUS annual cap |
| `tax_calculator.py` | Polish PIT (skala podatkowa), ZUS employee contributions, health insurance (składka zdrowotna), ulga dla młodych exemption, joint-filing estimate, net pay |
| `tax_dates.py` | Twój e-PIT availability (Feb 15), PIT-37/36 deadline (Apr 30), PIT-11 / PIT-8C issuance dates, quarterly self-employed advance payment deadlines |
| `social_contributions.py` | Employee ZUS (emerytalne 9.76% + rentowe 1.5% + chorobowe 2.45% = 13.71%), employer ZUS (~20.48%), składka zdrowotna 9% (not deductible), ZUS annual cap |
| `claim_rules.py` | Deduction discovery: koszty uzyskania przychodu, ulga dla młodych, ulga na dzieci, IKZE, ulga internetowa, darowizny, ulga rehabilitacyjna, ulga na powrót, wspólne rozliczenie z małżonkiem |

Key Polish-specific areas covered:

- **12%/32% PIT brackets (Polski Ład)** — 30,000 PLN tax-free amount applied as a 3,600 PLN flat tax reduction; 32% rate on income above 120,000 PLN
- **Składka zdrowotna** — 9% health insurance on (gross − ZUS) is **not deductible** from PIT since Polski Ład 2022; calculator separates this clearly
- **Ulga dla młodych** — full PIT exemption for employees under 26 earning up to 85,528 PLN/year; applies automatically via Twój e-PIT
- **Twój e-PIT auto-acceptance** — pre-filled return available from February 15; auto-accepted on April 30 if not modified or rejected
- **IKZE deduction** — annual pension contributions deductible up to 9,388 PLN (2024); indexed each year (1.2× average salary)
- **Ulga na dzieci** — 1,112.04 PLN (child 1–2), 2,000.04 PLN (child 3), 2,700 PLN (child 4+); refundable if tax insufficient
- **Wspólne rozliczenie** — joint filing with spouse halves combined income; `calculate_tax` returns estimated saving when `spouse_gross` is provided
- **Self-employed flag** — działalność gospodarcza can choose skala podatkowa, 19% podatek liniowy, or ryczałt; calculator uses skala podatkowa and returns `"Likely"` confidence when `employment_type=self_employed`
- **ZUS annual cap** — pension and disability contributions capped at 30× average monthly salary (~234,720 PLN for 2024)

Sources and verification dates for all parameters are tracked in `provenance.json`.

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
