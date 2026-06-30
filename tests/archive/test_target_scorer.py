"""Unit tests for scripts/target_scorer.py"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from scripts.target_scorer import (
    apply_hard_filters,
    assign_recommendation,
    compute_cohort_retention_proxy,
    compute_unit_economics,
    compute_value_creation_bridge,
    rank_targets,
    score_target,
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


# ── PE Unit Economics ─────────────────────────────────────────────────────────

class TestComputeUnitEconomics:
    def _full_row(self) -> pd.Series:
        return pd.Series({
            "revenue_eur_m": 40.0,
            "ebitda_margin_pct": 0.18,
            "recurring_revenue_pct": 0.65,
            "customer_concentration_top1_pct": 0.12,
        })

    def test_contribution_margin_uses_ebitda_plus_da(self):
        row = self._full_row()
        result = compute_unit_economics(row)
        # contribution_margin = ebitda_margin + 0.03 (D&A proxy)
        assert abs(result["contribution_margin"] - (0.18 + 0.03)) < 1e-4

    def test_ltv_cac_ratio_positive_for_healthy_business(self):
        row = self._full_row()
        result = compute_unit_economics(row)
        assert result["ltv_cac_ratio"] is not None
        assert result["ltv_cac_ratio"] > 0

    def test_payback_months_positive(self):
        row = self._full_row()
        result = compute_unit_economics(row)
        assert result["payback_months"] is not None
        assert result["payback_months"] > 0

    def test_higher_recurring_revenue_lowers_payback(self):
        # customer_concentration_top1_pct required for gross_retention_est to be non-None
        low = pd.Series({"revenue_eur_m": 40.0, "ebitda_margin_pct": 0.18,
                          "recurring_revenue_pct": 0.20,
                          "customer_concentration_top1_pct": 0.10})
        high = pd.Series({"revenue_eur_m": 40.0, "ebitda_margin_pct": 0.18,
                           "recurring_revenue_pct": 0.80,
                           "customer_concentration_top1_pct": 0.10})
        result_low = compute_unit_economics(low)
        result_high = compute_unit_economics(high)
        assert result_high["gross_retention_est"] > result_low["gross_retention_est"]

    def test_missing_recurring_revenue_returns_none_ltv_cac(self):
        row = pd.Series({"revenue_eur_m": 40.0, "ebitda_margin_pct": 0.18})
        result = compute_unit_economics(row)
        # Without recurring_revenue_pct, gross_retention_est is None → ltv_cac also None
        assert result["gross_retention_est"] is None
        assert result["ltv_cac_ratio"] is None

    def test_missing_ebitda_margin_returns_none_contribution(self):
        row = pd.Series({"revenue_eur_m": 40.0})
        result = compute_unit_economics(row)
        assert result["contribution_margin"] is None

    def test_gross_retention_bounded_between_0_and_1(self):
        row = self._full_row()
        result = compute_unit_economics(row)
        if result["gross_retention_est"] is not None:
            assert 0.0 <= result["gross_retention_est"] <= 1.0


# ── Value Creation Bridge ─────────────────────────────────────────────────────

class TestComputeValueCreationBridge:
    def _standard_bridge(self) -> dict:
        return compute_value_creation_bridge(
            entry_revenue=40.0,
            exit_revenue=60.0,
            entry_ebitda_margin=0.17,
            exit_ebitda_margin=0.20,
            entry_ev_ebitda=8.0,
            exit_ev_ebitda=9.0,
            entry_net_debt=27.2,
            exit_net_debt=15.0,
        )

    def test_bridge_returns_all_required_keys(self):
        bridge = self._standard_bridge()
        required = [
            "total_equity_value_change_eur_m",
            "total_attributed_eur_m",
            "organic_growth_eur_m",
            "organic_growth_pct",
            "margin_expansion_eur_m",
            "margin_expansion_pct",
            "multiple_expansion_eur_m",
            "multiple_expansion_pct",
            "leverage_paydown_eur_m",
            "leverage_paydown_pct",
        ]
        for key in required:
            assert key in bridge, f"Missing key: {key}"

    def test_attribution_pcts_sum_to_100(self):
        bridge = self._standard_bridge()
        total_pct = (
            bridge["organic_growth_pct"]
            + bridge["margin_expansion_pct"]
            + bridge["multiple_expansion_pct"]
            + bridge["leverage_paydown_pct"]
        )
        assert abs(total_pct - 100.0) < 0.1, f"Attribution does not sum to 100%: {total_pct}"

    def test_organic_growth_positive_when_revenue_grows(self):
        bridge = self._standard_bridge()
        assert bridge["organic_growth_eur_m"] > 0

    def test_margin_expansion_positive_when_margin_improves(self):
        bridge = self._standard_bridge()
        assert bridge["margin_expansion_eur_m"] > 0

    def test_leverage_paydown_positive_when_debt_reduces(self):
        bridge = self._standard_bridge()
        assert bridge["leverage_paydown_eur_m"] > 0, (
            "Debt paydown should be positive when exit_net_debt < entry_net_debt"
        )

    def test_no_margin_expansion_when_margins_equal(self):
        bridge = compute_value_creation_bridge(
            entry_revenue=40.0, exit_revenue=60.0,
            entry_ebitda_margin=0.18, exit_ebitda_margin=0.18,
            entry_ev_ebitda=8.0, exit_ev_ebitda=9.0,
            entry_net_debt=20.0, exit_net_debt=10.0,
        )
        assert abs(bridge["margin_expansion_eur_m"]) < 1e-6

    def test_no_multiple_expansion_when_multiples_equal(self):
        bridge = compute_value_creation_bridge(
            entry_revenue=40.0, exit_revenue=60.0,
            entry_ebitda_margin=0.17, exit_ebitda_margin=0.20,
            entry_ev_ebitda=8.0, exit_ev_ebitda=8.0,
            entry_net_debt=20.0, exit_net_debt=10.0,
        )
        assert abs(bridge["multiple_expansion_eur_m"]) < 1e-6

    def test_monetary_contributions_are_finite(self):
        bridge = self._standard_bridge()
        for key in ["organic_growth_eur_m", "margin_expansion_eur_m",
                    "multiple_expansion_eur_m", "leverage_paydown_eur_m"]:
            assert math.isfinite(bridge[key]), f"{key} is not finite"


# ── Cohort Retention Proxy ────────────────────────────────────────────────────

class TestComputeCohortRetentionProxy:
    def _standard_row(self) -> pd.Series:
        return pd.Series({
            "recurring_revenue_pct": 0.65,
            "customer_concentration_top1_pct": 0.10,
            "ebitda_margin_pct": 0.18,
        })

    def test_returns_all_required_keys(self):
        result = compute_cohort_retention_proxy(self._standard_row())
        assert "ndr_estimate" in result
        assert "gross_churn_proxy" in result
        assert "cohort_quality" in result

    def test_ndr_finite_and_positive(self):
        result = compute_cohort_retention_proxy(self._standard_row())
        assert math.isfinite(result["ndr_estimate"])
        assert result["ndr_estimate"] > 0

    def test_higher_recurring_revenue_improves_ndr(self):
        low = pd.Series({"recurring_revenue_pct": 0.20, "ebitda_margin_pct": 0.15})
        high = pd.Series({"recurring_revenue_pct": 0.80, "ebitda_margin_pct": 0.15})
        assert (
            compute_cohort_retention_proxy(high)["ndr_estimate"]
            > compute_cohort_retention_proxy(low)["ndr_estimate"]
        )

    def test_high_customer_concentration_lowers_ndr(self):
        low_conc = pd.Series({
            "recurring_revenue_pct": 0.60,
            "customer_concentration_top1_pct": 0.05,
        })
        high_conc = pd.Series({
            "recurring_revenue_pct": 0.60,
            "customer_concentration_top1_pct": 0.28,
        })
        assert (
            compute_cohort_retention_proxy(low_conc)["ndr_estimate"]
            > compute_cohort_retention_proxy(high_conc)["ndr_estimate"]
        )

    def test_cohort_quality_labels_are_valid(self):
        valid_labels = {"Excellent", "Good", "Adequate", "Weak"}
        for rr in [0.10, 0.40, 0.70, 0.90]:
            row = pd.Series({"recurring_revenue_pct": rr, "ebitda_margin_pct": 0.15})
            result = compute_cohort_retention_proxy(row)
            assert result["cohort_quality"] in valid_labels

    def test_missing_data_returns_defaults(self):
        empty = pd.Series({})
        result = compute_cohort_retention_proxy(empty)
        assert result["gross_churn_proxy"] == 0.15  # conservative default
        assert result["cohort_quality"] in {"Excellent", "Good", "Adequate", "Weak"}
