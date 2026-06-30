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
        """A 3σ+ outlier must be excluded from the result.

        Mean-based 3σ detection requires enough normal peers so the outlier
        doesn't dominate the standard deviation. With N normals + 1 outlier,
        the z-score of the outlier is N/sqrt(N+1), which exceeds 3 only when
        N ≥ 10. We therefore use 10 normal peers + 1 outlier.
        """
        normals = pd.DataFrame({
            "name": [f"Normal_{i}" for i in range(10)],
            "ev_eur_m": [100.0, 110.0, 105.0, 115.0, 98.0,
                         108.0, 112.0, 102.0, 118.0, 95.0],
            "ebitda_ltm_eur_m": [12.0, 13.5, 13.0, 14.0, 12.5,
                                  13.0, 14.0, 12.5, 14.5, 11.5],
            "revenue_ltm_eur_m": [60.0, 65.0, 62.0, 68.0, 58.0,
                                   63.0, 67.0, 61.0, 70.0, 57.0],
        })
        outlier = pd.DataFrame({
            "name": ["D_outlier"],
            "ev_eur_m": [9999.0],
            "ebitda_ltm_eur_m": [14.0],
            "revenue_ltm_eur_m": [70.0],
        })
        peers = pd.concat([normals, outlier], ignore_index=True)
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
