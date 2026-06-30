---
name: lbo-modeling
version: "2.1.0"
description: >
  Constructs a fully deterministic five-step Leveraged Buyout model for DACH mid-market
  acquisitions. Computes Sources & Uses, P&L down to Levered Free Cash Flow, a Senior TL /
  Notes debt waterfall with floating Euribor mechanics, exit MOIC and IRR, and an Entry ×
  Exit multiple sensitivity grid. Compute natively in context window.
  The agent orchestrates and calculates everything directly.
triggers:
  - "run LBO"
  - "leveraged buyout"
  - "LBO model"
  - "debt waterfall"
  - "MOIC"
  - "returns analysis"
  - "entry multiple"
  - "exit multiple"
  - "equity IRR"
inputs:
  required:
    - "entry_ebitda_eur_m — LTM EBITDA at acquisition (€m)"
    - "entry_multiple — EV/EBITDA paid at entry"
    - "equity_pct + senior_debt_pct + notes_pct — capital structure (must sum to 1.0)"
    - "revenue_base_eur_m — LTM revenue at entry (€m)"
    - "revenue_growth_rates — comma-separated decimals, one per projection year"
    - "ebitda_margins — comma-separated decimals, one per projection year"
    - "exit_multiple — EV/EBITDA assumed at exit"
  optional:
    - "euribor — current rate as decimal (default: 0.039)"
    - "euribor_floor — floor as decimal (default: 0.00)"
    - "rcf_facility_eur_m — Revolving Credit Facility size (default: 10.0)"
    - "min_cash_balance_eur_m — minimum operating cash not swept (default: 2.0)"
    - "senior_spread_bps — senior TL spread in basis points (default: 375)"
    - "notes_rate — fixed rate decimal or floating spread (default: 9.5%)"
    - "notes_pik_pct — fraction of notes interest paid in kind (default: 0.0%)"
    - "senior_amort_pct — mandatory annual amortisation as % of original principal (default: 5%)"
    - "senior_cash_sweep_pct — fraction of LFCF swept to senior repayment (default: 50%)"
    - "advisor_fee_pct — M&A success fee as % of EV (default: 1.5%)"
    - "financing_fee_pct — debt arrangement fee as % of total debt (default: 2.0%)"
    - "mip_pool_pct — Management Incentive Plan pool as % of exit equity (default: 10%)"
    - "tax_rate — corporate tax rate as decimal (default: DE 29.9%)"
    - "exit_year — hold period in years (default: 5)"
    - "projection_years — total forecast horizon (default: 5)"
refs:
  debt_structure_defaults: "skills/lbo-modeling/refs/debt-structure-defaults.yaml"
  sensitivity_config: "skills/lbo-modeling/refs/sensitivity-config.yaml"
  financial_constants: "config/financial_constants.yaml"
  auctus_criteria: "config/auctus_criteria.yaml"

outputs:
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_lbo_results.json"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_lbo_compact.json"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_projections.xlsx"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_sensitivity_irr.xlsx"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_model.xlsx"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_ic_report.md"
  - "outputs/dcf_models/lbo_{company}_{YYYYMMDD_HHMMSS}_ic_report.pdf"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG is a DACH-focused mid-market PE firm pursuing buy-and-build
strategies. LBO models use EUR cash flows with Euribor-linked senior debt. All arithmetic
is computed directly by the agent in context.

### Prerequisites

- `/sector-overview` — growth rate assumptions and EV/EBITDA exit multiple cross-check
- `/3-statement-model` — if building the P&L from scratch (no management accounts provided)
- `/relative-valuation` — for exit multiple cross-check against trading comps

### Data Source Hierarchy

1. **FactSet MCP** — primary for market data, sector benchmarks, comparable transactions
2. **User-provided data** — management accounts, IM financials, stated capital structure
3. **Web search / fetch** — fallback only; never for financial figures

### Currency & Units

- All values in **EUR millions (€m)**
- Number format: EUR values 2 decimal places; ratios/multiples 1 decimal (`0.0×`, `0.0%`)
- Negatives: parentheses `(€X.Xm)` — never minus sign

