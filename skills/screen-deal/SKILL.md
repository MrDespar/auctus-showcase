---
name: screen-deal
version: "2.1.0"
description: >
  Screens candidate companies using the full AUCTUS scoring stack: hard filters from
  auctus_criteria.yaml, weighted scoring model, and Phase-3 PE unit economics extensions.
  Implements the Anthropic deal-screening framework: extract deal facts → screen against
  criteria → Pass/Further Diligence/Hard Pass verdict → bull/bear/key questions format.
  Speed emphasis: screening should take minutes, not hours.
triggers:
  - "screen deal"
  - "screen candidate"
  - "evaluate candidate"
  - "score company"
  - "deal screen"
  - "PE screening"
  - "advanced screen"
  - "review this CIM"
  - "should we look at this"
  - "triage this teaser"
  - "deal screening"
inputs:
  required:
    - "targets_csv OR deal materials (CIM, teaser, description)"
    - "sector — sector label for output filename (e.g. hvac_services)"
  optional:
    - "criteria_yaml — override path (default: config/auctus_criteria.yaml)"
    - "ebitda_margin_pct column — enables unit economics and value bridge scoring"
    - "recurring_revenue_pct column — enables NDR proxy and LTV/CAC estimation"
    - "gross_margin_pct column — enables cost of delivery / scalability assessment"
    - "capex_pct column — enables free cash flow conversion proxy"
    - "tam_eur_m column — enables market sizing assessment"
    - "customer_concentration_top1_pct column — required for hard filter; improves cohort quality"
    - "ownership column — required for ownership scoring dimension"
    - "market_fragmentation column — enables fragmented market dimension scoring"
refs:
  investment_criteria: "config/auctus_criteria.yaml"
  scoring_rubric: "skills/competitor-analysis/refs/scoring-rubric.md"

outputs:
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_targets.xlsx"
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_screen.md"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG is a DACH-focused mid-market PE firm. Deal screening must be
fast (minutes, not hours) and must apply AUCTUS hard filters before any deeper analysis.
If a deal passes initial screen ("Further Diligence"), it triggers `/dcf-valuation`,
`/lbo-modeling`, and `/dd-checklist`.

### Prerequisites

None. This is the entry point for all inbound deal flow. Its output triggers downstream workflows:
- **Pass / Further Diligence** → triggers `/dcf-valuation`, `/lbo-modeling`, `/dd-checklist`
- **Hard Pass** → no further action; log exclusion reason

### Data Source Hierarchy

1. **User-provided data** — CIM, teaser, broker materials, deal description
2. **FactSet MCP** — enrichment with public comparable data (optional, use `--factset` flag)
3. **Web search / fetch** — fallback for missing company data

### Currency & Units

All monetary values in **EUR millions (€m)**. Revenue, EBITDA, and EV in €m.

### Execution Environment

**Single-candidate screen** (from CIM/teaser):
Follow Steps 1-4 below (Anthropic workflow), then score the target natively in your context window.

**Multi-candidate batch screen** (from CSV):
Score the candidates natively against the `auctus_criteria.yaml` and output the Excel matrices directly.

### AUCTUS Hard Filter Table

| Filter | AUCTUS Threshold | Check |
|--------|-----------------|-------|
| Revenue (TTM) | €5m – €250m | HARD |
| Geography | DACH primary; NL/BE/FR/IT/SE/DK/NO | HARD |
| Customer concentration | No single customer >30% | HARD |
| Excluded sectors | financial_services, real_estate, oil_gas | HARD |
| Deal type | Buy-and-build platform or add-on preferred | SOFT |
| Ownership | Founder-owned / family-owned preferred | SOFT |

**If any HARD filter fails: Hard Pass.** Report the failing criterion verbatim.

### AUCTUS-Specific Rules

**Verdict framework** (from Anthropic standard + AUCTUS specifics):
- **Pass → Further Diligence**: All hard filters pass, initial bull case is compelling,
  no obvious deal-breakers → escalate to full model (DCF + LBO)
- **Further Diligence – Conditional**: Hard filters pass but key information missing
  (e.g., EBITDA margin undisclosed) → request data before committing to full models
- **Hard Pass**: Any hard filter fails, or deal-breaker risk identified → log and close

