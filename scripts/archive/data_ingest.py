"""
AUCTUS Capital Partners AG — Financial Data Ingestion

Normalizes financial tables into the standard schema required by dcf_engine.py.
Supports two ingestion modes:

  file        (default) — Read from local Excel (.xlsx) or CSV files.
  factset-mcp           — Fetch live public financials from FactSet via the
                          Anthropic MCP beta.  Requires ANTHROPIC_API_KEY,
                          FACTSET_MCP_ENDPOINT, and FACTSET_MCP_TOKEN.

Architecture note
-----------------
The FactSet connector is authorised for PUBLIC market data only.  Confidential
deal inputs (management projections, IMs, client names) must never be sent to
the FactSet endpoint.  See mcp_config.json for the full data-policy declaration.

Usage — file mode (unchanged):
    python scripts/data_ingest.py \\
        --input data/inputs/company_im.xlsx \\
        --output data/inputs/ \\
        --company-name "Muster GmbH"

Usage — FactSet MCP mode:
    python scripts/data_ingest.py \\
        --source factset-mcp \\
        --entity-id "000C7D-E" \\
        --currency EUR \\
        --output data/inputs/ \\
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
    4  FactSet MCP fetch failure
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

# ── FactSet schema types ───────────────────────────────────────────────────────

@dataclass
class FactSetFinancialRow:
    """One fiscal year of FactSet-normalised financials (EUR millions)."""
    year: int
    revenue: float
    ebitda: float
    d_and_a: float
    capex: float
    nwc_change: float
    tax_rate: float


@dataclass
class FactSetTradingComps:
    """FactSet trading comparables payload for a single peer company."""
    ticker: str
    name: str
    ev_eur_m: float
    ebitda_ltm_eur_m: float
    revenue_ltm_eur_m: float
    ev_ebitda: float
    ev_revenue: float
    source: str = "factset_mcp"


@dataclass
class FactSetPrecedentTransaction:
    """FactSet precedent transaction record."""
    target_name: str
    acquirer_name: str
    close_year: int
    ev_eur_m: float
    ev_ebitda_multiple: float
    sector: str
    geography: str
    source: str = "factset_mcp"


@dataclass
class FactSetMCPResponse:
    """Aggregated response from a FactSet MCP fetch session."""
    entity_id: str
    company_name: str
    financials: list[FactSetFinancialRow] = field(default_factory=list)
    trading_comps: list[FactSetTradingComps] = field(default_factory=list)
    precedent_transactions: list[FactSetPrecedentTransaction] = field(default_factory=list)
    raw_tool_responses: list[dict[str, Any]] = field(default_factory=list)


# ── FactSet MCP client ─────────────────────────────────────────────────────────

class FactSetMCPClient:
    """
    Routes FactSet data queries through the Anthropic MCP beta.

    The client creates a Claude message with access to the configured FactSet
    MCP server.  Claude uses the FactSet tools to retrieve public market data
    and returns a structured JSON payload which is then deserialised into
    FactSetMCPResponse.

    Authorisation note:  This client may only fetch PUBLIC FactSet data
    (entity financials, trading multiples, precedent transactions, sector
    benchmarks).  Passing confidential deal data in the prompt is prohibited.
    """

    _FACTSET_TOOLS = [
        "factset_entity_search",
        "factset_entity_financials",
        "factset_trading_multiples",
        "factset_precedent_transactions",
        "factset_industry_benchmarks",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        mcp_endpoint: str | None = None,
        mcp_token: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._mcp_endpoint = mcp_endpoint or os.environ.get("FACTSET_MCP_ENDPOINT", "")
        self._mcp_token = mcp_token or os.environ.get("FACTSET_MCP_TOKEN", "")
        self._model = model
        self._max_retries = max_retries

        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for FactSet MCP mode")
        if not self._mcp_endpoint:
            raise ValueError(
                "FACTSET_MCP_ENDPOINT is required for FactSet MCP mode. "
                "Set the environment variable or pass mcp_endpoint explicitly."
            )

    def fetch_entity_financials(
        self,
        entity_id: str,
        company_name: str,
        currency: str = "EUR",
        years: int = 5,
    ) -> FactSetMCPResponse:
        """
        Fetch historical annual financials and public comps for entity_id.

        Sends a structured prompt to Claude with the FactSet MCP server attached.
        Claude calls the relevant FactSet tools (entity_financials, trading_multiples,
        precedent_transactions) and returns a machine-readable JSON payload.
        """
        try:
            import anthropic  # deferred import — optional dependency
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for FactSet MCP mode. "
                "Install it with: pip install anthropic>=0.30"
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        mcp_server: dict[str, Any] = {
            "type": "url",
            "name": "factset",
            "url": self._mcp_endpoint,
            "authorization_token": self._mcp_token,
            "tool_configuration": {
                "enabled": True,
                "allowed_tools": self._FACTSET_TOOLS,
            },
        }

        prompt = (
            f"Using the factset MCP tools, retrieve the following PUBLIC market data "
            f"for FactSet entity ID '{entity_id}' (company: {company_name}).\n\n"
            f"1. Call factset_entity_financials to retrieve {years} years of annual "
            f"income-statement and cash-flow data in {currency}. Required fields: "
            f"fiscal_year, revenue, ebitda, depreciation_amortization, capex, "
            f"nwc_change, effective_tax_rate.\n\n"
            f"2. Call factset_trading_multiples to retrieve the top 5 public "
            f"sector-comparable companies with EV, LTM EBITDA, LTM Revenue, and "
            f"EV/EBITDA in {currency}.\n\n"
            f"3. Call factset_precedent_transactions to retrieve up to 10 closed "
            f"M&A transactions in the same sector from the past 5 years, including "
            f"target name, acquirer, close year, EV ({currency}), and EV/EBITDA multiple.\n\n"
            f"Return ONLY a JSON object with this exact schema (no prose):\n"
            f"{{\n"
            f'  "entity_id": "{entity_id}",\n'
            f'  "company_name": "{company_name}",\n'
            f'  "financials": [{{\n'
            f'    "year": int, "revenue": float, "ebitda": float,\n'
            f'    "d_and_a": float, "capex": float, "nwc_change": float, "tax_rate": float\n'
            f'  }}],\n'
            f'  "trading_comps": [{{\n'
            f'    "ticker": str, "name": str, "ev_eur_m": float,\n'
            f'    "ebitda_ltm_eur_m": float, "revenue_ltm_eur_m": float,\n'
            f'    "ev_ebitda": float, "ev_revenue": float\n'
            f'  }}],\n'
            f'  "precedent_transactions": [{{\n'
            f'    "target_name": str, "acquirer_name": str, "close_year": int,\n'
            f'    "ev_eur_m": float, "ev_ebitda_multiple": float,\n'
            f'    "sector": str, "geography": str\n'
            f'  }}]\n'
            f"}}"
        )

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = client.beta.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    betas=["mcp-client-2025-04-04"],
                    mcp_servers=[mcp_server],
                    messages=[{"role": "user", "content": prompt}],
                )
                # Extract the text block from the response
                text_content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text_content += block.text
                raw_payload = json.loads(text_content)
                return self._deserialise(raw_payload)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "FactSet MCP fetch attempt %d/%d failed: %s",
                    attempt, self._max_retries, exc,
                )
                if attempt < self._max_retries:
                    time.sleep(2 ** attempt)

        raise RuntimeError(
            f"FactSet MCP fetch failed after {self._max_retries} attempts. "
            f"Last error: {last_exc}"
        )

    def fetch_trading_comps(
        self,
        sector: str,
        geographies: list[str] | None = None,
        limit: int = 10,
    ) -> list[FactSetTradingComps]:
        """Fetch trading comps for a sector from FactSet, returning normalized rows."""
        geo_filter = ", ".join(geographies or ["DE", "AT", "CH", "NL", "BE", "FR"])
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for FactSet MCP mode."
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        mcp_server: dict[str, Any] = {
            "type": "url",
            "name": "factset",
            "url": self._mcp_endpoint,
            "authorization_token": self._mcp_token,
            "tool_configuration": {
                "enabled": True,
                "allowed_tools": ["factset_trading_multiples"],
            },
        }
        prompt = (
            f"Using factset_trading_multiples, retrieve up to {limit} public companies "
            f"in sector '{sector}' listed in {geo_filter}. "
            f"Return ONLY JSON: "
            f'[{{"ticker": str, "name": str, "ev_eur_m": float, '
            f'"ebitda_ltm_eur_m": float, "revenue_ltm_eur_m": float, '
            f'"ev_ebitda": float, "ev_revenue": float}}]'
        )
        try:
            response = client.beta.messages.create(
                model=self._model,
                max_tokens=2048,
                betas=["mcp-client-2025-04-04"],
                mcp_servers=[mcp_server],
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            raw = json.loads(text)
            return [
                FactSetTradingComps(
                    ticker=r["ticker"],
                    name=r["name"],
                    ev_eur_m=float(r["ev_eur_m"]),
                    ebitda_ltm_eur_m=float(r["ebitda_ltm_eur_m"]),
                    revenue_ltm_eur_m=float(r["revenue_ltm_eur_m"]),
                    ev_ebitda=float(r["ev_ebitda"]),
                    ev_revenue=float(r["ev_revenue"]),
                )
                for r in raw
            ]
        except Exception as exc:
            raise RuntimeError(f"FactSet trading comps fetch failed: {exc}") from exc

    def fetch_precedent_transactions(
        self,
        sector: str,
        geographies: list[str] | None = None,
        years_back: int = 5,
        limit: int = 20,
    ) -> list[FactSetPrecedentTransaction]:
        """Fetch precedent M&A transactions for a sector from FactSet."""
        geo_filter = ", ".join(geographies or ["DE", "AT", "CH", "NL", "BE", "FR"])
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for FactSet MCP mode."
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        mcp_server: dict[str, Any] = {
            "type": "url",
            "name": "factset",
            "url": self._mcp_endpoint,
            "authorization_token": self._mcp_token,
            "tool_configuration": {
                "enabled": True,
                "allowed_tools": ["factset_precedent_transactions"],
            },
        }
        prompt = (
            f"Using factset_precedent_transactions, retrieve up to {limit} closed M&A "
            f"transactions in sector '{sector}' from the past {years_back} years "
            f"in geographies: {geo_filter}. "
            f"Return ONLY JSON: "
            f'[{{"target_name": str, "acquirer_name": str, "close_year": int, '
            f'"ev_eur_m": float, "ev_ebitda_multiple": float, '
            f'"sector": str, "geography": str}}]'
        )
        try:
            response = client.beta.messages.create(
                model=self._model,
                max_tokens=2048,
                betas=["mcp-client-2025-04-04"],
                mcp_servers=[mcp_server],
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in response.content if hasattr(b, "text"))
            raw = json.loads(text)
            return [
                FactSetPrecedentTransaction(
                    target_name=r["target_name"],
                    acquirer_name=r["acquirer_name"],
                    close_year=int(r["close_year"]),
                    ev_eur_m=float(r["ev_eur_m"]),
                    ev_ebitda_multiple=float(r["ev_ebitda_multiple"]),
                    sector=r["sector"],
                    geography=r["geography"],
                )
                for r in raw
            ]
        except Exception as exc:
            raise RuntimeError(f"FactSet precedent transactions fetch failed: {exc}") from exc

    @staticmethod
    def _deserialise(payload: dict[str, Any]) -> FactSetMCPResponse:
        financials = [
            FactSetFinancialRow(
                year=int(r["year"]),
                revenue=float(r["revenue"]),
                ebitda=float(r["ebitda"]),
                d_and_a=float(r["d_and_a"]),
                capex=float(r["capex"]),
                nwc_change=float(r["nwc_change"]),
                tax_rate=float(r["tax_rate"]),
            )
            for r in payload.get("financials", [])
        ]
        trading_comps = [
            FactSetTradingComps(
                ticker=r["ticker"],
                name=r["name"],
                ev_eur_m=float(r["ev_eur_m"]),
                ebitda_ltm_eur_m=float(r["ebitda_ltm_eur_m"]),
                revenue_ltm_eur_m=float(r["revenue_ltm_eur_m"]),
                ev_ebitda=float(r["ev_ebitda"]),
                ev_revenue=float(r["ev_revenue"]),
            )
            for r in payload.get("trading_comps", [])
        ]
        precedents = [
            FactSetPrecedentTransaction(
                target_name=r["target_name"],
                acquirer_name=r["acquirer_name"],
                close_year=int(r["close_year"]),
                ev_eur_m=float(r["ev_eur_m"]),
                ev_ebitda_multiple=float(r["ev_ebitda_multiple"]),
                sector=r["sector"],
                geography=r["geography"],
            )
            for r in payload.get("precedent_transactions", [])
        ]
        return FactSetMCPResponse(
            entity_id=payload.get("entity_id", ""),
            company_name=payload.get("company_name", ""),
            financials=financials,
            trading_comps=trading_comps,
            precedent_transactions=precedents,
        )


def factset_response_to_df(response: FactSetMCPResponse) -> pd.DataFrame:
    """Convert FactSetMCPResponse financials to the standard AUCTUS financial DataFrame."""
    rows = [
        {
            "year": row.year,
            "revenue": row.revenue,
            "ebitda": row.ebitda,
            "d_and_a": row.d_and_a,
            "capex": row.capex,
            "nwc_change": row.nwc_change,
            "tax_rate": row.tax_rate,
        }
        for row in response.financials
    ]
    df = pd.DataFrame(rows)
    return df[OUTPUT_COLUMNS].sort_values("year").reset_index(drop=True)


def factset_comps_to_df(response: FactSetMCPResponse) -> pd.DataFrame:
    """Convert FactSet trading comps to a peer_group.csv-compatible DataFrame."""
    rows = [
        {
            "name": c.name,
            "ticker": c.ticker,
            "sector": "factset_derived",
            "ev_eur_m": c.ev_eur_m,
            "ebitda_ltm_eur_m": c.ebitda_ltm_eur_m,
            "revenue_ltm_eur_m": c.revenue_ltm_eur_m,
            "ev_ebitda": c.ev_ebitda,
            "ev_revenue": c.ev_revenue,
            "source": c.source,
        }
        for c in response.trading_comps
    ]
    return pd.DataFrame(rows)


def factset_precedents_to_df(response: FactSetMCPResponse) -> pd.DataFrame:
    """Convert FactSet precedent transactions to a precedent_transactions.csv-compatible DataFrame."""
    rows = [
        {
            "target": p.target_name,
            "acquirer": p.acquirer_name,
            "year": p.close_year,
            "ev_eur_m": p.ev_eur_m,
            "ev_ebitda_multiple": p.ev_ebitda_multiple,
            "sector": p.sector,
            "geography": p.geography,
            "source": p.source,
        }
        for p in response.precedent_transactions
    ]
    return pd.DataFrame(rows)


# ── Local file ingestion (unchanged from v1.0) ────────────────────────────────

def _match_column(source_cols: list[str], target: str) -> str | None:
    aliases = COLUMN_ALIASES.get(target, [target])
    source_lower = {c.lower().strip().replace(" ", "_"): c for c in source_cols}
    for alias in aliases:
        normalized = alias.lower().strip().replace(" ", "_")
        if normalized in source_lower:
            return source_lower[normalized]
    return None


def _detect_and_rename(df: pd.DataFrame) -> pd.DataFrame:
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
    revenue_col = df["revenue"]
    if revenue_col.max() > 10_000:
        logger.info("Revenue values appear to be in EUR thousands — dividing by 1000")
        for col in ["revenue", "ebitda", "d_and_a", "capex", "nwc_change"]:
            if col in df.columns:
                df[col] = df[col] / 1000.0
    return df


def load_excel(path: Path) -> pd.DataFrame:
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
    """Ingest from a local Excel or CSV file."""
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


def ingest_from_factset(
    entity_id: str,
    company_name: str,
    output_dir: Path,
    currency: str = "EUR",
    years: int = 5,
    write_comps: bool = True,
    write_precedents: bool = True,
) -> dict[str, Path]:
    """
    Fetch financials, trading comps, and precedents from FactSet MCP and write
    them to the canonical AUCTUS data directories.

    Returns a dict of {artifact_name: path} for all written files.
    """
    client = FactSetMCPClient()
    logger.info(
        "Fetching FactSet data for entity '%s' (%s) over %d years",
        entity_id, company_name, years,
    )
    response = client.fetch_entity_financials(
        entity_id=entity_id,
        company_name=company_name,
        currency=currency,
        years=years,
    )

    if not response.financials:
        raise ValueError(
            f"FactSet returned no financial rows for entity '{entity_id}'. "
            "Verify entity ID and subscription permissions."
        )

    slug = company_name.lower().replace(" ", "_").replace("/", "_")
    written: dict[str, Path] = {}

    # Financials → data/inputs/{slug}_financials.csv
    fin_df = factset_response_to_df(response)
    fin_path = output_dir / f"{slug}_financials.csv"
    fin_df.to_csv(fin_path, index=False)
    written["financials"] = fin_path
    logger.info(
        "FactSet financials written: %d years → %s", len(fin_df), fin_path
    )

    # Trading comps → data/comps/peer_group.csv (appends / replaces FactSet-source rows)
    if write_comps and response.trading_comps:
        comps_dir = Path("data/comps")
        comps_dir.mkdir(parents=True, exist_ok=True)
        comps_df = factset_comps_to_df(response)
        comps_path = comps_dir / f"{slug}_factset_comps.csv"
        comps_df.to_csv(comps_path, index=False)
        written["trading_comps"] = comps_path
        logger.info(
            "FactSet comps written: %d peers → %s", len(comps_df), comps_path
        )

    # Precedent transactions → data/comps/{slug}_factset_precedents.csv
    if write_precedents and response.precedent_transactions:
        comps_dir = Path("data/comps")
        comps_dir.mkdir(parents=True, exist_ok=True)
        prec_df = factset_precedents_to_df(response)
        prec_path = comps_dir / f"{slug}_factset_precedents.csv"
        prec_df.to_csv(prec_path, index=False)
        written["precedent_transactions"] = prec_path
        logger.info(
            "FactSet precedents written: %d transactions → %s",
            len(prec_df), prec_path,
        )

    return written


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="AUCTUS Financial Data Ingest")
    parser.add_argument(
        "--source",
        choices=["file", "factset-mcp"],
        default="file",
        help="Data source: 'file' for local Excel/CSV (default) or 'factset-mcp' for live FactSet pull.",
    )
    # File-mode args
    parser.add_argument("--input", type=Path, default=None)
    # FactSet-mode args
    parser.add_argument("--entity-id", type=str, default=None, dest="entity_id",
                        help="FactSet entity ID (FSYM_ID or ticker) for factset-mcp mode.")
    parser.add_argument("--currency", type=str, default="EUR")
    parser.add_argument("--factset-years", type=int, default=5, dest="factset_years")
    # Common
    parser.add_argument("--output", type=Path, required=True, dest="output_dir")
    parser.add_argument("--company-name", type=str, default="company", dest="company_name")
    args = parser.parse_args()

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)

        if args.source == "factset-mcp":
            if not args.entity_id:
                logger.error("--entity-id is required when --source=factset-mcp")
                return 1
            written = ingest_from_factset(
                entity_id=args.entity_id,
                company_name=args.company_name,
                output_dir=args.output_dir,
                currency=args.currency,
                years=args.factset_years,
            )
            print(json.dumps({
                "status": "success",
                "source": "factset-mcp",
                "written_files": {k: str(v) for k, v in written.items()},
            }))
            return 0

        # File mode
        if not args.input:
            logger.error("--input is required when --source=file")
            return 1
        if not args.input.exists():
            logger.error("Input file not found: %s", args.input)
            return 1
        out_path = ingest(args.input, args.output_dir, args.company_name)
        print(json.dumps({"status": "success", "output_path": str(out_path)}))
        return 0

    except ValueError as exc:
        logger.error("Schema detection failure: %s", exc)
        return 2
    except OSError as exc:
        logger.error("Output write error: %s", exc)
        return 3
    except RuntimeError as exc:
        logger.error("FactSet MCP fetch failure: %s", exc)
        return 4


if __name__ == "__main__":
    sys.exit(main())
