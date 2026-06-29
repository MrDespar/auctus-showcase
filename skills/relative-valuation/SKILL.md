---
name: relative-valuation
version: "1.0.0"
description: >
  Maps a target company against a curated public comparable peer group and
  historical precedent transactions. Outputs a trading comps multiples table
  and precedent deal matrix with an implied Enterprise Value range.
  All multiple calculations are delegated to Python scripts.
triggers:
  - "run comps"
  - "trading comps"
  - "precedent transactions"
  - "relative valuation"
  - "market multiples"
  - "comparable company analysis"
  - "EV/EBITDA multiple"
inputs:
  required:
    - "data/inputs/{company}_financials.csv (at minimum LTM EBITDA and Revenue)"
    - "Sector / subsector description for peer group selection"
  optional:
    - "data/comps/peer_group.csv (pre-defined peer list with tickers)"
    - "data/comps/precedent_transactions.csv (pre-loaded deal database)"
    - "target_ebitda_eur_m — explicit LTM EBITDA for implied EV calculation"
refs:
  peer_criteria: "skills/relative-valuation/refs/peer-group-criteria.md"
  multiples_benchmarks: "skills/relative-valuation/refs/multiples-benchmarks.yaml"
  precedent_filters: "skills/relative-valuation/refs/precedent-filters.yaml"
  sector_benchmarks: "config/sector_benchmarks.yaml"
scripts:
  - "scripts/comps_engine.py"
  - "scripts/precedent_engine.py"
outputs:
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_trading_comps.csv"
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_precedents.csv"
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_valuation_report.md"
---

## STEP 1 — PEER GROUP DEFINITION

Read `skills/relative-valuation/refs/peer-group-criteria.md`.
Identify the peer selection criteria for this sector (inclusion rules, exclusion rules,
minimum data requirements).

If `data/comps/peer_group.csv` exists: load and validate against peer criteria.
If not: use `brave-search` + `fetch` MCP tools to identify 5–10 publicly listed
comparables matching: sector, revenue size (€10m–€500m), geography (EU/global peers
of similar profile), business model similarity.
Save identified peers to `data/comps/peer_group_{sector}_{timestamp}.csv`.

**Minimum requirement: 3 peers with publicly available LTM financials.**
If fewer than 3 qualify in the primary sector: read peer-group-criteria.md
Section "Adjacent Sector Expansions" and widen scope. Log the expansion decision.

## STEP 2 — BENCHMARK REFERENCE LOAD

Read `skills/relative-valuation/refs/multiples-benchmarks.yaml`.
Read `config/sector_benchmarks.yaml` for the relevant sector.
Extract: EV/EBITDA median, P25, P75; EV/Revenue median.
**These benchmarks are for sanity-checking only. Do NOT use them for computation.**
All multiples are calculated by the Python script in Step 3.

## STEP 3 — TRADING COMPS EXECUTION

Run:
```bash
python scripts/comps_engine.py \
  --peers data/comps/peer_group_{sector}_{timestamp}.csv \
  --target data/inputs/{company}_financials.csv \
  --output-dir outputs/valuation_reports/
```

Script computes for each peer: LTM EV/EBITDA, LTM EV/Revenue, LTM EV/EBIT.
Derives: median, mean, 25th percentile, 75th percentile across peer group.
Applies implied EV range to target using P25–P75 EV/EBITDA band.

Check exit code. Non-zero = stop and report error verbatim to user.
Read the output JSON file and extract `implied_ev_range_eur_m` field.

## STEP 4 — PRECEDENT TRANSACTIONS

Read `skills/relative-valuation/refs/precedent-filters.yaml` for deal filter parameters.

If `data/comps/precedent_transactions.csv` exists: load and apply filters from the YAML.
If not: use `brave-search` to find closed M&A transactions in the sector (past 10 years,
DACH + wider Europe, EV €10m–€500m). Save raw data to
`data/comps/precedent_raw_{timestamp}.csv`.

Run:
```bash
python scripts/precedent_engine.py \
  --transactions data/comps/precedent_transactions.csv \
  --filters config/auctus_criteria.yaml \
  --output-dir outputs/valuation_reports/
```

Check exit code. Non-zero = stop and report error verbatim to user.

Minimum: 3 precedent deals. If fewer than 3 found: expand to wider Europe
geography and note the expansion in the comparability limitations section.

## STEP 5 — IMPLIED VALUATION CONSOLIDATION

Read the comps_results.json output from Step 3.
Read the precedent_results.json output from Step 4.
Extract `implied_ev_range_eur_m` from each.

Do NOT recompute the implied EV range. Read the field directly from JSON output.

Present three valuation reference points:
  1. Trading comps implied range (P25–P75 EV/EBITDA applied to target EBITDA)
  2. Precedent transactions implied range (P25–P75 EV/EBITDA from deals)
  3. Sector benchmark reference (from multiples-benchmarks.yaml — for context only)

## STEP 6 — REPORT COMPOSITION

Compose the markdown valuation report with:
  1. Header: company, sector, run date
  2. Peer group rationale (why these comparables were selected, any caveats)
  3. Trading comps table (from CSV — all peers with LTM EV/EBITDA and EV/Revenue)
  4. Comps summary statistics (median, mean, P25, P75)
  5. Precedent transactions table (from CSV — deal name, date, EV, EV/EBITDA, buyer type)
  6. Implied valuation range: trading comps vs. precedents vs. sector benchmarks
  7. Comparability limitations (data vintage, size differences, cycle adjustments)

Write to `outputs/valuation_reports/{company}_{timestamp}_valuation_report.md`.

## STEP 7 — QUALITY GATE

Run: `pytest tests/test_comps_engine.py -v`
Must exit 0.
Validate:
  - Trading comps CSV has ≥3 peer rows; no null multiples columns
  - Precedents CSV has ≥3 deal rows
  - Implied EV range is a valid interval: lower bound < upper bound
  - Report is non-empty

Append completion entry to `logs/agent_activity.log`.

## EXIT CONDITION

Deliver paths to: trading comps CSV, precedents CSV, valuation report.
State explicitly: implied EV range (€m), EV/EBITDA multiple range applied,
and number of comps / precedents used.
