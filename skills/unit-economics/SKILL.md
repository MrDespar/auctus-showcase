---
name: unit-economics
version: "1.1.0"
description: >
  Analyzes unit economics for AUCTUS PE targets — ARR cohorts, LTV/CAC, net retention,
  payback periods, revenue quality, and margin waterfall. Essential for B2B SaaS,
  field service contracts, and recurring-revenue businesses in the DACH mid-market.
  Feeds IC Memo Section IV (Financial Analysis).
triggers:
  - "unit economics"
  - "cohort analysis"
  - "ARR analysis"
  - "LTV CAC"
  - "net retention"
  - "revenue quality"
  - "customer economics"
  - "recurring revenue"
  - "churn analysis"
  - "ARR bridge"
inputs:
  required:
    - "company_name — target company name"
    - "revenue_model — saas | recurring_services | transactional | hybrid"
  optional:
    - "financials_path — path to company financials CSV or Excel"
    - "customer_data — path to customer-level ARR or revenue data (if available)"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/ic_memos/unit_economics_{company}_{YYYYMMDD_HHMMSS}.md"
  - "outputs/ic_memos/unit_economics_{company}_{YYYYMMDD_HHMMSS}.xlsx"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG evaluates DACH mid-market companies across a range of business
models. Unit economics analysis is most critical for recurring-revenue targets (B2B SaaS,
field service contract businesses, maintenance agreements). The output feeds IC Memo
Section IV (Financial Analysis) and informs LBO projection assumptions.

### Prerequisites

`/3-statement-model` (or user-provided financials) — need historical revenue and margin data.
Optionally, `/sector-overview` for NDR and LTV:CAC benchmarks by sector.

### Data Source Hierarchy

1. **User-provided data** — customer-level data, ARR schedules, management accounts
2. **FactSet MCP** — public comparable unit economics benchmarks
3. **Web search / fetch** — sector-specific SaaS/recurring revenue benchmarks

**Ask for raw customer-level data if available** — aggregate metrics can hide problems.
If raw data is unavailable, work with cohort-level data and flag limitations.

### Currency & Units

All monetary values in **EUR millions (€m)** or EUR thousands (€k) depending on company size.
ARR in €m; LTV:CAC ratio dimensionless; payback period in months.

### Execution Environment

Output: `outputs/ic_memos/unit_economics_{company}_{YYYYMMDD_HHMMSS}.xlsx` (primary)
plus `.md` for IC memo integration.

### AUCTUS-Specific Rules

**DACH mid-market context**:
- DACH B2B SaaS tends to be lower-growth but higher-retention than US-equivalent
  (customer relationships are longer-term; churn is lower; expansion is slower)
- Field service businesses (HVAC, industrial maintenance) model differently:
  use contract renewal rate instead of ARR NDR; annual contract value instead of MRR
- Recurring-revenue targets where ≥60% of revenue is contracted/recurring command
  premium EV/EBITDA multiples — quantify and flag
- **Price Escalators (Wertsicherungsklauseln)**: In DACH, auto-CPI indexing is common. Always separate ARR growth from volume/upsell vs. pure price increases.

**Revenue quality threshold for AUCTUS**:
- Recurring revenue < 40% of total → flag as low-quality revenue mix in IC memo
- Customer concentration: top 1 customer > 30% → hard filter fail (also check Top 5 > 40%)
- Net retention < 90% (gross) → flag as churn risk; explain mitigants

**Output to IC Memo Section IV**: Summarize into:
1. Revenue quality score (1-5)
2. ARR bridge (if applicable)
3. Cohort retention table (if data available)
4. LTV:CAC ratio and payback period
5. Key revenue risks and mitigants (including churn and concentration)

---

# Unit Economics Analysis (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Identify Business Model

Determine the revenue model to tailor the analysis:
- **SaaS / Subscription**: ARR, net retention, cohorts
- **Recurring services**: Contract value, renewal rates, upsell
- **Transaction / usage-based**: Revenue per transaction, volume trends, take rate
- **Hybrid**: Break down by revenue stream

### Step 2: Core Metrics

#### ARR / Revenue Quality
- **ARR bridge**: Beginning ARR → New → Expansion (Volume) → Expansion (Price) → Contraction → Churn → Ending ARR
- **ARR by cohort**: Vintage analysis — how does each annual cohort retain and grow?
- **Revenue concentration**: Detail Top 1, Top 5, Top 10, Top 20 customers as % of total ARR/Revenue
- **Revenue by type**: Recurring vs. non-recurring vs. professional services
- **Contract structure**: ACV distribution, multi-year %, auto-renewal %

