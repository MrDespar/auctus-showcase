---
name: value-creation-plan
version: "1.1.0"
description: >
  Structures post-acquisition value creation plans with revenue, cost, and operational
  levers mapped to an EBITDA bridge. Emphasizes buy-and-build specific levers (add-on
  acquisition pipeline, geographic expansion within DACH, cross-sell to acquired customer
  bases). Feeds IC Memo Section V (Investment Thesis) and Section XI (Value Creation Plan).
triggers:
  - "value creation plan"
  - "100-day plan"
  - "post-close plan"
  - "EBITDA bridge"
  - "operating plan"
  - "value creation levers"
  - "100 day"
  - "post-acquisition"
  - "value creation"
inputs:
  required:
    - "company_name — target company name"
    - "entry_ebitda_eur_m — EBITDA at acquisition (€m)"
    - "exit_ebitda_target_eur_m — target EBITDA at exit (€m)"
  optional:
    - "hold_period_years — (default: 5)"
    - "lbo_compact — path to LBO compact JSON for returns context"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/ic_memos/vcp_{company}_{YYYYMMDD_HHMMSS}.md"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG pursues buy-and-build strategies in fragmented DACH mid-market
niches. The value creation plan must reflect buy-and-build specific levers — add-on M&A
is typically the largest value creation source, not just organic growth.

### Prerequisites

`/lbo-modeling` — the returns model establishes value creation targets (entry EBITDA,
exit EBITDA, MOIC/IRR hurdle). Run LBO before finalizing the EBITDA bridge here.

### Data Source Hierarchy

1. **User-provided data** — management presentations, operational assessments, 100-day plans
2. **FactSet MCP** — sector benchmarks for margin expansion potential, add-on multiples
3. **Web search / fetch** — fallback for sector-specific best practices

### Currency & Units

All monetary values in **EUR millions (€m)**. EBITDA bridge values in €m.

### Execution Environment

Output: `outputs/ic_memos/vcp_{company}_{YYYYMMDD_HHMMSS}.md`
This output is consumed by `/ic-memo` for Section V (Investment Thesis) and
Section XI (Value Creation Plan).

### AUCTUS-Specific Rules

**Buy-and-build specific levers** (add to standard Anthropic levers):

- **Add-on acquisition pipeline**: Start on Day 1. Map 10-20 potential add-on targets
  in the sector. AUCTUS's primary value creation thesis is consolidation — add-on M&A
  typically contributes 30-60% of total EBITDA growth in a buy-and-build strategy.
  For each add-on: estimated revenue (€m), EBITDA margin, synergies, integration cost.

- **Geographic expansion within DACH**: DE → AT → CH (or adjacent markets NL/BE/FR/IT).
  Model revenue lift from entering secondary geography. Typical timeline: 18-24 months.

- **Cross-sell to acquired customer bases**: After add-on acquisitions, estimate revenue
  from selling platform's existing products/services to add-on's customers.
  Typical uplift: 5-15% of acquired revenue within 24 months.

- **Procurement synergies**: Group purchasing power across acquired entities.
  DACH mid-market: typically 2-4% of COGS savings achievable in Year 2+.

- **Management professionalization**: Install CFO, commercial director, or HR director
  where missing (common in founder-led businesses). Cost: €0.3m–€0.8m/year.
  Benefit: enables bolt-on integration capacity and reporting quality.

**AUCTUS hurdle integration**: Value creation plan must bridge from entry EBITDA to
a level that supports MOIC ≥ 2.0× and IRR ≥ 20% at the assumed exit multiple.
If the bridge falls short of these hurdles, escalate — do not present an EBITDA bridge
that implies below-hurdle returns without explicit IC approval.

**Timeline**: Be realistic — most EBITDA improvement lags 12-24 months. Quick wins
(pricing, cost cuts) show in Year 1; add-on integration value shows in Year 2-3.

---

# Value Creation Plan (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Baseline Assessment

Understand the starting point:
- Current revenue, EBITDA, and margins
- Organizational structure and capabilities
- Key operational metrics by function
- Management team strengths and gaps
- Quick wins already identified during diligence

### Step 2: Value Creation Levers

Map all levers to an EBITDA bridge over the hold period:

#### Revenue Growth Levers
- **Organic growth**: Price increases, volume growth, market expansion
- **Cross-sell / upsell**: New products to existing customers
- **New market entry**: Geographic expansion, new verticals, new channels
- **Sales force effectiveness**: Hire reps, improve conversion, shorten cycle
- **M&A / add-ons**: Bolt-on acquisitions to add revenue and capabilities

For each lever:
- Current state → Target state
- Revenue/EBITDA impact (€m)
- Timeline to impact (months to run-rate)
- Investment required / Cost to Achieve (CTA)
- Confidence level (high/medium/low) & Sensitivities (Base / Downside / Upside)
- Executive Sponsor / RACI
- Link to Exit Multiple Expansion (if applicable, e.g., shift to recurring revenue)

#### Margin Expansion Levers
- **Pricing optimization**: Price increases, mix shift, bundling
- **COGS reduction**: Procurement savings, supplier consolidation, automation
- **OpEx optimization**: Overhead reduction, shared services, offshoring
- **Technology investment**: Automation, systems integration, data analytics
- **Scale leverage**: Fixed cost leverage as revenue grows

