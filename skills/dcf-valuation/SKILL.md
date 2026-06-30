---
name: dcf-valuation
version: "3.2.0"
description: >
  Constructs an institutional-quality DCF model for private company equity valuation
  following investment banking / PE standards. Retrieves financial data via FactSet MCP
  (with flagged web fallback), builds a full 3-statement projection with Bear/Base/Bull
  scenarios, computes WACC via full CAPM build, derives terminal value by both Gordon
  Growth Model and exit multiple, performs PE return analysis (MOIC/IRR), and outputs
  an 8-sheet Excel workbook. All arithmetic lives in Excel formula strings — never in
  Python-computed values.
triggers:
  - "run DCF"
  - "value this company"
  - "discounted cash flow"
  - "build a DCF"
  - "intrinsic valuation"
  - "enterprise value"
inputs:
  required:
    - "Target company name and domicile (DE / AT / CH)"
    - "Sector (matched to financial_constants.yaml)"
    - "At least 3 years of: revenue, EBITDA, D&A, CapEx, tax paid — in €m"
  optional:
    - "data/inputs/{company}_financials.csv — columns: year, revenue, ebitda, d_and_a, capex, nwc_change, tax_rate"
    - "Balance sheet items for NWC build: AR, inventory, AP (enables DSO/DIO/DPO method)"
    - "Net debt at analysis date (for equity bridge)"
    - "Entry EV / offer price (for MOIC/IRR analysis)"
    - "data/inputs/{company}_projections.csv — pre-built 5-year projection table"
refs:
  wacc_assumptions: "skills/dcf-valuation/refs/wacc-assumptions.yaml"
  projection_guide: "skills/dcf-valuation/refs/projection-guide.md"
  sensitivity_config: "skills/dcf-valuation/refs/sensitivity-config.yaml"
  financial_constants: "config/financial_constants.yaml"
  auctus_criteria: "config/auctus_criteria.yaml"

outputs:
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_dcf_model.xlsx"
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_dcf_results.json"
  - "outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_report.md"
---

# DCF Valuation Skill

---

## AUCTUS OVERLAY — Read This First. It Overrides Everything Below.

**Firm:** AUCTUS Capital Partners AG — DACH-focused mid-market PE, buy-and-build mandate.
**Mandate:** All DCF work supports private company acquisition valuation, not public equity research.

---

### A. Data Source Hierarchy

1. **FactSet MCP** — primary source for comparable betas, sector multiples, historical financials.
2. **User-provided data** — uploaded financials, IMs, management accounts.
3. **Web search / fetch** — permitted fallback when FactSet returns no data.
   - Tag all web-sourced figures `[WEB]` inline in the Excel cell comment.
   - Tag all management-provided but unverified figures `[MGMT]`.
   - Reserve `[UNSOURCED]` for figures where origin is genuinely unknown.
   - **Never** use web search as primary source when FactSet data exists.
   - **Never** halt the build solely because FactSet is unavailable — fall back, flag, proceed.

### B. Currency & Units

- All monetary values: **EUR millions (€m)** — convert USD inputs at spot rate and note it.
- EUR values: 2 decimal places (`€42.31m`). Ratios: 1 decimal place (`12.3%`). Multiples: 1 decimal (`8.5x`).
- Negatives: parentheses `(€12.3m)` — never a minus sign.

### C. Execution Environment

- **Python/openpyxl only** — no live Excel session, no Office JS.
- **CRITICAL: All arithmetic lives in Excel formula strings.** The Python script writes formula strings to cells — never pre-computed Python values.
  - CORRECT: `ws["D20"] = "=D19*(1+Inputs!$C$12)"`
  - WRONG: `ws["D20"] = python_computed_revenue`
- This rule applies to every UFCF row, every discount factor, every PV, every TV calculation, every sensitivity cell, every return metric. If you find yourself computing something numerically in Python and writing the result — stop and rewrite it as a formula string.
- Output path: `outputs/dcf_models/{company}_{YYYYMMDD_HHMMSS}_dcf_model.xlsx`

### D. DACH Tax & Regulatory Defaults

- Germany: 29.9% | Austria: 25.0% | Switzerland: 19.7% (canton-average)
- If multi-DACH: use 29.0% default from `financial_constants.yaml`
- Terminal growth ceiling: 4.0% (DACH long-run nominal GDP) — hard cap, never exceed.

---

## Workflow

### Step 0 — Input Validation & Data Gathering

1. Check for `data/inputs/{company}_financials.csv`. Required columns: `[year, revenue, ebitda, d_and_a, capex, nwc_change, tax_rate]`. Minimum 3 historical years.
2. If the CSV does not exist:
   - Try FactSet MCP for historical financials.
   - If FactSet unavailable, parse any uploaded IM, PDF, or Excel natively.
   - If sourced from web, tag all figures `[WEB]`.
   - **Do not halt.** Construct the data from whatever is available.
3. Check for balance sheet items (AR, inventory, AP). If present, use DSO/DIO/DPO NWC build. If absent, fall back to % of revenue with `[ESTIMATED]` tag.
4. Gather supplementary data required for normalisation and IFRS 16 treatment:
   - **Add-backs:** non-recurring items from P&L notes or management accounts — restructuring / severance, above-market management fees, stock-based compensation (SBC), one-time legal / advisory costs. Tag each `[MGMT]` or `[FILING]` per the data source hierarchy in Section A above.
   - **IFRS 16:** total lease liabilities from the balance sheet note. Confirm whether reported EBITDA is post-IFRS-16 (lease D&A stripped out of opex) or pre-IFRS-16 / management-adjusted (operating lease expense still in SG&A). Record the determination in the session log and flag it on the Checks sheet.
   - **Segment data:** revenue by segment or geography from the annual report if the target is multi-segment or operates across DACH borders. Required for Historicals segment block; note `[SEGMENT_DATA_UNAVAILABLE]` if absent.
   - **Deferred revenue:** balance and any known PPA write-down estimates if the target is a SaaS or subscription business. Flag `[PPA_HAIRCUT_REQUIRED]` in the session log if the deferred revenue balance exceeds 5 % of LTM revenue.
5. Record all data-quality observations in the session log and on the Checks sheet data sourcing log.

### Step 1 — Historical Analysis

Before projecting anything, build the Historical Ratio Analysis block (see Historicals sheet spec below). Present this to the user as a summary table:

```
Historical Ratio Analysis — {Company}

                        FY{n-2}   FY{n-1}   FY{n}   3Y Avg   Comment
Revenue (€m)               X         X        X
  YoY growth              X%        X%       X%       X%
Gross margin              X%        X%       X%       X%      [trend: expanding / flat / compressing]
Reported EBITDA (€m)       X         X        X
  EBITDA margin           X%        X%       X%       X%
  (+) Restructuring        X         X        X               [from P&L notes; 0 if none]
  (+) Mgmt fees above mkt  X         X        X               [excess; 0 if arm's length]
  (+) SBC                  X         X        X               [equity plans; 0 if none]
  (+) One-time items        X         X        X               [list individually if >€0.5m]
  = Normalised EBITDA      X         X        X
    Norm. EBITDA margin   X%        X%       X%       X%      [BASE FOR ALL PROJECTIONS]
    Normalisation delta   X%        X%       X%               [flag if >10%: HIGH_NORMALISATION]
EBIT margin               X%        X%       X%       X%
D&A % revenue             X%        X%       X%       X%
CapEx % revenue           X%        X%       X%       X%
FCF conversion            X%        X%       X%       X%      (UFCF / Normalised EBITDA)
NWC % revenue             X%        X%       X%       X%      (if balance sheet available)
ROIC                      X%        X%       X%       X%      (if balance sheet available)
Cash effective tax rate   X%        X%       X%       X%      (current tax / EBT — from tax note)
```

**The projection base is always normalised EBITDA, not reported EBITDA.** State explicitly in the assumptions review if add-backs are zero. If they are material (> 5 % of reported EBITDA), present the bridge from reported to normalised as the first block in the Step 2 review before any other assumption.

### Step 2 — Combined Assumptions Review (ONE approval gate)

Read `refs/wacc-assumptions.yaml` and `refs/projection-guide.md`. Derive and present ALL of the following in a single block for user review:

**A — WACC Build**
- Peer beta table: list 4–6 comparable public companies with observed equity beta, D/E ratio, tax rate, unlevered beta (Hamada). Show median unlevered beta.
- **Beta methodology (fixed — apply uniformly):** Source 2-year weekly raw betas (104 observations) from FactSet ([FACTSET]) or web ([WEB]). Apply Blume adjustment: β_adj = 0.67 × β_raw + 0.33. Record both β_raw and β_adj in the peer table. Use β_adj for Hamada unlevering. Market index: STOXX Europe 600 (DAX acceptable if all peers are German). Do not use daily betas or shorter observation periods — the choice shifts the final WACC by 20–30 bps.
- Re-lever to target capital structure (from `financial_constants.yaml → by_sector`).
- CAPM: Ke = Rf + βe × ERP + size_premium. Show each input.
- Cost of debt: credit spread from `wacc-assumptions.yaml → debt_spread_bps`. After-tax Kd.
- WACC = Ke × We + Kd × (1−t) × Wd. Flag any escalation triggers present.

**B — Projection Assumptions**
- Revenue projections: organic growth (Year 1–5), plus buy-and-build M&A contribution if AUCTUS mandate applies. Show derivation from historical CAGR per `projection-guide.md`.
- EBITDA margin: base from 2-year average, expansion rationale, cap flag if >500bps.
- D&A % revenue, CapEx % revenue: from 3-year historical average or sector default.
- NWC build method: DSO/DIO/DPO if balance sheet data exists; else flat % with tag.
- Tax rate: DACH country-specific or default 29.0%.
- Terminal growth rate: proposed vs. ceiling check.

**C — PE Return Assumptions (if entry price known)**
- Entry EV (from offer) and implied entry EV/EBITDA multiple.
- Exit assumptions: hold period (default 5 years), exit EV/EBITDA multiple assumption.
- Proposed exit EBITDA (Year 5 from projections).

**D — IFRS 16 Treatment Decision (mandatory for all DACH targets post-2019)**

State explicitly which treatment applies and write it as a cell note on Inputs!ifrs16_switch:

- **Post-IFRS-16 (default, switch = 1):** reported EBITDA already excludes lease D&A. Consequences: (1) IFRS 16 lease liabilities are included in the net debt definition; (2) CapEx row excludes lease principal repayments (those are financing cash outflows); (3) no adjustment to the UFCF build needed. This is standard for all DACH companies reporting under HGB or IFRS from 2019 onward.
- **Pre-IFRS-16 or management-adjusted EBITDA (switch = 0):** operating lease expense is embedded in SG&A / COGS. In this case: add back operating lease payments to arrive at a clean EBITDA; exclude lease liabilities from net debt; CapEx is gross CapEx per the cash flow statement. Tag all adjustments `[IFRS16_MGMT_ADJ]`.

**Getting this wrong silently inflates UFCF** — post-IFRS-16 EBITDA already strips out the lease charge, so if lease liabilities are also excluded from net debt, you double-count the benefit.

**E — Deferred Revenue / PPA Haircut Flag (SaaS / subscription businesses only)**

