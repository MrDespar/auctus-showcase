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
from datetime import datetime
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
        elif str(row.get("geography", "")).upper() not in [g.upper() for g in hf["geographies_allowed"]]:
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

    passing_df = pd.DataFrame(passing_rows) if passing_rows else pd.DataFrame()
    rejected_df = pd.DataFrame(rejected_rows) if rejected_rows else pd.DataFrame()
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
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = args.output_dir / f"{args.sector}_{ts}_targets.csv"
        ranked_df.to_csv(out_path, index=False)
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
