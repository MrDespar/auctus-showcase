---
name: sector-overview
version: "1.1.0"
description: >
  Creates comprehensive DACH industry and sector landscape reports covering market
  dynamics, competitive positioning, key players, and thematic trends. Outputs feed
  DCF growth assumptions and LBO projection assumptions. FactSet MCP is the primary
  data source for market sizing and company financials.
triggers:
  - "sector overview"
  - "industry report"
  - "market landscape"
  - "sector analysis"
  - "industry deep dive"
  - "thematic research"
  - "market sizing"
  - "DACH market"
  - "market context"
inputs:
  required:
    - "sector — sector name or description (e.g. 'HVAC services', 'industrial automation')"
  optional:
    - "geography — DACH | EU | global (default: DACH)"
    - "depth — overview (5-10 pages) | deep-dive (20-30 pages) (default: overview)"
    - "purpose — dcf-feed | lbo-feed | ic-memo | standalone (default: standalone)"
refs:
  financial_constants: "config/financial_constants.yaml"
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/valuation_reports/sector_{sector}_{YYYYMMDD_HHMMSS}_overview.md"
  - "data/inputs/{sector}_sector_context.yaml (for DCF/LBO downstream use)"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG focuses on DACH mid-market buy-and-build. Sector overviews
serve two primary purposes: (1) standalone research for IC memos; (2) feeding growth
rate assumptions and competitive positioning into DCF and LBO models.

### Prerequisites

None. This is a starting-point skill. Its outputs feed:
- `/dcf-valuation` — revenue growth rate assumptions (Step 3)
- `/lbo-modeling` — projection assumption validation
- `/competitor-analysis` — market sizing context (Section I)
- `/ic-memo` — Section III (Industry & Market)

### Data Source Hierarchy

1. **FactSet MCP** — primary for market data, company financials, M&A multiples
2. **User-provided data** — management presentations, CIM market sections, industry reports
3. **Web search / fetch** — fallback for qualitative trends, regulatory updates, news

**NEVER** use web search as the primary source for market sizing figures. If FactSet is
unavailable and no user data exists, state this explicitly rather than citing unverified
web sources as primary data.

### Currency & Units

- All monetary values in **EUR millions (€m)** or EUR billions (€bn) where appropriate
- Market sizes: cite source, base year, and currency; convert to EUR at stated FX rate
- Ratios: `0.0%` for growth rates, `0.0×` for multiples

### Execution Environment

- Output: `outputs/valuation_reports/sector_{sector}_{YYYYMMDD_HHMMSS}_overview.md`
- If feeding DCF/LBO: also export `data/inputs/{sector}_sector_context.yaml` with:
  ```yaml
  revenue_growth_assumption_pct: [base case CAGR]
  ebitda_margin_benchmark_pct: [sector median]
  ev_ebitda_median_x: [sector trading multiple]
  data_vintage: [YYYY-MM-DD]
  ```

### AUCTUS-Specific Rules

- **Geography first**: DACH (DE/AT/CH) is primary; EU-wide data is acceptable when
  DACH-specific data is unavailable, clearly labeled as "EU-wide"
- **Revenue size filter**: focus on companies with revenue €10m–€500m (the AUCTUS
  deal universe + larger public peers as valuation context)
- **Buy-and-build lens**: always assess consolidation opportunity, fragmentation level,
  and add-on acquisition pipeline potential
- **Excluded sectors**: do NOT cover financial services, real estate, or oil & gas
- **Source all market size data** — cite the research firm, methodology, and date
- **Charts essential**: market size waterfall, competitive positioning matrix, valuation scatter
- Note the report date; flag any data older than 12 months as potentially stale

---

# Sector Overview (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Define Scope

- **Sector / subsector**: What industry and how narrowly defined?
- **Purpose**: Client report, internal research, pitch material, idea generation
- **Depth**: High-level overview (5-10 pages) or deep dive (20-30 pages)
- **Angle**: Neutral landscape vs. thematic thesis (e.g., "AI infrastructure buildout")
- **Universe**: Public companies only, or include private?

### Step 2: Market Overview

**Market Size & Growth**
- Total addressable market (TAM) with source
- Historical growth rate (5-year CAGR)
- Forecast growth rate and key assumptions
- Market segmentation (by product, geography, end market, customer type)