If the deferred revenue balance exceeds 5 % of LTM revenue: purchase price accounting (PPA) will write it down to fair value at close. Estimated Year 1 revenue reduction = deferred revenue balance × write-down rate (default 30 % unless deal team provides a PPA estimate). Tag the Year 1 revenue projection `[PPA_HAIRCUT_REQUIRED]`. Do NOT finalise projections until the deal team confirms the PPA estimate — this is the only item that can unilaterally block Step 2 sign-off.

**Present all five blocks (A–E) together. Await one explicit user confirmation before proceeding.**
Write confirmed projections to `data/inputs/{company}_projections_approved.csv`.

### Step 3 — Build the Excel Workbook (8 Sheets)

Write a Python/openpyxl script that produces all 8 sheets in a single workbook. Sheet build order:

1. `Cover` — see spec below
2. `Inputs` — all blue cells
3. `Historicals` — full P&L spread and ratio analysis
4. `Projections` — 3-statement build, Bear/Base/Bull
5. `WACC` — full CAPM build
6. `DCF` — discounting, TV, valuation bridge
7. `Sensitivity` — 3 grids
8. `Checks` — formula audit

**The Python script must write formula strings, never computed values, for every non-input cell.**

**Named ranges (mandatory — register via `wb.defined_names` before `wb.save()`):**

```python
from openpyxl.workbook.defined_name import DefinedName

# Cell addresses are illustrative — update to match your actual row/column layout.
# The names are fixed; other skills (ic-memo, pitch-deck) reference these names, not raw addresses.
named_ranges = {
    "wacc_base":    "WACC!$C$28",
    "entry_ev":     "Inputs!$C$42",
    "year5_ebitda": "DCF!$G$12",
    "dcf_ev":       "DCF!$C$40",
    "dcf_moic":     "DCF!$C$58",
    "dcf_irr":      "DCF!$C$59",
}
for name, ref in named_ranges.items():
    wb.defined_names[name] = DefinedName(name, attr_text=ref)

assert all(n in wb.defined_names for n in named_ranges), "Missing named range — check cell addresses"
```

### Step 4 — PE Returns Calculation

In the DCF sheet (or a Returns section at the bottom of DCF), calculate:
- Entry equity = Entry EV − Entry net debt
- Exit EV = Year-5 EBITDA (projected) × exit EV/EBITDA assumption (from Inputs sheet)
- Exit net debt = projected net debt at exit year (simplified: use DCF-implied net debt or assume target leverage)
- Exit equity = Exit EV − Exit net debt
- MOIC = Exit equity / Entry equity (Excel formula)
- IRR = `=XIRR(cash_flows, dates)` (all as Excel formula)

All figures reference Inputs sheet cells. MOIC and IRR update when the user changes entry price or exit multiple.

### Step 5 — Sensitivity Grids (3 grids on Sensitivity sheet)

Per `refs/sensitivity-config.yaml`:

**Grid 1: WACC × Terminal Growth → Enterprise Value (€m)**
5×5, ODD, base case centered, all cells full DCF recalc formulas, center cell highlighted `#BDD7EE`.

**Grid 2: WACC × Terminal Growth → Implied EV/EBITDA exit multiple**
Same axes as Grid 1. Each cell = Grid1_EV / Year5_EBITDA. Enables instant sanity check vs. comps.

**Grid 3: Entry EV/EBITDA × Exit EV/EBITDA → MOIC**
5×5, axes centered on base case entry and exit multiples. Each cell recalculates MOIC using the full equity bridge. This is the primary returns sensitivity for IC presentation.

All 75 sensitivity cells per grid (225 total) must be fully populated with formula strings via openpyxl loops. No placeholders. No linear approximations.

### Step 6 — Quality Gate & Log

Verify in the Checks sheet:
- UFCF = NOPAT + D&A − CapEx − ΔNWC for each projection year (`TRUE/FALSE` formula)
- Debt schedule tie: closing = opening + drawdowns − amortisation for each year (`TRUE/FALSE`)
- Balance sheet balances: ABS(total assets − total liabilities & equity) < 0.01 for FY1–FY5 (`TRUE/FALSE`)
- S&U balance: equity check + debt drawn = total uses (`TRUE/FALSE`)
- TV/EV < 85% for base case (`TRUE/FALSE`)
- Terminal growth < WACC (`TRUE/FALSE`)
- No scenario produces negative EV (`TRUE/FALSE`)
- MOIC > 0 (`TRUE/FALSE`)

All checks must return TRUE before declaring the model complete. If any check fails, investigate and fix the underlying formula — do not override or comment out checks.

Append to `logs/agent_activity.log`:
```
[ISO8601] [dcf_valuation] [STATUS: SUCCESS|FAIL] [outputs/dcf_models/{company}_{timestamp}_dcf_model.xlsx]
```

---

## 8-Sheet Workbook Specification

### Sheet 1: Cover

```
Row 1:  [Company Name] — DCF Valuation Model
Row 2:  AUCTUS Capital Partners AG | Analyst: [name] | Date: [date]
Row 3:  Sector: [sector] | Domicile: [DE/AT/CH] | FY End: [month]
Row 4:  (blank)
Row 5:  Case Selector: [dropdown / input cell B5] — 1=Bear, 2=Base, 3=Bull
Row 6:  Active Case: =IF(B5=1,"Bear",IF(B5=2,"Base","Bull"))
Row 7:  (blank)
Row 8:  Model Version: 3.2 | Data Sources: [FactSet / Web / Management — list which]
Row 9:  [UNSOURCED] / [WEB] / [MGMT] tags: see Checks sheet for full source log
Row 10: (blank)
Row 11: SCENARIO SUMMARY — Bear / Base / Bull side by side (all cells are cross-sheet formula references — zero hardcodes)
Row 12: [headers] Metric (€m unless noted)    | Bear                               | Base                               | Bull
Row 13: Revenue FY5                           | =Projections!bear_rev_Y5           | =Projections!base_rev_Y5           | =Projections!bull_rev_Y5
Row 14: EBITDA FY5                            | =Projections!bear_ebitda_Y5        | =Projections!base_ebitda_Y5        | =Projections!bull_ebitda_Y5
Row 15: EBITDA margin % FY5                   | =bear_ebitda_Y5/bear_rev_Y5        | =base_ebitda_Y5/base_rev_Y5        | =bull_ebitda_Y5/bull_rev_Y5
Row 16: Enterprise Value                      | =DCF!ev_bear                       | =DCF!ev_base                       | =DCF!ev_bull
Row 17: Equity Value                          | =DCF!eq_bear                       | =DCF!eq_base                       | =DCF!eq_bull
Row 18: MOIC                                  | =DCF!moic_bear                     | =DCF!moic_base                     | =DCF!moic_bull
Row 19: IRR                                   | =DCF!irr_bear                      | =DCF!irr_base                      | =DCF!irr_bull
```

Scenario Summary header row: dark blue `#1F4E79` white text. Bear/Bull columns: light blue `#D9E1F2`. Base column: medium blue `#BDD7EE` bold. All 21 data cells must be cross-sheet formula references — the deal team reads this block first and it must always reflect live model state.

```
FOOTBALL FIELD CHART  (named chart object: "auctus_football_field")
  Position: Cover sheet, anchored at approximately Row 22, below the Scenario Summary block.
  Type: horizontal bar chart (bar, not column) on an EV (€m) axis.
  Bars — one per method, top to bottom:
    DCF Valuation (Bear → Bull):            low = =DCF!ev_bear   high = =DCF!ev_bull
    Trading Comps (Low → High):             low = =relative_valuation named range or [UNSOURCED]
    Precedent Transactions (Low → High):    low = =precedent named range or [UNSOURCED]
    LBO Floor:                              single point = =DCF!entry_ev (or LBO skill output if available)
  All four bar endpoints must be formula references to named ranges or cross-sheet cells — zero hardcodes.
  Chart title: "{Company} — Valuation Football Field (€m EV)"
  X-axis label: "Enterprise Value (€m EV)"
  The deal team approves this chart before any deliverable is produced. If the comps or
  precedents ranges are unavailable (named range does not exist), insert placeholder bars
  with cell note "[FOOTBALL_FIELD_PENDING — populate after relative-valuation skill runs]".
```

Color: dark blue header (`#1F4E79`) white text. Case selector cell in light grey with blue font (input).

### Sheet 2: Inputs

**Purpose:** Every hardcoded assumption in the entire workbook lives here. Every other sheet reads from this sheet via cross-sheet references. No hardcoded values anywhere else.

**Sections (all blue font, light grey fill, with cell comments citing source):**