**Speed is paramount**: A CIM screen should take < 30 minutes. If key data is missing,
flag it and give a preliminary verdict — don't block on perfect information.

**Save screening criteria to memory** once confirmed for reuse across deals in the same sector.

---

## STEP 1 — INPUT VALIDATION

Confirm `targets_csv` path exists and is readable (if batch mode).
Verify required columns are present: [company, revenue_eur_m, geography].
Note which optional PE analytics columns are present — log these as enabled dimensions.

For single-deal screen (CIM/teaser), proceed to Step 2 below.

Read `skills/competitor-analysis/refs/scoring-rubric.md` to confirm the full scoring
dimension set before proceeding.

---

## STEP 2 — EXTRACT DEAL FACTS

*(Anthropic deal-screening framework — apply for all inbound deal materials)*

From the provided CIM, teaser, or description, extract:

- **Company**: Name, location (city, country), sector/subsector
- **Description**: What they do (1-2 sentences)
- **Business Model & Revenue Quality**: Recurring revenue %, contract length, churn/retention, pricing power, and gross margin profile
- **Financials**: Historical (LTM, Y-1, Y-2) vs Projected (Y+1, Y+2) for Revenue (€m), Gross Margin (%), EBITDA (€m), EBITDA margin (%), Capex/FCF, and growth rates (%)
- **Market & Competitive Landscape**: TAM/SAM size, market growth (CAGR), key competitors, market share, and positioning
- **Growth Strategy**: Organic initiatives (new products, geos) vs Inorganic (M&A pipeline / add-ons)
- **Deal type**: Platform, add-on, recap, minority, carve-out
- **Asking price / valuation**: EV/EBITDA multiple, enterprise value if stated
- **Seller motivation**: Why selling now
- **Management**: Rolling or exiting; # of FTEs
- **Key customers**: Concentration risk (top 1 / top 3 as % of revenue)
- **Key risks**: Obvious red flags (sector, customer concentration, leverage)
- **Exit Potential**: Likely buyer universe (Strategic acquirers vs Financial sponsors)

If any of the above is missing, flag explicitly: "Information not provided — request from broker."

---

## STEP 3 — SCREEN AGAINST AUCTUS CRITERIA

Apply AUCTUS hard filters (from `config/auctus_criteria.yaml`):

| Criterion | AUCTUS Target | Actual | Pass/Fail |
|-----------|--------------|--------|-----------|
| Revenue range | €5m – €250m | | |

| Revenue growth | Positive trend preferred | | |
| Sector fit | Not financial svcs / RE / O&G | | |
| Geography | DACH primary | | |
| Deal size / EV | Implied by €10m–€150m rev range | | |
| Entry valuation | EV/EBITDA multiple asked | | |
| Customer concentration | No single customer >30% | | |
| Ownership structure | Founder/family preferred | | |
| Deal type | Buy-and-build fit? | | |

---

## STEP 4 — QUICK ASSESSMENT

Provide a 3-part assessment:

1. **Verdict**: Pass / Further Diligence / Hard Pass
2. **Bull case** (2-3 bullets): Why this could be a good AUCTUS deal
3. **Bear case** (2-3 bullets): Key risks and concerns
4. **Key questions**: What would need to be answered on a first call or in management presentation
5. **Valuation & Returns**: Initial view on entry multiple relative to comps/precedents, and high-level LBO feasibility

---

## STEP 5 — RUN TARGET SCORER (batch mode)

Score the target natively against the AUCTUS criteria.

Check exit code. If non-zero: read stderr, stop, report error verbatim to user.
Do NOT modify score values output by the script.

---

## STEP 6 — PE ANALYTICS AUGMENTATION

For each company that passed hard filters, augment with PE unit economics extensions.
Available when `ebitda_margin_pct` or `recurring_revenue_pct` columns are present:

```python
from scripts.target_scorer import compute_unit_economics, compute_cohort_retention_proxy
```

Additional output columns when PE data is available:
- `contribution_margin`, `gross_retention_est`, `ltv_cac_ratio`, `payback_months`
- `ndr_estimate`, `gross_churn_proxy`, `cohort_quality`

If no PE analytics columns are present, proceed without augmentation and note
"PE analytics unavailable — limited to standard scoring" in the output report.

---

## STEP 7 — FACTSET ENRICHMENT (OPTIONAL)

