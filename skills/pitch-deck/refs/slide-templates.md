# Content Mapping Reference

This file provides guidance for mapping source data to pitch deck template sections. The process is template-agnostic—these principles apply regardless of the specific template design.

**AUCTUS context:** Source data is always Python script outputs (LBO JSON, DCF JSON, target matrix Excel). Never use LLM-estimated financial figures. All monetary values in EUR millions (€m).

## Contents

- [Template Analysis Process](#template-analysis-process)
- [Content Mapping Workflow](#content-mapping-workflow)
- [Common Slide Types and Data Requirements](#common-slide-types-and-data-requirements)
- [AUCTUS-Specific Slide Mapping](#auctus-specific-slide-mapping)
- [Mapping Verification Checklist](#mapping-verification-checklist)
- [Handling Data-Template Mismatches](#handling-data-template-mismatches)
- [Template-Specific Adaptation](#template-specific-adaptation)

---

## Template Analysis Process

Before populating any template, analyze its structure:

### Step 1: Identify All Content Areas

Scan each slide for:
- **Title/header placeholders** — Where slide titles go
- **Subtitle/definition areas** — Secondary headers or definitions
- **Content boxes** — Main content areas (may have label sidebars)
- **Table placeholders** — Areas designated for tabular data
- **Chart/visual areas** — Spaces for charts, diagrams, or images
- **Metric callout boxes** — Highlighted key figures
- **Footnote/source bars** — Bottom areas for citations and notes
- **Logo placeholder** — Usually top-right corner

### Step 2: Note Template Conventions

Each template has its own style. Observe:
- **Color scheme** — What colors are used for headers, backgrounds, accents?
- **Font choices** — What fonts and sizes are already set?
- **Box styling** — Do content boxes have sidebars, borders, or shading?
- **Bullet styles** — What bullet symbols does the template use?
- **Alignment patterns** — How are parallel sections aligned?

### Step 3: Identify Instruction vs. Output Areas

Templates often include guidance:
- **Instruction boxes** — Colored boxes with guidance text (often yellow background, white text)
- **Placeholder text** — Text in [brackets] indicating what to replace
- **Example content** — Sample content showing expected format

**Key distinction**: Instruction boxes tell you what to do; they should be reformatted or removed in final output. Output areas are where your content goes.

---

## Content Mapping Workflow

### Step 1: Inventory Source Data

Create a list of all available data:
- Market size figures and ranges
- Growth rates (CAGR, YoY)
- Company names and descriptions
- Segment definitions
- Financial metrics (from LBO JSON / DCF JSON)
- Source citations and dates
- Footnote content

### Step 2: Match Data to Template Sections

For each template section, identify:

| Template Section | Required Data | Source Location |
|------------------|---------------|-----------------|
| [Section name] | [Data needed] | [Where to find it] |

### Step 3: Identify Gaps

After mapping, note:
- **Missing data** — Template requires data not in sources
- **Extra data** — Sources contain data with no template home
- **Format mismatches** — Data exists but in wrong format

### Step 4: Resolve Gaps Before Populating

- Missing data: Flag for user or search for additional sources
- Extra data: Confirm if it should be excluded or if template needs adjustment
- Format mismatches: Transform data to required format

---

## Common Slide Types and Data Requirements

These are typical data requirements for common slide types. Your specific template may vary—always follow the template's actual structure.

### Market Definition Slides

**Typical content areas:**
- Segments included in scope (with examples/key players)
- Segments excluded from scope (with examples)
- Market definition text
- Scope rationale/justification

**Data mapping considerations:**
- Source data should clearly distinguish included vs. excluded segments
- Key players should be mapped to their respective segments
- Definition text should align with how sources define the market

**Data typically needed:**
- List of market segments to include (with key player examples)
- List of market segments to exclude (with examples)
- Market definition text
- Scope rationale or justification

**Formatting principle:** Parallel sections (included vs. excluded) should use matching formatting.

**Verification questions:**
- Does every segment have the appropriate symbol (✓ for included, × for excluded)?
- Are key players correctly assigned to segments?
- Does the definition match the source methodology?

### Market Sizing / TAM Slides

**Typical content areas:**
- Current market size (with year)
- Growth rate (CAGR with period)
- Future projection (with target year)
- Source-by-source breakdown table
- Consensus/summary figures
- Key takeaways or insights

**Data typically needed:**
- Market size figures with base year (in €m or €bn)
- Growth rates (CAGR with time period)
- Projection figures with target year
- Source citations for each data point

**Example column headers:** Source | [Base Year] Size (€m) | CAGR | [Target Year] Projection (€m)

**Formatting principle:** If showing multiple sources, include a consensus/summary row.

**Verification questions:**
- Do all source figures match original documents?
- Is the consensus calculated correctly (not just copied from one source)?
- Are projection years consistent across all figures?
- Do CAGR-based projections match when manually verified?

### Competitive Landscape Slides

**Typical content areas:**
- Comparison table with competitors as columns
- Feature/capability rows
- Financial metric rows (revenue, growth, market share)
- Key observations or positioning notes

**Data typically needed:**
- List of competitors to compare
- Features or capabilities for each
- Financial metrics (revenue, growth, market share) if available
- Time period for financial data

**Formatting principle:** Subject company should be visually distinguished from competitors (e.g., bold text, different background color, border, or positioned in rightmost column).

**Verification questions:**
- Are all competitors from the source data represented?
- Is the subject company visually distinguished?
- Are financial figures from the same time period?
- Is the ✓/× usage consistent and accurate?

### Financial Summary Slides

**Typical content areas:**
- Key metric callouts (headline figures)
- Historical financials table (actuals)
- Projected financials table (estimates)
- Growth rates and margins
- Optional trend charts

**Data typically needed:**
- Historical financials (actuals) for recent years
- Projected financials (estimates) for future years
- Key metrics: Revenue (€m), Growth %, Margins, EBITDA (€m)

**Example column headers:** Metric | FY[Year-2]A | FY[Year-1]A | FY[Year]A | FY[Year+1]E | FY[Year+2]E

**Formatting principle:** Clearly distinguish historical (A) from projected (E) data.

**Verification questions:**
- Are historical vs. projected periods clearly labeled?
- Do calculated growth rates match source or manual calculation?
- Are metric definitions consistent with source documents?

### Transaction Comparables Slides

**Typical content areas:**
- Transaction table (date, target, acquirer, deal value)
- Valuation multiples (EV/Revenue, EV/EBITDA)
- Summary statistics (mean, median, high, low)
- Implied valuation for subject company

**Data typically needed:**
- Transaction details: Date, Target, Acquirer, EV (€m)
- Valuation multiples: EV/Revenue, EV/EBITDA
- Subject company metrics for implied valuation

**Formatting principle:** Include summary statistics (Mean, Median, High, Low) for multiples.

**Verification questions:**
- Are all relevant transactions from the source included?
- Are multiples calculated correctly (EV ÷ Metric)?
- Do summary statistics cover all transactions in the table?
- Is implied valuation clearly labeled as illustrative?

---

## AUCTUS-Specific Slide Mapping

### Slide 2 — Executive Summary
Source fields from LBO compact JSON:
- `entry_ev_eur_m` → "Enterprise Value"
- `moic` → "MOIC" (format as `0.0×`)
- `irr_pct` → "IRR" (format as `0.0%`)
- `entry_multiple` → "Entry EV/EBITDA"
- `exit_multiple` → "Exit EV/EBITDA"

### Slide 5 — Historical & Projected Financials
Source fields from `3statement.json`:
- `historical_financials` array → 3 years historical actuals
- `projected_financials` array → 5 years projections
- Map `revenue`, `ebitda`, `ebitda_margin`, `fcf` to main table

### Slide 6 & 7 — Trading Comparables & Precedent Transactions
Source fields from `comps.json` & `precedents.json`:
- `comparables` / `transactions` list → populate table rows
- Compute Mean, Median, High, Low for EV/Rev and EV/EBITDA

### Slide 8 — Valuation Summary (Football Field)
Source from all valuation outputs:
- Min and Max values for DCF, LBO, Comps, Precedents
- Ensure ranges are overlapping and proposed Entry EV is indicated with a vertical line

### Slide 9 — DCF Valuation
Source fields from DCF results JSON:
- `npv_eur_m` → "Equity Value / NPV"
- `enterprise_value_eur_m` → "Enterprise Value"
- `pv_fcf_eur_m` → "PV of Free Cash Flows"
- `terminal_value_eur_m` → "Terminal Value"
- `terminal_value_pct` → "Terminal Value / EV"
- `wacc` → "WACC" (format as `0.0%`)
- `terminal_growth_rate` → "Terminal Growth Rate" (format as `0.0%`)

### Slide 10 — LBO Analysis
Sources & Uses table: read from `sources_uses_table` in LBO compact JSON.
Exit Metrics table: read from `exit_metrics` block.
Balance check: `balance_check_eur_m` must be within ±€0.01m of zero.

### Slide 11 — Sensitivity Grid
Read IRR sensitivity matrix from `sensitivity_irr` in LBO compact JSON.
5×5 grid with center cell matching `irr_pct` field exactly.
Center cell highlighted #BDD7EE.

### Slide 12 — Value Creation Bridge
Read `value_creation_bridge` array from LBO compact JSON.
Present as 4 levers with €m attribution.

### Slide 13 — Risk Factors & Mitigants
Pair each identified risk factor with a tangible mitigant. Never list a risk without its corresponding AUCTUS mitigating action.

### Slide 14 — Management & Ownership
Source from `3statement.json` or `target_matrices`:
- Create current vs post-deal Cap Table (Diluted)
- Highlight Management rollover and equity incentive pool (MIP)

---

## Mapping Verification Checklist

Before moving to formatting, verify mapping completeness:

### Data Completeness
- [ ] Every template placeholder has mapped source data
- [ ] All source citations are recorded for footnotes
- [ ] No placeholder [brackets] remain unmapped

### Data Accuracy
- [ ] Figures match LBO JSON / DCF JSON exactly (not LLM-estimated)
- [ ] Years and time periods are correctly noted
- [ ] Company names are spelled correctly
- [ ] Calculated values (consensus, projections, multiples) verified per `calculation-standards.md`

### Logical Consistency
- [ ] Historical data precedes projected data chronologically
- [ ] Comparison data uses consistent time periods

- [ ] S&U balance_check_eur_m within ±€0.01m of zero

### Source Attribution
- [ ] Every data point traced to LBO JSON / DCF JSON / target matrix
- [ ] Source noted in footnote: "AUCTUS LBO Model, [company], [date]"

---

## Handling Data-Template Mismatches

### Template Requires More Data Than Available

**Options:**
1. Flag the gap explicitly for user review
2. Mark section as "Data not available — run [workflow] first"
3. Recommend running the relevant AUCTUS workflow (DCF / LBO / competitor-analysis)

**Do not:** Fabricate data or make LLM-estimated financial figures.

### Source Has More Data Than Template Accommodates

**Options:**
1. Include most relevant/recent data points
2. Summarize or aggregate where appropriate
3. Add footnotes referencing additional available data

### Data Format Doesn't Match Template Format

**Common transformations:**
- Individual figures → Range (use min-max from script output sensitivity grids)
- Detailed breakdown → Summary category
- Annual figures → CAGR (calculate from endpoints)
- Absolute values → Percentages (calculate share)

---

## Template-Specific Adaptation

Remember: This guidance describes common patterns, not requirements. Always:

1. **Follow the template** — If template uses different section names, use those
2. **Match template style** — Use AUCTUS brand colors (#1F4E79, #BDD7EE), not hardcoded orange/red
3. **Preserve template structure** — Don't rearrange slides
4. **Respect template spacing** — Content should fit designated areas without overflow

The goal is to populate the template as designed, not to redesign it.
