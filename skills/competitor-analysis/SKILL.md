---
name: competitor-analysis
version: "2.1.0"
description: >
  Identifies, screens, and scores buy-and-build add-on acquisition targets in fragmented
  DACH mid-market niches. Also builds competitive landscape decks covering market context,
  industry economics, competitor mapping, positioning visualization, and strategic synthesis
  with moat assessment. Implements Anthropic's full competitive analysis framework with
  AUCTUS buy-and-build lens and DACH registry data sources.
triggers:
  - "analyze competitors"
  - "map the market"
  - "scout add-on targets"
  - "target screening"
  - "build target list"
  - "find acquisition targets"
  - "competitive landscape"
  - "competitor analysis"
  - "peer comparison"
  - "market positioning"
  - "who are the competitors to"
  - "build a market map"
inputs:
  required:
    - "Sector description OR data/market/candidates.csv with company universe"
  optional:
    - "data/inputs/platform_profile.md (existing platform context)"
    - "competitor_set — specific companies to include in the analysis"
refs:
  scoring_rubric: "skills/competitor-analysis/refs/scoring-rubric.md"
  sector_taxonomy: "skills/competitor-analysis/refs/sector-taxonomy.yaml"
  output_template: "skills/competitor-analysis/refs/output-template.md"
  frameworks: "skills/competitor-analysis/refs/frameworks.md"
  investment_criteria: "config/auctus_criteria.yaml"

outputs:
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_targets.xlsx"
  - "outputs/target_matrices/{sector}_{YYYYMMDD_HHMMSS}_report.md"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG uses competitor analysis in two modes:
1. **Buy-and-build target screening**: identify and score add-on acquisition candidates
   in fragmented DACH niches (Steps 1-8 below, original AUCTUS workflow)
2. **Competitive landscape deck**: map the competitive dynamics for IC memo context
   (Anthropic workflow below, phases 1-2 + steps 0-9)

Both modes use the same DACH data sources and AUCTUS hard filters.

### Prerequisites

- `/sector-overview` — market sizing and competitive dynamics context (Section I of output)
- This skill feeds `/ic-memo` — Section II (Company Overview) and Section III (Industry & Market)

### Data Source Hierarchy

1. **FactSet MCP** — primary for company financials, market data, and M&A transactions
2. **User-provided data** — uploaded CSV, management presentations
3. **Web search / fetch** — DACH registry sources (Creditreform, Bisnode, Handelsregister),
   LinkedIn company search, industry association directories

**DACH registry sources** (preferred for private company discovery):
- Creditreform / Bisnode DACH registries
- Handelsregister (DE commercial register) search
- Industry association member directories (VDMA, ZVEI, etc.)
- LinkedIn company search (headcount as revenue proxy)

### Currency & Units

All monetary values in **EUR millions (€m)**. Revenue size filters in €m.

### Execution Environment

Score the target companies natively in your context window. Apply the AUCTUS criteria to the target candidates and generate the matrices without invoking Python scripts.

### AUCTUS-Specific Rules

**Hard filter table** (apply before scoring):
| Filter | AUCTUS Threshold |
|--------|-----------------|
| Revenue | €5m – €250m |
| Geography | DACH primary; NL/BE/FR/IT/SE/DK/NO |

| Customer concentration | No single customer >30% |
| Excluded sectors | financial_services, real_estate, oil_gas |

**Buy-and-build lens**: Always assess:
- Fragmentation level (top 5 market share <40% = highly fragmented)
- Add-on acquisition potential (revenue €5m–€50m, owner-operated, willing seller)
- Cross-sell synergy with the platform thesis
- Integration complexity (IT, culture, customer base overlap)

**Scope questions** (ask before Phase 1 research — mirrors Anthropic Phase 1):
- Are we mapping the market for a specific platform investment, or prospecting broadly?
- What is the platform company's core product/geography? (defines add-on fit)
- Include only private companies, or also map listed peers as benchmarks?

---

## STEP 1 — SECTOR DEFINITION & PREREQUISITES

Read `skills/competitor-analysis/refs/sector-taxonomy.yaml`.
Map the user's sector request to the taxonomy entry.
Extract: NACE codes, sub-segment definitions, and market fragmentation indicators.
Record the canonical sector slug (e.g. `hvac_services`) for use in output filenames.

If the required data to define the sector universe does not exist, do NOT halt and ask the user for it. Instead, you MUST proactively gather the data from FactSet MCP or chat context, and explicitly execute the necessary upstream skills to generate the required dependencies. Specifically, run the `/sector-overview` skill to establish the target's operating environment and market sizing.

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
Score the filtered targets natively against the `auctus_criteria.yaml` and output the Excel matrices directly.