### Execution Environment

Compute the LBO model natively in your context window. Calculate the Sources & Uses, debt paydown waterfall, P&L, MOIC, and IRR based on the AUCTUS criteria. Ensure precise math and generate the tables and documents as specified.

### AUCTUS-Specific Rules

**AUCTUS hard filters** (check before Step 2):
- Revenue €5m–€250m; no financial services/real estate/oil & gas
- Geography: DACH primary; NL/BE/FR/IT/SE/DK/NO secondary

**Euribor mechanics** (AUCTUS defaults, read from refs/debt-structure-defaults.yaml):
- Senior TL: Euribor (floor 0.00%) + 375bps
- Notes/Sub-Debt: 9.5% fixed (PIK interest accrues to principal; cash interest reduces LFCF)
- Senior amortization: 5% p.a. mandatory + 50% cash sweep
- RCF & Cash Sweep: Sweep applies only to cash above `min_cash_balance_eur_m`. RCF drawn if pre-debt cash flow is negative.

**IB/PE Modeling Standards** (Strictly Enforced):
- **Fees**: M&A fees are expensed (reduce day-1 retained earnings). Financing fees are capitalized and amortized straight-line over the debt tenor.
- **Taxes & NOLs**: Track Net Operating Losses (NOLs). If EBT < 0, Taxes = €0 and negative EBT adds to NOL carryforward. If EBT > 0, apply NOLs to offset taxable income before applying the tax rate.
- **MIP**: Management Incentive Plan pool (e.g. 10%) must be deducted from gross exit equity proceeds BEFORE calculating Sponsor MOIC/IRR.

**AUCTUS hurdle rates** (state explicitly in every report):
- MOIC ≥ 2.0× and IRR ≥ 20% are minimum targets
- Below hurdle: note as **BELOW IC HURDLE RATE** but do not discard — present to IC

**Excel workbook color conventions** (applies to lbo_{company}_model.xlsx):
- **Blue** (`#0000FF`): hardcoded inputs
- **Black** (`#000000`): calculation formulas
- **Purple** (`#800080`): links to cells on the **same tab** (no arithmetic)
- **Green** (`#008000`): links to cells on **different tabs**
- Section headers: dark blue `#1F4E79` fill, white bold text
- Column headers: light blue `#D9E1F2` fill, black bold text
- Key outputs (IRR, MOIC, Exit Equity): medium blue `#BDD7EE` fill, black bold

**Sensitivity grids**:
- 5×5 ODD dimensions only — never even dimensions
- Center cell = base case; must match model output exactly
- Highlight center cell: `#BDD7EE` fill, bold font


must exit **0** before declaring workflow complete.

---

## STEP 1 — INVESTMENT CRITERIA VALIDATION & PREREQUISITES

Read `config/auctus_criteria.yaml`. Verify the target satisfies **all** hard filters:

| Filter | Threshold | Source key |
|--------|-----------|------------|
| Revenue (TTM) | €5m – €250m | `hard_filters.revenue_min_eur` / `revenue_max_eur` |
| Geography | DACH preferred; NL/BE/FR/IT/SE/DK/NO allowed | `hard_filters.geographies_allowed` |

| Customer concentration | No single customer >30% | `hard_filters.customer_concentration_max_single` |
| Excluded sectors | financial_services, real_estate, oil_gas | `hard_filters.excluded_sectors` |

If the required data to validate these filters or to run the LBO model does not exist, do NOT halt and ask the user for it. Instead, you MUST proactively gather the data from FactSet MCP or chat context, and explicitly execute the necessary upstream skills to generate the required dependencies. Specifically, run the `/sector-overview` skill to gather growth and margin benchmarks, followed by the `/3-statement-model` skill to derive the historicals, and the `/relative-valuation` skill for exit multiple cross-checks.

If any hard filter fails: **stop**. Report the failing criterion verbatim. Do not proceed to Step 2.