```
MACRO INPUTS
  Risk-free rate (Rf)          [= German 10Y Bund, source + date]
  Equity risk premium (ERP)    [= Damodaran Europe, source + date]
  Size/illiquidity premium     [= config/financial_constants.yaml]
  EUR spot rate (if USD source)[only if conversion needed]

DACH TAX
  Tax rate — DE / AT / CH / Default  [from financial_constants.yaml]
  Active tax rate              [=CHOOSE(Cover!B5, ...) or hardcoded for single-country]

CAPITAL STRUCTURE (for WACC re-levering)
  Target D/E ratio             [from sector default or user input]
  Pre-tax cost of debt (Kd)    [= Rf + debt_spread_bps / 10000]

TERMINAL VALUE
  Terminal growth rate (g)     [user-confirmed]
  TV method                    [1=GGM, 2=Exit Multiple, 3=Average]
  Exit EV/EBITDA multiple      [for exit multiple TV method]

PROJECTION ASSUMPTIONS (Bear | Base | Bull × 5 years each)
  Revenue growth — organic: FY1…FY5 for each scenario
  Revenue growth — M&A contrib: FY1…FY5 (zero if no buy-and-build)
  EBITDA margin: FY1…FY5 for each scenario
  D&A % of revenue: FY1…FY5
  CapEx % of revenue: FY1…FY5

NWC DRIVERS (preferred — DSO/DIO/DPO method)
  DSO — Days Sales Outstanding  [historical avg or target]
  DIO — Days Inventory Outstanding [0 if no inventory]
  DPO — Days Payable Outstanding

  Fallback (if no balance sheet data):
  NWC % of revenue change       [tagged [ESTIMATED]]

PE RETURN ASSUMPTIONS
  Entry EV (€m)                 [offer price; [MGMT] if from IM]

  NET DEBT DEFINITION (mandatory decomposition — six separate input rows; sum = entry_net_debt)
    Gross financial debt (€m):           [bank loans, bonds, Schuldscheindarlehen; from balance sheet or credit agreement; [MGMT]/[FILING]]
    (+) IFRS 16 lease liabilities (€m):  [from balance sheet note; 0 if IFRS16_switch = 0; [FILING]]
    (+) Pension provisions (€m):         [Pensionsrückstellungen; frequently 1–3× EBITDA for DACH industrials; actuarial report or balance sheet note; [MGMT]/[FILING]]
    (+) Earnout obligations (€m):        [deferred consideration; 0 if not applicable; [MGMT]]
    (+) DTL on acquired intangibles (€m):[deferred tax liabilities from PPA; estimate if unavailable; [ESTIMATED]]
    (−) Cash and equivalents (€m):       [balance sheet cash; exclude restricted cash; [FILING]]
    (−) Short-term liquid investments:   [money market / T-bills; 0 if none; [FILING]]
    = Entry net debt (€m):               =SUM(gross_debt + ifrs16 + pension + earnouts + dtl − cash − liquid)  [formula — named range: entry_net_debt]

  IFRS 16 TREATMENT SWITCH
    IFRS 16 in EBITDA? (1=Yes, 0=No):   [1 = post-IFRS-16 reported EBITDA (default for DACH post-2019); 0 = pre-IFRS-16 or management-adjusted]
    Cell note: "1 → lease liabilities included in net debt; CapEx excludes lease repayments. 0 → operating lease in SG&A; lease liabilities = 0 in net debt; tag adjustments [IFRS16_MGMT_ADJ]."

  STUB PERIOD (if analysis date ≠ fiscal year-start; leave at defaults if analysis starts on FY1 opening)
    Analysis date:               [date of DCF analysis / expected close date — input]
    Fiscal year-end month:       [e.g., 12 = December; 6 = June — input]
    Stub months (FY1):           =MAX(1, 12 − MONTH(analysis_date) + fiscal_ye_month)  [formula; 12 if full year]
    Stub fraction (FY1):         =stub_months / 12  [formula; 1.0 if at FY start; feeds DCF discount periods]

  MAINTENANCE VS. GROWTH CAPEX
    Total CapEx % revenue:       [from historical 3Y avg or sector default — same as existing CapEx % assumption]
    Maintenance CapEx % revenue: [portion sustaining current capacity; default = D&A % revenue as proxy]
    Growth CapEx % revenue:      =total_capex_pct − maintenance_capex_pct  [formula — reference only; terminal FCF uses maintenance only]

  Hold period (years)           [default 5]
  Exit EV/EBITDA multiple       [base case; range for Grid 3 and Grid 4]
  Exit net debt:                [DO NOT enter manually — flows from Debt Schedule closing balance Year 5]

SOURCES & USES (at close — equity check drives MOIC entry equity; no hardcodes outside this block)
  Purchase price (€m):          [= Entry EV − cash acquired; or offer price from IM; [MGMT] tag]
  Transaction fees (€m):        [default 2.0% × Entry EV; adjust per credit agreement; from financial_constants.yaml]
  NWC adjustment (€m):          [positive = excess NWC acquired; negative = shortfall; 0 if not applicable]
  Total uses (€m):              =Purchase_price + Transaction_fees + NWC_adj  [formula — not an input]
  Debt drawn at close (€m):     [senior facility drawn on day 1; from credit agreement or [MGMT]]
  Equity check (€m):            =Total_uses − Debt_drawn  [formula — THIS is the entry equity for MOIC and IRR]

DEBT SCHEDULE INPUTS
  Opening debt balance (€m):    =Inputs!entry_net_debt  [formula — ties to debt drawn at close via S&U]
  Annual amortisation %:        [% of opening balance amortised per year; e.g., 10% = straight-line 10Y]
  Fixed amortisation (€m/yr):   [alternative — use whichever the credit agreement specifies; 0 if using % method]
  RCF headroom (€m):            [revolving credit facility limit; 0 if none]
  Drawdowns FY1 (€m):           [new debt drawn in FY1; 0 unless refinancing or add-on acquisition planned]
  Drawdowns FY2 (€m):           [same — one input cell per year; 0 for base case]
  Drawdowns FY3 (€m):           [0]
  Drawdowns FY4 (€m):           [0]
  Drawdowns FY5 (€m):           [0]
```

All cells have source comments. Blue font, light grey fill. This is the ONLY sheet with blue cells.

### Sheet 3: Historicals

**Purpose:** Full spread of historical financials. Every cell is a formula referencing raw input data or computing ratios — no hardcodes except raw reported figures (which have source comments).

**Columns:** FY(n-4) … FY(n) | LTM — as many years as data allows, minimum 3. The LTM column immediately follows the last historical FY column.

**LTM Column Rules:**
- If quarterly data is provided: flow items (Revenue, EBITDA, D&A, CapEx, UFCF) = Q(n) + Q(n−1) + Q(n−2) + Q(n−3). Balance sheet items (AR, Inventory, AP, Net PP&E) = last available quarter-end balance.
- If only annual data is available: insert an LTM column labelled "LTM*" with a cell note `"LTM not computed — quarterly data unavailable. Populate manually or leave as FY(n) proxy."` Copy FY(n) formulas as a proxy and tag those cells `[LTM_PROXY]`.
- The Projections sheet "last actual" column must reference LTM if quarterly data was used (LTM populated with real Q sums), otherwise reference the last FY column. This ensures projections anchor to the most recent trailing period.

```
INCOME STATEMENT (€m)
  Revenue
    YoY growth %
  COGS
  Gross Profit
    Gross margin %
  EBITDA (reported)
    EBITDA margin % (reported)
  D&A
  EBIT
    EBIT margin %
  Interest expense
  EBT
  Tax
    Effective tax rate % (reported — total tax / EBT)
  Net income
    Net margin %

NORMALISED EBITDA ADD-BACKS (€m — immediately below reported EBITDA; raw add-back inputs are blue with source comments)
  Reported EBITDA:               =cross-ref to Income Statement EBITDA row above  [formula — black font, green if cross-sheet]
  (+) Restructuring & severance: [raw input; blue font; cite P&L note or IM; [FILING]/[MGMT]; 0 if none]
  (+) Mgmt fees above market:    [excess advisory/management fees over arm's-length rate; blue; [MGMT]; 0 if arm's-length]
  (+) Stock-based compensation:  [equity plan expense; blue; cite remuneration note; [FILING]/[MGMT]; 0 if none — see SBC treatment note in Sheet 4]
  (+) One-time legal/advisory:   [M&A costs, litigation settlements, non-recurring; blue; list individually if >€0.5m; 0 if none]
  (+) Other non-recurring:       [any remaining material one-offs; blue; describe in cell comment; 0 if none]
  = Normalised EBITDA:           =Reported_EBITDA + SUM(above_addbacks)  [formula — black font]
    Normalisation delta %:       =(Normalised − Reported) / ABS(Reported)  [formula; flag [HIGH_NORMALISATION] if >10%]
    Normalised EBITDA margin %:  =Normalised_EBITDA / Revenue  [formula — THIS is the base for all projections]

CASH FLOW ITEMS (€m)
  D&A (add-back)
  CapEx
    CapEx % of revenue
  Change in NWC
    NWC % of revenue
  SBC (stock-based compensation): [from operating CF statement non-cash add-back; blue input; [FILING]; shown here for transparency only — NOT added back in UFCF build; see Sheet 4 SBC note]
  Unlevered FCF (derived)
    FCF conversion (UFCF / Normalised EBITDA)

NWC BALANCE SHEET (if data available)
  Accounts receivable
    DSO = AR / Revenue × 365
  Inventory
    DIO = Inventory / COGS × 365
  Accounts payable
    DPO = AP / COGS × 365
  Net working capital = AR + Inventory − AP

FIXED ASSETS (if data available)
  Gross PP&E
  Accumulated depreciation
  Net PP&E

LTM COLUMN (immediately after last FY — see LTM Column Rules above)
  LTM Revenue:                  =Q(n)+Q(n−1)+Q(n−2)+Q(n−3)  [or FY(n) value with [LTM_PROXY] tag]
  LTM EBITDA:                   =same quarterly sum or proxy
  LTM D&A:                      =same
  LTM CapEx:                    =same
  LTM UFCF:                     =same
  LTM AR / Inventory / AP:      =last quarter-end balance (or FY(n) balance with [LTM_PROXY])
  LTM NWC:                      =LTM AR + LTM Inventory − LTM AP
  LTM DSO / DIO / DPO:          =computed from LTM figures using standard formulae
  LTM EBITDA margin %:          =LTM EBITDA / LTM Revenue

CASH TAX ANALYSIS (from the tax note in the annual report or financial statements)
  Statutory tax rate:            =Inputs!tax_rate  [formula — DACH country rate]
  Current (cash) tax expense:    [raw input; blue font; from tax note "current" line; [FILING]]
  Deferred tax expense/(benefit):[raw input; blue font; from tax note "deferred" line; [FILING]; 0 if not disclosed]
  Total reported tax:            =current_tax + deferred_tax  [formula; cross-check vs. IS tax row above]
  Effective cash tax rate:       =current_tax / EBT  [formula]
    Cash vs. statutory delta:    =effective_cash_rate − Inputs!tax_rate  [flag if absolute delta >200 bps]
  NOL carry-forward balance:     [raw input; blue; cite filing; [FILING]; 0 if none; note expected utilisation period]
  [If effective cash rate deviates >200 bps from statutory for 2+ years: use effective cash rate in UFCF projections and tag [CASH_TAX_RATE]]

SEGMENT / GEOGRAPHY REVENUE SPLIT (optional — populate if annual report provides segment data)
  [One row per segment / geography. Columns match historical FY columns.]
  Segment A (describe):          [raw input; blue; [FILING]]
  Segment B (describe):          [raw input; blue; [FILING]]
  Group / elimination:           [raw input; blue; 0 if not applicable]
  Total (cross-check):           =SUM(segments)  [must equal Revenue row above]
  [If segment data unavailable: leave blank; add cell note "[SEGMENT_DATA_UNAVAILABLE — total revenue only"]
  [If segments have materially different growth profiles (>500 bps spread): project each separately on Sheet 4 and roll up]

RATIO SUMMARY (feeds Step 1 historical analysis table)
  Revenue CAGR (1Y, 3Y, all-period)
  Avg normalised EBITDA margin (2Y, all-period)
  Avg CapEx % (3Y)
  Avg D&A % (3Y)
  Avg NWC % (3Y)
  ROIC (if balance sheet available)
  Avg cash effective tax rate (3Y)
```

Section headers: dark blue `#1F4E79`. Sub-headers: light blue `#D9E1F2`. Raw historical inputs: blue font. Ratio formulas: black font.

### Sheet 4: Projections

**Purpose:** Full 3-statement projection for each of 5 forecast years, all three scenarios. Projection formulas reference Inputs sheet for all assumptions. No hardcoded growth rates or margins in this sheet.

**EBITDA base rule:** The EBITDA margin assumption in Year 1 (from Inputs sheet) is applied to the normalised EBITDA margin from the Historicals add-backs block — NOT the reported EBITDA margin. The "last actual" EBITDA column on this sheet must reference the Historicals normalised EBITDA row, not the reported EBITDA row. Projections anchored to reported EBITDA silently embed non-recurring costs into the forward run-rate.

**Columns:** LTM (or FY(n) if no quarterly data) [last actual] | FY(n+1)E … FY(n+5)E

The "last actual" column references the Historicals LTM column when quarterly data was used and the LTM column is populated with real Q sums. Otherwise it references the last annual FY column. This ensures projection anchors to the most recent trailing period, not an up-to-11-month-stale annual figure.

**Structure:**

