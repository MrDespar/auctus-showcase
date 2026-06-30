"""Unit and integration tests for scripts/dcf_engine.py"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.dcf_engine import (
    compute_ufcf,
    discount_cashflows,
    enterprise_value,
    terminal_value_gordon,
    run_dcf,
    load_financials,
    load_projections,
)


class TestComputeUFCF:
    def test_ufcf_formula(self):
        """UFCF = EBIT*(1-t) + D&A - CapEx - ΔNWC"""
        df = pd.DataFrame({
            "year": [2024],
            "revenue": [40.0],
            "ebitda": [6.5],
            "d_and_a": [1.1],
            "capex": [1.6],
            "nwc_change": [0.5],
            "tax_rate": [0.29],
        })
        ufcf = compute_ufcf(df)
        ebit = 6.5 - 1.1  # 5.4
        nopat = 5.4 * (1 - 0.29)  # 3.834
        expected = nopat + 1.1 - 1.6 - 0.5  # 2.834
        assert abs(float(ufcf.iloc[0]) - expected) < 1e-6

    def test_ufcf_series_length(self, sample_projections):
        """UFCF series has same length as projection DataFrame."""
        fcf = compute_ufcf(sample_projections)
        assert len(fcf) == len(sample_projections)

    def test_positive_ufcf_for_healthy_business(self, sample_projections):
        """Healthy margins and modest capex should produce positive UFCF."""
        fcf = compute_ufcf(sample_projections)
        assert all(fcf > 0)


class TestDiscountCashflows:
    def test_single_cashflow(self):
        """PV of single cash flow one year out = cf / (1 + wacc)."""
        pv = discount_cashflows(pd.Series([10.0]), wacc=0.10)
        assert abs(pv - 10.0 / 1.10) < 1e-6

    def test_zero_cashflows(self):
        """PV of all-zero series is 0."""
        pv = discount_cashflows(pd.Series([0.0, 0.0, 0.0]), wacc=0.10)
        assert pv == 0.0

    def test_higher_wacc_lowers_pv(self):
        """Increasing WACC must decrease present value."""
        fcf = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0])
        pv_low = discount_cashflows(fcf, wacc=0.08)
        pv_high = discount_cashflows(fcf, wacc=0.14)
        assert pv_low > pv_high


class TestTerminalValueGordon:
    def test_known_formula(self):
        """TV at t=0 = FCF*(1+g) / (WACC-g) / (1+WACC)^5"""
        wacc, tgr, fcf = 0.12, 0.025, 5.0
        tv_at_n = fcf * (1 + tgr) / (wacc - tgr)
        tv_pv_expected = tv_at_n / ((1 + wacc) ** 5)
        tv_pv_actual = terminal_value_gordon(fcf, wacc, tgr)
        assert abs(tv_pv_actual - tv_pv_expected) < 1e-6

    def test_raises_when_wacc_equals_tgr(self):
        """Gordon Growth is undefined when WACC == TGR."""
        with pytest.raises(ValueError, match="must exceed"):
            terminal_value_gordon(5.0, wacc=0.025, tgr=0.025)

    def test_raises_when_wacc_less_than_tgr(self):
        """Gordon Growth is undefined when WACC < TGR."""
        with pytest.raises(ValueError):
            terminal_value_gordon(5.0, wacc=0.02, tgr=0.03)

    def test_higher_tgr_increases_tv(self):
        """Higher terminal growth rate → higher terminal value."""
        tv_low = terminal_value_gordon(5.0, wacc=0.12, tgr=0.01)
        tv_high = terminal_value_gordon(5.0, wacc=0.12, tgr=0.03)
        assert tv_high > tv_low

    def test_higher_wacc_decreases_tv(self):
        """Higher WACC → lower terminal value."""
        tv_low_wacc = terminal_value_gordon(5.0, wacc=0.10, tgr=0.025)
        tv_high_wacc = terminal_value_gordon(5.0, wacc=0.14, tgr=0.025)
        assert tv_low_wacc > tv_high_wacc


class TestEnterpriseValue:
    def test_ev_is_sum(self):
        """EV = PV(FCFs) + PV(TV)."""
        assert abs(enterprise_value(20.0, 30.0) - 50.0) < 1e-6

    def test_ev_positive(self):
        """EV is positive for positive inputs."""
        assert enterprise_value(10.0, 25.0) > 0


class TestRunDCFIntegration:
    def test_full_pipeline_produces_outputs(
        self, sample_historicals, sample_projections, tmp_output_dir, tmp_path
    ):
        """End-to-end: write input files, run DCF, verify outputs exist."""
        hist_path = tmp_path / "test_financials.csv"
        proj_path = tmp_path / "test_projections.csv"
        sample_historicals.to_csv(hist_path, index=False)
        sample_projections.to_csv(proj_path, index=False)

        result = run_dcf(
            input_path=hist_path,
            projections_path=proj_path,
            wacc=0.12,
            tgr=0.025,
            years=5,
            output_dir=tmp_output_dir / "dcf_models",
            company_name="Test GmbH",
        )

        assert result["enterprise_value_eur_m"] > 0
        assert isinstance(result["enterprise_value_eur_m"], float)
        assert not pd.isna(result["enterprise_value_eur_m"])

    def test_terminal_value_threshold_warning_not_fatal(
        self, sample_historicals, sample_projections, tmp_output_dir, tmp_path
    ):
        """Terminal value exceeding 70% of EV should not stop execution."""
        hist_path = tmp_path / "test_financials.csv"
        proj_path = tmp_path / "test_projections.csv"
        sample_historicals.to_csv(hist_path, index=False)
        sample_projections.to_csv(proj_path, index=False)

        # Force a high TGR to push TV > 70%
        result = run_dcf(
            input_path=hist_path,
            projections_path=proj_path,
            wacc=0.10,
            tgr=0.08,
            years=5,
            output_dir=tmp_output_dir / "dcf_models",
            company_name="Test GmbH",
        )
        assert result["terminal_value_pct_of_ev"] > 0.70
        assert "enterprise_value_eur_m" in result

    def test_json_output_file_is_written(
        self, sample_historicals, sample_projections, tmp_output_dir, tmp_path
    ):
        hist_path = tmp_path / "test_financials.csv"
        proj_path = tmp_path / "test_projections.csv"
        sample_historicals.to_csv(hist_path, index=False)
        sample_projections.to_csv(proj_path, index=False)

        out_dir = tmp_output_dir / "dcf_models"
        out_dir.mkdir(exist_ok=True)
        run_dcf(hist_path, proj_path, 0.12, 0.025, 5, out_dir, "Test GmbH")

        json_files = list(out_dir.glob("*_dcf_results.json"))
        assert len(json_files) == 1
        with open(json_files[0]) as f:
            data = json.load(f)
        assert "enterprise_value_eur_m" in data
        assert data["enterprise_value_eur_m"] > 0
