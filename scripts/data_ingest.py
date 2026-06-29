"""
AUCTUS Capital Partners AG — Financial Data Ingestion

Normalizes financial tables from Excel (.xlsx) or CSV sources into the standard
financial schema required by dcf_engine.py. Handles multi-sheet Excel, currency
detection, and header row auto-detection.

Usage:
    python scripts/data_ingest.py \
        --input data/inputs/company_im.xlsx \
        --output data/inputs/ \
        --company-name "Muster GmbH"

Output:
    data/inputs/{company_slug}_financials.csv
    Columns: year, revenue, ebitda, d_and_a, capex, nwc_change, tax_rate
    All values in EUR millions.

Exit codes:
    0  success
    1  file not found or unreadable
    2  schema detection failure (cannot identify required columns)
    3  output write error
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = ["year", "revenue", "ebitda", "d_and_a", "capex", "nwc_change", "tax_rate"]

# Column name aliases: normalized name → list of possible source names (case-insensitive)
COLUMN_ALIASES: dict[str, list[str]] = {
    "year": ["year", "fiscal_year", "fy", "geschäftsjahr", "période"],
    "revenue": ["revenue", "revenues", "umsatz", "net_revenue", "net_sales", "sales", "turnover"],
    "ebitda": ["ebitda", "ebitda_reported", "operating_ebitda"],
    "d_and_a": ["d_and_a", "da", "d&a", "depreciation", "amortization",
                 "depreciation_amortization", "abschreibungen"],
    "capex": ["capex", "capital_expenditure", "capex_net", "investitionen", "capex_gross"],
    "nwc_change": ["nwc_change", "change_in_nwc", "delta_nwc", "working_capital_change",
                   "änderung_nwc"],
    "tax_rate": ["tax_rate", "effective_tax_rate", "steuersatz", "eff_tax"],
}


def _match_column(source_cols: list[str], target: str) -> str | None:
    aliases = COLUMN_ALIASES.get(target, [target])
    source_lower = {c.lower().strip().replace(" ", "_"): c for c in source_cols}
    for alias in aliases:
        normalized = alias.lower().strip().replace(" ", "_")
        if normalized in source_lower:
            return source_lower[normalized]
    return None


def _detect_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    """Detect column aliases and rename to standard schema."""
    rename_map: dict[str, str] = {}
    missing: list[str] = []
    for target in OUTPUT_COLUMNS:
        matched = _match_column(list(df.columns), target)
        if matched:
            rename_map[matched] = target
        elif target == "tax_rate":
            logger.warning("tax_rate column not found — defaulting to 0.29 (DACH average)")
            df["tax_rate"] = 0.29
        else:
            missing.append(target)
    if missing:
        raise ValueError(f"Cannot map required columns: {missing}. Available: {list(df.columns)}")
    return df.rename(columns=rename_map)


def _normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Convert thousands (EUR k) to millions (EUR m) if values suggest k-scale."""
    revenue_col = df["revenue"]
    if revenue_col.max() > 10_000:
        logger.info("Revenue values appear to be in EUR thousands — dividing by 1000")
        for col in ["revenue", "ebitda", "d_and_a", "capex", "nwc_change"]:
            if col in df.columns:
                df[col] = df[col] / 1000.0
    return df


def load_excel(path: Path) -> pd.DataFrame:
    """Load the first sheet that looks like a P&L from an Excel file."""
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet)
            df.columns = [str(c) for c in df.columns]
            if len(df) >= 3 and len(df.columns) >= 4:
                logger.info("Using Excel sheet: '%s'", sheet)
                return df
        except Exception:
            continue
    raise ValueError(f"No valid sheet found in {path}")


def ingest(input_path: Path, output_dir: Path, company_name: str) -> Path:
    suffix = input_path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        raw_df = load_excel(input_path)
    elif suffix == ".csv":
        raw_df = pd.read_csv(input_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    df = _detect_and_rename(raw_df)
    df = df[OUTPUT_COLUMNS].dropna(subset=["year", "revenue"])
    df["year"] = df["year"].astype(int)
    df = _normalize_currency(df)
    df = df.sort_values("year").reset_index(drop=True)

    slug = company_name.lower().replace(" ", "_").replace("/", "_")
    output_path = output_dir / f"{slug}_financials.csv"
    df.to_csv(output_path, index=False)
    logger.info("Ingest complete: %d years written to %s", len(df), output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Financial Data Ingest")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, dest="output_dir")
    parser.add_argument("--company-name", type=str, default="company", dest="company_name")
    args = parser.parse_args()

    try:
        if not args.input.exists():
            logger.error("Input file not found: %s", args.input)
            return 1
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = ingest(args.input, args.output_dir, args.company_name)
        print(json.dumps({"status": "success", "output_path": str(out_path)}))
        return 0
    except ValueError as exc:
        logger.error("Schema detection failure: %s", exc)
        return 2
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 3


if __name__ == "__main__":
    sys.exit(main())
