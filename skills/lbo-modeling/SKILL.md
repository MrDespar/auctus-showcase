---
name: lbo-modeling
version: "1.0.0"
description: >
  Constructs a fully deterministic five-step Leveraged Buyout model for German
  Mittelstand acquisitions. Computes Sources & Uses, P&L down to Levered Free
  Cash Flow, a Senior TL / Notes debt waterfall with floating Euribor mechanics,
  exit MOIC and IRR, and an Entry × Exit multiple sensitivity grid. All arithmetic
  is delegated to scripts/lbo_engine.py. The agent orchestrates; Python computes.
triggers:
  - "run LBO"
  - "leveraged buyout"
  - "LBO model"
  - "debt waterfall"
  - "MOIC"
  - "returns analysis"
  - "entry multiple"
  - "exit multiple"
  - "equity IRR"
inputs:
  required:
    - "entry_ebitda_eur_m — LTM EBITDA at acquisition (€m)"
    - "entry_multiple — EV/EBITDA paid at entry"
    - "equity_pct + senior_debt_pct + notes_pct — capital structure (must sum to 1.0)"
    - "revenue_base_eur_m — LTM revenue at entry (€m)"
    - "revenue_growth_rates — comma-separated decimals, one per projection year"
    - "ebitda_margins — comma-separated decimals, one per projection year"
    - "exit_multiple — EV/EBITDA assumed at exit"
  optional:
    - "euribor — current rate as decimal (default: 0.039)"
    - "euribor_floor — floor as decimal (default: 0.00)"
    - "senior_spread_bps — senior TL spread in basis points (default: 375)"
    - "notes_rate — fixed rate decimal or floating spread (default: 9.5%)"
    - "senior_amort_pct — mandatory annual amortisation as % of original principal (default: 5%)"
    - "senior_cash_sweep_pct — fraction of LFCF swept to senior repayment (default: 50%)"
    - "advisor_fee_pct — M&A success fee as % of EV (default: 1.5%)"
    - "financing_fee_pct — debt arrangement fee as % of total debt (default: 2.0%)"
    - "capitalize_fees — True = add to Uses & amortise; False = expense year 1 (default: True)"
    - "tax_rate — corporate tax rate as decimal (default: DE 29.9%)"
    - "exit_year — hold period in years (default: 5)"
    - "projection_years — total forecast horizon (default: 5)"
refs:
  debt_structure_defaults: "skills/lbo-modeling/refs/debt-structure-defaults.yaml"
  sensitivity_config: "skills/lbo-modeling/refs/sensitivity-config.yaml"
  financial_constants: "config/financial_constants.yaml"
  auctus_criteria: "config/auctus_criteria.yaml"
scripts:
  - "scripts/lbo_engine.py"
outputs:
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_lbo_results.json"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_lbo_compact.json"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_projections.csv"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_sensitivity_irr.csv"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_model.xlsx"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_ic_report.md"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_ic_report.pdf"
---

## STEP 1 — INVESTMENT CRITERIA VALIDATION

Read `config/auctus_criteria.yaml`. Verify the target satisfies **all** hard filters:

| Filter | Threshold | Source key |
|--------|-----------|------------|
| Revenue (TTM) | €10m – €150m | `hard_filters.revenue_min_eur` / `revenue_max_eur` |
| Geography | DACH preferred; NL/BE/FR/IT/SE/DK/NO allowed | `hard_filters.geographies_allowed` |
| EBITDA margin | ≥8% floor | `hard_filters.ebitda_margin_min` |
| Customer concentration | No single customer >30% | `hard_filters.customer_concentration_max_single` |
| Excluded sectors | financial_services, real_estate, oil_gas | `hard_filters.excluded_sectors` |

If any hard filter fails: **stop**. Report the failing criterion verbatim. Do not proceed to Step 2.

## STEP 2 — CAPITAL STRUCTURE ASSUMPTIONS

Read `skills/lbo-modeling/refs/debt-structure-defaults.yaml`.
Read `config/financial_constants.yaml` for the target sector's `debt_spread_bps` and `target_debt_to_equity`.

Present the proposed capital structure to the user:

```
Entry EV:              €{entry_ebitda} × {entry_multiple}x = €{ev}m
─────────────────────────────────────────────────────────────
Equity:                {equity_pct}% = €{equity}m
Senior Term Loan:      {senior_pct}% = €{senior}m   @ Euribor ({euribor:.2%}) floor {floor:.2%} + {spread}bps
Notes / Sub-Debt:      {notes_pct}% = €{notes}m     @ {notes_rate:.2%} fixed
─────────────────────────────────────────────────────────────
Total Sources:         €{total_sources}m
─────────────────────────────────────────────────────────────
Acquisition Price:     €{ev}m
Advisor Fees (1.5%):   €{advisor_fees}m
Financing Fees (2.0%): €{financing_fees}m
─────────────────────────────────────────────────────────────
Total Uses:            €{total_uses}m
```