#### Capital & Cash Flow Optimization
- **Working Capital (NWC)**: Optimize DSO (collections), DPO (payables terms), and DIO (inventory management).
- **Capex Optimization**: Realign maintenance vs. growth capex, shift from CapEx to OpEx (e.g. leasing, SaaS).
- **Cost to Achieve (CTA)**: Explicitly forecast one-time OpEx and CapEx required to implement value creation initiatives.

#### Strategic / Multiple Expansion
- **Platform building**: Add-on acquisitions, tuck-ins
- **Recurring revenue shift**: Move from project to recurring/subscription
- **Market positioning**: Category leadership, brand building
- **Management upgrades**: Key hires to professionalize the business
- **ESG / governance**: Board formation, reporting improvements

### Step 3: EBITDA & Cash Flow Bridge

Build the walk from current to target EBITDA and associated cash flows:

| Lever | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|-------|--------|--------|--------|--------|--------|
| Base EBITDA | | | | | |
| Organic revenue growth | | | | | |
| Pricing | | | | | |
| Add-on M&A | | | | | |
| COGS savings | | | | | |
| OpEx optimization | | | | | |
| Technology investment | | | | | |
| **Pro Forma EBITDA** | | | | | |
| **Margin** | | | | | |
| *Less: Cost to Achieve (CTA) OpEx* | | | | | |
| *Less: Working Capital Change* | | | | | |
| *Less: Capex (Maintenance & Growth)* | | | | | |
| **Operating Free Cash Flow** | | | | | |

### Step 4: 100-Day Plan

Prioritize the first 100 days post-close:

**Days 1-30: Stabilize & Assess**
- Management alignment and retention (sign employment agreements, set comp)
- Quick wins — pricing, obvious cost cuts, low-hanging fruit
- Detailed operational assessment by function
- Customer communication plan
- Set up reporting and KPI dashboards

**Days 31-60: Plan & Initiate**
- Finalize strategic plan and communicate to organization
- Launch top 3-5 value creation initiatives
- Begin add-on M&A pipeline development
- Hire for critical gaps
- Implement new reporting cadence (weekly flash, monthly review, quarterly board)

**Days 61-100: Execute & Measure**
- First results from quick-win initiatives
- First board meeting with operating metrics
- Progress report on each value creation lever
- Adjust plan based on early learnings

### Step 5: KPI Dashboard

Define the metrics that will track value creation:

| KPI | Current | Year 1 Target | Owner | Reporting Frequency |
|-----|---------|---------------|-------|-------------------|
| Revenue | | | CEO | Monthly |
| EBITDA | | | CFO | Monthly |
| EBITDA margin | | | CFO | Monthly |
| New customer wins | | | CRO | Weekly |
| Net retention | | | CRO | Monthly |
| Employee turnover | | | CHRO | Monthly |
| Cash conversion | | | CFO | Monthly |

### Step 6: Output

- Word document or PowerPoint with:
  - Executive summary (1 page)
  - EBITDA bridge chart
  - Value creation levers detail (1 page per lever)
  - 100-day plan timeline
  - KPI dashboard
  - Accountability matrix (who owns what)
- Excel model backing the EBITDA bridge

## Important Notes

- Be realistic about timing — most PE value creation takes 12-24 months to show in financials
- Quick wins matter for momentum and credibility, but don't over-rotate on cost cuts at the expense of growth
- Management buy-in is critical — co-develop the plan, don't impose it
- Track initiative-level P&L impact, not just top-line EBITDA — you need to know what's working
- Add-on M&A is often the largest value creation lever — start the pipeline on Day 1
- Always pressure-test assumptions with operating partners or industry experts

## Quality Rubric

- **Cost to Achieve (CTA) Modeled**: Are one-time implementation costs (OpEx and CapEx) explicitly captured and deducted from cash flow?
- **Working Capital Addressed**: Are DPO, DSO, and DIO optimization levers quantified?
- **Capex Separated**: Is capital expenditure clearly split between maintenance and growth/initiative-driven?
- **Risk / Sensitivities Included**: Are value creation levers flexed for downside risk and execution delays?
- **Multiple Expansion Logic**: If the exit multiple expands, is it explicitly linked to a fundamental shift in business quality (e.g., % recurring revenue, increased scale)?
- **PMO / Governance**: Is accountability clearly assigned via a RACI matrix, executive sponsorship, and a detailed 100-day plan?

## Correct Patterns

### Modeling Cost to Achieve (CTA)
When estimating the impact of an initiative (e.g., ERP rollout, factory consolidation), ensure one-time costs hit the cash flow before run-rate savings are realized.

```python
# GOOD: Explicitly separate run-rate savings from one-time CTA
initiative_savings = [0.0, 1.5, 3.0, 3.0, 3.0]  # €m EBITDA impact
initiative_cta_opex = [1.0, 0.5, 0.0, 0.0, 0.0]     # €m hit to EBITDA
initiative_cta_capex = [2.0, 0.0, 0.0, 0.0, 0.0]    # €m hit to Cash Flow
```

### Linking KPIs to Multiple Expansion
Do not assume arbitrary multiple expansion. Tie it to a shift in business mix.

```python
# GOOD: Blended exit multiple based on recurring vs. project revenue
recurring_rev_pct = 0.60
project_rev_pct = 0.40
recurring_multiple = 12.0x
project_multiple = 8.0x
blended_exit_multiple = (recurring_rev_pct * recurring_multiple) + (project_rev_pct * project_multiple)
```