## STEP 7 — REPORT COMPOSITION

Read the script-output Excel from `outputs/target_matrices/`.
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
Verify output Excel has all required columns:
  [company, revenue_eur_m, ebitda_margin_pct, geography, ownership, auctus_score, recommendation]
Verify output report is non-empty.
Append completion entry to `logs/agent_activity.log`.

## EXIT CONDITION

Deliver paths to:
  1. Ranked target matrix Excel (.xlsx)
  2. Markdown report

State: total candidates identified, hard-filter exclusions count, final shortlist count.

---

# Competitive Analysis (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

# Competitive Landscape Mapping

Build a complete competitive analysis deck. This is a two-phase process: gather requirements and get outline approval first, then build.

## Environment check

This skill works in both the PowerPoint add-in and chat. Identify which you're in before starting — the mechanics differ, the workflow doesn't:

- **Add-in** — the deck is open live; build slides directly into it.
- **Chat** — generate a `.pptx` file (or build into one the user uploaded).

Everything below applies in both.

## Phase 1 — Scope the analysis

Competitive analysis means different things to different people. Before any research or slide-building, use `ask_user_question` to pin down what they actually want. Don't guess — a 20-slide peer benchmarking deck and a 5-slide market map are both "competitive analysis" and take completely different shapes.

Gather in one round if you can (the tool takes up to 4 questions):

- **Scope** — Single target company with competitors around it? Or multi-company side-by-side with no protagonist?
- **Competitor set** — Which companies are in scope? If the user names them, use exactly those. If they say "the usual suspects," propose a set and confirm.
- **Audience and depth** — Quick read for someone already in the space, or a full primer? This drives whether you need market sizing, industry economics, and history — or can skip to the comparison.
- **Investment context** — Do they need bull/base/bear scenarios and signposts? That's Step 9 below; skip it if this is a strategic review rather than an investment thesis.

If they've uploaded an Excel/CSV with competitor data, confirm which columns map to which metrics before you start pulling numbers. Source-file fidelity matters: use values exactly as given, don't recalculate or re-round.

## Phase 2 — Outline, approve, then build

**Do not create slides until the outline is approved.** Propose slide titles and one-line content notes, present them to the user, get a yes. A competitive deck is 10-20 slides of interlocking content — rebuilding because slide 4 was wrong is expensive. The outline is the cheap iteration point.

When proposing the outline, `ask_user_question` works well for the structural decisions: which positioning visualization (2×2 matrix / radar / tier diagram — Step 5 below), how to group competitors (by business model / segment / posture — Step 4). These are taste calls the user likely has an opinion on.

---

## Standards — apply throughout

### Prompt fidelity

When the user specifies something, that's a requirement, not a suggestion:
- **Slide titles and section names** — exact wording. If they say "Overview and Competitive Scope," don't swap in "FY2024 Competitive Landscape."
- **Chart vs. table** — not interchangeable. "Embedded chart" means a real chart object with data labels on the bars/slices, not a formatted table.
- **Complete data series** — if they list 7 competitors, include all 7. If they show 2015-2025, include every year.
- **Exact values and ratios** — "surpasses DoorDash 4:1, Lyft 8:1" means those ratios, not "7.6x Lyft."

### Source quality, when sources conflict

1. 10-Ks / annual reports (audited)
2. Earnings calls / investor presentations (management commentary)
3. Sell-side research (analyst estimates, useful for private company sizing)
4. Industry reports (McKinsey, Gartner — market sizing, trends)
5. News (recent developments only; verify against primary sources)

### Data comparability

- All competitor metrics from the same fiscal year; flag exceptions explicitly ("FY24" vs "H1 2024")
- Same metric definitions across competitors
- Convert to EUR for international; note the exchange rate and date
- Missing data shows as "-" or "N/A" with an "[E]" flag for estimates — never blank
- Every number has a citation: "[Company] [Document] ([Date])"

### Design

- **Slide titles are insights, not labels.** "Scale leaders pulling away from niche players" — not "Competitive Analysis."
- **Signposts are quantified.** "Margin below 40%" — not "margins decline."
- **Ratings show the actual.** "●●● $160B" — not just "●●●."
- **Charts are real chart objects** — not text tables dressed up to look like charts.

**Typography** — set explicitly, don't rely on defaults:
- Slide titles: 28-32pt bold
- Section headers: 18-20pt bold
- Body text: 14-16pt (never below 14pt)
- Table text: 14pt
- Sources/footnotes: 14pt, gray
- Same element type = same size throughout the deck

