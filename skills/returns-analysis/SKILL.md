---
name: returns-analysis
version: "1.1.0"
description: >
  Builds IRR/MOIC sensitivity tables and returns waterfalls for AUCTUS PE deal evaluation.
  Models returns across entry multiple, leverage, exit multiple, growth, and hold period.
  EUR cash flows; Euribor-linked debt service in returns bridge. AUCTUS hurdle: MOIC ≥2.0×, IRR ≥20%.
triggers:
  - "returns analysis"
  - "IRR sensitivity"
  - "MOIC table"
  - "what's the return at"
  - "model the returns"
  - "back of the envelope"
  - "equity returns"
  - "returns bridge"
  - "IRR waterfall"
inputs:
  required:
    - "lbo_compact — path to LBO compact JSON (outputs/dcf_models/lbo_*_lbo_compact.json)"
  optional:
    - "entry_multiple_range — e.g. '8,9,10,11,12' for sensitivity axis"
    - "exit_multiple_range — e.g. '8,10,12,14' for sensitivity axis"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
  sensitivity_config: "skills/lbo-modeling/refs/sensitivity-config.yaml"

outputs:
  - "outputs/dcf_models/returns_{company}_{YYYYMMDD_HHMMSS}_analysis.md"
  - "outputs/dcf_models/returns_{company}_{YYYYMMDD_HHMMSS}_sensitivity.xlsx"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG targets MOIC ≥ 2.0× and IRR ≥ 20% as minimum hurdle rates.
Calculate these returns directly in your context window. EUR cash flows; Euribor-linked senior debt impacts returns bridge.

### Prerequisites

`/lbo-modeling` — all return inputs come from the LBO model. Run before this skill.
Read the compact JSON at `outputs/dcf_models/lbo_{company}_{timestamp}_lbo_compact.json`.

### Data Source Hierarchy

1. **LBO compact JSON** — primary source for all return inputs (IRR, MOIC, cash flows)
2. **User-provided data** — alternative scenarios, management rollover, dividend recaps
3. **FactSet MCP** — market comparable multiples for sensitivity axis calibration


### Currency & Units

- All monetary values in **EUR millions (€m)**
- IRR: `0.0%`; MOIC: `0.00×` (2 decimal places for precision)
- Negatives: `(€X.Xm)` — parentheses, no minus sign

### Execution Environment

Calculate the IRR, MOIC, sensitivity grids, and returns bridge natively in your context window based on the LBO parameters.

### AUCTUS-Specific Rules

**Hurdle rates** (state explicitly in output):
- **MOIC ≥ 2.0×** — minimum target
- **IRR ≥ 20%** — minimum target
- If either is missed: note as **BELOW IC HURDLE RATE** — present the deal to IC but flag clearly

**Returns bridge** (always include):
- EBITDA growth contribution (€m and %)
- Multiple expansion/contraction contribution
- Debt paydown contribution
- Euribor sensitivity: state impact of +100bps on Euribor on IRR (qualitative if not modeled)
- Fee/expense drag

**Sensitivity grids**: 5×5 ODD. Center cell = base case (must match LBO model output exactly).
Highlight center cell `#BDD7EE`. Both IRR (%) and MOIC (×) grids required.

**Transaction costs**: 2.0% financing fee + 1.5% advisor fee are AUCTUS defaults.
These reduce Day 1 equity value — confirm they're included in the LBO model.

---

# Returns Analysis (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Gather Deal Inputs

Ask for (or extract from prior analysis):

**Entry:**
- Entry EBITDA (LTM or NTM)
- Entry multiple (EV / EBITDA)
- Enterprise value
- Net debt at close
- Equity check size
- Transaction fees & expenses

**Financing:**
- Senior debt (x EBITDA, rate, amortization)
- Subordinated debt / mezzanine (if any)
- Total leverage at entry (x EBITDA)
- Equity contribution

**Operating Assumptions:**
- Revenue growth rate (annual)
- EBITDA margin trajectory
- Capex as % of revenue
- Working capital changes
- Debt paydown schedule

**Exit:**
- Hold period (years)
- Exit multiple (EV / EBITDA)
- Exit EBITDA (calculated from growth assumptions)
- Management Incentive Plan (MIP) terms (e.g., % of equity above hurdle)
- Exit transaction fees (e.g., 1-2% of EV)
- Interim cash flows (dividend recaps, add-on equity injections)

### Step 2: Base Case Returns

Calculate:

