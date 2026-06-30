"""
AUCTUS Capital Partners AG — Target Scoring Engine

Applies AUCTUS investment criteria hard filters and weighted scoring model to a
candidate company CSV. Outputs a ranked target matrix CSV.

Usage:
    python scripts/target_scorer.py \
        --targets data/market/candidates_filtered.csv \
        --criteria config/auctus_criteria.yaml \
        --output-dir outputs/target_matrices/ \
        --sector hvac_services

Exit codes:
    0  success
    1  input validation error
    2  no candidates passed hard filters
    3  output write error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

REQUIRED_INPUT_COLUMNS = {"company", "revenue_eur_m", "geography"}
OPTIONAL_COLUMNS = {
    "ebitda_margin_pct", "ownership", "customer_concentration_top1_pct",
    "recurring_revenue_pct", "dach_revenue_pct", "revenue_confidence"
}


def load_criteria(yaml_path: Path) -> dict:
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def apply_hard_filters(df: pd.DataFrame, criteria: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply binary pass/fail hard filters.

    Returns:
        (passing_df, rejected_df) — rejected_df has a 'hard_filter_fail_code' column.
    """
    hf = criteria["hard_filters"]
    rejected_rows = []
    passing_rows = []

    for _, row in df.iterrows():
        fail_code = None
        rev = row.get("revenue_eur_m", None)

        if rev is None or pd.isna(rev):
            fail_code = "REV_MISSING"
        elif rev < hf["revenue_min_eur"] / 1_000_000:
            fail_code = "REV_LOW"
        elif rev > hf["revenue_max_eur"] / 1_000_000:
            fail_code = "REV_HIGH"
        elif str(row.get("geography", "")).upper() not in [str(g).upper() for g in hf["geographies_allowed"]]:
            fail_code = "GEO_FAIL"
        elif str(row.get("sector", "")).lower() in [s.lower() for s in hf["excluded_sectors"]]:
            fail_code = "SEC_EXCL"

        ebitda_m = row.get("ebitda_margin_pct", None)
        if fail_code is None and ebitda_m is not None and not pd.isna(ebitda_m):
            margin = ebitda_m if ebitda_m <= 1.0 else ebitda_m / 100.0
            if margin < hf["ebitda_margin_min"]:
                fail_code = "EBITDA_LOW"

        customer_conc = row.get("customer_concentration_top1_pct", None)
        if fail_code is None and customer_conc is not None and not pd.isna(customer_conc):
            conc = customer_conc if customer_conc <= 1.0 else customer_conc / 100.0
            if conc > hf["customer_concentration_max_single"]:
                fail_code = "CUST_CONC"

        r = row.to_dict()
        if fail_code:
            r["hard_filter_pass"] = False
            r["hard_filter_fail_code"] = fail_code
            rejected_rows.append(r)
        else:
            r["hard_filter_pass"] = True
            r["hard_filter_fail_code"] = None
            passing_rows.append(r)

    passing_df = pd.DataFrame(passing_rows) if passing_rows else pd.DataFrame(
        columns=list(df.columns) + ["hard_filter_pass", "hard_filter_fail_code"]
    )
    rejected_df = pd.DataFrame(rejected_rows) if rejected_rows else pd.DataFrame(
        columns=list(df.columns) + ["hard_filter_pass", "hard_filter_fail_code"]
    )
    return passing_df, rejected_df


