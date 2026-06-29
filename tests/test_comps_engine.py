"""Unit tests for scripts/comps_engine.py"""

from __future__ import annotations

import pytest
import pandas as pd

from scripts.comps_engine import (
    load_peers,
    compute_multiples,
    summary_stats,
    implied_ev_range,
)


class TestComputeMultiples:
    def test_ev_ebitda_formula(self, sample_peers):
        result = compute_multiples(sample_peers)
        for _, row in result.iterrows():
            expected = row["ev_eur_m"] / row["ebitda_ltm_eur_m"]
            assert abs(row["ev_ebitda"] - expected) < 1e-6

    def test_ev_revenue_formula(self, sample_peers):
        result = compute_multiples(sample_peers)
        for _, row in result.iterrows():
            expected = row["ev_eur_m"] / row["revenue_ltm_eur_m"]
            assert abs(row["ev_revenue"] - expected) < 1e-6

    def test_minimum_3_peers_survive(self, sample_peers):
        result = compute_multiples(sample_peers)
        assert len(result) >= 3

    def test_outlier_excluded(self):
        """A 10σ outlier must be excluded from the result."""
        peers = pd.DataFrame({
            "name": ["A", "B", "C", "D_outlier"],
            "ev_eur_m": [100.0, 120.0, 110.0, 9999.0],
            "ebitda_ltm_eur_m": [12.0, 15.0, 13.0, 14.0],
            "revenue_ltm_eur_m": [60.0, 70.0, 65.0, 70.0],
        })
        result = compute_multiples(peers)
        assert "D_outlier" not in result["name"].values


class TestSummaryStats:
    def test_stats_keys_present(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        assert "ev_ebitda" in stats
        assert "median" in stats["ev_ebitda"]
        assert "p25" in stats["ev_ebitda"]
        assert "p75" in stats["ev_ebitda"]

    def test_p25_lte_median_lte_p75(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        s = stats["ev_ebitda"]
        assert s["p25"] <= s["median"] <= s["p75"]

    def test_count_matches_peer_count(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        assert stats["ev_ebitda"]["count"] == len(multiples)


class TestImpliedEVRange:
    def test_range_is_valid_interval(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        result = implied_ev_range(target_ebitda_eur_m=8.0, stats=stats)
        low, high = result["implied_ev_range_eur_m"]
        assert low < high

    def test_none_target_returns_none(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        result = implied_ev_range(target_ebitda_eur_m=None, stats=stats)
        assert result is None

    def test_range_uses_p25_p75(self, sample_peers):
        multiples = compute_multiples(sample_peers)
        stats = summary_stats(multiples)
        target_ebitda = 10.0
        result = implied_ev_range(target_ebitda_eur_m=target_ebitda, stats=stats)
        expected_low = target_ebitda * stats["ev_ebitda"]["p25"]
        expected_high = target_ebitda * stats["ev_ebitda"]["p75"]
        assert abs(result["implied_ev_low_eur_m"] - expected_low) < 1e-4
        assert abs(result["implied_ev_high_eur_m"] - expected_high) < 1e-4
