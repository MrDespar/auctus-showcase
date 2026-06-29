"""
AUCTUS Capital Partners AG — Precedent Transactions Engine

Filters and processes a historical M&A transaction database against AUCTUS
investment criteria and precedent filter parameters. Computes deal multiples
and outputs a ranked precedent transaction table.

Usage:
    python scripts/precedent_engine.py \
        --transactions data/comps/precedent_transactions.csv \
        --filters config/auctus_criteria.yaml \
        --output-dir outputs/valuation_reports/ \
        --sector hvac_services \
        --company-name "Muster GmbH"

Exit codes:
    0  success
    1  input error
    2  insufficient deals (< 3 after filtering)
    3  output write error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"target_company", "close_date", "ev_eur_m", "sector"}
MINIMUM_DEALS = 3
PRECEDENT_FILTERS_PATH = Path("skills/relative-valuation/refs/precedent-filters.yaml")


def load_filters() -> dict:
    if PRECEDENT_FILTERS_PATH.exists():
        with open(PRECEDENT_FILTERS_PATH) as f:
            return yaml.safe_load(f).get("filters", {})
    return {}


def load_transactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Transactions CSV missing columns: {missing}")
    df["close_date"] = pd.to_datetime(df["close_date"], errors="coerce")
    df = df.dropna(subset=["close_date", "ev_eur_m"])
    return df.sort_values("close_date", ascending=False).reset_index(drop=True)


def apply_filters(
    df: pd.DataFrame,
    sector: str,
    filters: dict,
    criteria: dict,
) -> pd.DataFrame:
    """Apply sector, geography, deal size, and vintage filters."""
    geo_allowed = (
        criteria.get("hard_filters", {}).get("geographies_allowed", [])
        + criteria.get("hard_filters", {}).get("geographies_preferred", [])
        + ["UK", "PL", "CZ", "HU"]
    )

    ev_min = filters.get("ev_min_eur_m", 5.0)
    ev_max = filters.get("ev_max_eur_m", 500.0)
    vintage_years = filters.get("vintage_years_back", 10)
    cutoff_date = pd.Timestamp(date.today()) - pd.DateOffset(years=vintage_years)

    mask = (
        (df["sector"].str.lower().str.contains(sector.lower(), na=False))
        & (df["ev_eur_m"] >= ev_min)
        & (df["ev_eur_m"] <= ev_max)
        & (df["close_date"] >= cutoff_date)
    )

    if "geography" in df.columns and geo_allowed:
        geo_mask = df["geography"].str.upper().isin([g.upper() for g in geo_allowed])
        mask = mask & geo_mask

    filtered = df[mask].copy()
    logger.info("Precedents: %d raw → %d after filtering", len(df), len(filtered))
    return filtered.reset_index(drop=True)


def compute_deal_multiples(df: pd.DataFrame) -> pd.DataFrame:
    """Compute EV/EBITDA and EV/Revenue multiples where data is available."""
    df = df.copy()
    if "ebitda_eur_m" in df.columns:
        valid_ebitda = df["ebitda_eur_m"] > 0
        df.loc[valid_ebitda, "ev_ebitda_multiple"] = (
            df.loc[valid_ebitda, "ev_eur_m"] / df.loc[valid_ebitda, "ebitda_eur_m"]
        ).round(2)
    if "revenue_eur_m" in df.columns:
        valid_rev = df["revenue_eur_m"] > 0
        df.loc[valid_rev, "ev_revenue_multiple"] = (
            df.loc[valid_rev, "ev_eur_m"] / df.loc[valid_rev, "revenue_eur_m"]
        ).round(2)
    return df


def precedent_summary_stats(df: pd.DataFrame) -> dict:
    stats = {}
    for col in ["ev_ebitda_multiple", "ev_revenue_multiple"]:
        if col in df.columns:
            series = df[col].dropna()
            if not series.empty:
                stats[col] = {
                    "count": int(len(series)),
                    "mean": round(float(series.mean()), 4),
                    "median": round(float(series.median()), 4),
                    "p25": round(float(series.quantile(0.25)), 4),
                    "p75": round(float(series.quantile(0.75)), 4),
                }
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Precedent Transactions Engine")
    parser.add_argument("--transactions", type=Path, required=True)
    parser.add_argument("--filters", type=Path, required=True, dest="criteria_path")
    parser.add_argument("--output-dir", type=Path, required=True, dest="output_dir")
    parser.add_argument("--sector", type=str, default="general")
    parser.add_argument("--company-name", type=str, default="company", dest="company_name")
    args = parser.parse_args()

    try:
        df = load_transactions(args.transactions)
        with open(args.criteria_path) as f:
            criteria = yaml.safe_load(f)
        filters = load_filters()
    except Exception as exc:
        logger.error("Input error: %s", exc)
        return 1

    filtered_df = apply_filters(df, args.sector, filters, criteria)

    if len(filtered_df) < MINIMUM_DEALS:
        logger.warning(
            "Only %d deals pass filters (minimum %d). Consider widening sector or geography.",
            len(filtered_df), MINIMUM_DEALS,
        )
        if filtered_df.empty:
            return 2

    filtered_df = compute_deal_multiples(filtered_df)
    stats = precedent_summary_stats(filtered_df)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = args.company_name.lower().replace(" ", "_").replace("/", "_")

        prec_path = args.output_dir / f"{slug}_{ts}_precedents.csv"
        filtered_df.to_csv(prec_path, index=False)

        result = {
            "company_name": args.company_name,
            "sector": args.sector,
            "run_timestamp": ts,
            "deal_count": len(filtered_df),
            "summary_statistics": stats,
            "precedents_path": str(prec_path),
        }
        json_path = args.output_dir / f"{slug}_{ts}_precedent_results.json"
        json_path.write_text(json.dumps(result, indent=2))

        logger.info("Precedents complete: %d deals processed", len(filtered_df))
        print(json.dumps({"status": "success", **result}))
        return 0
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