def score_target(row: pd.Series, weights: dict) -> float:
    """
    Apply weighted scoring model. Returns 0.0–100.0.
    Dimensions with missing data receive a conservative default score.
    """
    score = 0.0

    # Dimension 1: Revenue in sweet spot
    rev = row.get("revenue_eur_m", 0.0) or 0.0
    if 20 <= rev <= 80:
        d1 = 100.0
    elif 10 <= rev < 20 or 80 < rev <= 120:
        d1 = 70.0
    elif 120 < rev <= 150:
        d1 = 40.0
    else:
        d1 = 20.0
    score += d1 * weights.get("revenue_in_sweet_spot", 0.15)

    # Dimension 2: Ownership type
    ownership = str(row.get("ownership", "unknown")).lower()
    ownership_scores = {
        "founder": 100.0, "family": 85.0, "management_buyout": 75.0,
        "mbo": 75.0, "mixed": 50.0, "pe": 20.0, "pe_minority": 50.0,
    }
    d2 = ownership_scores.get(ownership, 30.0)
    score += d2 * weights.get("founder_owned", 0.20)

    # Dimension 3: Market fragmentation (proxy: sector-level indicator in input)
    fragmentation = str(row.get("market_fragmentation", "medium")).lower()
    frag_scores = {"very_high": 100.0, "high": 75.0, "medium": 50.0, "low": 25.0}
    d3 = frag_scores.get(fragmentation, 50.0)
    score += d3 * weights.get("fragmented_market", 0.20)

    # Dimension 4: Recurring revenue percentage
    rec_rev = row.get("recurring_revenue_pct", None)
    if rec_rev is not None and not pd.isna(rec_rev):
        rr = rec_rev if rec_rev <= 1.0 else rec_rev / 100.0
        if rr >= 0.60:
            d4 = 100.0
        elif rr >= 0.40:
            d4 = 75.0
        elif rr >= 0.20:
            d4 = 50.0
        else:
            d4 = 25.0
    else:
        d4 = 30.0  # unknown → conservative default
    score += d4 * weights.get("recurring_revenue_pct", 0.15)

    # Dimension 5: EBITDA margin quality
    ebitda_m = row.get("ebitda_margin_pct", None)
    if ebitda_m is not None and not pd.isna(ebitda_m):
        margin = ebitda_m if ebitda_m <= 1.0 else ebitda_m / 100.0
        if margin >= 0.20:
            d5 = 100.0
        elif margin >= 0.15:
            d5 = 85.0
        elif margin >= 0.10:
            d5 = 65.0
        elif margin >= 0.08:
            d5 = 40.0
        else:
            d5 = 10.0
    else:
        d5 = 30.0
    score += d5 * weights.get("ebitda_margin", 0.15)

    # Dimension 6: DACH geographic concentration
    dach_pct = row.get("dach_revenue_pct", None)
    if dach_pct is not None and not pd.isna(dach_pct):
        dp = dach_pct if dach_pct <= 1.0 else dach_pct / 100.0
        if dp >= 0.80:
            d6 = 100.0
        elif dp >= 0.60:
            d6 = 75.0
        elif dp >= 0.40:
            d6 = 50.0
        else:
            d6 = 25.0
    else:
        d6 = 60.0  # unknown → assume mostly DACH (mid score)
    score += d6 * weights.get("geographic_concentration_dach", 0.10)

    # Dimension 7: Customer concentration
    cust_conc = row.get("customer_concentration_top1_pct", None)
    if cust_conc is not None and not pd.isna(cust_conc):
        cc = cust_conc if cust_conc <= 1.0 else cust_conc / 100.0
        if cc < 0.10:
            d7 = 100.0
        elif cc < 0.20:
            d7 = 75.0
        else:
            d7 = 40.0
    else:
        d7 = 40.0
    score += d7 * weights.get("low_customer_concentration", 0.05)

    return round(score, 2)


def assign_recommendation(score: float, bands: dict) -> str:
    for label_key in ["strong_buy", "buy", "watch", "pass"]:
        band = bands.get(label_key, {})
        if score >= band.get("min_score", 0):
            return band.get("label", label_key)
    return "Pass"


