---
name: relative-valuation
version: "2.1.0"
description: >
  Maps a target company against a curated public comparable peer group and historical
  precedent transactions. Outputs an institutional-grade trading comps table and precedent
  deal matrix with implied Enterprise Value range. DACH/EU peer focus; FactSet MCP primary
  data source. All multiple calculations delegated to Python scripts. Output feeds DCF WACC
  (beta) and LBO terminal multiple cross-check. Incorporates standard IB/PE adjustments:
  Calendarization, NTM/Forward estimates, Adjusted EBITDA, and IFRS 16 lease consistency.
triggers:
  - "run comps"
  - "trading comps"
  - "precedent transactions"
  - "relative valuation"
  - "market multiples"
  - "comparable company analysis"
  - "EV/EBITDA multiple"
  - "peer comparison"
  - "comps analysis"
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
  auctus_criteria: "config/auctus_criteria.yaml"

outputs:
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_trading_comps.xlsx"
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_precedents.xlsx"
  - "outputs/valuation_reports/{company}_{YYYYMMDD_HHMMSS}_valuation_report.md"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG evaluates private DACH mid-market companies against public
comparable peers and historical M&A transactions. This skill feeds two downstream workflows:
(1) DCF: peer betas for WACC; (2) LBO: exit multiple cross-check against precedents.

### Prerequisites

None. Can run standalone. Its outputs feed:
- `/dcf-valuation` — WACC beta assumptions (Step 2)
- `/lbo-modeling` — exit multiple validation
- `/ic-memo` — Section VI (Valuation Summary)

### Data Source Hierarchy

1. **FactSet MCP** — primary for all market data, financial metrics, and M&A multiples
2. **User-provided data** — uploaded peer lists, precedent transaction databases
3. **Web search / fetch** — fallback only; never primary for financial figures

**NEVER** use web search as a primary source for EV/EBITDA multiples or financial metrics.
If FactSet is unavailable and no user data exists, state this explicitly.

### Currency & Units

- All values in **EUR millions (€m)**; convert any USD-denominated peer data at stated FX rate
- Multiples: `0.0×` (1 decimal); margins: `0.0%` (1 decimal)
- Statistics block: max, 75th percentile, median, 25th percentile, min — **mandatory** for all multiple columns

### Execution Environment

### Execution Environment

Run the comps analysis and precedent transactions natively in your context window.
Retrieve the financial data from FactSet (or User Data if provided) and manually apply the `auctus_criteria.yaml`.
Output the data in Excel format matching the requested paths, and provide a Markdown report.

### AUCTUS-Specific Rules

**Peer group criteria** (DACH context):
- **4–6 peers** required (not fewer; not more than 6 without explicit justification)
- Primary geography: DACH + wider EU (similar regulatory/tax environment)
- Revenue range: €10m–€500m (same order of magnitude as AUCTUS targets)
- Business model similarity is more important than exact sector classification
- Private company targets → use listed peers as proxies; apply private company discount
  (typically 10-30%) in the comparability limitations section
- **Calendarization**: All peer financials MUST be calendarized to the target's fiscal year-end (or standard Dec 31) to align periods.
- **IFRS 16 / Leases**: Ensure EV includes capitalized lease liabilities and EBITDA is presented pre-lease expense (or adjust to EBITA/EBITDAR for apples-to-apples).

**Multiples & Metrics**:
- **Forward Multiples**: Mandatory inclusion of NTM (Next Twelve Months) or CY1 (Current Year + 1) estimates for EV/EBITDA and EV/Revenue.
- **Adjusted EBITDA**: Always use normalized/adjusted EBITDA (scrubbed for one-offs, exceptional items, non-recurring restructuring) for calculation.

**Statistics block** (mandatory):
- For EVERY ratio/margin/multiple column: max, 75th percentile, median, 25th percentile, min
- One blank row between company data and statistics rows for visual separation
- Do NOT add a "STATISTICS" header row above the stats block

**Cross-reference rule**: Valuation multiples MUST reference operating metrics cells —
never input the same raw revenue/EBITDA figure twice in the spreadsheet.

**Precedent transactions**:
- Past 10 years, DACH + wider Europe, EV €10m–€500m
- Minimum 3 transactions; if < 3 in primary geography, expand to wider Europe and note
- Source all transactions: announce date, target, buyer, EV, EV/EBITDA, buyer type (PE/strategic)
- **Control Premium / Premium Paid**: For public targets, capture the premium paid over 1-day/1-month unaffected share price.
- **Synergies**: Note if EV/EBITDA is reported pre- or post-synergies. Prefer pre-synergy multiples for base valuation.



---

## STEP 1 — PEER GROUP DEFINITION & PREREQUISITES

Read `skills/relative-valuation/refs/peer-group-criteria.md`.
Identify the peer selection criteria for this sector (inclusion rules, exclusion rules,
minimum data requirements).

If the required target financials or sector description does not exist, do NOT halt and ask the user for it. Instead, you MUST proactively gather the data from FactSet MCP or chat context, and explicitly execute the necessary upstream skills to generate the required dependencies. Specifically, run the `/sector-overview` skill to establish the target's operating environment and the `/3-statement-model` skill to derive its LTM financial baseline.