```
REVENUE BUILD (€m)
  Revenue — organic:          =Prior × (1 + Inputs!organic_growth[year][scenario])
  Revenue — M&A contribution: =Prior × Inputs!ma_growth[year][scenario]
    [zero-filled if buy-and-build = No on Inputs sheet]
  Total revenue:              =organic + M&A

INCOME STATEMENT
  EBITDA:                     =Revenue × Inputs!ebitda_margin[year][scenario]
    EBITDA margin %
  D&A:                        =Revenue × Inputs!da_pct[year]
  EBIT:                       =EBITDA − D&A
    EBIT margin %
  Taxes:                      =EBIT × Inputs!tax_rate
  NOPAT:                      =EBIT − Taxes

CAPEX & DEPRECIATION SCHEDULE
  Opening net PP&E:           =Prior closing net PP&E
  Total CapEx:                =Revenue × Inputs!total_capex_pct[year]
  Maintenance CapEx:          =Revenue × Inputs!maintenance_capex_pct  [sustains current capacity]
  Growth CapEx:               =Total_CapEx − Maintenance_CapEx  [expansion / new capacity; shown for reference]
  Depreciation (new assets):  =Total_CapEx / Inputs!asset_life_years
    [asset_life_years on Inputs sheet, default 10]
  Total D&A:                  =Historical D&A (Year 0 base, declining) + Depreciation (new assets)
    [This replaces flat D&A % — the schedule feeds the IS D&A row above]
  Closing net PP&E:           =Opening + Total_CapEx − Total D&A
  [Note: UFCF uses Total CapEx during the projection period. Terminal FCF in DCF Section 3 uses Maintenance CapEx only — growth CapEx is not required to sustain earnings at steady-state.]

NWC SCHEDULE (DSO/DIO/DPO method — preferred)
  AR:                         =Revenue × Inputs!DSO / 365
  Inventory:                  =COGS × Inputs!DIO / 365
  AP:                         =COGS × Inputs!DPO / 365
  NWC:                        =AR + Inventory − AP
  ΔNWC:                       =NWC(t) − NWC(t−1)   [positive = cash outflow]

  Fallback (no balance sheet):
  NWC:                        =Revenue × Inputs!nwc_pct_revenue [ESTIMATED]
  ΔNWC:                       =NWC(t) − NWC(t−1)

FREE CASH FLOW
  NOPAT
  (+) D&A
  (−) Total CapEx             [full CapEx during projection years; terminal FCF uses maintenance only — see DCF sheet]
  (−) ΔNWC
  = Unlevered FCF

  **SBC treatment:** SBC must NOT be added back to UFCF. It appears as a non-cash item in the operating section of the cash flow statement, but it is a real economic cost (dilutes sponsor ownership at exit). The Historicals add-backs schedule normalises EBITDA for SBC (to establish what recurring EBITDA "should" be); in the UFCF build, SBC remains embedded in the cost structure. Do not deduct it separately either — it is already absent from NOPAT because EBIT reflects the SBC charge. The only risk is an analyst accidentally adding it back to the D&A row; do not do this.

DEBT SCHEDULE (€m — rolls forward from entry debt; exit net debt flows from here, never from a static input)
  Opening debt balance:         =Inputs!entry_net_debt (FY1) | =Prior year closing balance (FY2–FY5)
  (+) Drawdowns:                =Inputs!drawdowns_FYn  [zero for base case; non-zero if add-on or refinancing]
  (−) Scheduled amortisation:  =MAX(Opening × Inputs!amort_pct, Inputs!amort_fixed)
                                  [take the larger of % method and fixed €m method; if only one is set the other is 0]
  = Closing debt balance:       =Opening + Drawdowns − Amortisation  [Year 5 closing → DCF exit net debt]
  Cash interest expense:        =Opening × Inputs!kd_pretax  [feeds interest line if levered cash flows required]

BALANCE SHEET (€m — cash is the residual plug; retained earnings roll forward; BS balance check on Checks sheet)
  ASSETS
    Cash (plug):                =Prior cash + UFCF − Cash interest − Amortisation
                                  [FY1 opening cash = Inputs!opening_cash_cell or 0]
    Accounts receivable:        =AR from NWC schedule above
    Inventory:                  =Inventory from NWC schedule (0 if DIO = 0)
    Net PP&E:                   =Closing net PP&E from CapEx/Depreciation schedule above
    Total assets:               =Cash + AR + Inventory + Net_PPE

  LIABILITIES & EQUITY
    Accounts payable:           =AP from NWC schedule above
    Total debt:                 =Closing debt balance from Debt Schedule above
    Retained earnings:          =Prior retained earnings + Net income
                                  [Net income = EBIT − Cash interest − Tax on EBT]
                                  [FY1 opening retained earnings = 0; acquisition resets the equity stack]
    Contributed equity:         =Inputs!su_equity_check  [sponsor equity at entry — constant for all years]
    Total equity:               =Contributed equity + Retained earnings
    Total liabilities & equity: =AP + Total debt + Total equity

  BS balance check (inline):    =ABS(Total_assets − Total_liabilities_and_equity) < 0.01
    [Must be TRUE for each year — mirrored on Checks sheet; a failing check means a flow is broken or a row is missing]

SCENARIO STRUCTURE:
  Three full blocks (Bear | Base | Bull), each with the complete IS + FCF above.
  The Cover!B5 case selector drives which block's formulas feed the DCF sheet.
  Consolidation column (column immediately right of Bull block) uses:
    =INDEX(bear_value:bull_value, 1, Cover!$B$5)
  DCF sheet references only the consolidation column — not the scenario blocks directly.
```

**Note on D&A schedule:** The CapEx/Depreciation schedule replaces the flat D&A % approach. It is a 6-row addition per projection year. New CapEx is depreciated at `1 / asset_life_years` per year. The resulting D&A is more accurate for capital-intensive businesses and correctly models the lagged tax shield from heavy early CapEx.

### Sheet 5: WACC

**Purpose:** Full CAPM cost of capital build traceable from first principles. No yaml lookups embedded as hardcodes — all inputs from Inputs sheet or sourced with comments.

```
PEER BETA TABLE
  Company | Market Cap | Net Debt | EV | β_raw | β_adj (Blume) | D/E | Tax | Unlevered Beta (β_adj)
  [4–6 comparable public companies — source FactSet [FACTSET] or web [WEB]]
  Median unlevered beta: =MEDIAN(unlevered_beta_range)

BETA METHODOLOGY (fixed — must be applied uniformly across all peers)
  Data source:            FactSet or Bloomberg; tag [FACTSET] or [WEB]
  Observation period:     2-year weekly returns (104 observations)
  Raw beta (β_raw):       OLS regression of weekly stock return on market-index return; raw input — blue font
  Blume adjustment:       β_adj = 0.67 × β_raw + 0.33   [formula in β_adj column for each peer]
    Rationale: mean-reverts raw betas toward 1.0; standard IB practice; omitting it shifts final WACC 20–30 bps
  Beta used for Hamada:   β_adj (not β_raw) — record both columns so reviewers can see the adjustment
  Market index:           STOXX Europe 600 (preferred for DACH targets); DAX 40 acceptable if all peers are German-listed
  Do not mix observation periods or market indices across peers in the same table — flag any deviation [METHODOLOGY_EXCEPTION].

CAPM — COST OF EQUITY
  Rf (risk-free rate):         =Inputs!rf_rate  [German 10Y Bund, cite date]
  Median unlevered beta (βu):  =Peer table median
  Target D/E:                  =Inputs!target_de_ratio
  Tax rate:                    =Inputs!tax_rate
  Re-levered beta (βe):        =βu × (1 + (1−tax) × D/E)   [Hamada equation]
  ERP:                         =Inputs!erp   [Damodaran Europe]
  Size premium:                =Inputs!size_premium
  Cost of equity (Ke):         =Rf + βe × ERP + size_premium

COST OF DEBT
  Debt spread (bps):           =from wacc-assumptions.yaml sector entry
  Pre-tax Kd:                  =Rf + debt_spread / 10000
  Tax rate:                    =Inputs!tax_rate
  After-tax Kd:                =Pre-tax Kd × (1 − tax_rate)

CAPITAL STRUCTURE
  Equity weight (We):          =1 / (1 + Inputs!target_de_ratio)
  Debt weight (Wd):            =Inputs!target_de_ratio / (1 + Inputs!target_de_ratio)

WACC
  WACC:                        =Ke × We + after_tax_Kd × Wd
  [Output cell: named range "wacc_base" for cross-sheet reference]

WACC ESCALATION CHECK
  [List each trigger from wacc-assumptions.yaml. Flag TRUE/FALSE for each.]
  Escalation applicable?       =IF(any_trigger_true, "Use WACC_HIGH", "WACC_MID OK")

ROIC — TERMINAL VALUE CREDIBILITY (computed here; referenced by DCF sheet and Checks sheet)
  Terminal NOPAT (Year 5):     =Projections!nopat_Y5  [formula cross-reference]
  Terminal invested capital:   =Projections!net_ppe_Y5 + Projections!nwc_Y5  [formula]
  ROIC (terminal):             =terminal_nopat / terminal_invested_capital  [formula — named range: roic_terminal]
  Implied reinvestment rate:   =Inputs!tgr / roic_terminal  [formula — if >50%, flag as implausible]
  ROIC > WACC:                 =roic_terminal > wacc_base  [TRUE = value-creating steady-state; FALSE = GGM TV suspect]
```

### Sheet 6: DCF

**Purpose:** Discounting engine, terminal value, enterprise-to-equity bridge, PE returns. All cells are formulas referencing WACC sheet, Projections sheet consolidation column, and Inputs sheet.