**Industry Structure & Moats (Porter's Five Forces)**
- Threat of new entrants & Barriers to entry (capital, regulatory, technical)
- Bargaining power of suppliers & buyers
- Threat of substitutes
- Competitive rivalry & Fragmented vs. consolidated (top 5 market share)
- Value chain map — where does value accrue?
- Business model types (subscription, transaction, licensing, services)

**Key Trends & Drivers**
- Macroeconomic sensitivities (interest rates, inflation, supply chain)
- Secular tailwinds (3-5 major trends) and headwinds/risks
- Technology disruption vectors
- Regulatory developments & ESG/sustainability considerations
- M&A activity and consolidation trends

### Step 3: Competitive Landscape

**Company Profiles** (for top 5-10 players):

| Company | Revenue | Growth | EBITDA Margin | Market Share | Key Differentiator |
|---------|---------|--------|--------------|-------------|-------------------|
| | | | | | |

For each company, brief profile:
- Business description (2-3 sentences)
- Strategic positioning and moat
- Recent developments (earnings, M&A, product launches)
- Valuation snapshot (P/E, EV/EBITDA, EV/Revenue)

**Unit Economics & KPI Benchmarking**
- Customer Acquisition Cost (CAC), Lifetime Value (LTV), LTV/CAC ratio
- Churn rates, net retention, and gross retention
- Cohort analysis and payback periods

**Competitive Dynamics**
- How do companies compete? (price, product, service, distribution)
- Who is gaining/losing share and why?
- Disruption risk from new entrants or adjacent players

### Step 4: Valuation Context

- Sector trading multiples (current and historical range)
- Premium/discount drivers (growth, margins, market position)
- Recent M&A transaction multiples
- How does the sector compare to the broader market?

### Step 5: Investment Implications & Value Creation

- **Risk/Reward**: Where are the best risk/reward opportunities?
- **Thematic Bets**: What thematic bets can be expressed through this sector?
- **Key Debates**: Bull vs. bear arguments in the sector.
- **Value Creation Playbook**: Standard LBO operational levers (pricing power, cost rationalization, buy-and-build add-on strategies).
- **Exit Environment**: Typical buyer universe (strategics vs. financial sponsors), recent sponsor-to-sponsor exits, and IPO window status.
- **Catalysts**: Events that could change the sector narrative.

### Step 6: Output

- Word document or PowerPoint with:
  - Market overview and sizing
  - Competitive landscape map
  - Company comparison table
  - Valuation summary
  - Key charts: market growth, share trends, valuation history
- Excel appendix with detailed company data

## Important Notes

- Source all market size data — cite the research firm or methodology
- Distinguish between TAM hype and realistic addressable market
- Sector overviews age fast — note the date and flag data that may be stale
- Charts are essential — market size waterfall, competitive positioning matrix, valuation scatter plot
- If for a client, tailor the "so what" to their specific situation (M&A target identification, competitive positioning, market entry)

## Quality Rubric

- **Comprehensiveness**: Does the overview cover TAM, Porter's Five Forces, Unit Economics, and macroeconomic sensitivities?
- **AUCTUS Alignment**: Is the primary focus on the DACH region and companies with €10m–€500m revenue? Are excluded sectors properly avoided?
- **Data Provenance**: Are all market size figures and multiples explicitly sourced (preferably FactSet)? Are older data points flagged?
- **Actionability**: Does the report clearly define the buy-and-build consolidation opportunity and provide a realistic exit environment assessment?
- **Format Compliance**: Are outputs correctly structured as markdown reports and precisely formatted YAML files for downstream DCF/LBO models?

## Correct Patterns

### Downstream YAML Export (`data/inputs/{sector}_sector_context.yaml`)
When exporting the data for downstream DCF/LBO consumption, ensure strictly typed YAML without markdown formatting inside values.

```yaml
# CORRECT
revenue_growth_assumption_pct: 5.5
ebitda_margin_benchmark_pct: 18.2
ev_ebitda_median_x: 8.5
data_vintage: "2023-10-15"
consolidation_opportunity: "High"
```

```yaml
# INCORRECT (Do not use strings for numbers or add % symbols)
revenue_growth_assumption_pct: "5.5%"
ebitda_margin_benchmark_pct: "18.2%"
ev_ebitda_median_x: "8.5x"
data_vintage: 2023-10-15
```