## STEP 2 — CAPITAL STRUCTURE ASSUMPTIONS

Read `skills/lbo-modeling/refs/debt-structure-defaults.yaml`.
Read `config/financial_constants.yaml` for the target sector's `debt_spread_bps` and `target_debt_to_equity`.

Present the proposed capital structure to the user:

```
Entry EV:              €{entry_ebitda} × {entry_multiple}x = €{ev}m
─────────────────────────────────────────────────────────────
Equity:                {equity_pct}% = €{equity}m
Senior Term Loan:      {senior_pct}% = €{senior}m   @ Euribor ({euribor:.2%}) floor {floor:.2%} + {spread}bps
Notes / Sub-Debt:      {notes_pct}% = €{notes}m     @ {notes_rate:.2%} fixed
─────────────────────────────────────────────────────────────
Total Sources:         €{total_sources}m
─────────────────────────────────────────────────────────────
Acquisition Price:     €{ev}m
Advisor Fees (1.5%):   €{advisor_fees}m
Financing Fees (2.0%): €{financing_fees}m
─────────────────────────────────────────────────────────────
Total Uses:            €{total_uses}m
```

Await explicit user confirmation of the capital structure before proceeding to Step 3.

**Hard check:** Equity_pct + Senior_pct + Notes_pct must equal exactly 1.000.
If not, stop and report the imbalance.

## STEP 3 — PROJECTION ASSUMPTIONS

Present the 5-year operating assumptions:

| Year | Revenue (€m) | Growth | EBITDA (€m) | Margin |
|------|-------------|--------|-------------|--------|
| 1    | ...         | x.x%   | ...         | x.x%   |
| ...  | ...         | ...    | ...         | ...    |

Confirm:
- Revenue CAGR is consistent with the sector benchmark in `config/sector_benchmarks.yaml`.
- EBITDA margin trajectory is realistic (check `by_sector.{sector}.ev_ebitda_median` for context).
- D&A, CapEx, and NWC assumptions align with `config/financial_constants.yaml → projection_defaults`.

Await explicit user confirmation before proceeding.

## STEP 4 — LBO ENGINE EXECUTION

Execute the LBO natively in context based on the confirmed parameters.

## STEP 5 — OUTPUT VERIFICATION

Read the compact JSON file: `outputs/dcf_models/lbo_{company}_{timestamp}_lbo_compact.json`.

Verify all of the following before proceeding:



**Debt service coverage:** For every year in `inflection_projections`, verify:
```
interest_coverage_x = ebit_eur_m / total_interest_eur_m
```
Must be ≥ 1.0 in all years. If any year has coverage < 1.0: flag as **COVENANT BREACH RISK** and
escalate to the user immediately. Do not silently continue.

**Leverage at exit:** `exit_metrics.leverage_at_exit_x` must be < `leverage_at_entry_x`.
If not: flag as **DELEVERAGING FAILURE** and escalate.

**MOIC / IRR sanity:**
- `irr_solver_converged` must be `true`. If `false`: report solver failure, stop.
- `moic` and `irr_pct` must be finite real numbers. NaN = stop.
- For AUCTUS to invest: MOIC ≥ 2.0× and IRR ≥ 20% are the minimum target thresholds.
  If either is missed: note as **BELOW IC HURDLE RATE** in the report but do not discard — present
  the deal and let the Investment Committee decide.


## STEP 6 — REPORT COMPOSITION

Compose the Investment Committee 1-pager with these sections (in order):

### 1. Header
Company name | Sector | Geography | Run date | Model version

### 2. Transaction Summary
```
Entry EV:    €{ev}m ({entry_multiple}× LTM EBITDA of €{ebitda}m)
Equity:      €{equity}m ({equity_pct}% of EV)
Total Debt:  €{total_debt}m ({leverage_x:.1f}× Entry EBITDA)
```

### 3. Capital Structure & Debt Terms
Table: Tranche | Amount | Rate | Amortisation | Structure
Include Euribor floor citation and spread above base rate.
For capitalised fees: show annual amortisation charge.