```
SECTION 1: PROJECTION SUMMARY (pulled from Projections consolidation column)
  FY1E … FY5E
  Revenue (€m)
  EBITDA (€m)
  EBIT (€m)
  UFCF (€m)

SECTION 2: DISCOUNTING
  Stub fraction (FY1):            =Inputs!stub_fraction  [months remaining in FY1 / 12; = 1.0 if at fiscal year-start]
  Discount period (mid-year, stub-aware):
    FY1: =Inputs!stub_fraction / 2
    FY2: =Inputs!stub_fraction + 0.5
    FY3: =Inputs!stub_fraction + 1.5
    FY4: =Inputs!stub_fraction + 2.5
    FY5: =Inputs!stub_fraction + 3.5
    [When stub_fraction = 1.0 these collapse to the standard 0.5 | 1.5 | 2.5 | 3.5 | 4.5 convention]
    [When stub_fraction = 0.25 (3-month stub) FY1 period = 0.125; FY2 = 0.75; etc.]
  WACC:                           =WACC!wacc_base
  Discount factor:                =1 / (1 + WACC)^period     [formula, not value]
  PV of UFCF:                     =UFCF × discount_factor     [formula, not value]
  Sum of PV FCFs:                 =SUM(pv_fcf_range)

SECTION 3: TERMINAL VALUE (both methods — cross-check)
  Method A — Gordon Growth Model (maintenance CapEx only)
    Terminal CapEx adj:           =Year5_revenue × (Inputs!maintenance_capex_pct − Inputs!total_capex_pct)
                                    [positive adjustment adds back growth CapEx — not required at steady-state]
    Terminal UFCF (adj):          =UFCF_Year5 + Terminal_CapEx_adj  [formula; UFCF using maintenance CapEx only]
    Terminal FCF:                 =Terminal_UFCF_adj × (1 + Inputs!tgr)
    TV (GGM):                     =Terminal_FCF / (WACC − Inputs!tgr)
    PV of TV (GGM):               =TV_GGM / (1 + WACC)^(Inputs!stub_fraction + 3.5)
    [Discount exponent uses stub-aware Year 5 mid-point — same formula as Section 2 FY5 period]

  Method B — Exit Multiple
    Exit EBITDA:                  =EBITDA_Year5 (from Projections consolidation)
    Exit EV/EBITDA:               =Inputs!exit_ev_ebitda_multiple
    TV (Exit):                    =Exit_EBITDA × Exit_Multiple
    PV of TV (Exit):              =TV_Exit / (1 + WACC)^4.5

  Selected TV:                    =IF(Inputs!tv_method=1, PV_TV_GGM,
                                       IF(Inputs!tv_method=2, PV_TV_Exit,
                                          (PV_TV_GGM + PV_TV_Exit) / 2))
  TV % of EV:                     =Selected_TV / (Sum_PV_FCFs + Selected_TV)
  Cross-check — GGM implied multiple:  =PV_TV_GGM / EBITDA_Year5   [should be near comps]

SECTION 4: VALUATION BRIDGE (full PE equity bridge — each line is a separate row with a source comment)
  Sum of PV FCFs (€m)
  (+) PV of Terminal Value (€m)
  = Enterprise Value (€m)                      [named range: dcf_ev]
  (−) Gross financial debt (€m):               =Inputs!gross_financial_debt_cell
  (−) IFRS 16 lease liabilities (€m):          =Inputs!ifrs16_lease_liabilities_cell   [0 if switch=0]
  (−) Pension provisions (€m):                 =Inputs!pension_provisions_cell          [Pensionsrückstellungen — can be 1–3× EBITDA for DACH industrials]
  (−) Minority interest at market (€m):        =Inputs!minority_interest_cell           [0 if 100% acquisition]
  (−) Earnout obligations (€m):                =Inputs!earnouts_cell
  (+) Associates / equity investments (€m):    =Inputs!associates_at_equity_cell        [0 if none]
  (+) Cash and equivalents (€m):              =Inputs!cash_and_equivalents_cell
  (+) Short-term liquid investments (€m):      =Inputs!liquid_investments_cell
  = Equity Value to Acquirer (€m)              [formula: EV − gross_debt − ifrs16 − pension − minority − earnouts + associates + cash + liquid]
  [Tie check: gross_debt + ifrs16 + pension + earnouts − cash − liquid = Inputs!entry_net_debt ± 0.01]
  Entry EV check:                              =Inputs!entry_ev  [entry EV vs. implied DCF EV]
  Premium / (Discount) to DCF:                =(Inputs!entry_ev − EV) / EV

SECTION 5: PE RETURNS — Base Case (active scenario driven by Cover!B5)
  Entry equity:                    =Inputs!su_equity_check  [Sources & Uses equity check — NOT entry_ev minus entry_net_debt]
  Exit EBITDA (Year 5):            =EBITDA_Year5 from Projections consolidation column  [named range: year5_ebitda]
  Exit EV:                         =Exit_EBITDA × Inputs!exit_ev_ebitda_base
  Exit net debt:                   =Projections!debt_closing_Y5  [Debt Schedule Year 5 closing balance — NOT a static Inputs entry]
  Exit equity:                     =Exit_EV − Exit_net_debt
  MOIC:                            =Exit_equity / Entry_equity  [named range: dcf_moic]
  IRR:                             =XIRR({−Entry_equity, 0, 0, 0, 0, Exit_equity},
                                          {close_date, Y1, Y2, Y3, Y4, exit_date})  [named range: dcf_irr]
    [All as Excel formula strings referencing Inputs dates and Projections values]

SECTION 6: SCENARIO RETURNS SUMMARY (three parallel rows — always visible; feeds Cover Scenario Summary block)
  [Each row independently references its scenario's projection block, not the consolidation column.]
  [Bear and Bull EVs use Bear/Bull UFCF series with same WACC and TGR as Base — only cash flows differ.]

  Row headers       | Bear                                    | Base                                    | Bull
  Revenue FY5:        =Projections!bear_rev_Y5                | =Projections!base_rev_Y5                | =Projections!bull_rev_Y5
  EBITDA FY5:         =Projections!bear_ebitda_Y5             | =Projections!base_ebitda_Y5             | =Projections!bull_ebitda_Y5
  Exit EV:            =bear_ebitda_Y5×Inputs!exit_mult        | =base_ebitda_Y5×Inputs!exit_mult        | =bull_ebitda_Y5×Inputs!exit_mult
  Exit equity:        =Exit_EV_bear − Projections!debt_Y5     | =Exit_EV_base − Projections!debt_Y5     | =Exit_EV_bull − Projections!debt_Y5
  DCF EV:             [full DCF recalc using Bear UFCF series] | =DCF!enterprise_value (active case)     | [full DCF recalc using Bull UFCF series]
  MOIC:               =eq_bear / Inputs!su_equity_check        | =DCF!moic_base                          | =eq_bull / Inputs!su_equity_check
  IRR:                =XIRR bear cash flow array               | =DCF!irr_base                           | =XIRR bull cash flow array

  Named output cells referenced by Cover Scenario Summary:
    ev_bear, ev_base, ev_bull, eq_bear, eq_base, eq_bull,
    moic_bear, moic_base, moic_bull, irr_bear, irr_base, irr_bull
```

Output rows (EV, equity value, MOIC, IRR): medium blue fill `#BDD7EE`, bold.

### Sheet 7: Sensitivity

**Purpose:** Three 5×5 grids, fully populated with formula strings via openpyxl loops. 225 total formulas. No approximations, no placeholders, no Excel Data Table feature.

**Grid 1 — WACC × Terminal Growth → Enterprise Value (€m)**
- WACC axis: base ± 200bps in 100bps steps (5 points)
- TGR axis: base ± 100bps in 50bps steps (5 points)
- Each cell: full DCF recalculation using that WACC and TGR, returning EV
- Center cell = base case EV, highlighted `#BDD7EE`, bold

**Grid 2 — WACC × Terminal Growth → Implied EV/EBITDA exit multiple**
- Same axes as Grid 1
- Each cell: =Grid1_EV_cell / EBITDA_Year5
- Enables instant comparison to trading comps and precedents
- Center cell highlighted `#BDD7EE`, bold

**Grid 3 — Entry EV/EBITDA × Exit EV/EBITDA → MOIC**
- Entry multiple axis: base ± 2.0x in 1.0x steps (5 points)
- Exit multiple axis: base ± 2.0x in 1.0x steps (5 points)
- Each cell: full MOIC recalculation using that entry and exit multiple
  - Entry EV = entry_multiple × LTM_EBITDA
  - Entry equity = Entry EV − entry_net_debt
  - Exit EV = exit_multiple × Year5_EBITDA
  - Exit equity = Exit EV − exit_net_debt
  - MOIC = Exit_equity / Entry_equity
- Center cell = base case MOIC, highlighted `#BDD7EE`, bold
- Conditional formatting: green scale (higher MOIC), red scale (lower)

**Grid 4 — Entry Leverage (Net Debt / EBITDA) × Exit EV/EBITDA → IRR**
- Entry leverage axis: base ± 2.0x Net Debt / EBITDA in 1.0x steps (5 points), e.g., [2x, 3x, 4x, 5x, 6x] for a base of 4x. Each step changes entry debt (= leverage × LTM_EBITDA), holding entry EV fixed.
- Exit multiple axis: base ± 2.0x in 1.0x steps — same as Grid 3 exit multiple axis.
- Each cell: full IRR recalculation
  - Entry EV: fixed = Inputs!entry_ev (does not change across leverage axis)
  - Entry debt: = leverage × Historicals!ltm_ebitda_norm (normalised LTM EBITDA)
  - Entry equity: = Entry_EV − Entry_debt
  - Exit EV: = exit_multiple × Projections!year5_ebitda_norm
  - Exit debt: = Projections!debt_closing_Y5 adjusted for the different opening debt (Debt Schedule is re-parameterised by leverage; for each cell, exit debt ≈ entry_debt × (1 − cumulative_amort_pct)^5)
  - IRR: =XIRR({−entry_equity, exit_equity}, {Inputs!close_date, Inputs!exit_date})  [formula string]
- Center cell = base case IRR, highlighted `#BDD7EE`, bold
- Conditional formatting: green ≥ 20 % IRR (AUCTUS target); amber 15–19.9 %; red < 15 %
- Purpose for IC: separates financial engineering (leverage effect) from value creation (exit multiple effect). IC can reject leverage assumptions without rejecting the deal thesis.

**Implementation:**
```python
# Pattern for all 4 grids — write formula strings in a loop
for r_idx, wacc_val in enumerate(wacc_axis):       # 5 values
    for c_idx, tgr_val in enumerate(tgr_axis):     # 5 values
        formula = build_dcf_formula_string(wacc_val, tgr_val, ...)
        ws.cell(row=start_row + r_idx, col=start_col + c_idx).value = formula
```

### Sheet 8: Checks

**Purpose:** Formula audit. All cells are TRUE/FALSE formulas. All must return TRUE before model is delivered.

```
FORMULA INTEGRITY (one row per projection year, FY1–FY5)
  UFCF check:        =ABS(Projections!ufcf_cell − (nopat + da − capex − dnwc)) < 0.01
  D&A schedule tie:  =ABS(Projections!da_cell − depreciation_schedule_cell) < 0.01
  Debt schedule tie: =ABS(Projections!debt_closing_Yn − (debt_opening + drawdowns − amort)) < 0.01

BALANCE SHEET CHECKS (one row per projection year, FY1–FY5 — all must be TRUE before delivery)
  BS balances FY1:   =ABS(Projections!total_assets_Y1 − Projections!total_liab_eq_Y1) < 0.01
  BS balances FY2:   =ABS(Projections!total_assets_Y2 − Projections!total_liab_eq_Y2) < 0.01
  BS balances FY3:   =ABS(Projections!total_assets_Y3 − Projections!total_liab_eq_Y3) < 0.01
  BS balances FY4:   =ABS(Projections!total_assets_Y4 − Projections!total_liab_eq_Y4) < 0.01
  BS balances FY5:   =ABS(Projections!total_assets_Y5 − Projections!total_liab_eq_Y5) < 0.01
  [A failing BS check means a row is missing, a cash flow is double-counted, or an opening balance is wrong]

SOURCES & USES CHECK
  S&U balances:      =ABS(Inputs!total_uses − (Inputs!debt_drawn + Inputs!su_equity_check)) < 0.01
  [Equity check + Debt drawn must equal Total uses to the cent — if this fails, MOIC entry equity is wrong]

VALUATION SANITY
  TV % of EV < 85%:  =DCF!tv_pct_ev < 0.85
  TGR < WACC:        =Inputs!tgr < WACC!wacc_base
  EV > 0:            =DCF!enterprise_value > 0
  MOIC > 0:          =DCF!moic > 0
  GGM vs Exit within 30%:  =ABS(DCF!pv_tv_ggm / DCF!pv_tv_exit − 1) < 0.30

ROIC — TERMINAL VALUE CREDIBILITY
  ROIC > WACC:            =WACC!roic_terminal > WACC!wacc_base
    [If FALSE: GGM terminal value implies value-destroying steady-state; flag and use exit-multiple TV as primary method]
  Implied reinvestment rate: =Inputs!tgr / WACC!roic_terminal  [formula]
  Reinvestment rate plausible: =AND(Inputs!tgr/WACC!roic_terminal > 0, Inputs!tgr/WACC!roic_terminal < 0.5)
    [> 50% reinvestment rate at terminal is implausible for a mature DACH business]
  TV method override flag:  =IF(WACC!roic_terminal < WACC!wacc_base,
                               "WARN: ROIC < WACC — switch TV method to Exit Multiple (Inputs!tv_method=2)",
                               "OK: GGM credible")

IFRS 16 CONSISTENCY
  IFRS 16 switch set:       =Inputs!ifrs16_switch  [should be 1 for all post-2019 DACH targets]
  Lease liabilities in net debt: =IF(Inputs!ifrs16_switch=1,
                                      Inputs!ifrs16_lease_liabilities_cell > 0,
                                      Inputs!ifrs16_lease_liabilities_cell = 0)
    [If switch=1 but lease liabilities = 0: flag for confirmation — may be genuine zero or missing data]
  CapEx includes no lease repayments: [manual confirmation — cell note required: "CapEx excludes IFRS 16 lease principal repayments (confirmed / not applicable)"]

DATA SOURCING LOG
  [Table: row per major input, columns: Cell Ref | Value | Source Tag | Comment]
  [Auto-populated with named ranges where possible; else manual completion note]

OVERALL STATUS
  All checks pass:   =AND(all_check_cells)   [TRUE = model ready to deliver — includes UFCF checks, D&A tie, debt schedule tie ×5, BS balance checks ×5, S&U balance check, valuation sanity checks, ROIC > WACC check, reinvestment rate plausible, IFRS 16 consistency]
```

