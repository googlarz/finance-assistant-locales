"""
LocaleContext — the normalized input contract for all locale plugins.

Instead of passing the Finance Assistant's raw profile dict (which callers
have to reverse-engineer), locale functions accept a LocaleContext.

Standalone usage:
    ctx = LocaleContext(
        tax_year=2025,
        annual_gross=65000,
        tax_class="I",
        homeoffice_days_per_week=3,
    )
    from de import calculate_tax
    result = calculate_tax(ctx)

Finance Assistant usage (automatic conversion):
    ctx = LocaleContext.from_finance_profile(profile, year=2025)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChildInfo:
    birth_year: int
    childcare: bool = False
    childcare_annual_cost: float = 0.0


@dataclass
class ReceiptItem:
    """A single deductible expense."""
    category: str        # equipment, fortbildung, donation, steuerberatung, handwerker, medical, etc.
    amount: float
    business_use_pct: float = 100.0
    description: str = ""
    deductible_amount: Optional[float] = None  # override if pre-calculated


@dataclass
class LocaleContext:
    """Normalized input for locale tax calculations. All fields have sensible defaults."""

    tax_year: int

    # ── Employment ────────────────────────────────────────────────────────
    employment_type: str = "employed"   # employed | freelancer | self_employed | retired
    annual_gross: float = 0.0
    side_income: float = 0.0

    # ── Tax profile ───────────────────────────────────────────────────────
    tax_class: str = "I"                # German Steuerklasse: I II III IV V VI
    church_tax: bool = False
    region: str = ""                    # Bundesland — affects Kirchensteuer rate

    # ── Family ────────────────────────────────────────────────────────────
    married: bool = False
    children: list[ChildInfo] = field(default_factory=list)

    # ── Housing / work location ───────────────────────────────────────────
    homeoffice_days_per_week: Optional[float] = None
    commute_km: float = 0.0
    commute_days_per_year: int = 0

    # ── Retirement / savings contributions ───────────────────────────────
    riester: bool = False
    riester_contribution: float = 0.0
    ruerup: bool = False
    ruerup_contribution: float = 0.0
    bav: bool = False
    bav_contribution: float = 0.0

    # ── Other deductions ─────────────────────────────────────────────────
    union_dues: float = 0.0
    disability_grade: int = 0           # GdB 0-100

    # ── Expense receipts ─────────────────────────────────────────────────
    receipts: list[ReceiptItem] = field(default_factory=list)

    # ── Misc ──────────────────────────────────────────────────────────────
    expat: bool = False
    dba_relevant: bool = False          # Double-taxation treaty relevant

    # ── Extra (locale-specific overflow) ─────────────────────────────────
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_finance_profile(cls, profile: dict, tax_year: Optional[int] = None) -> "LocaleContext":
        """
        Convert a Finance Assistant profile dict to LocaleContext.
        This is the bridge used by the main skill — standalone callers
        should construct LocaleContext directly.
        """
        meta = profile.get("meta", {})
        emp = profile.get("employment", {})
        fam = profile.get("family", {})
        housing = profile.get("housing", {})
        personal = profile.get("personal", {})
        tax_extra = profile.get("tax_profile", {}).get("extra", {})

        year = tax_year or meta.get("tax_year", 2025)

        children = []
        for ch in fam.get("children", []):
            children.append(ChildInfo(
                birth_year=ch.get("birth_year", 2010),
                childcare=bool(ch.get("childcare") or ch.get("kita")),
                childcare_annual_cost=float(
                    ch.get("childcare_annual_cost") or ch.get("kita_annual_cost") or 0.0
                ),
            ))

        raw_receipts = profile.get("current_year_receipts", [])
        receipts = []
        for r in raw_receipts:
            receipts.append(ReceiptItem(
                category=r.get("category", "other"),
                amount=float(r.get("amount", 0.0) or 0.0),
                business_use_pct=float(r.get("business_use_pct", 100.0) or 100.0),
                description=r.get("description", ""),
                deductible_amount=r.get("deductible_amount"),
            ))

        return cls(
            tax_year=year,
            employment_type=emp.get("type", "employed"),
            annual_gross=float(emp.get("annual_gross") or 0.0),
            side_income=float(emp.get("side_income") or 0.0),
            tax_class=str(profile.get("tax_profile", {}).get("tax_class") or "I"),
            church_tax=bool(profile.get("tax_profile", {}).get("church_tax", False)),
            region=personal.get("region", ""),
            married=fam.get("status") in ("married", "civil_partnership"),
            children=children,
            homeoffice_days_per_week=housing.get("homeoffice_days_per_week"),
            commute_km=float(housing.get("commute_km") or 0.0),
            commute_days_per_year=int(housing.get("commute_days_per_year") or 0),
            riester=bool(tax_extra.get("riester", False)),
            riester_contribution=float(tax_extra.get("riester_contribution") or 0.0),
            ruerup=bool(tax_extra.get("ruerup", False)),
            ruerup_contribution=float(tax_extra.get("ruerup_contribution") or 0.0),
            bav=bool(tax_extra.get("bav", False)),
            bav_contribution=float(tax_extra.get("bav_contribution") or 0.0),
            union_dues=float(tax_extra.get("gewerkschaft_beitrag") or 0.0),
            disability_grade=int(tax_extra.get("disability_grade") or 0),
            receipts=receipts,
            expat=bool(tax_extra.get("expat", False)),
            dba_relevant=bool(tax_extra.get("dba_relevant", False)),
            extra=tax_extra,
        )