### 4. 5-Year P&L & Debt Waterfall
Full year-by-year table from `{company}_{timestamp}_projections.xlsx`:
Revenue | EBITDA | EBIT | Total Interest | EBT | Net Income | LFCF | Senior Debt | Total Debt

Show leverage (×) and interest coverage (×) for each year.

**Negative formatting convention:** losses and interest expenses shown as `(€Xm)` in parentheses.

### 5. Exit Analysis
```
Exit Year:      {exit_year}
Exit EBITDA:    €{exit_ebitda}m
Exit Multiple:  {exit_multiple}×
Exit EV:        €{exit_ev}m
Net Debt:       (€{net_debt}m)
Gross Equity:   €{gross_equity_proceeds}m
MIP Pool:       (€{mip_deduction}m)
Sponsor Equity: €{equity_proceeds}m
─────────────────────────────
Sponsor MOIC:   {moic:.2f}×
Sponsor IRR:    {irr_pct:.1f}%
```

All figures cited with their source JSON key.

### 6. Entry × Exit Sensitivity Grid
Reproduce the `_sensitivity_irr.xlsx` as a formatted markdown table.
Rows = Entry Multiples (low → high), Columns = Exit Multiples (low → high).
Highlight the base-case cell with **bold**.
Add a MOIC grid immediately below with same dimensions.

### 7. Investment Risks & Covenant Summary
- Minimum interest coverage year (from waterfall): state the year and ratio.
- Leverage at exit vs. entry.
- Sensitivity to Euribor +100bps (qualitative, not computed).
- Key operational assumptions (growth rate, margin trajectory).

Write the report to `outputs/dcf_models/lbo_{company}_{timestamp}_ic_report.md`.

Compile the report to PDF format using `pandoc`:

```bash
pandoc outputs/dcf_models/lbo_{company}_{timestamp}_ic_report.md \
  -o outputs/dcf_models/lbo_{company}_{timestamp}_ic_report.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2.5cm \
  -V fontsize=11pt \
  -V mainfont="Helvetica"
```

## STEP 7 — QA VERIFICATION

The zero-context LLM QA verification is deprecated. All core financial constraints (sources and uses balancing, deleveraging, interest waterfall logic, MOIC/IRR consistency) are verified deterministically via standard unit tests and checks in the engine itself.

## STEP 8 — QUALITY GATE



Verify:
1. All four output files exist and are non-empty.
2. `balance_check_eur_m` in compact JSON is within €0.01m of zero.
3. Sensitivity grid Excel has no NaN cells in the central 3×3 region.
4. `irr_solver_converged == true` in compact JSON.
5. `lbo_{company}_{timestamp}_model.xlsx` exists and is non-empty.
6. **MIP Quality Gate**: Exit Sponsor Equity must strictly equal Gross Equity - MIP Pool.
7. **NOL Quality Gate**: Taxes in year N must be zero if accumulated NOLs >= EBT.
8. **RCF Quality Gate**: RCF balance at exit must be included in Net Debt deduction.

## CORRECT PATTERNS (IB/PE Standards)

### RCF Draw / Repayment Logic (Excel Formula)
```excel
=MAX(0, MIN(RCF_Beginning_Balance, Cash_Flow_Available_For_Debt_Service - Mandatory_Amort - Min_Cash))
' If CF is negative, RCF Draw = MIN(RCF_Max_Capacity - RCF_Beginning_Balance, ABS(CF))
```

### NOL Carryforward Logic
```excel
' NOL_Beginning (positive number representing loss)
NOL_Generated = IF(EBT < 0, -EBT, 0)
NOL_Used = IF(EBT > 0, MIN(EBT, NOL_Beginning), 0)
NOL_Ending = NOL_Beginning + NOL_Generated - NOL_Used
Tax_Expense = IF(EBT > 0, (EBT - NOL_Used) * Tax_Rate, 0)
```