Await explicit user confirmation of the capital structure before proceeding to Step 3.

**Hard check:** Equity_pct + Senior_pct + Notes_pct must equal exactly 1.000.
If not, stop and report the imbalance.

## STEP 3 — PROJECTION ASSUMPTIONS

Present the 5-year operating assumptions:

| Year | Revenue (€m) | Growth | EBITDA (€m) | Margin |
|------|-------------|--------|-------------|--------|
| 1    | ...         | x.x%   | ...         | x.x%   |
| ...  | ...         | ...    | ...         | ...    |

Confirm:
- Revenue CAGR is consistent with the sector benchmark in `config/sector_benchmarks.yaml`.
- EBITDA margin trajectory is realistic (check `by_sector.{sector}.ev_ebitda_median` for context).
- D&A, CapEx, and NWC assumptions align with `config/financial_constants.yaml → projection_defaults`.

Await explicit user confirmation before proceeding.

## STEP 4 — LBO ENGINE EXECUTION

```bash
python scripts/lbo_engine.py \
  --company-name "{company_name}" \
  --geography "{geography}" \
  --entry-ebitda {entry_ebitda_eur_m} \
  --entry-multiple {entry_multiple} \
  --revenue-base {revenue_base_eur_m} \
  --equity-pct {equity_pct} \
  --senior-debt-pct {senior_debt_pct} \
  --notes-pct {notes_pct} \
  --euribor {euribor_rate} \
  --euribor-floor {euribor_floor} \
  --senior-spread-bps {senior_spread_bps} \
  --notes-rate {notes_fixed_rate} \
  --notes-fixed \
  --senior-amort-pct {senior_amort_pct_annual} \
  --senior-cash-sweep-pct {senior_cash_sweep_pct} \
  --advisor-fee-pct {advisor_fee_pct_ev} \
  --financing-fee-pct {financing_fee_pct_debt} \
  --capitalize-fees \
  --tax-rate {tax_rate} \
  --revenue-growth {revenue_growth_csv} \
  --ebitda-margins {ebitda_margins_csv} \
  --da-pct {da_pct_revenue} \
  --capex-pct {capex_pct_revenue} \
  --nwc-pct {nwc_pct_revenue_change} \
  --exit-year {exit_year} \
  --exit-multiple {exit_multiple} \
  --output-dir outputs/dcf_models/
```

**Exit code handling:**
- `0` → success; continue to Step 5.
- `1` → input validation error; read `logs/dcf_engine.log`, report verbatim to user, stop.
- `2` → computation error (IRR, arithmetic); read log, stop.
- `3` → output write failure; check disk permissions, stop.

Never attempt to estimate, recompute, or approximate any figure from the script output in your own context.

## STEP 5 — OUTPUT VERIFICATION

Read the compact JSON file: `outputs/dcf_models/lbo_{company}_{timestamp}_lbo_compact.json`.

Verify all of the following before proceeding:

**Sources & Uses balance:** `sources_uses.balance_check_eur_m` must be within €0.01m of zero.
If imbalanced by more than €0.01m: stop and escalate — do not silently continue.

**Debt service coverage:** For every year in `inflection_projections`, verify:
```
interest_coverage_x = ebit_eur_m / total_interest_eur_m
```
Must be ≥ 1.0 in all years. If any year has coverage < 1.0: flag as **COVENANT BREACH RISK** and
escalate to the user immediately. Do not silently continue.

**Leverage at exit:** `exit_metrics.leverage_at_exit_x` must be < `leverage_at_entry_x`.
If not: flag as **DELEVERAGING FAILURE** and escalate.

**MOIC / IRR sanity:**
- `irr_solver_converged` must be `true`. If `false`: report solver failure, stop.
- `moic` and `irr_pct` must be finite real numbers. NaN = stop.
- For AUCTUS to invest: MOIC ≥ 2.0× and IRR ≥ 20% are the minimum target thresholds.
  If either is missed: note as **BELOW IC HURDLE RATE** in the report but do not discard — present
  the deal and let the Investment Committee decide.

**Net interest vs. average balance trace:**
Read `projections` from the full JSON. For each year, verify:
```
senior_interest ≈ senior_opening × effective_senior_rate
notes_interest  ≈ notes_opening  × effective_notes_rate
```
Tolerance: ≤ €0.001m rounding error. Any larger discrepancy = computation error, escalate.