If `data/comps/peer_group.csv` exists: load and validate against peer criteria.
If not: use FactSet MCP (primary) or `brave-search` + `fetch` (fallback) to identify 4–6
publicly listed comparables matching: sector, revenue size (€10m–€500m), geography (EU/global
peers of similar profile), business model similarity.
Save identified peers to `data/comps/peer_group_{sector}_{timestamp}.csv`.

**Minimum requirement: 4 peers with publicly available LTM financials.**
If fewer than 4 qualify in the primary sector: read peer-group-criteria.md
Section "Adjacent Sector Expansions" and widen scope. Log the expansion decision.

## STEP 2 — BENCHMARK REFERENCE LOAD

Read `skills/relative-valuation/refs/multiples-benchmarks.yaml`.
Read `config/sector_benchmarks.yaml` for the relevant sector.
Extract: EV/EBITDA median, P25, P75; EV/Revenue median.
**These benchmarks are for sanity-checking only.**

## STEP 3 — TRADING COMPS EXECUTION

Calculate for each peer directly in your context window: 
- LTM & NTM/CY1 Revenue, Adjusted EBITDA, and EBIT.
- **Calendarize** the financials to align fiscal periods across peers (e.g. `Calendarized LTM = Latest FY + Latest Quarter - Same Quarter Prior Year`).
- Calculate multiples: LTM & NTM EV/Adjusted EBITDA, LTM & NTM EV/Revenue.
- Ensure Enterprise Value includes IFRS 16 lease liabilities (with EBITDA appropriately unburdened).

Derive: median, mean, 25th percentile, 75th percentile across peer group.
Apply implied EV range to target using P25–P75 EV/EBITDA band (LTM and NTM).

## STEP 4 — PRECEDENT TRANSACTIONS

Read `skills/relative-valuation/refs/precedent-filters.yaml` for deal filter parameters.

If `data/comps/precedent_transactions.csv` exists: load and apply filters from the YAML.
If not: use FactSet MCP (primary) or `brave-search` (fallback) to find closed M&A transactions
in the sector (past 10 years, DACH + wider Europe, EV €10m–€500m). Save raw data to
`data/comps/precedent_raw_{timestamp}.csv`.

Calculate precedent multiples natively in context based on the transactions dataset.

Minimum: 3 precedent deals. If fewer than 3 found: expand to wider Europe
geography and note the expansion in the comparability limitations section.

## STEP 5 — IMPLIED VALUATION CONSOLIDATION

Consolidate the calculated metrics.

Present three valuation reference points:
  1. Trading comps implied range (P25–P75 EV/EBITDA applied to target EBITDA)
  2. Precedent transactions implied range (P25–P75 EV/EBITDA from deals)
  3. Sector benchmark reference (from multiples-benchmarks.yaml — for context only)

## STEP 6 — REPORT COMPOSITION

Compose the markdown valuation report with:
  1. Header: company, sector, run date
  2. Peer group rationale (why these comparables were selected, any caveats)
  3. Trading comps table (from Excel — all peers with LTM & NTM EV/Adjusted EBITDA and EV/Revenue)
  4. Comps summary statistics (max, 75th percentile, median, 25th percentile, min)
  5. Precedent transactions table (from CSV — deal name, date, EV, EV/EBITDA, premium paid, buyer type)
  6. Implied valuation range: trading comps vs. precedents vs. sector benchmarks
  7. Comparability limitations (data vintage, size differences, cycle adjustments)

Write to `outputs/valuation_reports/{company}_{timestamp}_valuation_report.md`.

## STEP 7 — QUALITY GATE


Validate:
  - Trading comps Excel has 4–6 peer rows; no null multiples columns
  - Forward/NTM multiples are present for at least 80% of peers
  - Financials are calendarized where fiscal year-ends misalign
  - Precedents Excel has ≥3 deal rows
  - Implied EV range is a valid interval: lower bound < upper bound
  - Statistics block (max, 75th, median, 25th, min) present for all ratio/margin columns
  - Report is non-empty

Append completion entry to `logs/agent_activity.log`.

## EXIT CONDITION

Deliver paths to: trading comps Excel (.xlsx), precedents Excel (.xlsx), valuation report.
State explicitly: implied EV range (€m), EV/EBITDA multiple range applied,
and number of comps / precedents used.

---

# Comparable Company Analysis (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

# Comparable Company Analysis

## ⚠️ CRITICAL: Data Source Priority (READ FIRST)

**ALWAYS follow this data source hierarchy:**

1. **FIRST: Check for MCP data sources** - If S&P Kensho MCP, FactSet MCP, or Daloopa MCP are available, use them exclusively for financial and trading information
2. **DO NOT use web search** if the above MCP data sources are available
3. **ONLY if MCPs are unavailable:** Then use Bloomberg Terminal, SEC EDGAR filings, or other institutional sources
4. **NEVER use web search as a primary data source** - it lacks the accuracy, audit trails, and reliability required for institutional-grade analysis

**Why this matters:** MCP sources provide verified, institutional-grade data with proper citations. Web search results can be outdated, inaccurate, or unreliable for financial analysis.

