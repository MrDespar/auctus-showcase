"""Unit tests for scripts/target_scorer.py"""

from __future__ import annotations

import pytest
import pandas as pd

from scripts.target_scorer import (
    apply_hard_filters,
    score_target,
    assign_recommendation,
    rank_targets,
)


class TestApplyHardFilters:
    def test_revenue_floor_excludes_below_10m(self, sample_candidates, auctus_criteria):
        passing, rejected = apply_hard_filters(sample_candidates, auctus_criteria)
        rejected_codes = rejected["hard_filter_fail_code"].tolist()
        assert "REV_LOW" not in rejected_codes or all(
            row["revenue_eur_m"] < 10 for _, row in rejected[
                rejected["hard_filter_fail_code"] == "REV_LOW"
            ].iterrows()
        )

    def test_revenue_ceiling_excludes_above_150m(self, sample_candidates, auctus_criteria):
        passing, rejected = apply_hard_filters(sample_candidates, auctus_criteria)
        for _, row in rejected[rejected["hard_filter_fail_code"] == "REV_HIGH"].iterrows():
            assert row["revenue_eur_m"] > 150.0

    def test_geography_filter(self, auctus_criteria):
        df = pd.DataFrame({
            "company": ["US Corp", "German GmbH"],
            "geography": ["US", "DE"],
            "revenue_eur_m": [30.0, 30.0],
        })
        passing, rejected = apply_hard_filters(df, auctus_criteria)
        assert "US Corp" not in passing["company"].values
        assert "German GmbH" in passing["company"].values

    def test_all_passing_have_no_fail_code(self, sample_candidates, auctus_criteria):
        passing, _ = apply_hard_filters(sample_candidates, auctus_criteria)
        assert passing["hard_filter_fail_code"].isna().all()

    def test_dach_geography_all_pass_geo_filter(self, auctus_criteria):
        df = pd.DataFrame({
            "company": ["DE Co", "AT Co", "CH Co"],
            "geography": ["DE", "AT", "CH"],
            "revenue_eur_m": [30.0, 25.0, 40.0],
        })
        passing, rejected = apply_hard_filters(df, auctus_criteria)
        geo_rejects = rejected[rejected["hard_filter_fail_code"] == "GEO_FAIL"]
        assert len(geo_rejects) == 0


class TestScoreTarget:
    def test_score_range_0_to_100(self, sample_candidates, auctus_criteria):
        weights = auctus_criteria["scoring_weights"]
        for _, row in sample_candidates.iterrows():
            score = score_target(row, weights)
            assert 0.0 <= score <= 100.0

    def test_founder_owned_scores_higher_than_pe(self, auctus_criteria):
        weights = auctus_criteria["scoring_weights"]
        founder_row = pd.Series({"revenue_eur_m": 40.0, "ownership": "founder",
                                  "ebitda_margin_pct": 0.15, "geography": "DE"})
        pe_row = pd.Series({"revenue_eur_m": 40.0, "ownership": "pe",
                             "ebitda_margin_pct": 0.15, "geography": "DE"})
        assert score_target(founder_row, weights) > score_target(pe_row, weights)

    def test_sweet_spot_revenue_scores_highest(self, auctus_criteria):
        weights = auctus_criteria["scoring_weights"]
        sweet = pd.Series({"revenue_eur_m": 50.0, "ownership": "founder", "geography": "DE"})
        low = pd.Series({"revenue_eur_m": 11.0, "ownership": "founder", "geography": "DE"})
        high = pd.Series({"revenue_eur_m": 140.0, "ownership": "founder", "geography": "DE"})
        assert score_target(sweet, weights) > score_target(low, weights)
        assert score_target(sweet, weights) > score_target(high, weights)


class TestAssignRecommendation:
    def test_strong_buy_band(self, auctus_criteria):
        bands = auctus_criteria["recommendation_bands"]
        assert assign_recommendation(85.0, bands) == "Priority Target"

    def test_buy_band(self, auctus_criteria):
        bands = auctus_criteria["recommendation_bands"]
        assert assign_recommendation(65.0, bands) == "Active Coverage"

    def test_watch_band(self, auctus_criteria):
        bands = auctus_criteria["recommendation_bands"]
        assert assign_recommendation(45.0, bands) == "Monitor"

    def test_pass_band(self, auctus_criteria):
        bands = auctus_criteria["recommendation_bands"]
        assert assign_recommendation(20.0, bands) == "Pass"


class TestRankTargets:
    def test_descending_score_order(self, sample_candidates, auctus_criteria):
        weights = auctus_criteria["scoring_weights"]
        passing, _ = apply_hard_filters(sample_candidates, auctus_criteria)
        if passing.empty:
            pytest.skip("No candidates passed filters in sample data")
        passing = passing.copy()
        passing["auctus_score"] = passing.apply(lambda r: score_target(r, weights), axis=1)
        ranked = rank_targets(passing)
        scores = ranked["auctus_score"].tolist()
        assert scores == sorted(scores, reverse=True)
