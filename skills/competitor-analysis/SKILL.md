---
name: competitor-analysis
version: "1.0.0"
description: >
  Identifies, screens, and scores buy-and-build add-on acquisition targets
  in fragmented European/DACH mid-market niches. Produces a ranked target
  matrix (CSV + markdown report) filtered against AUCTUS investment criteria.
triggers:
  - "analyze competitors"
  - "map the market"
  - "scout add-on targets"
  - "target screening"
  - "build target list"
  - "find acquisition targets"
inputs:
  required:
    - "Sector description OR data/market/candidates.csv with company universe"
  optional:
    - "data/inputs/platform_profile.md (existing platform context)"
refs:
  scoring_rubric: "skills/competitor-analysis/refs/scoring-rubric.md"
  sector_taxonomy: "skills/competitor-analysis/refs/sector-taxonomy.yaml"
  output_template: "skills/competitor-analysis/refs/output-template.md"
  investment_criteria: "config/auctus_criteria.yaml"
scripts:
  - "scripts/target_scorer.py"
outputs:
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_targets.csv"
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_report.md"
---

## STEP 1 — SECTOR DEFINITION

Read `skills/competitor-analysis/refs/sector-taxonomy.yaml`.
Map the user's sector request to the taxonomy entry.
Extract: NACE codes, sub-segment definitions, and market fragmentation indicators.
Record the canonical sector slug (e.g. `hvac_services`) for use in output filenames.

## STEP 2 — INVESTMENT CRITERIA LOAD

Read `config/auctus_criteria.yaml`.
Extract the active `hard_filters` block and `scoring_weights` block.
These values are immutable for this workflow run. Do not modify them.
Note the `recommendation_bands` thresholds for use in Step 7.

## STEP 3 — UNIVERSE CONSTRUCTION

If `data/market/candidates.csv` exists and is non-empty: load it as the input universe.
If no file exists: use the `brave-search` MCP tool to identify companies matching
sector + geography criteria from Step 2. Source priority:
  a. Creditreform / Bisnode DACH registries
  b. Handelsregister (DE commercial register) search
  c. Industry association member directories
  d. LinkedIn company search (headcount as revenue proxy)

Cap the initial longlist at 50 companies.
Save raw results to `data/market/{sector}_raw_{timestamp}.json`.
Record: company name, country, estimated revenue range, website, data source.

## STEP 4 — DATA ENRICHMENT

For each company in the longlist: use the `fetch` MCP tool to retrieve public
profile data (website, LinkedIn company page, news mentions).
Append enriched fields: ownership type (founder/family/PE/listed), approximate
headcount, any public revenue disclosures, customer concentration indicators.
Do not call external APIs with any client-confidential data.

## STEP 5 — HARD FILTER PASS

Read `skills/competitor-analysis/refs/scoring-rubric.md` **Section 1: Hard Filters**.
Apply each filter from `config/auctus_criteria.yaml → hard_filters` to every company.
Discard any company failing any single hard filter.
Save the filtered universe to `data/market/{sector}_filtered_{timestamp}.csv`.
Log: total candidates in, exclusion reason per rejected company, total passing.

## STEP 6 — QUANTITATIVE SCORING

Read `skills/competitor-analysis/refs/scoring-rubric.md` **Section 2: Scoring Matrix**.
Run:

```bash
python scripts/target_scorer.py \
  --targets data/market/{sector}_filtered_{timestamp}.csv \
  --criteria config/auctus_criteria.yaml \
  --output-dir outputs/target_matrices/
```

Check exit code. If non-zero: read stderr, stop, report error to user.
Do NOT modify score values output by the script.

## STEP 7 — REPORT COMPOSITION

Read the script-output CSV from `outputs/target_matrices/`.
Read `skills/competitor-analysis/refs/output-template.md`.
Compose the markdown report following the template structure exactly.
Limit final shortlist to top 15 scored companies.
Write report to `outputs/target_matrices/{sector}_{timestamp}_report.md`.

Include a 3-paragraph market commentary covering:
  1. Niche fragmentation level and consolidation rationale
  2. Top 3 recommended targets with strategic fit narrative
  3. Key risks and information gaps

## STEP 8 — QUALITY GATE

Run: `pytest tests/test_target_scorer.py -v`
Must exit 0.
Verify output CSV has all required columns:
  [company, revenue_eur_m, ebitda_margin_pct, geography, ownership, auctus_score, recommendation]
Verify output report is non-empty.
Append completion entry to `logs/agent_activity.log`.

## EXIT CONDITION

Deliver paths to:
  1. Ranked target matrix CSV
  2. Markdown report

State: total candidates identified, hard-filter exclusions count, final shortlist count.