---

## Overview
This skill teaches Claude to build institutional-grade comparable company analyses that combine operating metrics, valuation multiples, and statistical benchmarking. The output is a structured Excel/spreadsheet that enables informed investment decisions through peer comparison.

**Reference Material & Contextualization:**

An example comparable company analysis is provided in `examples/comps_example.xlsx`. When using this or other example files in this skill directory, use them intelligently:

**DO use examples for:**
- Understanding structural hierarchy (how sections flow)
- Grasping the level of rigor expected (statistical depth, documentation standards)
- Learning principles (clear headers, transparent formulas, audit trails)

**DO NOT use examples for:**
- Exact reproduction of format or metrics
- Copying layout without considering context
- Applying the same visual style regardless of audience

**ALWAYS ask yourself first:**
1. **"Do you have a preferred format or should I adapt the template style?"**
2. **"Who is the audience?"** (Investment committee, board presentation, quick reference, detailed memo)
3. **"What's the key question?"** (Valuation, growth analysis, competitive positioning, efficiency)
4. **"What's the context?"** (M&A evaluation, investment decision, sector benchmarking, performance review)

**Adapt based on specifics:**
- **Industry context**: Big tech mega-caps need different metrics than emerging SaaS startups
- **Sector-specific needs**: Add relevant metrics early (e.g., cloud ARR, enterprise customers, developer ecosystem for tech)
- **Company familiarity**: Well-known companies may need less background, more focus on delta analysis
- **Decision type**: M&A requires different emphasis than ongoing portfolio monitoring

**Core principle:** Use template principles (clear structure, statistical rigor, transparent formulas) but vary execution based on context. The goal is institutional-quality analysis, not institutional-looking templates.

User-provided examples and explicit preferences always take precedence over defaults.

## Core Philosophy
**"Build the right structure first, then let the data tell the story."**

Start with headers that force strategic thinking about what matters, input clean data, build transparent formulas, and let statistics emerge automatically. A good comp should be immediately readable by someone who didn't build it.

---

## ⚠️ CRITICAL: Formulas Over Hardcodes + Step-by-Step Verification

**Environment — Office JS vs Python:**
- **If running inside Excel (Office Add-in / Office JS):** Use Office JS directly (`Excel.run(async (context) => {...})`). Write formulas via `range.formulas = [["=E7/C7"]]`, not `range.values`. No separate recalc step — Excel handles it natively. Use `range.format.*` for colors/fonts.
- **If generating a standalone .xlsx file:** Use Python/openpyxl. Write `cell.value = "=E7/C7"` (formula string).
- Same principles either way — just translate the API calls.
- **Office JS merged cell pitfall:** Do NOT call `.merge()` then set `.values` on the merged range (throws `InvalidArgument` — range still reports its pre-merge dimensions). Instead write the value to the top-left cell alone, then merge + format the full range:
  ```js
  ws.getRange("A1").values = [["TECHNOLOGY — COMPARABLE COMPANY ANALYSIS"]];
  const hdr = ws.getRange("A1:H1");
  hdr.merge();
  hdr.format.fill.color = "#1F4E79";
  hdr.format.font.color = "#FFFFFF";
  hdr.format.font.bold = true;
  ```

**Formulas, not hardcodes:**
- Every derived value (margin, multiple, statistic) MUST be an Excel formula referencing input cells — never a pre-computed number pasted in
- When using Python/openpyxl to build the sheet: write `cell.value = "=E7/C7"` (formula string), NOT `cell.value = 0.687` (computed result)
- The only hardcoded values should be raw input data (revenue, EBITDA, share price, etc.) — and every one of those gets a cell comment with its source
- Why: the model must update automatically when an input changes. A hardcoded margin is a silent bug waiting to happen.

**Verify step-by-step with the user:**
- After setting up the structure → show the user the header layout before filling data
- After entering raw inputs → show the user the input block and confirm sources/periods before building formulas
- After building operating metrics formulas → show the calculated margins and sanity-check with the user before moving to valuation
- After building valuation multiples → show the multiples and confirm they look reasonable before adding statistics
- Do NOT build the entire sheet end-to-end and then present it — catch errors early by confirming each section

---

## Section 1: Document Structure & Setup

### Header Block (Rows 1-3)
```
Row 1: [ANALYSIS TITLE] - COMPARABLE COMPANY ANALYSIS
Row 2: [List of Companies with Tickers] • [Company 1 (TICK1)] • [Company 2 (TICK2)] • [Company 3 (TICK3)]
Row 3: As of [Period] | All figures in [EUR Millions/Billions] except per-share amounts and ratios
```

**Why this matters:** Establishes context immediately. Anyone opening this file knows what they're looking at, when it was created, and how to interpret the numbers.

### Visual Convention Standards (OPTIONAL - User preferences and uploaded templates always override)

**IMPORTANT: These are suggested defaults only. Always prioritize:**
1. User's explicit formatting preferences
2. Formatting from any uploaded template files
3. Company/team style guides
4. These defaults (only if no other guidance provided)