def rank_targets(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("auctus_score", ascending=False).reset_index(drop=True)


# ── PE Unit Economics (additive, Phase-3 extension) ───────────────────────────

def compute_unit_economics(row: pd.Series) -> dict:
    """
    Derive PE-relevant unit economics from available company metrics.

    All inputs are read from the candidate row (same schema as score_target).
    Missing fields degrade gracefully — missing values produce None.

    Returns a dict with keys:
      ltv_cac_ratio        — estimated LTV/CAC; >3× is healthy for SaaS/services
      payback_months       — months to recover CAC; <24 preferred
      contribution_margin  — gross-profit proxy (EBITDA + est. overhead)
      gross_retention_est  — estimated gross revenue retention proxy
    """
    result: dict = {}

    ebitda_m = row.get("ebitda_margin_pct")
    rev = row.get("revenue_eur_m")
    rec_rev_pct = row.get("recurring_revenue_pct")
    cust_conc = row.get("customer_concentration_top1_pct")

    # Contribution margin proxy: EBITDA margin + D&A / Revenue ≈ gross contribution
    # For services businesses D&A is typically 2–4% of revenue
    if ebitda_m is not None and not (isinstance(ebitda_m, float) and ebitda_m != ebitda_m):
        margin = ebitda_m if ebitda_m <= 1.0 else ebitda_m / 100.0
        # Assume 3% D&A for typical B2B services in DACH
        result["contribution_margin"] = round(margin + 0.03, 4)
    else:
        result["contribution_margin"] = None

    # Gross retention estimate: proxy from recurring revenue pct + customer concentration
    # High recurring + low concentration → high retention
    if rec_rev_pct is not None and cust_conc is not None:
        rr = rec_rev_pct if rec_rev_pct <= 1.0 else rec_rev_pct / 100.0
        cc = cust_conc if cust_conc <= 1.0 else cust_conc / 100.0
        # Rough proxy: base 85% + up to +10% for high recurring, −10% for high concentration
        retention_est = 0.85 + 0.10 * rr - 0.10 * cc
        result["gross_retention_est"] = round(min(max(retention_est, 0.5), 0.99), 4)
    else:
        result["gross_retention_est"] = None

    # LTV / CAC ratio proxy
    # LTV = avg contract value × gross retention / churn
    # CAC = estimated sales & marketing spend (S&M ≈ 15% revenue for mid-market services)
    if (
        result["contribution_margin"] is not None
        and result["gross_retention_est"] is not None
        and rev is not None
    ):
        sm_pct = 0.15  # typical mid-market services S&M / Revenue
        churn = max(1.0 - result["gross_retention_est"], 0.01)
        # LTV proxy: annual contribution × (1 / churn)
        annual_contribution = rev * result["contribution_margin"]
        ltv_proxy = annual_contribution / churn
        cac_proxy = rev * sm_pct
        result["ltv_cac_ratio"] = round(ltv_proxy / cac_proxy, 2) if cac_proxy > 0 else None
    else:
        result["ltv_cac_ratio"] = None

    # Payback months: CAC / (annual contribution per customer)
    # Simplified: 12 × S&M pct / contribution margin
    if result["contribution_margin"] and result["contribution_margin"] > 0:
        sm_pct = 0.15
        result["payback_months"] = round(12.0 * sm_pct / result["contribution_margin"], 1)
    else:
        result["payback_months"] = None

    return result


def compute_value_creation_bridge(
    entry_revenue: float,
    exit_revenue: float,
    entry_ebitda_margin: float,
    exit_ebitda_margin: float,
    entry_ev_ebitda: float,
    exit_ev_ebitda: float,
    entry_net_debt: float,
    exit_net_debt: float,
) -> dict:
    """
    Value creation bridge — attribute equity-value change to four levers:

      1. Organic growth   — EBITDA lift from revenue growth at entry margin
      2. Margin expansion — EBITDA lift from margin improvement at exit revenue
      3. Multiple expansion — EV lift from re-rating at exit EBITDA
      4. Leverage paydown  — equity lift from debt reduction

    All monetary inputs in EUR millions.  Returns a dict of contributions (€m)
    and percentage attribution (summing to 100% of total equity value change).
    """
    entry_ebitda = entry_revenue * entry_ebitda_margin
    exit_ebitda = exit_revenue * exit_ebitda_margin

    entry_ev = entry_ebitda * entry_ev_ebitda
    exit_ev = exit_ebitda * exit_ev_ebitda

    entry_equity = entry_ev - entry_net_debt
    exit_equity = exit_ev - exit_net_debt
    total_equity_change = exit_equity - entry_equity

    # Lever 1: organic growth — hold entry margin and entry multiple, grow revenue
    growth_ebitda = exit_revenue * entry_ebitda_margin
    growth_ev = growth_ebitda * entry_ev_ebitda
    organic_growth_contribution = growth_ev - entry_ev

    # Lever 2: margin expansion — hold exit revenue and entry multiple, expand margin
    margin_ebitda_delta = (exit_ebitda_margin - entry_ebitda_margin) * exit_revenue
    margin_expansion_contribution = margin_ebitda_delta * entry_ev_ebitda

    # Lever 3: multiple expansion — on exit EBITDA, value of re-rating
    multiple_expansion_contribution = exit_ebitda * (exit_ev_ebitda - entry_ev_ebitda)

    # Lever 4: leverage paydown — direct equity lift
    leverage_paydown_contribution = entry_net_debt - exit_net_debt

    total_attributed = (
        organic_growth_contribution
        + margin_expansion_contribution
        + multiple_expansion_contribution
        + leverage_paydown_contribution
    )

    def safe_pct(value: float) -> float:
        if total_attributed == 0:
            return 0.0
        return round(value / total_attributed * 100.0, 2)

    return {
        "total_equity_value_change_eur_m": round(total_equity_change, 4),
        "total_attributed_eur_m": round(total_attributed, 4),
        "organic_growth_eur_m": round(organic_growth_contribution, 4),
        "organic_growth_pct": safe_pct(organic_growth_contribution),
        "margin_expansion_eur_m": round(margin_expansion_contribution, 4),
        "margin_expansion_pct": safe_pct(margin_expansion_contribution),
        "multiple_expansion_eur_m": round(multiple_expansion_contribution, 4),
        "multiple_expansion_pct": safe_pct(multiple_expansion_contribution),
        "leverage_paydown_eur_m": round(leverage_paydown_contribution, 4),
        "leverage_paydown_pct": safe_pct(leverage_paydown_contribution),
    }


def compute_cohort_retention_proxy(row: pd.Series) -> dict:
    """
    Estimate cohort-level retention metrics from aggregate company data.

    In the absence of full cohort data, we derive conservative proxies from
    recurring revenue percentage and customer concentration — both of which
    are standard fields in AUCTUS candidate CSVs.

    Returns a dict with:
      ndr_estimate      — Net Dollar Retention proxy (0.0–1.5+)
      gross_churn_proxy — Annual gross revenue churn estimate
      cohort_quality    — qualitative label: "Excellent", "Good", "Adequate", "Weak"
    """
    rec_rev_pct = row.get("recurring_revenue_pct")
    cust_conc = row.get("customer_concentration_top1_pct")
    ebitda_m = row.get("ebitda_margin_pct")

    # Gross churn proxy: higher recurring → lower churn
    if rec_rev_pct is not None:
        rr = rec_rev_pct if rec_rev_pct <= 1.0 else rec_rev_pct / 100.0
        # Best-in-class SaaS: ~5% annual churn; typical B2B services: 10–20%
        gross_churn_proxy = round(0.20 - 0.15 * rr, 4)
    else:
        gross_churn_proxy = 0.15  # conservative default

    # NDR proxy: base retention + upsell/expansion estimate
    # For DACH B2B services, expansion is typically modest (2–5%)
    expansion_proxy = 0.03 if ebitda_m and ebitda_m >= 0.15 else 0.01
    ndr_estimate = round(1.0 - gross_churn_proxy + expansion_proxy, 4)

    # Concentration penalty on NDR: high concentration is a single-customer risk
    if cust_conc is not None:
        cc = cust_conc if cust_conc <= 1.0 else cust_conc / 100.0
        ndr_estimate = round(ndr_estimate - 0.05 * cc, 4)

    # Cohort quality label
    if ndr_estimate >= 1.10:
        quality = "Excellent"
    elif ndr_estimate >= 1.00:
        quality = "Good"
    elif ndr_estimate >= 0.90:
        quality = "Adequate"
    else:
        quality = "Weak"

    return {
        "ndr_estimate": ndr_estimate,
        "gross_churn_proxy": gross_churn_proxy,
        "cohort_quality": quality,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Target Scoring Engine")
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, dest="output_dir")
    parser.add_argument("--sector", type=str, default="general")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.targets)
        df.columns = df.columns.str.strip().str.lower()
        missing = REQUIRED_INPUT_COLUMNS - set(df.columns)
        if missing:
            logger.error("Input CSV missing required columns: %s", missing)
            return 1
        criteria = load_criteria(args.criteria)
    except Exception as exc:
        logger.error("Input error: %s", exc)
        return 1

    passing_df, rejected_df = apply_hard_filters(df, criteria)
    logger.info(
        "Hard filters: %d in → %d pass, %d rejected",
        len(df), len(passing_df), len(rejected_df),
    )

    if passing_df.empty:
        logger.error("No candidates passed hard filters.")
        return 2

    weights = criteria.get("scoring_weights", {})
    bands = criteria.get("recommendation_bands", {})
    passing_df = passing_df.copy()
    passing_df["auctus_score"] = passing_df.apply(
        lambda row: score_target(row, weights), axis=1
    )
    passing_df["recommendation"] = passing_df["auctus_score"].apply(
        lambda s: assign_recommendation(s, bands)
    )
    ranked_df = rank_targets(passing_df)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = args.output_dir / f"{args.sector}_{ts}_targets.xlsx"
        ranked_df.to_excel(out_path, index=False, engine="openpyxl")
        logger.info("Target matrix written: %s (%d companies)", out_path, len(ranked_df))
        print(json.dumps({
            "status": "success",
            "output_path": str(out_path),
            "total_candidates": len(df),
            "passed_filters": len(ranked_df),
            "rejected": len(rejected_df),
        }))
        return 0
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
