"""Unit and integration tests for scripts/lbo_engine.py"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scripts.lbo_engine import (
    EntryAssumptions,
    LBOMetrics,
    LBOResult,
    SourcesUses,
    YearProjection,
    _compute_irr,
    _notes_rate,
    _senior_rate,
    build_sensitivity_grid,
    build_sources_uses,
    compute_exit_metrics,
    compute_projections,
    run_lbo,
)

if TYPE_CHECKING:
    pass


# ── Sources & Uses ─────────────────────────────────────────────────────────────

class TestSourcesUses:
    def test_entry_ev_formula(self, lbo_assumptions: EntryAssumptions) -> None:
        """Entry EV = entry_ebitda × entry_multiple."""
        su = build_sources_uses(lbo_assumptions)
        expected_ev = lbo_assumptions.entry_ebitda_eur_m * lbo_assumptions.entry_multiple
        assert abs(su.entry_ev_eur_m - expected_ev) < 1e-4

    def test_capital_structure_splits(self, lbo_assumptions: EntryAssumptions) -> None:
        """Sources (equity + debt) must equal Uses (EV + all closing-statement fees)."""
        su = build_sources_uses(lbo_assumptions)
        total = su.equity_eur_m + su.senior_debt_eur_m + su.notes_eur_m
        assert abs(total - su.total_uses_eur_m) < 1e-4

    def test_sources_balance_with_capitalised_fees(self, lbo_assumptions: EntryAssumptions) -> None:
        """S&U must always balance: equity is the residual that absorbs all fees in Uses."""
        su = build_sources_uses(lbo_assumptions)
        assert abs(su.balance_eur_m) < 0.01, (
            f"S&U imbalance of €{su.balance_eur_m:.4f}m — equity residual logic broken"
        )

    def test_fee_amort_positive_when_capitalised(self, lbo_assumptions: EntryAssumptions) -> None:
        su = build_sources_uses(lbo_assumptions)
        assert su.fee_amort_annual_eur_m > 0

    def test_no_fee_amort_when_expensed(self, lbo_assumptions: EntryAssumptions) -> None:
        tweaked = EntryAssumptions(
            **{**lbo_assumptions.model_dump(), "fees_capitalized": False}
        )
        su = build_sources_uses(tweaked)
        assert su.fee_amort_annual_eur_m == 0.0

    def test_advisor_fee_magnitude(self, lbo_assumptions: EntryAssumptions) -> None:
        """Advisor fee = advisor_fee_pct_ev × entry EV."""
        su = build_sources_uses(lbo_assumptions)
        expected = su.entry_ev_eur_m * lbo_assumptions.advisor_fee_pct_ev
        assert abs(su.advisor_fees_eur_m - expected) < 1e-6

    def test_zero_notes(self, lbo_assumptions: EntryAssumptions) -> None:
        """All-senior structure: notes tranche is zero."""
        tweaked = EntryAssumptions(
            **{
                **lbo_assumptions.model_dump(),
                "equity_pct": 0.45,
                "senior_debt_pct": 0.55,
                "notes_pct": 0.00,
            }
        )
        su = build_sources_uses(tweaked)
        assert su.notes_eur_m == 0.0


# ── Floating-Rate Mechanics ───────────────────────────────────────────────────

class TestFloatingRate:
    def test_senior_rate_above_floor(self, lbo_assumptions: EntryAssumptions) -> None:
        """Effective rate = max(euribor, floor) + spread."""
        rate = _senior_rate(lbo_assumptions)
        expected = (
            max(lbo_assumptions.euribor_rate, lbo_assumptions.euribor_floor)
            + lbo_assumptions.senior_spread_bps / 10_000.0
        )
        assert abs(rate - expected) < 1e-8

    def test_floor_binds_when_euribor_negative(self, lbo_assumptions: EntryAssumptions) -> None:
        """When Euribor < floor, floor is used."""
        tweaked = EntryAssumptions(
            **{**lbo_assumptions.model_dump(), "euribor_rate": -0.005, "euribor_floor": 0.0}
        )
        rate = _senior_rate(tweaked)
        expected = 0.0 + tweaked.senior_spread_bps / 10_000.0
        assert abs(rate - expected) < 1e-8

    def test_fixed_notes_rate(self, lbo_assumptions: EntryAssumptions) -> None:
        assert lbo_assumptions.notes_is_fixed
        assert abs(_notes_rate(lbo_assumptions) - lbo_assumptions.notes_fixed_rate) < 1e-8

    def test_floating_notes_rate(self, lbo_assumptions: EntryAssumptions) -> None:
        tweaked = EntryAssumptions(
            **{
                **lbo_assumptions.model_dump(),
                "notes_is_fixed": False,
                "notes_euribor_spread_bps": 550,
            }
        )
        rate = _notes_rate(tweaked)
        expected = max(tweaked.euribor_rate, tweaked.euribor_floor) + 550 / 10_000.0
        assert abs(rate - expected) < 1e-8


# ── P&L Projections ───────────────────────────────────────────────────────────

class TestProjections:
    def test_projection_count(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """One YearProjection per projection_years."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        assert len(projs) == lbo_assumptions.projection_years

    def test_revenue_compounds_correctly(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """Year-1 revenue = base × (1 + growth[0])."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        expected_yr1_rev = lbo_assumptions.revenue_base_eur_m * (1.0 + lbo_assumptions.revenue_growth_rates[0])
        assert abs(projs[0].revenue_eur_m - expected_yr1_rev) < 1e-4

    def test_ebitda_margin_applied(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """EBITDA = Revenue × margin for each year."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for i, p in enumerate(projs):
            expected = p.revenue_eur_m * lbo_assumptions.ebitda_margins[i]
            assert abs(p.ebitda_eur_m - expected) < 1e-4, f"Year {i+1} EBITDA mismatch"

    def test_ebit_equals_ebitda_minus_da(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            assert abs(p.ebit_eur_m - (p.ebitda_eur_m - p.da_eur_m)) < 1e-5, (
                f"Year {p.year}: EBIT ≠ EBITDA − D&A"
            )

    def test_senior_balance_declines(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """Senior debt must decrease or stay flat each year (mandatory amort + sweep)."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            assert p.senior_closing_eur_m <= p.senior_opening_eur_m + 1e-6, (
                f"Year {p.year}: senior balance increased — waterfall logic error"
            )

    def test_senior_balance_non_negative(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            assert p.senior_closing_eur_m >= -1e-6, (
                f"Year {p.year}: senior balance went negative ({p.senior_closing_eur_m})"
            )

    def test_notes_balance_constant(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """Notes are bullet — no amortisation, balance stays flat."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            assert abs(p.notes_closing_eur_m - p.notes_opening_eur_m) < 1e-6

    def test_net_income_derivation(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """Net income = EBT − tax; tax ≥ 0."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            assert p.tax_eur_m >= -1e-6
            assert abs(p.net_income_eur_m - (p.ebt_eur_m - p.tax_eur_m)) < 1e-5

    def test_interest_coverage_computed(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for p in projs:
            if p.total_interest_eur_m > 0:
                expected = p.ebit_eur_m / p.total_interest_eur_m
                assert abs(p.interest_coverage_x - expected) < 1e-3

    def test_senior_opening_equals_prior_closing(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        """Debt schedule must be self-consistent: opening[t] == closing[t-1]."""
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        for i in range(1, len(projs)):
            assert abs(projs[i].senior_opening_eur_m - projs[i - 1].senior_closing_eur_m) < 1e-6, (
                f"Year {projs[i].year}: opening ≠ prior closing"
            )

    def test_fee_amort_in_year1_when_capitalised(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
    ) -> None:
        projs = compute_projections(lbo_assumptions, lbo_sources_uses)
        assert projs[0].fee_amort_eur_m > 0

    def test_year1_fee_expense_when_not_capitalised(self, lbo_assumptions: EntryAssumptions) -> None:
        tweaked = EntryAssumptions(
            **{**lbo_assumptions.model_dump(), "fees_capitalized": False}
        )
        su = build_sources_uses(tweaked)
        projs = compute_projections(tweaked, su)
        # Year 1 should have financing fees hit P&L
        assert projs[0].fee_amort_eur_m > 0
        # Year 2+ should have zero non-cash amort
        assert projs[1].fee_amort_eur_m == 0.0


# ── IRR Solver ────────────────────────────────────────────────────────────────

class TestIRRSolver:
    def test_known_irr_simple(self) -> None:
        """MOIC 2× over 5 years → IRR ≈ 14.87%."""
        cash_flows = [-100.0, 0.0, 0.0, 0.0, 0.0, 200.0]
        irr, converged = _compute_irr(cash_flows)
        expected = 2.0 ** (1 / 5) - 1  # ≈ 14.87%
        assert converged
        assert abs(irr - expected) < 1e-5

    def test_irr_moic_1x_is_zero(self) -> None:
        """If equity proceeds equal equity invested, IRR = 0."""
        cash_flows = [-50.0, 0.0, 0.0, 0.0, 0.0, 50.0]
        irr, converged = _compute_irr(cash_flows)
        assert converged
        assert abs(irr) < 1e-5

    def test_irr_increases_with_higher_exit(self) -> None:
        """Higher exit proceeds → higher IRR, all else equal."""
        cf_low = [-100.0, 0.0, 0.0, 0.0, 0.0, 150.0]
        cf_high = [-100.0, 0.0, 0.0, 0.0, 0.0, 250.0]
        irr_low, _ = _compute_irr(cf_low)
        irr_high, _ = _compute_irr(cf_high)
        assert irr_high > irr_low

    def test_irr_negative_for_loss(self) -> None:
        """When exit proceeds < equity invested, IRR < 0."""
        cash_flows = [-100.0, 0.0, 0.0, 0.0, 0.0, 60.0]
        irr, converged = _compute_irr(cash_flows)
        assert converged
        assert irr < 0


# ── Exit Metrics ──────────────────────────────────────────────────────────────

class TestExitMetrics:
    def test_exit_ev_formula(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        """Exit EV = exit-year EBITDA × exit_multiple."""
        metrics = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        exit_ebitda = lbo_projections[lbo_assumptions.exit_year - 1].ebitda_eur_m
        expected_ev = exit_ebitda * lbo_assumptions.exit_multiple
        assert abs(metrics.exit_ev_eur_m - expected_ev) < 1e-4

    def test_equity_proceeds_formula(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        """Equity proceeds = exit EV − net debt at exit."""
        metrics = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        expected = metrics.exit_ev_eur_m - metrics.net_debt_at_exit_eur_m
        assert abs(metrics.equity_proceeds_eur_m - expected) < 1e-4

    def test_moic_positive_for_healthy_deal(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        metrics = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        assert metrics.moic > 1.0, "Healthy HVAC deal at 8×/9× should return > 1× MOIC"

    def test_irr_positive_for_healthy_deal(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        metrics = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        assert metrics.irr_solver_converged
        assert math.isfinite(metrics.irr)
        assert metrics.irr > 0

    def test_irr_moic_consistency(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        """Higher MOIC (same hold period) must correspond to higher IRR."""
        metrics_base = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        higher_exit = EntryAssumptions(
            **{**lbo_assumptions.model_dump(), "exit_multiple": lbo_assumptions.exit_multiple + 2.0}
        )
        projs_higher = compute_projections(higher_exit, lbo_sources_uses)
        metrics_higher = compute_exit_metrics(higher_exit, lbo_sources_uses, projs_higher)
        assert metrics_higher.moic > metrics_base.moic
        assert metrics_higher.irr > metrics_base.irr

    def test_leverage_decreases_over_hold(
        self,
        lbo_assumptions: EntryAssumptions,
        lbo_sources_uses: SourcesUses,
        lbo_projections: list[YearProjection],
    ) -> None:
        """Leverage at exit must be lower than at entry (debt paid down, EBITDA grows)."""
        metrics = compute_exit_metrics(lbo_assumptions, lbo_sources_uses, lbo_projections)
        assert metrics.leverage_at_exit_x < metrics.leverage_at_entry_x, (
            "Leverage should decline over the hold period"
        )


# ── Sensitivity Grid ──────────────────────────────────────────────────────────

class TestSensitivityGrid:
    def test_grid_dimensions(self, lbo_assumptions: EntryAssumptions) -> None:
        """Default 5×5 grid: 5 entry multiples × 5 exit multiples."""
        irr_grid, moic_grid = build_sensitivity_grid(lbo_assumptions)
        assert len(irr_grid) == 5
        for row in irr_grid.values():
            assert len(row) == 5

    def test_base_case_in_grid(self, lbo_assumptions: EntryAssumptions) -> None:
        """Base-case cell (entry_multiple, exit_multiple) must exist in grid."""
        irr_grid, _ = build_sensitivity_grid(lbo_assumptions)
        base_entry_key = f"{lbo_assumptions.entry_multiple:.1f}x"
        base_exit_key = f"{lbo_assumptions.exit_multiple:.1f}x"
        assert base_entry_key in irr_grid
        assert base_exit_key in irr_grid[base_entry_key]

    def test_higher_exit_multiple_raises_irr(self, lbo_assumptions: EntryAssumptions) -> None:
        """Within a fixed entry row, IRR must increase as exit multiple increases."""
        irr_grid, _ = build_sensitivity_grid(lbo_assumptions)
        base_entry_key = f"{lbo_assumptions.entry_multiple:.1f}x"
        exit_irrs = list(irr_grid[base_entry_key].values())
        finite_irrs = [v for v in exit_irrs if math.isfinite(v)]
        assert finite_irrs == sorted(finite_irrs), (
            "IRR must monotonically increase with exit multiple (fixed entry)"
        )

    def test_lower_entry_multiple_raises_irr(self, lbo_assumptions: EntryAssumptions) -> None:
        """Within a fixed exit column, IRR must increase as entry multiple decreases."""
        irr_grid, _ = build_sensitivity_grid(lbo_assumptions)
        base_exit_key = f"{lbo_assumptions.exit_multiple:.1f}x"
        entry_keys = sorted(irr_grid.keys(), key=lambda k: float(k[:-1]))
        col_irrs = [irr_grid[ek][base_exit_key] for ek in entry_keys]
        finite_irrs = [v for v in col_irrs if math.isfinite(v)]
        assert finite_irrs == sorted(finite_irrs, reverse=True), (
            "IRR must decrease as entry multiple increases (buy cheaper = higher IRR)"
        )

    def test_no_nan_in_healthy_grid(self, lbo_assumptions: EntryAssumptions) -> None:
        """For a well-structured deal, the central 3×3 cells must be finite."""
        irr_grid, moic_grid = build_sensitivity_grid(lbo_assumptions)
        entry_keys = sorted(irr_grid.keys(), key=lambda k: float(k[:-1]))
        exit_keys = sorted(next(iter(irr_grid.values())).keys(), key=lambda k: float(k[:-1]))
        central_entries = entry_keys[1:-1]
        central_exits = exit_keys[1:-1]
        for ek in central_entries:
            for xk in central_exits:
                val = irr_grid[ek][xk]
                assert math.isfinite(val), (
                    f"NaN in sensitivity grid cell ({ek}, {xk}) — computation error"
                )


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidation:
    def test_capital_structure_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            EntryAssumptions(
                company_name="Bad Co",
                geography="DE",
                entry_ebitda_eur_m=8.5,
                entry_multiple=8.0,
                equity_pct=0.50,
                senior_debt_pct=0.40,
                notes_pct=0.20,  # 0.50+0.40+0.20 = 1.10
                euribor_rate=0.039,
                euribor_floor=0.0,
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
                ebitda_margins=[0.175, 0.18, 0.185, 0.19, 0.195],
                da_pct_revenue=0.025,
                capex_pct_revenue=0.035,
                nwc_pct_revenue_change=0.08,
                exit_year=5,
                exit_multiple=9.0,
            )

    def test_exit_year_cannot_exceed_projection_years(self) -> None:
        with pytest.raises(ValueError, match="exit_year"):
            EntryAssumptions(
                company_name="Bad Co",
                geography="DE",
                entry_ebitda_eur_m=8.5,
                entry_multiple=8.0,
                equity_pct=0.45,
                senior_debt_pct=0.40,
                notes_pct=0.15,
                euribor_rate=0.039,
                euribor_floor=0.0,
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
                ebitda_margins=[0.175, 0.18, 0.185, 0.19, 0.195],
                da_pct_revenue=0.025,
                capex_pct_revenue=0.035,
                nwc_pct_revenue_change=0.08,
                exit_year=7,        # > projection_years=5
                exit_multiple=9.0,
            )

    def test_mismatched_growth_rates_raises(self) -> None:
        with pytest.raises(ValueError, match="revenue_growth_rates"):
            EntryAssumptions(
                company_name="Bad Co",
                geography="DE",
                entry_ebitda_eur_m=8.5,
                entry_multiple=8.0,
                equity_pct=0.45,
                senior_debt_pct=0.40,
                notes_pct=0.15,
                euribor_rate=0.039,
                euribor_floor=0.0,
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
                revenue_growth_rates=[0.07, 0.07],  # only 2 values for 5 years
                ebitda_margins=[0.175, 0.18, 0.185, 0.19, 0.195],
                da_pct_revenue=0.025,
                capex_pct_revenue=0.035,
                nwc_pct_revenue_change=0.08,
                exit_year=5,
                exit_multiple=9.0,
            )

    def test_negative_entry_ebitda_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            EntryAssumptions(
                company_name="Bad Co",
                geography="DE",
                entry_ebitda_eur_m=-1.0,
                entry_multiple=8.0,
                equity_pct=0.45,
                senior_debt_pct=0.40,
                notes_pct=0.15,
                euribor_rate=0.039,
                euribor_floor=0.0,
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
                ebitda_margins=[0.175, 0.18, 0.185, 0.19, 0.195],
                da_pct_revenue=0.025,
                capex_pct_revenue=0.035,
                nwc_pct_revenue_change=0.08,
                exit_year=5,
                exit_multiple=9.0,
            )


# ── Full Integration ───────────────────────────────────────────────────────────

class TestRunLBOIntegration:
    def test_full_pipeline_produces_five_outputs(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        slug = lbo_assumptions.company_name.lower().replace(" ", "_")
        ts = result.run_timestamp
        prefix = out_dir / f"lbo_{slug}_{ts}"

        assert Path(str(prefix) + "_lbo_results.json").exists()
        assert Path(str(prefix) + "_lbo_compact.json").exists()
        assert Path(str(prefix) + "_projections.csv").exists()
        assert Path(str(prefix) + "_sensitivity_irr.csv").exists()
        assert Path(str(prefix) + "_model.xlsx").exists()

    def test_excel_workbook_has_four_sheets(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        import openpyxl
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        slug = lbo_assumptions.company_name.lower().replace(" ", "_")
        xlsx_path = out_dir / f"lbo_{slug}_{result.run_timestamp}_model.xlsx"
        wb = openpyxl.load_workbook(xlsx_path)
        assert set(wb.sheetnames) == {"Summary", "P&L Waterfall", "Sensitivity – IRR", "Sensitivity – MOIC"}

    def test_full_json_contains_required_keys(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        slug = lbo_assumptions.company_name.lower().replace(" ", "_")
        json_path = out_dir / f"lbo_{slug}_{result.run_timestamp}_lbo_results.json"
        data = json.loads(json_path.read_text())
        for key in ("company_name", "sources_uses", "projections", "metrics",
                    "sensitivity_irr", "sensitivity_moic"):
            assert key in data, f"Missing key in full JSON: {key}"

    def test_compact_json_inflection_years(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        """Compact JSON must contain inflection-year projections (yr1, mid, exit)."""
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        slug = lbo_assumptions.company_name.lower().replace(" ", "_")
        compact_path = out_dir / f"lbo_{slug}_{result.run_timestamp}_lbo_compact.json"
        data = json.loads(compact_path.read_text())
        years_in_compact = {p["year"] for p in data["inflection_projections"]}
        exit_y = lbo_assumptions.exit_year
        mid_y = max(1, exit_y // 2)
        assert 1 in years_in_compact
        assert exit_y in years_in_compact
        assert mid_y in years_in_compact

    def test_sensitivity_csv_no_nan_central_cells(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        import pandas as pd
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        slug = lbo_assumptions.company_name.lower().replace(" ", "_")
        csv_path = out_dir / f"lbo_{slug}_{result.run_timestamp}_sensitivity_irr.csv"
        df = pd.read_csv(csv_path, index_col=0)
        # Central 3×3 of a 5×5 grid should be finite
        central = df.iloc[1:-1, 1:-1]
        assert not central.isnull().any().any(), (
            "NaN in central sensitivity cells — computation error"
        )

    def test_moic_and_irr_are_finite(
        self, lbo_assumptions: EntryAssumptions, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "lbo_models"
        result = run_lbo(lbo_assumptions, out_dir)
        assert math.isfinite(result.metrics.moic)
        assert math.isfinite(result.metrics.irr)
        assert result.metrics.irr_solver_converged