**Suggested Font & Typography:**
- **Font family**: Times New Roman (professional, readable, industry standard)
- **Font size**: 11pt for data cells, 12pt for headers
- **Bold text**: Section headers, company names, statistic labels

**Default Color & Shading — Professional Blue/Grey Palette (minimal is better):**
- **Keep it restrained** — only blues and greys. Do NOT introduce greens, oranges, reds, or multiple accent colors. A clean comps sheet uses 3-4 colors total.
- **Section headers** (e.g., "OPERATING STATISTICS & FINANCIAL METRICS"):
  - Dark blue background (`#1F4E79` or `#17365D` navy)
  - White bold text
  - Full row shading across all columns
- **Column headers** (e.g., "Company", "Revenue", "Margin"):
  - Light blue background (`#D9E1F2` or similar pale blue)
  - Black bold text
  - Centered alignment
- **Data rows**:
  - White background for company data
  - Black text for formulas; blue text for hardcoded inputs
- **Statistics rows** (Maximum, 75th Percentile, etc.):
  - Light grey background (`#F2F2F2`)
  - Black text, left-aligned labels
- **That's the whole palette**: dark blue + light blue + light grey + white. Nothing else unless the user's template says otherwise.

**Suggested Formatting Conventions:**
- **Decimal precision**:
  - Percentages: 1 decimal (12.3%)
  - Multiples: 1 decimal (13.5x)
  - Dollar amounts: No decimals, thousands separator (69,632)
  - Margins shown as percentages: 1 decimal (68.7%)
- **Borders**: No borders (clean, minimal appearance)
- **Alignment**: All metrics center-aligned for clean, uniform appearance
- **Cell dimensions**: All column widths should be uniform/even, all row heights should be consistent (creates clean, professional grid)

**Note:** If the user provides a template file or specifies different formatting, use that instead.

---

## Section 2: Operating Statistics & Financial Metrics

### Core Columns (Start with these)
1. **Company** - Names with consistent formatting
2. **Revenue** - Size metric (show both LTM and NTM / Forward 1Y)
3. **Revenue Growth** - Year-over-year percentage change (Historical and Forward)
4. **Gross Profit** - Revenue minus cost of goods sold
5. **Gross Margin** - GP/Revenue (fundamental profitability)
6. **Adjusted EBITDA** - Normalized earnings before interest, tax, depreciation, amortization (excluding one-offs)
7. **Adjusted EBITDA Margin** - Adjusted EBITDA/Revenue (operating efficiency)

### Optional Additions (Choose based on industry/purpose)
- **Calendarization Adjustments** - Document formula used to align fiscal years
- **Quarterly vs LTM** - Include both if seasonality matters
- **Free Cash Flow** - For capital-intensive or SaaS businesses
- **FCF Margin** - FCF/Revenue (cash generation efficiency)
- **Net Income** - For mature, profitable companies
- **Operating Income** - For businesses with varying D&A
- **CapEx metrics** - For asset-heavy industries
- **Rule of 40** - Specifically for SaaS (Growth % + Margin %)
- **FCF Conversion** - For quality of earnings analysis (advanced)

### Formula Examples (Using Row 7 as example)
```excel
// Core ratios - these are always calculated
Gross Margin (F7): =E7/C7
EBITDA Margin (H7): =G7/C7

// Optional ratios - include if relevant
FCF Margin: =[FCF]/[Revenue]
Net Margin: =[Net Income]/[Revenue]
Rule of 40: =[Growth %]+[FCF Margin %]
```

**Golden Rule:** Every ratio should be [Something] / [Revenue] or [Something] / [Something from this sheet]. Keep it simple.

### Statistics Block (After company data)

**CRITICAL: Add statistics formulas for all comparable metrics (ratios, margins, growth rates, multiples).**

```
[Leave one blank row for visual separation]
- Maximum: =MAX(B7:B9)
- 75th Percentile: =QUARTILE(B7:B9,3)
- Median: =MEDIAN(B7:B9)
- 25th Percentile: =QUARTILE(B7:B9,1)
- Minimum: =MIN(B7:B9)
```

**Columns that NEED statistics (comparable metrics):**
- Revenue Growth %, Gross Margin %, EBITDA Margin %, EPS
- EV/Revenue, EV/EBITDA, P/E, Dividend Yield %, Beta

**Columns that DON'T need statistics (size metrics):**
- Revenue, EBITDA, Net Income (absolute size varies by company scale)
- Market Cap, Enterprise Value (not comparable across different-sized companies)

**Note:** Add one blank row between company data and statistics rows for visual separation. Do NOT add a "SECTOR STATISTICS" or "VALUATION STATISTICS" header row.

**Why quartiles matter:** They show distribution, not just average. A 75th percentile multiple tells you what "premium" companies trade at.

---

## Section 3: Valuation Multiples & Investment Metrics