**Charts:**
- Legend inside the chart boundary, not floating over the plot area
- Right-side legend for pies (≤6 slices), bottom legend for line/bar (≤4 series)
- More than 6 series → split into multiple charts or use a table
- Pie charts show percentages on slices, not just in the legend

**Tables:**
- Light gray header row, bold
- Right-align numbers, left-align text
- Enough cell padding that text doesn't touch borders

**Color:** 2-3 colors max. Muted — navy, gray, one accent. Same color meanings throughout.

### What's strict vs. flexible

| Always | Case-by-case |
|---|---|
| Exact titles/sections when user specifies | Creative titles when they don't |
| Chart when user says chart; table when they say table | Visualization type when unspecified |
| Every competitor/data point they list | Number of competitors when unspecified |
| Exact values when specified | Rounding when precision unspecified |
| Titles fit without overflow | Number of competitor categories |
| No overlapping elements | Which dimensions to compare |

---

## Analysis workflow

### Step 0 — Industry-defining metrics

Before anything else: what 3-5 metrics does this industry actually run on? Use these consistently across every competitor.

| Industry | Key metrics |
|---|---|
| SaaS | ARR, NRR, CAC payback, LTV/CAC, Rule of 40 |
| Payments | GPV, take rate, attach rate, transaction margin |
| Marketplaces | GMV, take rate, buyer/seller ratio, repeat rate |
| Retail | Same-store sales, inventory turns, sales per sq ft |
| Logistics | Volume, cost per unit, on-time delivery %, capacity utilization |

Industry not listed — pick the metrics investors and operators benchmark on.

### Step 1 — Market context

Size, growth, drivers, headwinds. With sources.

Correct: "Embedded payments is $80-100B in 2024, growing 20-25% CAGR (McKinsey 2024)"
Wrong: "The market is large and growing rapidly"

### Step 2 — Industry economics

Map how value flows. Approach depends on industry structure:
- **Vertically structured** — value chain layers, typical margin at each
- **Platform/network** — ecosystem participants, value flows between them
- **Fragmented** — consolidation dynamics, margin differences by scale

### Step 3 — Target company profile

```
| Metric | Value |
|---|---|
| Revenue | $4.96B |
| Growth | +26% YoY |
| Gross Margin | 45% |
| Profitability | $373M Adj. EBITDA |
| Customers | 134K |
| Retention | 92% |
| Market Share | ~15% |
```

Multi-segment companies add a breakdown:

```
| Segment | Revenue | Rev YoY | Rev % | EBITDA | EBITDA YoY | Margin |
|---|---|---|---|---|---|---|
| Seg A | $25.1B | +26% | 57% | $6.5B | +31% | 26% |
| Seg B | $13.8B | +31% | 31% | $2.5B | +64% | 18% |
| Seg C | $5.1B | -2% | 12% | -$74M | -16% | -1% |
| Total | $44.0B | +18% | 100% | $6.5B* | - | 15% |
```
*Note corporate costs if applicable

### Step 4 — Competitor mapping

