---
name: dcf-valuation
version: "1.0.0"
description: >
  Constructs a deterministic 5-year Unlevered Free Cash Flow DCF model,
  discounts at WACC, computes terminal value via Gordon Growth Model, and
  outputs a precision sensitivity analysis grid (WACC × TGR). All arithmetic
  is delegated to Python scripts. The agent orchestrates; Python computes.
triggers:
  - "run DCF"
  - "value this company"
  - "discounted cash flow"
  - "build a DCF"
  - "intrinsic valuation"
  - "enterprise value"
inputs:
  required:
    - "data/inputs/{company}_financials.csv — columns: year, revenue, ebitda, d_and_a, capex, nwc_change, tax_rate"
    - "WACC as decimal (e.g. 0.12) OR sector name for lookup in refs"
    - "Terminal growth rate as decimal (e.g. 0.025)"
  optional:
    - "data/inputs/{company}_projections.csv — pre-built 5-year projection table"
    - "net_debt_eur_m — for equity bridge (enterprise → equity value)"
refs:
  wacc_assumptions: "skills/dcf-valuation/refs/wacc-assumptions.yaml"
  projection_guide: "skills/dcf-valuation/refs/projection-guide.md"
  sensitivity_config: "skills/dcf-valuation/refs/sensitivity-config.yaml"
  financial_constants: "config/financial_constants.yaml"
scripts:
  - "scripts/data_ingest.py"
  - "scripts/dcf_engine.py"
  - "scripts/sensitivity.py"
outputs:
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_cashflows.csv"
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_dcf_results.json"
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_sensitivity.csv"
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_report.md"
---

## STEP 1 — INPUT VALIDATION

Verify `data/inputs/{company}_financials.csv` exists and is readable.
Required columns: [year, revenue, ebitda, d_and_a, capex, nwc_change, tax_rate].
All values must be in EUR millions.

If source is Excel (.xlsx) or PDF, run ingest first:
```bash
python scripts/data_ingest.py \
  --input data/inputs/{source_file} \
  --output data/inputs/
```

Confirm at least 3 historical years are present. If fewer than 3 years available:
proceed but flag LOW_HISTORICAL_DEPTH in the report and reduce projection confidence.

## STEP 2 — WACC DETERMINATION

Read `skills/dcf-valuation/refs/wacc-assumptions.yaml`.
Also read `config/financial_constants.yaml` for macro assumptions.

Resolution order:
1. If user provided an explicit WACC decimal → use it; document source as "User-specified".
2. If user provided a sector name → look up `by_sector[sector].wacc_midpoint` from the YAML.
3. If sector is unknown → use `config/financial_constants.yaml → by_sector.default`.

Present the proposed WACC to the user with rationale. Do NOT proceed to Step 3
without explicit user confirmation of the WACC value.

## STEP 3 — PROJECTION APPROVAL

Read `skills/dcf-valuation/refs/projection-guide.md` for methodology.

If `data/inputs/{company}_projections.csv` exists:
  → Load and present the projection assumptions table to the user for confirmation.

If no projections file exists:
  → Derive revenue CAGR from the last 3 historical years (using compound growth formula).
  → Apply sector-typical EBITDA margin improvement trajectory from the guide.
  → Present all assumptions in a clear table to the user.
  → Await explicit confirmation before proceeding.
  → Write confirmed projections to `data/inputs/{company}_projections_approved.csv`.

## STEP 4 — DCF ENGINE EXECUTION

Run:
```bash
python scripts/dcf_engine.py \
  --input data/inputs/{company}_financials.csv \
  --projections data/inputs/{company}_projections_approved.csv \
  --wacc {confirmed_wacc} \
  --terminal-growth {confirmed_tgr} \
  --projection-years 5 \
  --output-dir outputs/dcf_models/
```

Check exit code. If non-zero: read `logs/` for the Python traceback, stop, and
report the error verbatim to the user. Do not attempt to estimate the output.

Read the output JSON file. Verify it contains:
  - enterprise_value_eur_m
  - terminal_value_eur_m
  - terminal_value_pct_of_ev
  - wacc_used
  - terminal_growth_rate_used
  - forecast_cash_flows (array)

**Circuit breaker:** If `terminal_value_pct_of_ev > 0.70`, stop immediately and
escalate to the user with the JSON path. Do not silently continue.

## STEP 5 — SENSITIVITY GRID

Read `skills/dcf-valuation/refs/sensitivity-config.yaml` for grid dimensions.
Run:
```bash
python scripts/sensitivity.py \
  --dcf-results outputs/dcf_models/{company}_{timestamp}_dcf_results.json \
  --output-dir outputs/dcf_models/
```

Grid must span: WACC ±200bps × TGR ±100bps (exact dimensions in sensitivity-config.yaml).
Check exit code. Non-zero = stop and report error.
Verify output CSV has no NaN cells before proceeding.

## STEP 6 — REPORT COMPOSITION

Read the four output files from `outputs/dcf_models/`.
Compose the markdown report with these sections:
  1. Header: company, run date, WACC, TGR, model version
  2. Historical financials summary (3-year table from input CSV)
  3. 5-year projection assumptions (confirmed in Step 3)
  4. Year-by-year UFCF table (from cashflows.csv)
  5. Enterprise value derivation: PV(FCFs) + PV(Terminal Value) = EV
  6. Equity bridge (if net_debt provided): EV − Net Debt = Equity Value
  7. Sensitivity heatmap (formatted text table from sensitivity.csv)
  8. WACC rationale paragraph

When citing numbers, always reference the source JSON key, e.g.:
  "Enterprise Value: €42.3m (source: dcf_results.json → enterprise_value_eur_m)"

Write to `outputs/dcf_models/{company}_{timestamp}_report.md`.

## STEP 7 — QUALITY GATE

Run: `pytest tests/test_dcf_engine.py -v --tb=short`
Must exit 0.
Validate:
  - NPV is a finite float and > 0
  - Sensitivity grid CSV has no NaN cells
  - All four output files exist and are non-empty
  - Terminal value ≤ 70% of EV (already checked at Step 4, confirm again)

Append completion entry to `logs/agent_activity.log`.

## EXIT CONDITION

Deliver paths to all four output files.
State explicitly: base case Enterprise Value (€m), WACC used, terminal growth rate used.