### Core Valuation Columns (Start with these)
1. **Company** - Same order as operating section
2. **Market Cap** - Current market valuation
3. **Enterprise Value** - Market Cap ± Net Debt/Cash + IFRS 16 Capitalized Leases + Minority Interest - Associates
4. **EV/LTM Revenue** - How much market pays per dollar of historical sales
5. **EV/NTM Revenue** - Forward revenue multiple (crucial for growth stocks)
6. **EV/LTM Adj. EBITDA** - How much market pays per dollar of historical earnings
7. **EV/NTM Adj. EBITDA** - Forward earnings multiple (standard PE/IB metric)
8. **P/E Ratio (LTM & NTM)** - Price relative to net earnings

### Optional Valuation Metrics (Choose based on context)
- **FCF Yield** - FCF/Market Cap (for cash-focused analysis)
- **PEG Ratio** - P/E/Growth Rate (for growth companies)
- **Price/Book** - Market value vs. book value (for asset-heavy businesses)
- **ROE/ROA** - Return metrics (for profitability comparison)
- **Revenue/EBITDA CAGR** - Historical growth rates (for trend analysis)
- **Asset Turnover** - Revenue/Assets (for operational efficiency)
- **Debt/Equity** - Leverage (for capital structure analysis)

**Key Principle:** Include 3-5 core multiples that matter for your industry. Don't include every possible metric just because you can.

### Formula Examples
```excel
// Core multiples - always include these
EV/LTM Revenue: =[Enterprise Value]/[LTM Revenue]
EV/NTM Revenue: =[Enterprise Value]/[NTM Revenue]
EV/LTM Adj. EBITDA: =[Enterprise Value]/[LTM Adj. EBITDA]
EV/NTM Adj. EBITDA: =[Enterprise Value]/[NTM Adj. EBITDA]
P/E Ratio: =[Market Cap]/[Net Income]

// Optional multiples - include if data available
FCF Yield: =[LTM FCF]/[Market Cap]
PEG Ratio: =[P/E]/[Growth Rate %]
```

### Cross-Reference Rule
**CRITICAL:** Valuation multiples MUST reference the operating metrics section. Never input the same raw data twice. If revenue is in C7, then EV/Revenue formula should reference C7.

### Statistics Block
Same structure as operating section: Max, 75th, Median, 25th, Min for every metric. Add one blank row for visual separation between company data and statistics. Do NOT add a "VALUATION STATISTICS" header row.

---

## Section 4: Notes & Methodology Documentation

### Required Components

**Data Sources & Quality:**
- Where did the data come from? (S&P Kensho MCP, FactSet MCP, Daloopa MCP, Bloomberg, SEC filings)
- What period does it cover? (Q4 2024, audited figures)
- How was it verified? (Cross-checked against 10-K/10-Q)
- Note: Prioritize MCP data sources (S&P Kensho, FactSet, Daloopa) if available for better accuracy and traceability

**Key Definitions:**
- EBITDA calculation method (Gross Profit + D&A, or Operating Income + D&A)
- Free Cash Flow formula (Operating CF - CapEx)
- Special metrics explained (Rule of 40, FCF Conversion)
- Time period definitions (LTM, CAGR calculation periods)

**Valuation Methodology:**
- How was Enterprise Value calculated? (Market Cap + Net Debt)
- What growth rates were used? (Historical CAGR, forward estimates)
- Any adjustments made? (One-time items excluded, normalized margins)

**Analysis Framework:**
- What's the investment thesis? (Cloud/SaaS efficiency)
- What metrics matter most? (Cash generation, capital efficiency)
- How should readers interpret the statistics? (Quartiles provide context)

---

## Section 5: Choosing the Right Metrics (Decision Framework)

### Start with "What question am I answering?"

**"Which company is undervalued?"**
→ Focus on: EV/Revenue, EV/EBITDA, P/E, Market Cap
→ Skip: Operational details, growth metrics

**"Which company is most efficient?"**
→ Focus on: Gross Margin, EBITDA Margin, FCF Margin, Asset Turnover
→ Skip: Size metrics, absolute dollar amounts

**"Which company is growing fastest?"**
→ Focus on: Revenue Growth %, EBITDA CAGR, User/Customer Growth
→ Skip: Margin metrics, leverage ratios

**"Which is the best cash generator?"**
→ Focus on: FCF, FCF Margin, FCF Conversion, CapEx intensity
→ Skip: EBITDA, P/E ratios

### Industry-Specific Metric Selection

**Software/SaaS:**
Must have: Revenue Growth, Gross Margin, Rule of 40
Optional: ARR, Net Dollar Retention, CAC Payback
Skip: Asset Turnover, Inventory metrics

**Manufacturing/Industrials:**
Must have: EBITDA Margin, Asset Turnover, CapEx/Revenue
Optional: ROA, Inventory Turns, Backlog
Skip: Rule of 40, SaaS metrics

**Financial Services:**
Must have: ROE, ROA, Efficiency Ratio, P/E
Optional: Net Interest Margin, Loan Loss Reserves
Skip: Gross Margin, EBITDA (not meaningful for banks)

**Retail/E-commerce:**
Must have: Revenue Growth, Gross Margin, Inventory Turnover
Optional: Same-Store Sales, Customer Acquisition Cost
Skip: Heavy R&D or CapEx metrics

### The "5-10 Rule"