### PIK Interest
```excel
PIK_Interest = Notes_Beginning_Balance * Notes_Rate * Notes_PIK_Pct
Cash_Interest = Notes_Beginning_Balance * Notes_Rate * (1 - Notes_PIK_Pct)
Notes_Ending_Balance = Notes_Beginning_Balance + PIK_Interest
```

Append completion entry to `logs/agent_activity.log`:
```
[ISO8601] [lbo_modeling] [STATUS: SUCCESS] [outputs/dcf_models/lbo_{company}_{timestamp}_*]
```

## EXIT CONDITION

Deliver paths to all output files plus the IC report.

State explicitly:
- Entry EV (€m) and entry multiple (×)
- MOIC (×) and IRR (%)
- Exit EV (€m) and net debt at exit (€m)
- Whether AUCTUS IC hurdle rates (≥2.0× MOIC, ≥20% IRR) were met
- QA gate: PASS or FAIL
- Excel model path (`outputs/dcf_models/lbo_*_model.xlsx`)
- PDF report path (`outputs/dcf_models/lbo_*_ic_report.pdf`) — or note if pandoc was not installed

---

# LBO Model (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## TEMPLATE REQUIREMENT

**This skill uses templates for LBO models. Always check for an attached template file first.**

Before starting any LBO model:
1. **If a template file is attached/provided**: Use that template's structure exactly - copy it and populate with the user's data
2. **If no template is attached**: Ask the user: *"Do you have a specific LBO template you'd like me to use? If not, I can use the standard template which includes Sources & Uses, Operating Model, Debt Schedule, and Returns Analysis."*
3. **If using the standard template**: Copy `examples/LBO_Model.xlsx` as your starting point and populate it with the user's assumptions

**IMPORTANT**: When a file like `LBO_Model.xlsx` is attached, you MUST use it as your template - do not build from scratch. Even if the template seems complex or has more features than needed, copy it and adapt it to the user's requirements. Never decide to "build from scratch" when a template is provided.

---

## CRITICAL INSTRUCTIONS FOR CLAUDE - READ FIRST

### Environment: Office JS vs Python

**If running inside Excel (Office Add-in / Office JS environment):**
- Use Office JS (`Excel.run(async (context) => {...})`) directly — do NOT use Python/openpyxl
- Write formulas via `range.formulas = [["=B5*B6"]]` — Office JS formulas recalculate natively in the live workbook
- The same formulas-over-hardcodes rule applies: set `range.formulas`, never `range.values` for anything that should be a calculation
- Use `range.format.font.color` / `range.format.fill.color` for the blue/black/purple/green convention
- No separate recalc step needed — Excel handles calculation natively
- **Merged cell pitfall:** Do NOT call `.merge()` then set `.values` on the merged range (throws `InvalidArgument` — range still reports original dimensions). Instead: write value to top-left cell alone (`ws.getRange("A7").values = [["SOURCES & USES"]]`), then merge + format the full range (`ws.getRange("A7:F7").merge(); ws.getRange("A7:F7").format.fill.color = "#1F4E79";`)

**If generating a standalone .xlsx file (no live Excel session):**
- Use Python/openpyxl as described below
- Write formula strings (`ws["D20"] = "=B5*B6"`)

The rest of this skill is written with openpyxl examples, but the same principles apply to Office JS — just translate the API calls.

### Core Principles
* **Every calculation must be an Excel formula** - NEVER compute values in Python and hardcode results into cells. When using openpyxl, write `cell.value = "=B5*B6"` (formula string), NOT `cell.value = 1250` (computed result). The model must be dynamic and update when inputs change.
* **Use the template structure** - Follow the organization in `examples/LBO_Model.xlsx` or the user's provided template. Do not invent your own layout.
* **Use proper cell references** - All formulas should reference the appropriate cells. Never type numbers that should come from other cells.
* **Maintain sign convention consistency** - Follow whatever sign convention the template uses (some use negative for outflows, some use positive). Be consistent throughout.
* **Work section by section, verify with user at each step** - Complete one section fully, show the user what was built, run the section's verification checks, and get confirmation BEFORE moving to the next section. Do NOT build the entire model end-to-end and then present it — later sections depend on earlier ones, so catching a mistake in Sources & Uses after the returns are already built means rework everywhere.