Group by whichever lens fits (this is a good `ask_user_question` decision if the user hasn't specified):
- By business model — platform / vertical / horizontal
- By segment — enterprise / SMB / consumer
- By posture — direct / adjacent / emerging
- By origin — incumbent / disruptor / new entrant

### Step 5 — Positioning visualization

| Type | When |
|---|---|
| 2×2 matrix | Two dominant competitive factors |
| Radar/spider | Multi-factor comparison |
| Tier diagram | Natural clustering into strategic groups |
| Value chain map | Vertical industries |
| Ecosystem map | Platform markets |

See `references/frameworks.md` for 2×2 axis pairs by industry.

### Step 6 — Competitor deep-dives

Two tables per competitor.

**Metrics:**
```
| Metric | Value |
|---|---|
| Revenue | $X.XB |
| Growth | +XX% YoY |
| Gross Margin | XX% |
| Market Cap | $X.XB |
| Profitability | $XXXM EBITDA |
| Customers | XXK |
| Retention | XX% |
| Market Share | ~XX% |
```

**Qualitative:**
```
| Category | Assessment |
|---|---|
| Business | What they do (1 sentence) |
| Strengths | 2-3 bullets |
| Weaknesses | 2-3 bullets |
| Strategy | Current priorities |
```

### Step 7 — Comparative analysis

Requires three distinct benchmarking views:

**1. Financial & Operating Benchmarking**
```
| Dimension | Company A | Company B | Company C |
|---|---|---|---|
| Scale | ●●● $160B | ●●○ $45B | ●○○ $8B |
| Growth | ●●○ +26% | ●●● +35% | ●●○ +22% |
| Margins | ●●○ 7.5% | ●○○ 3.2% | ●●● 15% |
```

**2. Trading Comps (Public Market Comparables)**
For listed peers, calculate standard valuation multiples based on Last Twelve Months (LTM) or Next Twelve Months (NTM) estimates.
```
| Company | Share Price | Market Cap | EV | EV/Rev (LTM) | EV/EBITDA (LTM) | Net Debt/EBITDA |
|---|---|---|---|---|---|---|
| Company A | $50.00 | $5.0B | $5.5B | 5.2x | 14.5x | 2.1x |
```

**3. Product / Service Capability Matrix**
Detailed feature or service-line comparison using Harvey balls (●, ◐, ○).
```
| Capability | Company A | Company B | Company C | Target |
|---|---|---|---|---|
| Core Feature 1 | ● | ● | ◐ | ● |
| Advanced Feature 2 | ● | ○ | ○ | ◐ |
| Enterprise Integration | ◐ | ● | ○ | ○ |
```

### Step 8 — Strategic context & Valuation Baselines

M&A transactions (multiples, rationale), partnership trends, capital raising patterns, regulatory developments. See `references/schemas.md` for the M&A transaction table format.

**Precedent Transactions Valuation Range:**
Provide a summary table of relevant precedent M&A transactions, including derivation of a valuation range (Min, Max, Median, Mean EV/EBITDA or EV/Rev).

**Capital Structure & Funding History (Private Peers):**
Track funding rounds, lead investors, and last known valuations to map the capitalization of private competitors.

### Step 9 — Synthesis

**Moat assessment** — rate each competitor Strong / Moderate / Weak on:

| Moat | What to assess |
|---|---|
| Network effects | User/supplier flywheel strength; cross-side vs same-side |
| Switching costs | Technical integration depth, contractual lock-in, behavioral habits |
| Scale economies | Unit cost advantages at volume; minimum efficient scale |
| Intangible assets | Brand, proprietary data, regulatory licenses, patents |

**Required synthesis elements:**
- Durable advantages (hard to replicate) — map to moat categories
- Structural vulnerabilities (hard to fix)
- Current state vs. trajectory

**For investment contexts** (skip if the Phase 1 scoping said no):

```
| Scenario | Probability | Key driver |
|---|---|---|
| Bull | 30% | Market share gains, margin expansion |
| Base | 50% | Current trajectory continues |
| Bear | 20% | Competitive pressure, margin compression |
```

---

## Quality checklist

Before finishing:

**Prompt fidelity**
- Slide titles match what the user specified, verbatim
- Charts where they said chart; tables where they said table
- Every competitor/year/data point they listed is present
- Exact values and formats as specified

**Data consistency**
- Source-file values extracted directly, not recalculated
- Same metric shows the same value on every slide it appears
- Same decimal precision as the source

**Layout**
- Titles fit without overflow
- No overlapping elements
- All text within containers, no clipping

**Content**
- Every number has a citation
- All metrics from the same fiscal period (or flagged)
- Slide titles state insights, not topics
- Charts are real chart objects
- **Valuation Integrity:** EV/EBITDA and EV/Rev multiples use strictly aligned LTM or NTM periods.
- **Capability Matrix Consistency:** Harvey ball definitions are consistent (e.g., ● always means full support/native, ◐ means partial/partner, ○ means none).

Run standard visual verification checks on every slide — this catches overlaps, overflow, and low-contrast text that don't show up when you're reading back the XML.

---

## Correct Patterns (Non-Obvious Implementations)

**1. Enterprise Value (EV) Calculation & Multiples Alignment**
- *Pattern:* Always explicitly state the date of the market cap / share price used for EV. `EV = Market Cap + Total Debt + Preferred Equity + Minority Interest - Cash & Cash Equivalents`.
- *Rule:* Do not mix LTM financial metrics with historical enterprise values. Multiples must use the EV as of the current/specified date divided by the trailing (LTM) or forward (NTM) metric.

**2. Rendering Harvey Balls**
- *Pattern:* Use standard Unicode characters for capability matrices: `●` (U+25CF) for Full, `◐` (U+25D0) for Partial, `○` (U+25CB) for None.
- *Rule:* In `.pptx` generation via python-pptx, ensure the font supports these glyphs (e.g., Arial, Segoe UI Symbol) to prevent missing character boxes.

**3. Handling Missing Private Company Financials**
- *Pattern:* Use the notation `[E]` for estimates and cite the methodology in a footnote (e.g., "*Revenue estimated based on LinkedIn headcount of 150 @ €120k/FTE*").
- *Rule:* Never leave a cell blank. If totally unknown, use `N/A` or `ND` (Not Disclosed).
