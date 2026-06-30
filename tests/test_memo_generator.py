"""Unit and integration tests for scripts/memo_generator.py"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.memo_generator import generate_memo


# ── Reuse the same LBO compact fixture ───────────────────────────────────────

@pytest.fixture
def sample_lbo_compact(tmp_path: Path) -> Path:
    payload = {
        "company_name": "Muster GmbH",
        "run_timestamp": "20260629_120000",
        "sources_uses": {
            "entry_ev_eur_m": 68.0,
            "equity_eur_m": 32.3,
            "senior_debt_eur_m": 27.2,
            "notes_eur_m": 10.2,
            "total_uses_eur_m": 69.7,
            "balance_check_eur_m": 0.0,
        },
        "inflection_projections": [
            {
                "year": 1,
                "revenue_eur_m": 53.5,
                "ebitda_eur_m": 9.36,
                "ebitda_margin_pct": 17.5,
                "total_interest_eur_m": 2.85,
                "levered_fcf_eur_m": 1.2,
                "total_debt_closing_eur_m": 35.1,
                "leverage_x": 3.75,
                "interest_coverage_x": 2.3,
            },
            {
                "year": 5,
                "revenue_eur_m": 65.4,
                "ebitda_eur_m": 12.75,
                "ebitda_margin_pct": 19.5,
                "total_interest_eur_m": 1.9,
                "levered_fcf_eur_m": 3.2,
                "total_debt_closing_eur_m": 23.5,
                "leverage_x": 1.84,
                "interest_coverage_x": 4.2,
            },
        ],
        "exit_metrics": {
            "exit_ev_eur_m": 114.75,
            "net_debt_at_exit_eur_m": 23.5,
            "equity_proceeds_eur_m": 91.25,
            "moic": 2.82,
            "irr_pct": 23.1,
            "irr_solver_converged": True,
            "leverage_at_entry_x": 4.37,
            "leverage_at_exit_x": 1.84,
            "interest_coverage_min_x": 2.3,
        },
        "sensitivity_irr_pct": {
            "7.0x": {"8.0x": 17.8, "9.0x": 20.2, "10.0x": 22.3},
            "8.0x": {"8.0x": 15.1, "9.0x": 17.7, "10.0x": 19.9},
            "9.0x": {"8.0x": 12.5, "9.0x": 15.3, "10.0x": 17.7},
        },
        "sensitivity_moic": {},
        "assumptions": {
            "entry_multiple": 8.0,
            "exit_multiple": 9.0,
            "exit_year": 5,
            "geography": "DE",
            "revenue_growth_rates": [0.07, 0.07, 0.06, 0.06, 0.05],
            "ebitda_margins": [0.175, 0.18, 0.185, 0.19, 0.195],
            "da_pct_revenue": 0.025,
            "capex_pct_revenue": 0.035,
            "senior_spread_bps": 375,
            "notes_fixed_rate": 0.095,
            "tax_rate": 0.299,
            "senior_amort_pct_annual": 0.05,
            "senior_cash_sweep_pct": 0.50,
            "fees_capitalized": True,
            "nwc_pct_revenue_change": 0.08,
        },
    }
    p = tmp_path / "lbo_compact.json"
    p.write_text(json.dumps(payload))
    return p


@pytest.fixture
def sample_dcf_results(tmp_path: Path) -> Path:
    payload = {
        "company_name": "Muster GmbH",
        "run_timestamp": "20260629_120000",
        "wacc_used": 0.12,
        "terminal_growth_rate_used": 0.025,
        "projection_years": 5,
        "pv_forecast_cashflows_eur_m": 15.2,
        "terminal_value_pv_eur_m": 42.8,
        "enterprise_value_eur_m": 58.0,
        "terminal_value_pct_of_ev": 0.738,
    }
    p = tmp_path / "dcf_results.json"
    p.write_text(json.dumps(payload))
    return p


# ── Memo structure tests ───────────────────────────────────────────────────────

REQUIRED_SECTIONS = [
    "Investment Committee Memorandum",
    "# Executive Summary",
    "# Company Overview",
    "# Industry & Market",
    "# Financial Analysis",
    "# Investment Thesis",
    "# Deal Terms & Structure",
    "# Returns Analysis",
    "# Risk Factors",
    "# Recommendation",
    "# Appendix — Model Assumptions",
]


class TestGenerateMemoStructure:
    def test_memo_created_with_no_data(self, tmp_path: Path) -> None:
        written = generate_memo("No Data GmbH", output_dir=tmp_path)
        assert "markdown" in written
        assert written["markdown"].exists()

    def test_memo_contains_all_required_sections(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        text = written["markdown"].read_text()
        for section in REQUIRED_SECTIONS:
            assert section in text, f"Missing section: '{section}'"

    def test_memo_is_non_empty(self, tmp_path: Path, sample_lbo_compact: Path) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        size = written["markdown"].stat().st_size
        assert size > 1000, f"Memo too short: {size} bytes"

    def test_memo_filename_contains_slug_and_timestamp(self, tmp_path: Path) -> None:
        written = generate_memo("Alpha Beta GmbH", output_dir=tmp_path)
        assert "alpha_beta_gmbh" in written["markdown"].name
        assert written["markdown"].name.endswith(".md")

    def test_memo_contains_company_name(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        assert "Muster GmbH" in written["markdown"].read_text()

    def test_memo_contains_lbo_metrics_when_provided(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        text = written["markdown"].read_text()
        # MOIC and IRR from fixture should appear
        assert "2.82" in text or "2.82×" in text
        assert "23.1" in text

    def test_memo_contains_dcf_metrics_when_provided(
        self, tmp_path: Path, sample_lbo_compact: Path, sample_dcf_results: Path
    ) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            dcf_results_path=sample_dcf_results,
            output_dir=tmp_path,
        )
        text = written["markdown"].read_text()
        assert "58.00" in text  # enterprise value from DCF fixture



    def test_memo_recommendation_section_present(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "Muster GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        text = written["markdown"].read_text()
        assert "# Recommendation" in text
        assert "Proposed next steps" in text

    def test_memo_confidentiality_footer(
        self, tmp_path: Path
    ) -> None:
        written = generate_memo("Footer Test GmbH", output_dir=tmp_path)
        text = written["markdown"].read_text()
        assert "deterministic model outputs" in text

    def test_memo_output_dir_created_automatically(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "memos"
        written = generate_memo("Deep GmbH", output_dir=nested)
        assert nested.exists()
        assert written["markdown"].exists()

    def test_missing_lbo_path_does_not_crash(self, tmp_path: Path) -> None:
        written = generate_memo(
            "Missing GmbH",
            lbo_compact_path=tmp_path / "nonexistent.json",
            output_dir=tmp_path,
        )
        assert written["markdown"].exists()


class TestMemoWordExport:
    def test_word_file_created_when_flag_set(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "Word GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
            write_word=True,
        )
        assert "word" in written
        assert written["word"].exists()
        assert written["word"].suffix == ".docx"
        assert written["word"].stat().st_size > 0

    def test_word_file_not_created_by_default(
        self, tmp_path: Path, sample_lbo_compact: Path
    ) -> None:
        written = generate_memo(
            "No Word GmbH",
            lbo_compact_path=sample_lbo_compact,
            output_dir=tmp_path,
        )
        assert "word" not in written