### Formula Color Conventions
* **Blue (0000FF)**: Hardcoded inputs - typed numbers that don't reference other cells
* **Black (000000)**: Formulas with calculations - any formula using operators or functions (`=B4*B5`, `=SUM()`, `=-MAX(0,B4)`)
* **Purple (800080)**: Links to cells on the **same tab** - direct references with no calculation (`=B9`, `=B45`)
* **Green (008000)**: Links to cells on **different tabs** - cross-sheet references (`=Assumptions!B5`, `='Operating Model'!C10`)

### Fill Color Palette — Professional Blues & Greys (Default unless user/template specifies otherwise)
* **Keep it minimal** — only use blues and greys for cell fills. Do NOT introduce greens, yellows, reds, or multiple accents. A professional LBO model uses restraint.
* **Default fill palette:**
  * **Section headers** (Sources & Uses, Operating Model, etc.): Dark blue `#1F4E79` with white bold text
  * **Column headers** (Year 1, Year 2, etc.): Light blue `#D9E1F2` with black bold text
  * **Input cells**: Light grey `#F2F2F2` (or just white) — the blue *font* is the signal, fill is secondary
  * **Formula/calculated cells**: White, no fill
  * **Key outputs** (IRR, MOIC, Exit Equity): Medium blue `#BDD7EE` with black bold text
* **That's the whole palette.** 3 blues + 1 grey + white. If the template uses its own colors, follow the template instead.
* Note: The blue/black/purple/green **font** colors above are for distinguishing inputs vs formulas vs links. Those are separate from the **fill** palette here — both work together.

### Number Formatting Standards
* **Currency**: `€#,##0;(€#,##0);"-"` or `€#,##0.0` depending on template
* **Percentages**: `0.0%` (one decimal)
* **Multiples**: `0.0"x"` (one decimal)
* **MOIC/Detailed Ratios**: `0.00"x"` (two decimals for precision)
* **All numeric cells**: Right-aligned

---

### Clarify Requirements First

Before filling any formulas:

* **Examine the template structure** - Identify all sections, understand the timeline (which columns are which periods), note any existing formulas
* **Ask the user if anything is unclear** - If the template structure, calculation methods, or requirements are ambiguous, ask before proceeding
* **Confirm key assumptions** - Any key inputs, calculation preferences, or specific requirements
* **ONLY AFTER understanding the template**, proceed to fill in formulas

---

## TEMPLATE ANALYSIS PHASE - DO THIS FIRST

Before filling any formulas, examine the template thoroughly:

1. **Map the structure** - Identify where each section lives and how they relate to each other. Note which sections feed into others.

2. **Understand the timeline** - Which columns represent which periods? Is there a "Closing" or "Pro Forma" column? Where does the projection period start?

3. **Identify input vs formula cells** - Templates often use color coding, borders, or shading to indicate which cells need inputs vs formulas. Respect these conventions.

4. **Read existing labels carefully** - The row labels tell you exactly what calculation is expected. Don't assume - read what the template is asking for.

5. **Check for existing formulas** - Some templates come partially filled. Don't overwrite working formulas unless specifically asked.

6. **Note template-specific conventions** - Sign conventions, subtotal structures, how sections are organized, whether there are separate tabs for different components, etc.

---

## FILLING FORMULAS - GENERAL APPROACH

For each cell that needs a formula, follow this hierarchy:

### Step 1: Check the Template
* Does the cell already have a formula? If yes, verify it's correct and move on.
* Is there a comment or note indicating the expected calculation?
* Does the row/column label make the calculation obvious?
* Do neighboring cells show a pattern you should follow?

### Step 2: Check the User's Instructions
* Did the user specify a particular calculation method?
* Are there stated assumptions that affect this formula?
* Any special requirements mentioned?