## STEP 6 — REPORT COMPOSITION

Compose the Investment Committee 1-pager with these sections (in order):

### 1. Header
Company name | Sector | Geography | Run date | Model version

### 2. Transaction Summary
```
Entry EV:    €{ev}m ({entry_multiple}× LTM EBITDA of €{ebitda}m)
Equity:      €{equity}m ({equity_pct}% of EV)
Total Debt:  €{total_debt}m ({leverage_x:.1f}× Entry EBITDA)
```

### 3. Capital Structure & Debt Terms
Table: Tranche | Amount | Rate | Amortisation | Structure
Include Euribor floor citation and spread above base rate.
For capitalised fees: show annual amortisation charge.

### 4. 5-Year P&L & Debt Waterfall
Full year-by-year table from `{company}_{timestamp}_projections.csv`:
Revenue | EBITDA | EBIT | Total Interest | EBT | Net Income | LFCF | Senior Debt | Total Debt

Show leverage (×) and interest coverage (×) for each year.

**Negative formatting convention:** losses and interest expenses shown as `(€Xm)` in parentheses.

### 5. Exit Analysis
```
Exit Year:      {exit_year}
Exit EBITDA:    €{exit_ebitda}m
Exit Multiple:  {exit_multiple}×
Exit EV:        €{exit_ev}m
Net Debt:       (€{net_debt}m)
Equity Proceeds: €{equity_proceeds}m
─────────────────────────────
MOIC:           {moic:.2f}×
IRR:            {irr_pct:.1f}%
```

All figures cited with their source JSON key.

### 6. Entry × Exit Sensitivity Grid
Reproduce the `_sensitivity_irr.csv` as a formatted markdown table.
Rows = Entry Multiples (low → high), Columns = Exit Multiples (low → high).
Highlight the base-case cell with **bold**.
Add a MOIC grid immediately below with same dimensions.

### 7. Investment Risks & Covenant Summary
- Minimum interest coverage year (from waterfall): state the year and ratio.
- Leverage at exit vs. entry.
- Sensitivity to Euribor +100bps (qualitative, not computed).
- Key operational assumptions (growth rate, margin trajectory).

Write the report to `outputs/dcf_models/lbo_{company}_{timestamp}_ic_report.md`.

## STEP 7 — QA VERIFICATION (ISOLATED REVIEW THREAD)

Trigger the zero-context QA hook via `deploy/scripts/trigger_agent.sh`:

```bash
bash deploy/scripts/trigger_agent.sh lbo_qa "{company_name}" \
  "compact_json=outputs/dcf_models/lbo_{company}_{timestamp}_lbo_compact.json"
```

The QA agent:
- Reads **only** `config/auctus_criteria.yaml`, `config/financial_constants.yaml`,
  and the compact JSON output.
- Has **zero** knowledge of the deal history, assumptions negotiated, or prior outputs.
- Independently verifies: interest traces against opening balances, negative formatting
  convention, MOIC/IRR arithmetic consistency, and AUCTUS hard-filter compliance.
- Returns PASS or FAIL with line-item citations.

If QA returns FAIL on any item: **stop delivery**, fix the flagged issue, and re-run from Step 4.

## STEP 8 — QUALITY GATE

```bash
pytest tests/test_lbo_engine.py -v --tb=short --cov=scripts/lbo_engine --cov-report=term-missing
```

Must exit with code **0**.

Verify:
1. All four output files exist and are non-empty.
2. `balance_check_eur_m` in compact JSON is within €0.01m of zero.
3. Sensitivity grid CSV has no NaN cells in the central 3×3 region.
4. `irr_solver_converged == true` in compact JSON.
5. `lbo_{company}_{timestamp}_model.xlsx` exists and is non-empty.

Append completion entry to `logs/agent_activity.log`:
```
[ISO8601] [lbo_modeling] [STATUS: SUCCESS] [outputs/dcf_models/lbo_{company}_{timestamp}_*]
```

## EXIT CONDITION

Deliver paths to all output files plus the IC report.

State explicitly:
- Entry EV (€m) and entry multiple (×)
- MOIC (×) and IRR (%)
- Exit EV (€m) and net debt at exit (€m)
- Whether AUCTUS IC hurdle rates (≥2.0× MOIC, ≥20% IRR) were met
- QA gate: PASS or FAIL
- Excel model path (`outputs/dcf_models/lbo_*_model.xlsx`)
- PDF report path (`outputs/dcf_models/lbo_*_ic_report.pdf`) — or note if pandoc was not installed