**5 operating metrics** - Revenue, Growth, 2-3 margins/efficiency metrics
**5 valuation metrics** - Market Cap, EV, 3 multiples
**= 10 total columns** - Enough to tell the story, not so many you lose the thread

If you have more than 15 metrics, you're probably including noise. Edit ruthlessly.

---

## Section 6: Best Practices & Quality Checks

### Before You Start
1. **Define the peer group** - Companies must be truly comparable (similar business model, scale, geography)
2. **Choose the right period** - LTM smooths seasonality; quarterly shows trends
3. **Standardize units upfront** - Millions vs. billions decision affects everything
4. **Map data sources** - Know where each number comes from

### As You Build
1. **Input all raw data first** - Complete the blue text before writing formulas
2. **Add cell comments to ALL hard-coded inputs** - Right-click cell → Insert Comment → Document source OR assumption

   **For sourced data, cite exactly where it came from:**
   - Example: "Bloomberg Terminal - MSFT Equity DES, accessed 2024-10-02"
   - Example: "Q4 2024 10-K filing, page 42, line item 'Total Revenue'"
   - Example: "FactSet consensus estimate as of 2024-10-02"
   - **Include hyperlinks when possible**: Right-click cell → Link → paste URL to SEC filing, data source, or report

   **For assumptions, explain the reasoning:**
   - Example: "Assumed 15% EBITDA margin based on peer median, company does not disclose"
   - Example: "Estimated Enterprise Value as Market Cap + $50M net debt (from Q3 balance sheet, Q4 not yet available)"
   - Example: "Forward P/E based on street consensus EPS of $3.45 (average of 12 analyst estimates)"

   **Why this matters**: Enables audit trails, data verification, assumption transparency, and future updates
3. **Build formulas row by row** - Test each calculation before moving on
4. **Use absolute references for headers** - $C$6 locks the header row
5. **Format consistently** - Percentages as percentages, not decimals
6. **Add conditional formatting** - Highlight outliers automatically

### Sanity Checks
- **Margin test**: Gross margin > EBITDA margin > Net margin (always true by definition)
- **Multiple reasonableness**: 
  - EV/Revenue: typically 0.5-20x (varies widely by industry)
  - EV/EBITDA: typically 8-25x (fairly consistent across industries)
  - P/E: typically 10-50x (depends on growth rate)
- **Growth-multiple correlation**: Higher growth usually means higher multiples
- **Size-efficiency trade-off**: Larger companies often have better margins (scale benefits)

### Common Mistakes to Avoid
❌ Mixing market cap and enterprise value in formulas
❌ Using different time periods for numerator and denominator (LTM vs quarterly)
❌ Hardcoding numbers into formulas instead of cell references
❌ **Hard-coded inputs without cell comments citing the source OR explaining the assumption**
❌ Missing hyperlinks to SEC filings or data sources when available
❌ Including too many metrics without clear purpose
❌ Including non-comparable companies (different business models)
❌ Using outdated data without disclosure
❌ Calculating averages of percentages incorrectly (should be median)

---

## Section 6: Advanced Features

### Dynamic Headers
For columns showing calculations, use clear unit labels:
```
Revenue Growth (YoY) % | EBITDA Margin | FCF Margin | Rule of 40
```

### Quartile Analysis Benefits
Instead of just mean/median, quartiles show:
- **75th percentile** = "Premium" companies trade here
- **Median** = Typical market valuation
- **25th percentile** = "Discount" territory

This helps answer: "Is our target company trading rich or cheap vs. peers?"

### Industry-Specific Modifications

**Software/SaaS:**
- Add: ARR, Net Dollar Retention, CAC Payback Period
- Emphasize: Rule of 40, FCF margins, gross margins >70%

**Healthcare:**
- Add: R&D/Revenue, Pipeline value, Regulatory status
- Emphasize: EBITDA margins, growth rates, reimbursement risk

**Industrials:**
- Add: Backlog, Order book trends, Geographic mix
- Emphasize: ROIC, asset turnover, cyclical adjustments

**Consumer:**
- Add: Same-store sales, Customer acquisition cost, Brand value
- Emphasize: Revenue growth, gross margins, inventory turns

### Correct Patterns: Non-Obvious Implementations

**Calendarization**:
When a peer's fiscal year ends on a month other than the target's, calculate the calendarized metric:
`Calendarized LTM = Latest Annual Result + Latest YTD - Prior Year YTD`. 
Alternatively, for forward estimates, weight the broker estimates across the two fiscal years that overlap the target's 12-month forward period.

**IFRS 16 / ASC 842 Lease Adjustments**:
Ensure consistency between numerator (EV) and denominator (EBITDA). 
- If EBITDA is reported post-IFRS 16 (i.e. lease expenses are below EBITDA as D&A and interest), then EV MUST include Capitalized Lease Liabilities in the debt bridge. 
- If evaluating pre-IFRS 16 / EBITA, deduct lease liabilities from EV and subtract lease expenses from EBITDA.

**Premium Paid Analysis (Precedents)**:
For public company precedents, fetch the unaffected share price (typically 1-day, 1-week, or 4-weeks prior to rumor/announcement) and compute:
`Premium % = (Offer Price / Unaffected Price) - 1`. Document this in the precedents table to understand how much of the EV/EBITDA multiple is driven by a control premium.