---

## Formatting Standards (applies to all sheets)

**Font color convention (mandatory):**
- Blue (`RGB 0,0,255`): ALL hardcoded inputs — lives ONLY on Inputs sheet
- Black (`RGB 0,0,0`): ALL formulas and calculated cells
- Green (`RGB 0,128,0`): Cross-sheet links (references to another sheet)

**Fill color convention (minimal palette):**
- `#1F4E79` dark blue + white bold text: section headers
- `#D9E1F2` light blue + black bold: sub-headers / column headers
- `#F2F2F2` light grey + blue font: input cells (Inputs sheet only)
- `#BDD7EE` medium blue + black bold: key output cells (EV, equity, MOIC, IRR, base-case sensitivity cells)
- White: all other calculated cells

**Borders (mandatory):**
- Thick (1.5pt): around each major section
- Medium (1pt): between sub-sections
- Thin (0.5pt): around data tables

**Number formats:**
- EUR millions: `€#,##0.00` | Percentages: `0.0%` | Multiples: `0.0"x"` | Negatives: `(#,##0.00)`
- All zeros displayed as `"-"` via custom format `€#,##0.00;(€#,##0.00);"-"`

**Cell comments (mandatory for every hardcoded input):**
Format: `"Source: [System/Document/Management], [Date], [Reference], [Tag: FACTSET/WEB/MGMT/UNSOURCED]"`
Add comments AS each input cell is written — not at the end.

---

## AUCTUS Output File Naming

`dcf_{company}_{YYYYMMDD_HHMMSS}.xlsx` — NOT `[Ticker]_DCF_Model_[Date].xlsx`

---

## Correct Patterns

> Everything in this section has been verified. Follow these patterns exactly.

### Formulas Over Hardcodes — Non-Negotiable

Every projection, ratio, discount factor, PV, TV, sensitivity cell, and return metric MUST be a live Excel formula. The only cells that may contain hardcoded numbers are those on the Inputs sheet (and raw reported historicals on the Historicals sheet).

```python
# CORRECT
ws["D20"] = "=Projections!consolidation_rev_Y1 * (1 + Inputs!$C$12)"

# WRONG — python value written to cell
ws["D20"] = 42.31
```

### Scenario Consolidation Column (INDEX, not nested IF)

```python
# Consolidation column for Year 1 revenue growth:
ws["H10"] = "=INDEX(B10:D10, 1, Cover!$B$5)"
# B10=Bear, C10=Base, D10=Bull, Cover!B5=case selector

# Projection formula references consolidation column only:
ws["L10"] = "=L9 * (1 + Projections!$H$10)"
```

### Sensitivity Table Population (Loop)

```python
for r, wacc in enumerate(wacc_axis):      # 5 values
    for c, tgr in enumerate(tgr_axis):    # 5 values
        # Inline the assumption values into a full DCF recalc formula string
        formula = (
            f"=( SUM_PV_FCF_FORMULA_WITH_{wacc} "
            f"+ TERMINAL_VALUE_FORMULA_WITH_{wacc}_AND_{tgr} "
            f"- Inputs!entry_net_debt )"
        )
        ws.cell(row=start + r, column=start_c + c).value = formula
        if r == 2 and c == 2:  # center cell
            ws.cell(...).fill = PatternFill("solid", fgColor="BDD7EE")
            ws.cell(...).font = Font(bold=True)
```

### NWC Build (DSO/DIO/DPO)

```python
# AR for projection year (column E = FY1)
ws["E_ar"] = f"=E_revenue * Inputs!$DSO_cell / 365"
ws["E_inv"] = f"=E_cogs * Inputs!$DIO_cell / 365"
ws["E_ap"]  = f"=E_cogs * Inputs!$DPO_cell / 365"
ws["E_nwc"] = f"=E_ar + E_inv - E_ap"
ws["E_dnwc"]= f"=E_nwc - D_nwc"   # D = prior year
```

### CapEx / Depreciation Schedule (rolling forward)

```python
# For each projection year (col E = FY1, F = FY2, ...)
ws["E_capex"]      = "=E_revenue * Inputs!$capex_pct_cell"
ws["E_depr_new"]   = "=E_capex / Inputs!$asset_life_cell"
ws["E_depr_exist"] = "=D_depr_exist * (1 - 1/Inputs!$asset_life_cell)"  # declining
ws["E_da_total"]   = "=E_depr_new + E_depr_exist"
ws["E_net_ppe"]    = "=D_net_ppe + E_capex - E_da_total"
```

### PE Returns Formulas

```python
ws["moic_cell"] = "=DCF_exit_equity / DCF_entry_equity"
ws["irr_cell"]  = (
    "=XIRR("
    "{-DCF_entry_equity,0,0,0,0,DCF_exit_equity},"
    "{Inputs!close_date,Inputs!y1_date,Inputs!y2_date,"
    "Inputs!y3_date,Inputs!y4_date,Inputs!exit_date}"
    ")"
)
```

### Dual Terminal Value Cross-Check

```python
# After computing both GGM and Exit Multiple TV:
ws["tv_cross_check"] = (
    "=IF(ABS(DCF_pv_tv_ggm/DCF_pv_tv_exit - 1) > 0.30,"
    '"WARN: GGM and Exit TV differ >30% — review assumptions",'
    '"OK: TV methods consistent")'
)
```

### Debt Schedule Roll-Forward

```python
# Debt Schedule — one column per projection year (E=FY1, F=FY2, G=FY3, H=FY4, I=FY5)
# Rows: debt_open=90, debt_draw=91, debt_amort=92, debt_close=93, debt_interest=94
# Update row numbers to match your actual layout.

COLS = ['E', 'F', 'G', 'H', 'I']
for col_idx, col in enumerate(COLS):
    yr = col_idx + 1
    prev = COLS[col_idx - 1] if col_idx > 0 else None

    # Opening balance: FY1 = entry net debt from Inputs; FY2+ = prior closing
    if col_idx == 0:
        ws[f"{col}90"] = "=Inputs!$entry_net_debt_cell"
    else:
        ws[f"{col}90"] = f"={prev}93"

    # Drawdowns (usually 0 — one input cell per year on Inputs sheet)
    ws[f"{col}91"] = f"=Inputs!$drawdown_FY{yr}_cell"

    # Amortisation: take the larger of % method or fixed € method
    ws[f"{col}92"] = (
        f"=MAX({col}90*Inputs!$amort_pct_cell,"
        f"Inputs!$amort_fixed_cell)"
    )

    # Closing balance — Year 5 closing referenced by DCF exit net debt
    ws[f"{col}93"] = f"={col}90+{col}91-{col}92"

    # Cash interest (feeds IS interest line if modelling levered cash flows)
    ws[f"{col}94"] = f"={col}90*Inputs!$kd_pretax_cell"

# DCF sheet exit net debt references debt schedule Year 5 closing, NOT a static input:
ws["dcf_exit_net_debt"] = "=Projections!$I$93"   # I93 = debt_close FY5
```

### Sources & Uses Equity Check

```python
# Sources & Uses block on Inputs sheet
# Three outputs: su_total_uses, su_debt_drawn, su_equity_check
# su_equity_check is the ONLY valid source for entry equity in the MOIC / IRR calculation.

# Blue hardcoded inputs (Inputs sheet only):
ws["su_purchase_price"] = purchase_price_value          # raw input — source comment required
ws["su_txn_fees_pct"]   = 0.020                         # raw input — default 2.0%
ws["su_nwc_adj"]        = nwc_adj_value                 # raw input — 0 if not applicable
ws["su_debt_drawn"]     = debt_drawn_value              # raw input — from credit agreement

# Formula cells (black font — computed from inputs above):
ws["su_txn_fees_eur"]   = "=su_purchase_price * su_txn_fees_pct"
ws["su_total_uses"]     = "=su_purchase_price + su_txn_fees_eur + su_nwc_adj"
ws["su_equity_check"]   = "=su_total_uses - su_debt_drawn"

# DCF sheet entry equity must reference the S&U equity check, not entry_ev - entry_net_debt:
ws["dcf_entry_equity"]  = "=Inputs!$su_equity_check_cell"
```

### Balance Sheet with Cash Plug

```python
# Balance sheet on Projections sheet — added to support BS balance check
# Cash is the residual plug: absorbs all free cash after debt service
# Required rows already present: ufcf (row u), interest (row 94), amort (row 92)

COLS = ['E', 'F', 'G', 'H', 'I']
for col_idx, col in enumerate(COLS):
    prev = COLS[col_idx - 1] if col_idx > 0 else None

    # ── ASSETS ──
    if col_idx == 0:
        ws[f"{col}_cash"] = (
            f"=Inputs!$opening_cash+{col}_ufcf"
            f"-{col}94-{col}92"       # minus interest, minus debt amort
        )
    else:
        ws[f"{col}_cash"] = (
            f"={prev}_cash+{col}_ufcf"
            f"-{col}94-{col}92"
        )
    ws[f"{col}_total_assets"] = f"={col}_cash+{col}_ar+{col}_inv+{col}_net_ppe"

    # ── LIABILITIES & EQUITY ──
    ws[f"{col}_total_debt"] = f"={col}93"    # closing balance from debt schedule

    # Net income = EBIT - cash interest - tax on EBT
    ws[f"{col}_net_income"] = (
        f"=({col}_ebit-{col}94)"             # EBT
        f"*(1-Inputs!$tax_rate_cell)"
    )
    if col_idx == 0:
        ws[f"{col}_ret_earn"] = f"={col}_net_income"   # FY1 opens at 0 (acquisition resets equity)
    else:
        ws[f"{col}_ret_earn"] = f"={prev}_ret_earn+{col}_net_income"

    ws[f"{col}_contrib_eq"]    = "=Inputs!$su_equity_check_cell"  # fixed at entry for all years
    ws[f"{col}_total_eq"]      = f"={col}_contrib_eq+{col}_ret_earn"
    ws[f"{col}_total_liab_eq"] = f"={col}_ap+{col}_total_debt+{col}_total_eq"

    # Inline BS balance check (also mirrored on Checks sheet)
    ws[f"{col}_bs_check"] = f"=ABS({col}_total_assets-{col}_total_liab_eq)<0.01"
```