### Step 3: Apply Standard Practice
* If neither template nor user specifies, use standard LBO modeling conventions
* Document any assumptions you make
* If genuinely uncertain, ask the user

---

## COMMON PROBLEM AREAS

The following calculation patterns frequently cause issues across LBO models. Pay special attention when you encounter these:

### Balancing Sections
* When two sections must equal (e.g., Sources = Uses), one item is typically the "plug" (balancing figure)
* Identify which item is the plug and calculate it as the difference

### Tax Calculations
* Tax formulas should only reference the relevant income line and tax rate
* Should NOT reference unrelated sections (e.g., debt schedules)
* Consider whether losses create tax shields or are simply ignored

### Interest and Circular References
* Interest calculations can create circularity if they reference balances affected by cash flows
* Use **Beginning Balance** (not average or ending) to break circular references
* Pattern: Interest → Cash Flow → Paydown → Ending Balance (if interest uses ending balance, this circles back)

### Debt Paydown / Cash Sweeps
* When multiple debt tranches exist, there's usually a priority order
* Cash sweep should respect the priority waterfall
* Balances cannot go negative - use MAX or MIN functions appropriately

### Returns Calculations (IRR/MOIC)
* Cash flows must have correct signs: Investment = negative, Proceeds = positive
* If using XIRR, need corresponding dates
* If using IRR, cash flows should be in consecutive periods
* MOIC = Total Proceeds / Total Investment

### Sensitivity Tables
* **Use ODD dimensions** (5×5 or 7×7) — never 4×4 or 6×6. Odd dimensions guarantee a true center cell.
* **Center cell = base case.** Build the row and column axis values symmetrically around the model's actual assumptions (e.g., if base entry multiple = 10.0x, axis = `[8.0x, 9.0x, 10.0x, 11.0x, 12.0x]`). The center cell's IRR/MOIC MUST then equal the model's actual IRR/MOIC output — this is the proof the table is wired correctly.
* **Highlight the center cell** — medium-blue fill (`#BDD7EE`) + bold font so the base case is visually anchored.
* Excel's DATA TABLE function may not work with openpyxl — instead write explicit formulas that reference row/column headers
* Each cell should show a DIFFERENT value — if all same, formulas aren't varying correctly
* Use mixed references (e.g., `$A5` for row input, `B$4` for column input)

---

## VERIFICATION CHECKLIST - RUN AFTER COMPLETION


### Section Balancing
- [ ] Any sections that must balance (Sources/Uses, Assets/Liabilities) balance exactly
- [ ] Plug items are calculated correctly as the balancing figure
- [ ] Amounts that should match across sections are consistent

### Income/Operating Projections
- [ ] Revenue/top-line builds correctly from drivers or growth rates
- [ ] All cost and expense items calculated appropriately
- [ ] Subtotals and totals sum correctly
- [ ] Margins and ratios are reasonable
- [ ] Links to assumptions are correct

### Balance Sheet (if applicable)
- [ ] Assets = Liabilities + Equity (must balance)
- [ ] All items link to appropriate schedules or roll-forwards
- [ ] Beginning balances = prior period ending balances
- [ ] Check row included and shows zero

### Cash Flow (if applicable)
- [ ] Starts with correct income figure
- [ ] Non-cash items added/subtracted appropriately
- [ ] Working capital changes have correct signs
- [ ] Ending Cash = Beginning Cash + Net Cash Flow
- [ ] Cash balances are consistent across statements

### Supporting Schedules
- [ ] Roll-forward schedules balance (Beginning + Changes = Ending)
- [ ] Schedules link correctly to main statements
- [ ] Calculated items use appropriate drivers
- [ ] All periods are calculated consistently

### Debt/Financing Schedules (if applicable)
- [ ] Beginning balances tie to sources or prior period
- [ ] Interest calculated on appropriate balance (typically beginning)
- [ ] Paydowns respect cash availability and priority
- [ ] Ending balances cannot be negative
- [ ] Totals sum tranches correctly