---

## Section 7: Workflow & Practical Tips

### Step-by-Step Process
1. **Set up structure** (30 minutes)
   - Create all headers
   - Format cells (blue for inputs, black for formulas)
   - Lock in units and date references

2. **Gather data** (60-90 minutes)
   - Pull from primary sources (S&P Kensho MCP, FactSet MCP, Daloopa MCP if available; otherwise Bloomberg, SEC)
   - Input all raw numbers in blue
   - Document sources in notes section

3. **Build formulas** (30 minutes)
   - Start with simple ratios (margins)
   - Progress to multiples (EV/Revenue)
   - Add cross-checks (do margins make sense?)

4. **Add statistics** (15 minutes)
   - Copy formula structure for all columns
   - Verify ranges are correct (B7:B9, not B7:B10)
   - Check quartile logic

5. **Quality control** (30 minutes)
   - Run sanity checks
   - Verify formula references
   - Check for #DIV/0! or #REF! errors
   - Compare against known benchmarks

6. **Documentation** (15 minutes)
   - Complete notes section
   - Add data sources
   - Define methodologies
   - Date-stamp the analysis

### Pro Tips
- **Save templates**: Build once, reuse forever
- **Color-code outliers**: Conditional formatting for values >2 standard deviations
- **Link to source files**: Hyperlink to Bloomberg screenshots or SEC filings
- **Version control**: Save as "Comps_v1_2024-12-15" with clear dating
- **Collaborative reviews**: Have someone else check your formulas

### Excel Formatting Checklist (Optional - adapt to user preferences)
- [ ] Font set to user's preferred style (default: Times New Roman, 11pt data, 12pt headers)
- [ ] Section headers formatted per user's template (default: dark blue #17365D with white bold text)
- [ ] Column headers formatted per user's template (default: light blue/gray #D9E2F3 with black bold text)
- [ ] Statistics rows formatted per user's template (default: light gray #F2F2F2)
- [ ] No borders applied (clean, minimal appearance)
- [ ] **Column widths set to uniform/even width** (creates clean, professional appearance)
- [ ] **Row heights set to consistent height** (typically 20-25pt for data rows)
- [ ] Numbers formatted with proper decimal precision and thousands separators
- [ ] **All metrics center-aligned** for clean, uniform appearance
- [ ] **One blank row for separation between company data and statistics rows**
- [ ] **No separate "SECTOR STATISTICS" or "VALUATION STATISTICS" header rows**
- [ ] **Every hard-coded input cell has a comment with either: (1) exact data source, OR (2) assumption explanation**
- [ ] **Hyperlinks added to cells where applicable** (SEC filings, data provider pages, reports)

---

## Section 8: Example Template Layout

**Simple Version (Start here):**
```
┌─────────────────────────────────────────────────────────────┐
│ TECHNOLOGY - COMPARABLE COMPANY ANALYSIS                    │
│ Microsoft • Alphabet • Amazon                               │
│ As of Q4 2024 | All figures in EUR Millions                │
├─────────────────────────────────────────────────────────────┤
│ OPERATING METRICS                                           │
├──────────┬─────────┬─────────┬──────────┬──────────────────┤
│ Company  │ Revenue │ Growth  │ Gross    │ EBITDA  │ EBITDA │
│          │ (LTM)   │ (YoY)   │ Margin   │ (LTM)   │ Margin │
├──────────┼─────────┼─────────┼──────────┼─────────┼────────┤
│ MSFT     │ 261,400 │ 12.3%   │ 68.7%    │ 205,100 │ 78.4%  │
│ GOOGL    │ 349,800 │ 11.8%   │ 57.9%    │ 239,300 │ 68.4%  │
│ AMZN     │ 638,100 │ 10.5%   │ 47.3%    │ 152,600 │ 23.9%  │
│          │         │         │          │         │        │ [blank row]
│ Median   │ =MEDIAN │ =MEDIAN │ =MEDIAN  │ =MEDIAN │=MEDIAN │
│ 75th %   │ =QUART  │ =QUART  │ =QUART   │ =QUART  │=QUART  │
│ 25th %   │ =QUART  │ =QUART  │ =QUART   │ =QUART  │=QUART  │
├─────────────────────────────────────────────────────────────┤
│ VALUATION MULTIPLES                                         │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Company  │ Mkt Cap  │ EV       │ EV/Rev   │ EV/EBITDA │ P/E│
├──────────┼──────────┼──────────┼──────────┼───────────┼────┤
│ MSFT     │3,550,000 │3,530,000 │ 13.5x    │ 17.2x     │36.0│
│ GOOGL    │2,030,000 │1,960,000 │  5.6x    │  8.2x     │24.5│
│ AMZN     │2,226,000 │2,320,000 │  3.6x    │ 15.2x     │58.3│
│          │          │          │          │           │    │ [blank row]
│ Median   │ =MEDIAN  │ =MEDIAN  │ =MEDIAN  │ =MEDIAN   │=MED│
│ 75th %   │ =QUART   │ =QUART   │ =QUART   │ =QUART    │=QRT│
│ 25th %   │ =QUART   │ =QUART   │ =QUART   │ =QUART    │=QRT│
└──────────┴──────────┴──────────┴──────────┴───────────┴────┘
```