### Normalised EBITDA Add-Backs Block

```python
# Historicals sheet — add-backs block immediately below reported EBITDA rows.
# Raw add-back inputs are blue; normalised EBITDA and derived rows are black formulas.

for col, yr in zip(year_cols, years):
    # These are raw inputs (blue font, [FILING] or [MGMT] source comment):
    ws[f"{col}{ROW_EBITDA_REP}"]  = reported_ebitda_values[yr]    # blue
    ws[f"{col}{ROW_AB_RESTR}"]    = restructuring_values[yr]       # blue; 0 if none
    ws[f"{col}{ROW_AB_MGMT}"]     = mgmt_fee_addback_values[yr]    # blue; 0 if none
    ws[f"{col}{ROW_AB_SBC}"]      = sbc_values[yr]                 # blue; 0 if none
    ws[f"{col}{ROW_AB_ONETIME}"]  = one_time_values[yr]            # blue; 0 if none
    ws[f"{col}{ROW_AB_OTHER}"]    = other_nonrecurring_values[yr]   # blue; 0 if none

    # Formula rows (black font):
    ws[f"{col}{ROW_EBITDA_NORM}"] = (
        f"={col}{ROW_EBITDA_REP}"
        f"+{col}{ROW_AB_RESTR}"
        f"+{col}{ROW_AB_MGMT}"
        f"+{col}{ROW_AB_SBC}"
        f"+{col}{ROW_AB_ONETIME}"
        f"+{col}{ROW_AB_OTHER}"
    )
    ws[f"{col}{ROW_NORM_DELTA}"]  = (
        f"=IF({col}{ROW_EBITDA_REP}<>0,"
        f"({col}{ROW_EBITDA_NORM}-{col}{ROW_EBITDA_REP})/ABS({col}{ROW_EBITDA_REP}),0)"
    )
    ws[f"{col}{ROW_NORM_MARGIN}"] = f"={col}{ROW_EBITDA_NORM}/{col}{ROW_REVENUE}"

# Projections sheet Year 1 EBITDA anchors to normalised margin, NOT reported margin:
ws[f"E{ROW_PROJ_EBITDA}"] = (
    f"=E{ROW_PROJ_REVENUE}*Inputs!$ebitda_margin_Y1_cell"
    # Inputs!ebitda_margin_Y1_cell was derived from Historicals!normalised margin, not reported
)
```

### Stub-Aware Discount Periods

```python
# DCF sheet Section 2 — stub period from Inputs; all periods are formulas, not hard-coded values.
# stub_cell = the Inputs cell that holds stub_months/12 (e.g., "Inputs!$C$55")

stub_cell = "Inputs!$stub_frac_cell"   # update to actual address
year_offsets = ["/ 2", "+ 0.5", "+ 1.5", "+ 2.5", "+ 3.5"]  # mid-year convention
for col, offset in zip(proj_cols, year_offsets):   # proj_cols = ['E','F','G','H','I']
    ws[f"{col}{ROW_DISC_PERIOD}"] = f"={stub_cell}{offset}"
    ws[f"{col}{ROW_DISC_FACTOR}"] = f"=1/(1+WACC!$wacc_base_cell)^{col}{ROW_DISC_PERIOD}"
    ws[f"{col}{ROW_PV_FCF}"]      = f"={col}{ROW_UFCF}*{col}{ROW_DISC_FACTOR}"

# Terminal value discount exponent also uses stub-aware Year 5 mid-point:
ws[f"{TV_PV_GGM_CELL}"]  = f"={TV_GGM_CELL}/(1+WACC!$wacc_base_cell)^(I{ROW_DISC_PERIOD})"
ws[f"{TV_PV_EXIT_CELL}"] = f"={TV_EXIT_CELL}/(1+WACC!$wacc_base_cell)^(I{ROW_DISC_PERIOD})"
```

### Blume Beta Adjustment in Peer Table

```python
# WACC sheet — peer beta table with both β_raw and β_adj columns.
# β_adj used for Hamada unlevering; β_raw shown for auditability.
# COL_RAW, COL_ADJ, COL_DE, COL_TAX, COL_ULEV = column letters for respective fields.

for row_idx, peer in enumerate(peers):
    r = BETA_TABLE_START_ROW + row_idx
    ws.cell(r, COL_NAME).value   = peer["name"]
    ws.cell(r, COL_RAW).value    = peer["beta_raw"]    # raw input — blue font
    ws.cell(r, COL_ADJ).value    = f"=0.67*{COL_RAW}{r}+0.33"   # Blume — formula, black
    ws.cell(r, COL_DE).value     = peer["de_ratio"]    # raw input — blue
    ws.cell(r, COL_TAX).value    = peer["tax_rate"]    # raw input — blue
    # Hamada unlevering uses β_adj, not β_raw:
    ws.cell(r, COL_ULEV).value   = (
        f"={COL_ADJ}{r}/(1+(1-{COL_TAX}{r})*{COL_DE}{r})"
    )

# Median uses unlevered betas (β_adj unlev), not raw:
ws[f"{MEDIAN_BETA_CELL}"] = f"=MEDIAN({COL_ULEV}{BETA_TABLE_START_ROW}:{COL_ULEV}{r})"
```

### ROIC Terminal Value Credibility Check

```python
# WACC sheet — compute terminal ROIC from Year 5 projection figures.
# Referenced by Checks sheet; named range "roic_terminal" for cross-sheet use.

ws[f"{ROIC_NOPAT_CELL}"]    = f"=Projections!${nopat_Y5_cell}"      # cross-sheet, green font
ws[f"{ROIC_INV_CAP_CELL}"]  = f"=Projections!${net_ppe_Y5}+Projections!${nwc_Y5}"
ws[f"{ROIC_TERMINAL_CELL}"] = f"={ROIC_NOPAT_CELL}/{ROIC_INV_CAP_CELL}"  # named: roic_terminal

# Checks sheet — TV credibility block:
ws[f"{ROIC_GT_WACC_CHECK}"] = f"=WACC!$roic_terminal_cell>WACC!$wacc_base_cell"
ws[f"{REINVEST_RATE_CELL}"] = f"=Inputs!$tgr_cell/WACC!$roic_terminal_cell"
ws[f"{REINVEST_PLAUS_CHECK}"]= (
    f"=AND(Inputs!$tgr_cell/WACC!$roic_terminal_cell>0,"
    f"Inputs!$tgr_cell/WACC!$roic_terminal_cell<0.5)"
)
ws[f"{TV_OVERRIDE_FLAG}"] = (
    f'=IF(WACC!$roic_terminal_cell<WACC!$wacc_base_cell,'
    f'"WARN: ROIC<WACC — use Exit Multiple TV (tv_method=2)",'
    f'"OK")'
)
```

### Maintenance CapEx in Terminal FCF

```python
# DCF sheet Section 3 — terminal FCF uses maintenance CapEx only.
# During projection years UFCF uses total CapEx; at steady-state growth CapEx is optional.

maint_pct = "Inputs!$maintenance_capex_pct_cell"
total_pct  = "Inputs!$total_capex_pct_cell"
rev_Y5     = f"Projections!${rev_Y5_cell}"

# The adjustment adds back the growth CapEx excess not required at steady-state:
ws[f"{TV_CAPEX_ADJ_CELL}"] = f"={rev_Y5}*({maint_pct}-{total_pct})"  # positive if maint < total
ws[f"{TV_UFCF_ADJ_CELL}"]  = f"=Projections!${ufcf_Y5_cell}+{TV_CAPEX_ADJ_CELL}"
ws[f"{TV_FCF_CELL}"]        = f"={TV_UFCF_ADJ_CELL}*(1+Inputs!$tgr_cell)"
ws[f"{TV_GGM_CELL}"]        = f"={TV_FCF_CELL}/(WACC!$wacc_base_cell-Inputs!$tgr_cell)"
```

### Full EV-to-Equity Bridge

```python
# DCF sheet Section 4 — nine separate bridge rows, each cross-referencing Inputs sheet.
# Write as a list of (label, formula) pairs; apply green font (cross-sheet reference) to formulas.

bridge = [
    ("Sum of PV FCFs (€m)",                    f"={sum_pv_fcf_cell}"),
    ("(+) PV of Terminal Value (€m)",           f"={selected_tv_cell}"),
    ("= Enterprise Value (€m)",                 f"={sum_pv_fcf_cell}+{selected_tv_cell}"),   # dcf_ev
    ("(−) Gross financial debt (€m)",           "=Inputs!$gross_debt_cell"),
    ("(−) IFRS 16 lease liabilities (€m)",      "=Inputs!$ifrs16_lease_cell"),
    ("(−) Pension provisions (€m)",             "=Inputs!$pension_cell"),
    ("(−) Minority interest at market (€m)",    "=Inputs!$minority_cell"),
    ("(−) Earnout obligations (€m)",            "=Inputs!$earnouts_cell"),
    ("(+) Associates at equity (€m)",           "=Inputs!$associates_cell"),
    ("(+) Cash and equivalents (€m)",           "=Inputs!$cash_cell"),
    ("(+) Short-term liquid investments (€m)",  "=Inputs!$liquid_inv_cell"),
    ("= Equity Value to Acquirer (€m)",         "=ev-gross_debt-ifrs16-pension-minority-earnouts+associates+cash+liquid"),
    ("Bridge tie check",                        "=ABS((gross_debt+ifrs16+pension+earnouts-cash-liquid)-Inputs!$entry_net_debt_cell)<0.01"),
]
for i, (label, formula) in enumerate(bridge):
    r = BRIDGE_START_ROW + i
    ws.cell(r, COL_LABEL).value   = label
    ws.cell(r, COL_FORMULA).value = formula
    if "=Inputs!" in formula:
        ws.cell(r, COL_FORMULA).font = Font(color="008000")  # green — cross-sheet reference
```

### Named Ranges Registration

```python
from openpyxl.workbook.defined_name import DefinedName

# Register after all sheets are built, immediately before wb.save().
# Cell addresses below are illustrative — update to match your actual row/column layout.
# The six names are fixed contracts used by ic-memo and pitch-deck skills.
named_ranges = {
    "wacc_base":    "WACC!$C$28",
    "entry_ev":     "Inputs!$C$42",
    "year5_ebitda": "DCF!$G$12",
    "dcf_ev":       "DCF!$C$40",
    "dcf_moic":     "DCF!$C$58",
    "dcf_irr":      "DCF!$C$59",
}
for name, ref in named_ranges.items():
    wb.defined_names[name] = DefinedName(name, attr_text=ref)

# Hard assertion — catches any renamed or missed cell during build
assert all(n in wb.defined_names for n in named_ranges), \
    f"Missing named range(s): {[n for n in named_ranges if n not in wb.defined_names]}"
```