| Metric | Value |
|--------|-------|
| Entry EV | |
| Entry NWC Adjustments / Cash | |
| Equity invested | |
| Exit EBITDA | |
| Exit EV | |
| Exit Transaction Fees | |
| Net debt at exit (incl. PIK/Sub) | |
| Pre-MIP Exit Equity Value | |
| MIP Payout | |
| Sponsor Exit Equity Value | |
| **Gross MOIC** | |
| **Gross IRR** | |
| Net MOIC / Net IRR | |
| Cash-on-cash | |

Show the returns waterfall (Value Creation Bridge):
- Revenue growth contribution
- EBITDA margin expansion contribution
- Multiple expansion/contraction contribution
- Free Cash Flow generation (debt paydown & cash accumulation)
- Fee/expense drag and MIP dilution

### Step 3: Sensitivity Tables

Build 2-way sensitivity matrices:

**Entry Multiple vs. Exit Multiple**
| | Exit 6x | Exit 7x | Exit 8x | Exit 9x | Exit 10x |
|---|---------|---------|---------|---------|----------|
| Entry 7x | | | | | |
| Entry 8x | | | | | |
| Entry 9x | | | | | |
| Entry 10x | | | | | |

**EBITDA Growth vs. Exit Multiple** (at fixed entry)

**Leverage vs. Exit Multiple** (at fixed entry and growth)

**Hold Period vs. Exit Multiple**

Show both IRR and MOIC in each cell (IRR / MOIC format).

### Step 4: Scenario Analysis

Build 3 scenarios:

| | Bull | Base | Bear |
|---|------|------|------|
| Revenue CAGR | | | |
| Exit EBITDA margin | | | |
| Exit multiple | | | |
| Exit EBITDA | | | |
| MOIC | | | |
| IRR | | | |

### Step 5: Output

- Excel workbook with:
  - Assumptions tab
  - Returns calculation
  - Sensitivity tables (formatted with conditional coloring)
  - Scenario summary
- One-page returns summary suitable for IC deck

## Key Formulas

- **MOIC** = Exit Equity Value / Equity Invested
- **IRR** = solve for r using XIRR for exact timing of cash flows, accommodating interim dividends or equity injections.
- **Value Creation Bridge attribution**:
  - Revenue Growth: (Exit Rev - Entry Rev) × Entry Margin × Entry Multiple
  - Margin Expansion: Exit Rev × (Exit Margin - Entry Margin) × Entry Multiple
  - Multiple Expansion: Exit EBITDA × (Exit Multiple - Entry Multiple)
  - FCF Generation (Leverage/Cash): (Entry Net Debt - Exit Net Debt)
- **MIP Payout**: (Pre-MIP Exit Equity Value - Hurdle) × MIP %

## Important Notes

- Always show returns both gross and net of fees/carry where applicable
- Management rollover and co-invest change the equity check — ask if relevant
- Dividend recaps or interim distributions affect IRR significantly — include if planned (use XIRR)
- Don't forget transaction costs (typically 2-4% of EV) — they reduce Day 1 equity value
- Tax considerations (asset vs. stock deal, 338(h)(10) election) can materially affect after-tax returns

## Quality Rubric

- **MIP Dilution Modelled:** Management Incentive Plan is correctly deducted from exit equity value before calculating sponsor returns.
- **Value Creation Granularity:** EBITDA growth is correctly bifurcated into revenue growth and margin expansion in the returns bridge.
- **Cash Flow Exactness:** IRR utilizes exact dates (e.g., XIRR equivalent) if interim cash flows (dividend recaps, follow-ons) exist.
- **Gross vs Net Distinction:** Clearly distinguishes between Sponsor Gross Returns and Fund Net Returns (accounting for fund-level fees and carry).

## Correct Patterns

### Value Creation Bridge Calculation
When splitting EBITDA growth into Revenue and Margin contributions, ensure the interaction effect is handled cleanly (standard practice allocates it to margin or splits it).
```python
# Standard PE Value Creation Bridge (in EUR m)
entry_ev = entry_ebitda * entry_multiple
exit_ev = exit_ebitda * exit_multiple

# 1. Revenue Growth Contribution
rev_growth_val = (exit_rev - entry_rev) * entry_margin * entry_multiple

# 2. Margin Expansion Contribution
margin_exp_val = exit_rev * (exit_margin - entry_margin) * entry_multiple

# 3. Multiple Expansion Contribution
multiple_exp_val = exit_ebitda * (exit_multiple - entry_multiple)

# 4. FCF Generation / Deleveraging
fcf_val = (entry_net_debt - exit_net_debt) # assuming no leakages
```
