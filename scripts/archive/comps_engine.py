"""
AUCTUS Capital Partners AG — Trading Comps Engine

Normalizes public comparable company financials and computes LTM EV multiples.
Derives an implied Enterprise Value range for the target company.

Usage:
    python scripts/comps_engine.py \
        --peers data/comps/peer_group.csv \
        --target data/inputs/company_financials.csv \
        --output-dir outputs/valuation_reports/ \
        --company-name "Muster GmbH"

Exit codes:
    0  success
    1  input validation error
    2  insufficient peers (< 3)
    3  computation error
    4  output write error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

REQUIRED_PEER_COLUMNS = {"name", "ev_eur_m", "ebitda_ltm_eur_m", "revenue_ltm_eur_m"}
MINIMUM_PEERS = 3
OUTLIER_STD_THRESHOLD = 3.0


def load_peers(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    missing = REQUIRED_PEER_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Peer group CSV missing columns: {missing}")
    df = df.dropna(subset=["ev_eur_m", "ebitda_ltm_eur_m", "revenue_ltm_eur_m"])
    df = df[df["ebitda_ltm_eur_m"] > 0]
    return df.reset_index(drop=True)


def compute_multiples(peers: pd.DataFrame) -> pd.DataFrame:
    """Compute EV/EBITDA and EV/Revenue multiples; exclude 3σ outliers."""
    df = peers.copy()
    df["ev_ebitda"] = df["ev_eur_m"] / df["ebitda_ltm_eur_m"]
    df["ev_revenue"] = df["ev_eur_m"] / df["revenue_ltm_eur_m"]

    for col in ["ev_ebitda", "ev_revenue"]:
        mean = df[col].mean()
        std = df[col].std()
        outlier_mask = (df[col] - mean).abs() > OUTLIER_STD_THRESHOLD * std
        excluded = outlier_mask.sum()
        if excluded:
            logger.warning("Excluding %d outlier(s) from %s column", excluded, col)
        df = df[~outlier_mask]

    return df.reset_index(drop=True)


def summary_stats(multiples: pd.DataFrame) -> dict:
    """Compute descriptive statistics for EV/EBITDA and EV/Revenue."""
    stats: dict = {}
    for col in ["ev_ebitda", "ev_revenue"]:
        if col not in multiples.columns:
            continue
        series = multiples[col].dropna()
        stats[col] = {
            "count": int(len(series)),
            "mean": round(float(series.mean()), 4),
            "median": round(float(series.median()), 4),
            "p25": round(float(series.quantile(0.25)), 4),
            "p75": round(float(series.quantile(0.75)), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
        }
    return stats


def load_target_ebitda(target_path: Path) -> Optional[float]:
    """Extract LTM EBITDA from target financials CSV (last year of historical data)."""
    try:
        df = pd.read_csv(target_path)
        df.columns = df.columns.str.strip().str.lower()
        if "ebitda" in df.columns:
            return float(df["ebitda"].iloc[-1])
    except Exception as exc:
        logger.warning("Could not load target EBITDA: %s", exc)
    return None


def implied_ev_range(
    target_ebitda_eur_m: Optional[float],
    stats: dict,
) -> Optional[dict]:
    """Apply P25–P75 EV/EBITDA to target EBITDA to derive implied EV range."""
    if target_ebitda_eur_m is None or "ev_ebitda" not in stats:
        return None
    p25 = stats["ev_ebitda"]["p25"]
    p75 = stats["ev_ebitda"]["p75"]
    return {
        "target_ebitda_eur_m": round(target_ebitda_eur_m, 4),
        "ev_ebitda_multiple_p25": p25,
        "ev_ebitda_multiple_p75": p75,
        "implied_ev_low_eur_m": round(target_ebitda_eur_m * p25, 4),
        "implied_ev_high_eur_m": round(target_ebitda_eur_m * p75, 4),
        "implied_ev_range_eur_m": [
            round(target_ebitda_eur_m * p25, 4),
            round(target_ebitda_eur_m * p75, 4),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Trading Comps Engine")
    parser.add_argument("--peers", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, dest="output_dir")
    parser.add_argument("--company-name", type=str, default="company", dest="company_name")
    args = parser.parse_args()

    try:
        peers_raw = load_peers(args.peers)
    except Exception as exc:
        logger.error("Peer group load error: %s", exc)
        return 1

    if len(peers_raw) < MINIMUM_PEERS:
        logger.error("Fewer than %d valid peers after loading (%d found)", MINIMUM_PEERS, len(peers_raw))
        return 2

    try:
        peers_with_multiples = compute_multiples(peers_raw)
        if len(peers_with_multiples) < MINIMUM_PEERS:
            logger.error(
                "After outlier exclusion only %d peers remain (minimum %d required)",
                len(peers_with_multiples), MINIMUM_PEERS,
            )
            return 2
        stats = summary_stats(peers_with_multiples)
    except Exception as exc:
        logger.error("Multiples computation error: %s", exc)
        return 3

    target_ebitda = load_target_ebitda(args.target)
    ev_range = implied_ev_range(target_ebitda, stats)

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slug = args.company_name.lower().replace(" ", "_").replace("/", "_")

        comps_path = args.output_dir / f"{slug}_{ts}_trading_comps.xlsx"
        peers_with_multiples.to_excel(comps_path, index=False, engine="openpyxl")

        result = {
            "company_name": args.company_name,
            "run_timestamp": ts,
            "peer_count": len(peers_with_multiples),
            "summary_statistics": stats,
            "implied_ev": ev_range,
            "implied_ev_range_eur_m": ev_range["implied_ev_range_eur_m"] if ev_range else None,
            "comps_path": str(comps_path),
        }
        json_path = args.output_dir / f"{slug}_{ts}_comps_results.json"
        json_path.write_text(json.dumps(result, indent=2))

        logger.info(
            "Comps complete: %d peers, EV/EBITDA median=%.1fx",
            len(peers_with_multiples), stats.get("ev_ebitda", {}).get("median", 0),
        )
        print(json.dumps({"status": "success", "peer_count": len(peers_with_multiples), **result}))
        return 0
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 4


if __name__ == "__main__":
    sys.exit(main())