#### Customer Economics
- **CAC (Customer Acquisition Cost)**: (Total S&M spend - CS/Retention costs) offset by typical sales cycle lag / new customers acquired
- **LTV (Lifetime Value)**: (ARPU × Recurring Gross Margin) / Logo Churn Rate. Never use blended Gross Margin
- **LTV:CAC ratio**: Target >3x for healthy businesses
- **CAC payback period**: CAC / (Monthly ARPU × Recurring Gross Margin)
- **Blended vs. segmented**: Break down by customer segment (enterprise vs. SMB vs. mid-market), cohort vintage, and acquisition channel (inbound vs. outbound)

#### Retention & Expansion
- **Gross retention**: % of beginning ARR retained (excludes expansion)
- **Net retention (NDR)**: % of beginning ARR retained including expansion
- **Logo churn**: % of customers lost
- **Dollar churn**: % of revenue lost (often different from logo churn)
- **Expansion rate**: Upsell + cross-sell as % of beginning ARR

#### Cohort Analysis
Build a cohort matrix showing:

| Cohort | Year 0 | Year 1 | Year 2 | Year 3 | Year 4 |
|--------|--------|--------|--------|--------|--------|
| 2020 | €1.0M | €1.1M | €1.2M | €1.1M | |
| 2021 | €1.5M | €1.7M | €1.8M | | |
| 2022 | €2.0M | €2.3M | | | |
| 2023 | €3.0M | | | | |

Show both absolute € and indexed (Year 0 = 100%) views.

#### Margin Waterfall
- Revenue → Gross Profit → Contribution Margin → EBITDA
- Fully loaded unit economics: what does it cost to acquire, serve, and retain a customer?
- Gross margin by revenue stream (subscription vs. services vs. other)

### Step 3: Benchmarking

Compare unit economics to relevant benchmarks:
- **SaaS Rule of 40**: Growth rate + EBITDA margin > 40%
- **SaaS Magic Number**: Net new ARR / prior period S&M spend > 0.75x
- **NDR benchmarks**: Best-in-class >120%, good >110%, concerning <100%
- **LTV:CAC**: Best-in-class >5x, good >3x, concerning <2x
- **Gross retention**: Best-in-class >95%, good >90%, concerning <85%
- **CAC payback**: Best-in-class <12mo, good <18mo, concerning >24mo

### Step 4: Revenue Quality Score

Synthesize into a revenue quality assessment:

| Factor | Score (1-5) | Notes |
|--------|-------------|-------|
| Recurring % | | |
| Net retention | | |
| Customer concentration | | |
| Cohort stability | | |
| Growth durability | | |
| Margin profile | | |
| **Overall** | | |

### Step 5: Output

- Excel workbook with ARR bridge, cohort matrix, unit economics dashboard
- Summary slide with key metrics and benchmarks
- Red flags and areas for further diligence

## Important Notes

- Always ask for raw customer-level data if available — aggregate metrics can hide problems
- NDR above 100% can mask high gross churn if expansion is strong enough — always show both
- Cohort analysis is the single most important view for revenue quality — push for this data
- Differentiate between contracted ARR and actual recognized revenue
- For usage-based models, focus on consumption trends and expansion patterns rather than traditional ARR metrics
- Professional services revenue should be evaluated separately — it's not recurring and margins are typically lower

## Quality Rubric

- **Are all CAC metrics adjusted for sales cycle lag and stripped of CS costs?** (Required)
- **Is LTV and Payback Period calculated using Recurring Gross Margin?** (Required)
- **Is revenue expansion separated into Volume vs. Price (CPI) growth?** (Required)
- **Are Top 1, 5, 10, and 20 customer concentration percentages explicitly calculated?** (Required)

## Correct Patterns

### S&M Lag Calculation for CAC
When calculating CAC, offset the S&M spend by the sales cycle. For a 3-month sales cycle, use Q1 S&M expenses divided by Q2 new logos. Always exclude retention-focused Customer Success expenses.

### Unit Economics Formulas
```python
# CORRECT
recurring_gm = (recurring_revenue - recurring_cogs) / recurring_revenue
cac = lagged_acquisition_sm_spend / new_logos
ltv = (arpu * recurring_gm) / logo_churn_rate
payback_months = cac / (mrr_per_logo * recurring_gm)

# INCORRECT (Do not use blended GM or unlagged S&M)
blended_gm = total_gross_profit / total_revenue
cac = total_current_sm_spend / new_logos
```