Only execute if user explicitly requests `--factset` AND `FACTSET_MCP_ENDPOINT` is set.
Use `FactSetMCPClient.fetch_trading_comps(sector=sector)` to enrich candidate data with
public market comparables before scoring. FactSet data is supplemental only — never
override user-supplied financial data with FactSet values.

---

## STEP 8 — QUALITY GATE


Must exit 0.
Verify:
  - Output Excel has columns `auctus_score` and `recommendation`
  - Output Excel has columns `hard_filter_pass` and `hard_filter_fail_code`
  - At least 1 company has `recommendation` ≠ "Pass"
  - Financial extraction explicitly distinguishes between historical and projected financials
  - Output includes TAM, competitive landscape, growth strategy, and exit potential
  - Assessment provides an initial valuation/returns view

Append completion entry to `logs/agent_activity.log`.

---

## CORRECT PATTERNS

**Structuring Financial Extraction:**
```markdown
### Financial Overview (€m)
| Metric | 2023A (Y-1) | 2024A (LTM) | 2025E (Y+1) | 2026E (Y+2) |
|--------|-------------|-------------|-------------|-------------|
| Revenue| 45.0 | 52.0 | 60.0 | 70.0 |
| % YoY | - | 15.5% | 15.3% | 16.6% |
| Gr. Mgn| 60.0% | 61.5% | 62.0% | 62.5% |
| EBITDA | 9.0 | 11.0 | 13.5 | 16.5 |
| % Mgn | 20.0% | 21.1% | 22.5% | 23.5% |
| Capex | (1.5) | (2.0) | (2.2) | (2.5) |
```

**Formulating Valuation & Returns View:**
```markdown
- **Valuation Context**: Asking price of €110m EV implies 10.0x LTM EBITDA. Listed DACH IT Services comps trade at 11.0x-13.0x, offering a slight entry arbitrage.
- **LBO Feasibility**: Strong FCF conversion (~80% EBITDA-Capex) comfortably supports ~4.0x-4.5x opening leverage. A 10.0x entry with base-case growth should clear the 25% IRR / 3.0x MOIC hurdle without multiple expansion.
```

---

## EXIT CONDITION

Deliver path to the ranked target matrix Excel (.xlsx).
State explicitly: total candidates in, hard-filter exclusions count, final scored shortlist count,
and which PE analytics dimensions were active.

For single-deal screens: state the verdict (Pass / Further Diligence / Hard Pass),
bull case (2-3 bullets), bear case (2-3 bullets), and key questions for first call.

---

# Deal Screening (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Extract Deal Facts

From the provided CIM, teaser, or description, extract:

- **Company**: Name, location, sector/subsector
- **Description**: What they do (1-2 sentences)
- **Financials**: Revenue, EBITDA, margins, growth rate
- **Deal type**: Platform, add-on, recap, minority, carve-out
- **Asking price / valuation**: Multiple, enterprise value if stated
- **Seller motivation**: Why selling now
- **Management**: Rolling or exiting
- **Key customers**: Concentration risk
- **Key risks**: Obvious red flags

### Step 2: Screen Against Criteria

Apply the fund's investment criteria (ask user if not known):

| Criterion | Target | Actual | Pass/Fail |
|-----------|--------|--------|-----------|
| Revenue range | | | |
| EBITDA range | | | |
| EBITDA margin | | | |
| Growth profile | | | |
| Sector fit | | | |
| Geography | | | |
| Deal size / EV | | | |
| Valuation (x EBITDA) | | | |
| Customer concentration | | | |
| Management continuity | | | |

### Step 3: Quick Assessment

Provide a 3-part assessment:

1. **Verdict**: Pass / Further Diligence / Hard Pass
2. **Bull case** (2-3 bullets): Why this could be a good deal
3. **Bear case** (2-3 bullets): Key risks and concerns
4. **Key questions**: What you'd need to answer on a first call

### Step 4: Output

One-page screening memo suitable for sharing with partners or an IC quick screen.

## Important Notes

- Speed matters — screening should take minutes, not hours
- Be direct about red flags. Don't bury concerns
- If financials seem inconsistent or incomplete, flag it explicitly
- Ask for the fund's criteria upfront if this is the first screening
- Save screening criteria in memory for future deals once confirmed
