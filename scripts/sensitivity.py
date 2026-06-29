"""
AUCTUS Capital Partners AG — DCF Sensitivity Grid Generator

Reads a dcf_results.json file and produces a WACC × TGR enterprise value matrix.
Grid dimensions are configured via skills/dcf-valuation/refs/sensitivity-config.yaml.

Usage:
    python scripts/sensitivity.py \
        --dcf-results outputs/dcf_models/company_20260629_120000_dcf_results.json \
        --output-dir outputs/dcf_models/

Exit codes:
    0  success
    1  invalid DCF input JSON
    2  grid computation error
    3  output write error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

SENSITIVITY_CONFIG_PATH = Path("skills/dcf-valuation/refs/sensitivity-config.yaml")
DEFAULT_WACC_BPS_RANGE = 200
DEFAULT_TGR_BPS_RANGE = 100
DEFAULT_STEPS = 5


def _load_config() -> dict:
    if SENSITIVITY_CONFIG_PATH.exists():
        with open(SENSITIVITY_CONFIG_PATH) as f:
            return yaml.safe_load(f).get("grid", {})
    return {}


def _gordon_growth_ev(fcf_series: list[float], wacc: float, tgr: float) -> float:
    """Recompute EV for a given WACC/TGR pair from raw FCF series."""
    if wacc <= tgr:
        return float("nan")
    pv_fcfs = sum(cf / ((1.0 + wacc) ** (t + 1)) for t, cf in enumerate(fcf_series))
    terminal_fcf = fcf_series[-1] if fcf_series else 0.0
    tv_at_n = terminal_fcf * (1.0 + tgr) / (wacc - tgr)
    n = len(fcf_series)
    tv_pv = tv_at_n / ((1.0 + wacc) ** n)
    return float(round(pv_fcfs + tv_pv, 4))


def build_sensitivity_grid(dcf_result: dict, config: dict) -> pd.DataFrame:
    """Build a WACC (rows) × TGR (columns) DataFrame of enterprise values."""
    fcf_series: list[float] = dcf_result["forecast_cash_flows"]
    base_wacc: float = dcf_result["wacc_used"]
    base_tgr: float = dcf_result["terminal_growth_rate_used"]

    wacc_bps_range = config.get("wacc_bps_range", DEFAULT_WACC_BPS_RANGE)
    tgr_bps_range = config.get("tgr_bps_range", DEFAULT_TGR_BPS_RANGE)
    wacc_steps = config.get("wacc_steps", DEFAULT_STEPS)
    tgr_steps = config.get("tgr_steps", DEFAULT_STEPS)

    wacc_values = np.linspace(
        base_wacc - wacc_bps_range / 10000,
        base_wacc + wacc_bps_range / 10000,
        wacc_steps,
    )
    tgr_values = np.linspace(
        base_tgr - tgr_bps_range / 10000,
        base_tgr + tgr_bps_range / 10000,
        tgr_steps,
    )

    rows = {}
    for w in wacc_values:
        row = {}
        for g in tgr_values:
            row[round(g, 4)] = _gordon_growth_ev(fcf_series, float(w), float(g))
        rows[round(w, 4)] = row

    df = pd.DataFrame(rows).T
    df.index.name = "wacc"
    df.columns.name = "tgr"
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Sensitivity Grid Generator")
    parser.add_argument("--dcf-results", type=Path, required=True, dest="dcf_results")
    parser.add_argument("--output-dir", type=Path, required=True, dest="output_dir")
    args = parser.parse_args()

    try:
        with open(args.dcf_results) as f:
            dcf_result = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        logger.error("Cannot load DCF results JSON: %s", exc)
        return 1

    required = {"forecast_cash_flows", "wacc_used", "terminal_growth_rate_used", "company_name"}
    missing = required - set(dcf_result.keys())
    if missing:
        logger.error("DCF results JSON missing fields: %s", missing)
        return 1

    try:
        config = _load_config()
        grid_df = build_sensitivity_grid(dcf_result, config)
    except Exception as exc:
        logger.error("Grid computation error: %s", exc)
        return 2

    nan_count = int(grid_df.isna().sum().sum())
    if nan_count > 0:
        logger.error("Sensitivity grid contains %d NaN cells — likely WACC ≤ TGR in some cells", nan_count)
        return 2

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        ts = dcf_result["run_timestamp"]
        slug = dcf_result["company_name"].lower().replace(" ", "_").replace("/", "_")
        out_path = args.output_dir / f"{slug}_{ts}_sensitivity.csv"
        grid_df.to_csv(out_path)
        logger.info("Sensitivity grid written: %s (%dx%d)", out_path, *grid_df.shape)
        print(json.dumps({"status": "success", "output_path": str(out_path), "shape": list(grid_df.shape)}))
        return 0
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