**Add complexity only when needed:**
- Include quarterly AND LTM if seasonality matters
- Add FCF metrics if cash generation is key story
- Include industry-specific metrics (Rule of 40 for SaaS, etc.)
- Add more statistics rows if you have >5 companies

---

## Section 9: Industry-Specific Additions (Optional)

Only add these if they're critical to your analysis. Most comps work fine with just core metrics.

**Software/SaaS:**
Add if relevant: ARR, Net Dollar Retention, Rule of 40

**Financial Services:**
Add if relevant: ROE, Net Interest Margin, Efficiency Ratio

**E-commerce:**
Add if relevant: GMV, Take Rate, Active Buyers

**Healthcare:**
Add if relevant: R&D/Revenue, Pipeline Value, Patent Timeline

**Manufacturing:**
Add if relevant: Asset Turnover, Inventory Turns, Backlog

---

## Section 10: Red Flags & Warning Signs

### Data Quality Issues
🚩 Inconsistent time periods (mixing quarterly and annual)  
🚩 Missing data without explanation  
🚩 Significant differences between data sources (>10% variance)

### Valuation Red Flags
🚩 Negative EBITDA companies being valued on EBITDA multiples (use revenue multiples instead)  
🚩 P/E ratios >100x without hypergrowth story  
🚩 Margins that don't make sense for the industry

### Comparability Issues
🚩 Different fiscal year ends (causes timing problems)  
🚩ixing pure-play and conglomerates  
🚩 Materially different business models labeled as "comps"

**When in doubt, exclude the company.** Better to have 3 perfect comps than 6 questionable ones.

---

## Section 11: Formulas Reference Guide

### Essential Excel Formulas
```excel
// Statistical Functions
=AVERAGE(range)          // Simple mean
=MEDIAN(range)           // Middle value
=QUARTILE(range, 1)      // 25th percentile
=QUARTILE(range, 3)      // 75th percentile
=MAX(range)              // Maximum value
=MIN(range)              // Minimum value
=STDEV.P(range)          // Standard deviation

// Financial Calculations
=B7/C7                   // Simple ratio (Margin)
=SUM(B7:B9)/3            // Average of multiple companies
=IF(B7>0, C7/B7, "N/A")  // Conditional calculation
=IFERROR(C7/D7, 0)       // Handle divide by zero

// Cross-Sheet References
='Sheet1'!B7             // Reference another sheet
=VLOOKUP(A7, Table1, 2)  // Lookup from data table
=INDEX(MATCH())          // Advanced lookup

// Formatting
=TEXT(B7, "0.0%")        // Format as percentage
=TEXT(C7, "#,##0")       // Thousands separator
```

### Common Ratio Formulas
```excel
Gross Margin = Gross Profit / Revenue
EBITDA Margin = EBITDA / Revenue
FCF Margin = Free Cash Flow / Revenue
FCF Conversion = FCF / Operating Cash Flow
ROE = Net Income / Shareholders' Equity
ROA = Net Income / Total Assets
Asset Turnover = Revenue / Total Assets
Debt/Equity = Total Debt / Shareholders' Equity
```

---

## Key Principles Summary

1. **Structure drives insight** - Right headers force right thinking
2. **Less is more** - 5-10 metrics that matter beat 20 that don't
3. **Choose metrics for your question** - Valuation analysis ≠ efficiency analysis
4. **Statistics show patterns** - Median/quartiles reveal more than average
5. **Transparency beats complexity** - Simple formulas everyone understands
6. **Comparability is king** - Better to exclude than force a bad comp
7. **Document your choices** - Explain which metrics and why in notes section

---

## Output Checklist

Before delivering a comp analysis, verify:
- [ ] All companies are truly comparable
- [ ] Data is from consistent time periods
- [ ] Units are clearly labeled (millions/billions)
- [ ] Formulas reference cells, not hardcoded values
- [ ] **All hard-coded input cells have comments with either: (1) exact data source with citation, OR (2) clear assumption with explanation**
- [ ] **Hyperlinks added where relevant** (SEC EDGAR filings, Bloomberg pages, research reports)
- [ ] Statistics include at least 5 metrics (Max, 75th, Med, 25th, Min)
- [ ] Notes section documents sources and methodology
- [ ] Visual formatting follows conventions (blue = input, black = formula)
- [ ] Sanity checks pass (margins logical, multiples reasonable)
- [ ] Date stamp is current ("As of [Date]")
- [ ] Formula auditing shows no errors (#DIV/0!, #REF!, #N/A)

---

## Continuous Improvement

After completing a comp analysis, ask:
1. Did the statistics reveal unexpected insights?
2. Were there any data gaps that limited analysis?
3. Did stakeholders ask for metrics you didn't include?
4. How long did it take vs. how long should it take?
5. What would make this more useful next time?

The best comp analyses evolve with each iteration. Save templates, learn from feedback, and refine the structure based on what decision-makers actually use.