### Returns/Output Analysis
- [ ] Exit/terminal values calculated correctly
- [ ] All relevant adjustments included
- [ ] Cash flow signs are correct (negative for investment, positive for proceeds)
- [ ] IRR/MOIC formulas reference complete ranges
- [ ] Results are reasonable for the scenario

### Sensitivity Tables (if applicable)
- [ ] Grid dimensions are ODD (5×5 or 7×7) — there is a true center cell
- [ ] Row and column axis values are symmetric around the base case (`[base-2Δ, base-Δ, base, base+Δ, base+2Δ]`)
- [ ] Center cell output equals the model's actual IRR/MOIC — confirms the table is wired correctly
- [ ] Center cell is highlighted (medium-blue fill `#BDD7EE`, bold font)
- [ ] Row and column headers contain appropriate input values
- [ ] Each data cell contains a formula (not hardcoded)
- [ ] Each data cell shows a DIFFERENT value
- [ ] Values move in expected directions (higher exit multiple → higher IRR, etc.)

### Formatting
- [ ] Hardcoded inputs are blue (0000FF)
- [ ] Calculated formulas are black (000000)
- [ ] Same-tab links are purple (800080)
- [ ] Cross-tab links are green (008000)
- [ ] All numbers are right-aligned
- [ ] Appropriate number formats applied throughout
- [ ] No cells show error values (#REF!, #DIV/0!, #VALUE!, #NAME?)

### Logical Sanity Checks
- [ ] Numbers are reasonable order of magnitude
- [ ] Trends make sense (growth, decline, stabilization as expected)
- [ ] No obviously wrong values (negative where should be positive, impossible percentages, etc.)
- [ ] Key outputs are within reasonable ranges for the type of analysis

---

## COMMON ERRORS TO AVOID

| Error | What Goes Wrong | How to Fix |
|-------|-----------------|------------|
| Hardcoding calculated values | Model doesn't update when inputs change | Always use formulas that reference source cells |
| Wrong cell references after copying | Formulas point to wrong cells | Verify all links, use appropriate $ anchoring |
| Circular reference errors | Model can't calculate | Use beginning balances for interest-type calcs, break the circle |
| Sections don't balance | Totals that should match don't | Ensure one item is the plug (calculated as difference) |
| Negative balances where impossible | Paying/using more than available | Use MAX(0, ...) or MIN functions appropriately |
| IRR/return errors | Wrong signs or incomplete ranges | Check cash flow signs and ensure formula covers all periods |
| Sensitivity table shows same value | Formula not varying with inputs | Check cell references - need mixed references ($A5, B$4) |
| Roll-forwards don't tie | Beginning ≠ prior ending | Verify links between periods |
| Inconsistent sign conventions | Additions become subtractions or vice versa | Follow template's convention consistently throughout |

---

## WORKING WITH THE USER — SECTION-BY-SECTION CHECKPOINTS

* **If the template structure is unclear**, ask before proceeding
* **If the user's requirements conflict with the template**, confirm their preference
* **After completing each major section**, STOP and verify with the user before continuing:
  - **After Sources & Uses** → show the balanced table, confirm the plug is correct, get sign-off before building the operating model
  - **After Operating Model / Projections** → show the projected P&L, confirm growth rates and margins look right, get sign-off before the debt schedule
  - **After Debt Schedule** → show beginning/ending balances and interest, confirm the waterfall logic, get sign-off before returns
  - **After Returns (IRR/MOIC)** → show the cash flow series and outputs, confirm signs and ranges, get sign-off before sensitivity tables
  - **After Sensitivity Tables** → show that each cell varies, confirm the base case lands where expected
* **If errors are found during verification**, fix them before moving to the next section
* **Show your work** - explain key formulas or assumptions when helpful
* **Never present a completed model without having checked in at each section** — it's faster to catch a wrong cell reference at the source than to trace it backwards from a broken IRR

---

**This skill produces investment banking-quality LBO models by filling templates with correct formulas, proper formatting, and validated calculations. The skill adapts to any template structure while ensuring financial accuracy and professional presentation standards.**
