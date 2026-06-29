"""Shared pytest fixtures for AUCTUS platform test suite."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest
import yaml

if TYPE_CHECKING:
    from scripts.lbo_engine import EntryAssumptions, SourcesUses, YearProjection


@pytest.fixture
def sample_historicals() -> pd.DataFrame:
    """5-year P&L for fictional 'Muster GmbH' — known DCF inputs."""
    return pd.DataFrame({
        "year": [2020, 2021, 2022, 2023, 2024],
        "revenue": [30.0, 33.0, 36.5, 40.0, 44.0],    # EUR millions
        "ebitda": [4.5, 5.0, 5.8, 6.5, 7.0],
        "d_and_a": [0.8, 0.9, 1.0, 1.1, 1.2],
        "capex": [1.2, 1.3, 1.5, 1.6, 1.8],
        "nwc_change": [0.3, 0.4, 0.4, 0.5, 0.5],
        "tax_rate": [0.29, 0.29, 0.29, 0.29, 0.29],
    })


@pytest.fixture
def sample_projections() -> pd.DataFrame:
    """5-year approved projections for Muster GmbH."""
    return pd.DataFrame({
        "year": [2025, 2026, 2027, 2028, 2029],
        "revenue": [47.5, 51.0, 54.6, 57.8, 60.7],
        "ebitda": [7.6, 8.2, 8.7, 9.2, 9.7],
        "d_and_a": [1.3, 1.4, 1.5, 1.6, 1.7],
        "capex": [1.9, 2.0, 2.2, 2.3, 2.4],
        "nwc_change": [0.5, 0.5, 0.5, 0.5, 0.5],
        "tax_rate": [0.29, 0.29, 0.29, 0.29, 0.29],
    })


@pytest.fixture
def sample_peers() -> pd.DataFrame:
    """5-company public comparable peer group with known multiples."""
    return pd.DataFrame({
        "name": ["Alpha AG", "Beta GmbH", "Gamma SE", "Delta NV", "Epsilon SA"],
        "ticker": ["ALPH.DE", "BETA.DE", "GAMM.DE", "DELT.NL", "EPSI.FR"],
        "sector": ["hvac_services"] * 5,
        "ev_eur_m": [120.0, 85.0, 200.0, 150.0, 95.0],
        "ebitda_ltm_eur_m": [15.0, 10.0, 25.0, 18.0, 12.0],
        "revenue_ltm_eur_m": [80.0, 55.0, 140.0, 100.0, 65.0],
    })


@pytest.fixture
def sample_candidates() -> pd.DataFrame:
    """10-company candidate universe for competitor analysis tests."""
    return pd.DataFrame({
        "company": [
            "MusterService GmbH", "Kleinanlage AG", "Großtechnik GmbH",
            "HVAC Plus OG", "Facility Pro GmbH", "OutOfRange Corp",
            "Family Wärme GmbH", "Listed Energy AG", "Regionalheizung GmbH",
            "Schweizer Klima AG",
        ],
        "geography": ["DE", "AT", "DE", "CH", "DE", "US", "AT", "DE", "DE", "CH"],
        "revenue_eur_m": [25.0, 15.0, 200.0, 30.0, 45.0, 50.0, 20.0, 80.0, 12.0, 35.0],
        "ebitda_margin_pct": [0.14, 0.10, 0.12, 0.18, 0.09, 0.15, 0.20, 0.11, 0.10, 0.16],
        "ownership": [
            "founder", "family", "pe", "founder", "management_buyout",
            "listed", "family", "listed", "founder", "family",
        ],
        "sector": ["hvac_services"] * 10,
        "customer_concentration_top1_pct": [0.15, 0.20, 0.10, 0.08, 0.25, 0.30, 0.12, 0.35, 0.18, 0.10],
    })


@pytest.fixture
def auctus_criteria() -> dict:
    """Load the actual AUCTUS criteria YAML for integration tests."""
    path = Path("config/auctus_criteria.yaml")
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    # Fallback inline criteria if config not found
    return {
        "hard_filters": {
            "revenue_min_eur": 10_000_000,
            "revenue_max_eur": 150_000_000,
            "ebitda_margin_min": 0.08,
            "customer_concentration_max_single": 0.30,
            "geographies_allowed": ["DE", "AT", "CH", "NL", "BE", "FR", "IT", "SE", "DK", "NO"],
            "excluded_sectors": ["financial_services", "real_estate", "oil_gas"],
        },
        "scoring_weights": {
            "revenue_in_sweet_spot": 0.15,
            "founder_owned": 0.20,
            "fragmented_market": 0.20,
            "recurring_revenue_pct": 0.15,
            "ebitda_margin": 0.15,
            "geographic_concentration_dach": 0.10,
            "low_customer_concentration": 0.05,
        },
        "recommendation_bands": {
            "strong_buy": {"min_score": 80, "label": "Priority Target"},
            "buy": {"min_score": 60, "label": "Active Coverage"},
            "watch": {"min_score": 40, "label": "Monitor"},
            "pass": {"min_score": 0, "label": "Pass"},
        },
    }


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for test output artifacts."""
    (tmp_path / "dcf_models").mkdir()
    (tmp_path / "target_matrices").mkdir()
    (tmp_path / "valuation_reports").mkdir()
    return tmp_path


# ── LBO Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def lbo_assumptions() -> "EntryAssumptions":
    """Canonical AUCTUS test case: Muster GmbH HVAC platform, 8.0× entry, 45% equity."""
    from scripts.lbo_engine import EntryAssumptions
    return EntryAssumptions(
        company_name="Muster GmbH",
        geography="DE",
        entry_ebitda_eur_m=8.5,
        entry_multiple=8.0,
        equity_pct=0.45,
        senior_debt_pct=0.40,
        notes_pct=0.15,
        euribor_rate=0.039,
        euribor_floor=0.00,
        senior_spread_bps=375,
        notes_is_fixed=True,
        notes_fixed_rate=0.095,
        notes_euribor_spread_bps=550,
        senior_amort_pct_annual=0.05,
        senior_cash_sweep_pct=0.50,
        advisor_fee_pct_ev=0.015,
        financing_fee_pct_debt=0.020,
        fees_capitalized=True,
        tax_rate=0.299,
        projection_years=5,
        revenue_base_eur_m=50.0,
        revenue_growth_rates=[0.07, 0.07, 0.06, 0.06, 0.05],
        ebitda_margins=[0.175, 0.180, 0.185, 0.190, 0.195],
        da_pct_revenue=0.025,
        capex_pct_revenue=0.035,
        nwc_pct_revenue_change=0.08,
        exit_year=5,
        exit_multiple=9.0,
    )


@pytest.fixture
def lbo_sources_uses(lbo_assumptions: "EntryAssumptions") -> "SourcesUses":
    from scripts.lbo_engine import build_sources_uses
    return build_sources_uses(lbo_assumptions)


@pytest.fixture
def lbo_projections(
    lbo_assumptions: "EntryAssumptions",
    lbo_sources_uses: "SourcesUses",
) -> "list[YearProjection]":
    from scripts.lbo_engine import compute_projections
    return compute_projections(lbo_assumptions, lbo_sources_uses)