---

## Common Mistakes to Avoid

### Fatal: Computing values in Python instead of writing formula strings

```python
# WRONG — kills model flexibility
pv_fcf = fcf / (1 + wacc)**period
ws["E70"] = pv_fcf   # dead number — model won't flex

# CORRECT
ws["E70"] = f"=E65 / (1 + WACC!$wacc_base)^E68"   # live formula
```

### Fatal: Sensitivity tables with linear approximations

```python
# WRONG
ws["B88"] = "=B88_base * (1 + (0.096 - 0.116))"   # not a real DCF recalc

# CORRECT — full DCF recalculation in every cell, via loop
```

### Skipping the centralized Inputs sheet

Hardcoding assumptions directly in Projections or DCF sheet makes the model un-auditable. Every assumption must live on Inputs and be referenced cross-sheet. Without this, changing one assumption requires hunting across multiple sheets.

### Single-sheet model

Cramming everything into one sheet (or two) eliminates the audit trail. The Historicals sheet is what justifies every projection assumption. The Checks sheet is what proves the model is internally consistent.

### Missing exit multiple TV method

Building only GGM means you have no cross-check for the terminal value. For PE specifically, exit multiple is often the more defensible method because it ties directly to observable market multiples.

### Flat D&A % instead of depreciation schedule

Flat D&A % ignores the compound effect of CapEx investments: heavy Year 1 CapEx generates Years 2-5 depreciation that increases the tax shield. The rolling schedule captures this correctly.

### Blocking on FactSet unavailability

If FactSet is down or unauthenticated, fall back to web data with `[WEB]` tags. Never halt the build because one data source is unavailable.

### Too many sequential approval gates

Do not present WACC for approval, wait, then present projections for approval. Present all assumptions together in Step 2 and collect one confirmation.

### Using reported EBITDA as the projection base

Without the normalised EBITDA add-backs schedule, you project from a distorted starting point. If a DACH target had €3m of restructuring in the last historical year, every projection year will be understated by €3m before any growth assumption is applied. For DACH mid-market companies, add-backs of 5–15 % of reported EBITDA are common. The bridge from reported → normalised is the first thing any PE sponsor builds — build it before touching projections.

### IFRS 16 mismatch — silent error in UFCF

Post-IFRS-16 EBITDA (the standard since 2019 for DACH companies) already strips lease depreciation from operating expenses. If lease liabilities are also excluded from net debt, the equity bridge overstates equity value. Conversely, if EBITDA is adjusted to exclude IFRS 16 but lease liabilities are included in net debt, there is double-counting. Always set the IFRS 16 switch explicitly and confirm both sides (EBITDA treatment and net debt treatment) are consistent. For DACH industrial targets, lease liabilities can represent 0.5–2.0× EBITDA.

### Hard-coded mid-year discount periods

Writing `0.5, 1.5, 2.5, 3.5, 4.5` as fixed numbers in the discounting section embeds the assumption that the analysis starts on the first day of the fiscal year. PE transactions almost never close on January 1st. If the close date is October 1st and fiscal year-end is December 31st, Year 1 is a 3-month stub; the first discount period should be 0.125, not 0.5. Reference the stub fraction from the Inputs sheet using formulas.

### Using total CapEx in terminal FCF

Terminal value assumes steady-state earnings power with no aggressive growth reinvestment. Writing `UFCF_Y5 × (1+g) / (WACC − g)` with the Year 5 total CapEx (which includes growth CapEx the business chose to deploy during the projection period) understates the terminal FCF for capital-intensive businesses. At steady-state, growth CapEx is an optional reinvestment decision — only maintenance CapEx (required to sustain current capacity) belongs in the terminal FCF. Use the maintenance CapEx adjustment formula in the GGM section.

### Adding SBC back to UFCF

SBC appears as a non-cash add-back in the operating section of the GAAP/IFRS cash flow statement, which tempts analysts to add it back alongside D&A. Do not. SBC dilutes sponsor ownership at exit and is a real economic cost. The Historicals add-backs block does add SBC back to reported EBITDA (to derive normalised EBITDA) — this is correct and appropriate for establishing the recurring run-rate. But in the UFCF build, SBC is already reflected through EBIT (the P&L charge is in there); it is not added back separately. The two uses of "add-back" (normalisation vs. cash flow) mean completely different things.

### Single-line net debt input

Entering net debt as one number (`entry_net_debt: 45.0`) makes the equity bridge unauditable and silently drops pension provisions and IFRS 16 lease liabilities — both of which are explicitly deducted by PE buyers in DACH acquisitions. For DACH industrial targets, pension provisions (Pensionsrückstellungen) routinely equal 1–3× EBITDA. Decompose net debt into its seven components on the Inputs sheet from the first day of the build.

---

## Quality Rubric

Every DCF model must satisfy:

1. **All arithmetic in Excel formulas** — zero Python-computed values in derived cells
2. **8 sheets complete** — Cover, Inputs, Historicals, Projections, WACC, DCF, Sensitivity, Checks
3. **Checks sheet all TRUE** — UFCF tie, TV/EV <85%, TGR<WACC, EV>0, MOIC>0
4. **Three sensitivity grids fully populated** — 225 formula cells, no placeholders
5. **Both TV methods built** — GGM and exit multiple, cross-check within 30%
6. **PE returns complete** — MOIC and IRR calculated as live Excel formulas
7. **NWC from DSO/DIO/DPO** — or flat % with [ESTIMATED] tag if no balance sheet
8. **Depreciation schedule present** — rolling PP&E forward-forward, D&A from schedule
9. **WACC from CAPM** — peer beta table, Hamada re-levering, full cost of equity build
10. **All sources tagged** — FACTSET / WEB / MGMT / UNSOURCED on every hardcoded input cell comment
11. **Debt schedule rolled forward** — opening + drawdowns − amortisation = closing for FY1–FY5; exit net debt references Debt Schedule Year 5 closing balance, never a static Inputs entry; Checks sheet debt schedule tie TRUE for all 5 years
12. **Balance sheet complete and balanced** — cash plug, total debt (from Debt Schedule), retained earnings roll-forward, contributed equity (= S&U equity check, fixed); BS balance check TRUE for FY1–FY5 on Checks sheet; S&U balance check TRUE
13. **Scenario Summary on Cover** — Bear/Base/Bull side by side (Revenue FY5, EBITDA FY5, EBITDA margin %, EV, equity value, MOIC, IRR); all 21 cells are cross-sheet formula references to DCF Scenario Returns Summary rows; zero hardcodes
14. **Named ranges defined** — `wacc_base`, `entry_ev`, `year5_ebitda`, `dcf_ev`, `dcf_moic`, `dcf_irr` all registered via `wb.defined_names` before workbook save; assertion confirms none are missing; LTM column present on Historicals sheet with quarterly sums or [LTM_PROXY] tag
15. **Normalised EBITDA add-backs present** — Historicals sheet has a dedicated add-backs block: reported EBITDA → restructuring → management fees → SBC → one-time items → normalised EBITDA with normalisation delta %. Projections Sheet 4 anchors Year 1 EBITDA margin to normalised EBITDA margin, not reported. If add-backs are zero, this is stated explicitly.
16. **Net debt fully decomposed** — Inputs sheet lists all seven net debt components separately (gross financial debt, IFRS 16 lease liabilities, pension provisions, earnouts, DTL on intangibles, minus cash, minus liquid investments). Entry net debt = formula SUM of components. A single-line net debt input is not acceptable.
17. **IFRS 16 treatment explicitly stated** — Inputs!ifrs16_switch is populated (1 or 0) with a cell note. If switch = 1: IFRS 16 lease liabilities > 0 in net debt decomposition; CapEx excludes lease principal repayments. IFRS 16 consistency check TRUE on Checks sheet.
18. **Football field chart present on Cover** — Named chart object "auctus_football_field" on Cover sheet (anchored below Scenario Summary) showing DCF range (Bear→Bull), trading comps range, precedent transactions range, and LBO floor on a single EV axis. All endpoints are formula references. If comps/precedents unavailable: placeholder bars with [FOOTBALL_FIELD_PENDING] note.
19. **Beta methodology uniform across all peers** — WACC sheet peer table has both β_raw and β_adj (Blume: 0.67 × β_raw + 0.33) columns. β_adj used for Hamada unlevering. Observation period is 2-year weekly (104 observations). Market index is STOXX Europe 600 or DAX 40. BETA METHODOLOGY block present in WACC sheet.
20. **ROIC → TV credibility check on Checks sheet** — WACC sheet computes roic_terminal = NOPAT_Y5 / (Net_PPE_Y5 + NWC_Y5). Checks sheet has: ROIC > WACC TRUE/FALSE; implied reinvestment rate formula; reinvestment rate < 50 % check; TV override warning if ROIC < WACC.
21. **Full EV-to-equity bridge** — DCF Section 4 has nine bridge rows: gross financial debt, IFRS 16 lease liabilities, pension provisions, minority interest, earnouts, associates at equity, cash, short-term liquid investments. Not a single-line net debt deduction. Tie check confirms bridge components sum to Inputs!entry_net_debt.
22. **Stub period handled** — Inputs sheet has analysis date and fiscal year-end month. Stub fraction computed as formula. DCF Section 2 discount periods reference stub fraction formula (not hard-coded 0.5 | 1.5 | 2.5 | 3.5 | 4.5). TV discount exponent also uses stub-aware Year 5 mid-point.
23. **Maintenance vs. growth CapEx split** — Inputs sheet has separate total CapEx % and maintenance CapEx % rows. Projections sheet shows the split. Terminal FCF in DCF Section 3 uses maintenance CapEx only (growth CapEx adjustment formula present). UFCF during projection years uses total CapEx.
24. **SBC treatment explicit** — Historicals sheet shows SBC with note that it is NOT added back to UFCF. Projections sheet Section 4 (Free Cash Flow) contains the SBC treatment note. SBC does not appear as an add-back in the D&A row of the UFCF build.
25. **Deferred revenue PPA flag** — If target is SaaS/subscription with deferred revenue > 5 % of LTM revenue: Step 2 review flags [PPA_HAIRCUT_REQUIRED] and estimates Year 1 revenue impact. Projections cannot be finalised without deal team sign-off on the PPA estimate.
26. **IRR × leverage sensitivity (Grid 4)** — Sensitivity sheet has a fourth 5×5 grid: entry Net Debt/EBITDA × exit EV/EBITDA → IRR. All 25 cells are formula strings. Center cell = base case IRR highlighted `#BDD7EE`. Conditional formatting: green ≥ 20 %, amber 15–19.9 %, red < 15 %.
27. **Revenue by segment (if available)** — If annual report provides segment/geography data: Historicals sheet has a segment revenue block with cross-check to total. If segments have materially different growth profiles (> 500 bps spread), Projections sheet projects each separately and rolls up. If unavailable: [SEGMENT_DATA_UNAVAILABLE] note on Historicals.
28. **Cash tax vs. statutory tax** — Historicals sheet shows current tax, deferred tax, and cash effective tax rate separately. If the 3-year average cash effective rate deviates > 200 bps from the statutory rate: UFCF projections use cash effective rate tagged [CASH_TAX_RATE]. NOL carry-forwards noted if material.
