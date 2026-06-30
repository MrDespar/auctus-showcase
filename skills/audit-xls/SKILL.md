---
name: audit-xls
version: "1.1.0"
description: >
  Audits AUCTUS model workbooks for formula accuracy, financial integrity, and
  AUCTUS-specific quality checks (balance_check_eur_m ±€0.01m, IRR convergence,
  sensitivity grid NaN check, terminal value cap). Also runs the pytest quality gate.
  Call after any DCF, LBO, or comps workflow before delivering outputs to the user.
triggers:
  - "audit this sheet"
  - "check my formulas"
  - "find formula errors"
  - "QA this spreadsheet"
  - "sanity check this"
  - "debug model"
  - "model check"
  - "model won't balance"
  - "something's off in my model"
  - "model review"
  - "audit model"
  - "validate model"
  - "run QA"
inputs:
  required:
    - "model_path — path to the .xlsx file to audit"
    - "model_type — dcf | lbo | comps | 3-statement"
  optional:
    - "scope — selection | sheet | model (default: model)"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"

outputs:
  - "Findings report (in-session markdown)"
  - "logs/agent_activity.log entry"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG requires a deterministic quality gate on every model before
user delivery. This skill wraps the Anthropic audit-xls methodology with AUCTUS-specific
checks and the pytest quality gate.

### Prerequisites

None. This skill is called **after** a valuation workflow completes and before outputs
are delivered to the user. It does not run models — it validates what other skills produced.

### Data Source Hierarchy

This skill reads existing output artifacts — it does not fetch new data.

### Currency & Units

- Monetary values in **EUR millions (€m)**; all checks are in €m scale
- `balance_check_eur_m` must be within **±€0.01m** of zero for LBO models

### Execution Environment

Verify that the output documents meet all AUCTUS constraints natively.

### AUCTUS-Specific Rules

Run these checks IN ADDITION to the Anthropic audit workflow below:

**LBO-specific:**
- `irr_solver_converged` must be `true` in compact JSON
- `balance_check_eur_m` within ±€0.01m of zero
- Sensitivity grids: no NaN cells in central 3×3 region
- Leverage at exit < leverage at entry
- Interest coverage ≥ 1.0× in all projection years

**DCF-specific:**
- NPV must be finite and > 0
- Sensitivity grid (5×5): no NaN cells; center cell = base case output

**Comps-specific:**
- 4–6 peers (not fewer, not more than 6 without explanation)
- No null multiples in any column
- Implied EV range: lower bound < upper bound
- Statistics block (max, 75th, median, 25th, min) present for all ratio/margin columns

**All models:**
- Color convention: blue = hardcoded input, black = formula, green = cross-tab link,
  purple = same-tab link (LBO/3-statement models)
- Sensitivity grids: ODD dimensions (5×5), center cell highlighted `#BDD7EE`
- Negative formatting: parentheses `(€X.Xm)`, never minus sign

---

# Audit Spreadsheet (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

Audit formulas and data for accuracy and mistakes. Scope determines depth — from quick formula checks on a selection up to full financial-model integrity audits.

## Step 1: Determine scope

If the user already gave a scope, use it. Otherwise **ask them**:

> What scope do you want me to audit?
> - **selection** — just the currently selected range
> - **sheet** — the current active sheet only
> - **model** — the whole workbook, including financial-model integrity checks (BS balance, cash tie-out, roll-forwards, logic sanity)

The **model** scope is the deepest — use it for DCF, LBO, 3-statement, merger, comps, or any integrated financial model before sending to a client or IC.

---

## Step 2: Formula-level checks (ALL scopes)

Run these regardless of scope:

| Check | What to look for |
|---|---|
| Formula errors | `#REF!`, `#VALUE!`, `#N/A`, `#DIV/0!`, `#NAME?` |
| Hardcodes inside formulas | `=A1*1.05` — the `1.05` should be a cell reference |
| Plugs & dummy variables | `+ 0.001` or manual additions to force balancing |
| Inconsistent formulas | A formula that breaks the pattern of its neighbors in a row/column |
| Off-by-one ranges | `SUM`/`AVERAGE` that misses the first or last row |
| Pasted-over formulas | Cell that looks like a formula but is actually a hardcoded value |
| Circular references | Intentional or accidental. Check if "Circ Breaker" logic is present and working. |
| Broken cross-sheet links | References to cells that moved or were deleted |
| Unit/scale mismatches | Thousands mixed with millions, % stored as whole numbers |
| Hidden data | Hidden rows, columns, `VeryHidden` tabs, or text colored same as background (white-on-white) |
| Name Manager bloat | Unused named ranges, `#REF!` errors in named ranges |

---

## Step 3: Model-integrity checks (MODEL scope only)

If scope is **model**, identify the model type (DCF / LBO / 3-statement / merger / comps / custom) and run the appropriate integrity checks below.

### 3a. Structural review

| Check | What to look for |
|---|---|
| Input/formula separation | Are inputs clearly separated from calculations? |
| Color convention | Blue=input, black=formula, green=link — or whatever the model uses, applied consistently? |
| Tab flow | Logical order (Assumptions → IS → BS → CF → Valuation)? |
| Date headers & flags | Consistent across all tabs? Are boolean timing flags used correctly? |
| Units | Consistent (thousands vs millions vs actuals)? |

### 3b. Balance Sheet

| Check | Test |
|---|---|
| BS balances | Total Assets = Total Liabilities + Equity (every period). Max tolerance is 0.0001 (floating point variance). |
| RE rollforward | Prior RE + Net Income − Dividends = Current RE |
| Goodwill/intangibles | Flow from acquisition assumptions (if M&A) |

If BS doesn't balance, **quantify the gap per period and trace where it breaks** — nothing else matters until this is fixed.

### 3c. Cash Flow Statement

| Check | Test |
|---|---|
| Cash tie-out | CF Ending Cash = BS Cash (every period) |
| CF sums | CFO + CFI + CFF = Δ Cash |
| D&A match | D&A on CF = D&A on IS |
| CapEx match | CapEx on CF matches PP&E rollforward on BS |
| WC changes | Signs match BS movements (increase in Asset = cash outflow; increase in Liab = cash inflow) |

### 3d. Income Statement

| Check | Test |
|---|---|
| Revenue build | Ties to segment/product detail |
| Tax | Tax expense = Pre-tax income × tax rate (allow for deferred tax adj) |
| Share count | Ties to dilution schedule (options, converts, buybacks, Treasury Stock Method applied correctly) |

### 3e. Circular references & Circuit Breaker

- Interest → debt balance → cash → interest is a common intentional circ in LBO/3-stmt models.
- If intentional: verify iteration toggle exists and works, AND that a "Circ Breaker" or "Circ Flush" is implemented.
- If unintentional: trace the loop and flag how to break it.

### 3f. Logic & reasonableness

| Check | Flag if |
|---|---|
| Growth rates | >100% revenue growth without explanation |
| Margins | Outside industry norms |
| Terminal value dominance | TV > ~75% of DCF EV (yellow flag) |
| Hockey-stick | Projections ramp unrealistically in out-years |
| Compounding | EBITDA compounds to absurd $ by Year 10 |
| Edge cases | Model breaks at 0% or negative growth, negative EBITDA, leverage goes negative |

### 3g. Model-type-specific bugs

**DCF:**
- Discount rate applied to wrong period (mid-year vs end-of-year convention errors).
- Discount factor calculations not using actual days (should use XNPV/XIRR for exact timing).
- Terminal value not discounted back properly.
- WACC uses book values instead of market values for capital structure weights.
- FCF includes interest expense (FCF should be strictly unlevered).
- Tax shield double-counted.

**LBO:**
- Debt paydown sweep doesn't match cash sweep mechanics (must use `MIN` function).
- PIK interest not accruing to principal.
- Revolver circularity not bounded correctly.
- Management rollover and options/promote waterfall not reflected in equity returns.
- Cash-on-Cash (MOIC) calculation is incorrect.
- Exit multiple applied to wrong EBITDA (LTM vs NTM).
- Fees/expenses not deducted from Day 1 equity.

**Merger:**
- Accretion/dilution uses wrong share count (pre- vs post-deal).
- Synergies not phased in over time.
- Purchase price allocation (PPA) doesn't balance or creates incorrect DTL on asset step-up.
- Foregone interest on cash not included.
- Transaction fees not in sources & uses.

**Comps:**
- Calendarization mismatch (companies have different FY ends not properly aligned).
- Non-recurring items not correctly excluded from adjusted EBITDA.
- Fully Diluted Shares Outstanding (FDSO) miscalculated (Treasury Stock Method).

**3-statement:**
- Working capital changes have wrong sign.
- Depreciation doesn't match PP&E schedule.
- Debt maturity schedule doesn't match principal payments.
- Dividends exceed net income without explanation.

---

## Step 4: Correct Patterns

When suggesting fixes for the gaps above, use these standardized IB/PE implementation patterns:

**1. Circuit Breaker for Intentional Circularities:**
```excel
=IF(Circ_Toggle=1, 0, [Normal Interest Calculation])
```
*Note: A dedicated cell `Circ_Toggle` (1 = break, 0 = normal) should be linked to all circular dependencies (e.g., Interest Expense, Revolver Draw) to easily flush `#REF!` errors.*

**2. Exact Timing Discounting (XNPV / XIRR over NPV / IRR):**
```excel
=XNPV(Discount_Rate, Cash_Flows_Range, Dates_Range)
```
*Note: Prefer `XNPV` over standard `NPV` because PE holding periods and cash flows often occur off-cycle or exactly on closing/exit dates.*

**3. Mid-Year Convention Discount Factor:**
```excel
=1 / ((1 + WACC) ^ (Year_Index - 0.5))
```
*Note: Operating cash flows are assumed to be generated evenly throughout the year, hence `Year_Index - 0.5`. Terminal value typically uses end-of-year `Year_Index`.*

**4. Cash Sweep (Debt Paydown) Logic:**
```excel
=MIN(Available_Cash_for_Debt_Service, Beginning_Debt_Balance)
```
*Note: Avoid `IF` statements when a `MIN` function mathematically bounds the paydown to not exceed the outstanding principal.*

**5. Treasury Stock Method (Fully Diluted Shares):**
```excel
=Basic_Shares + MAX(0, Options_Outstanding - (Options_Outstanding * Strike_Price / Current_Share_Price))
```

---

## Step 5: Quality Rubric

Grade the audit based on the following rubric:

- **Pass (Clean):** Zero critical errors. Zero hardcodes in formula blocks. Balance sheets tie perfectly (±0.0001). Circularities have a functioning circuit breaker.
- **Pass with Remarks:** No critical errors but contains formatting inconsistencies, missing named ranges, or minor warnings (e.g., hardcoded plugs identified and justified).
- **Fail:** Any #REF! errors, unbalanced balance sheet > ±0.01m, broken cash sweep logic, missing circuit breaker for circular references, or cash flow signs inverted.

---

## Step 6: Report

Output a findings table:

| # | Sheet | Cell/Range | Severity | Category | Issue | Suggested Fix |
|---|---|---|---|---|---|---|

**Severity:**
- **Critical** — wrong output (BS doesn't balance, formula broken, cash doesn't tie)
- **Warning** — risky (hardcodes, inconsistent formulas, edge-case failures, missing Circ Breaker)
- **Info** — style/best-practice (color coding, layout, naming, unused named ranges)

For **model** scope, prepend a summary line:

> Model type: [DCF/LBO/3-stmt/...] — Overall: [Clean / Minor Issues / Major Issues] — [N] critical, [N] warnings, [N] info

**Don't change anything without asking** — report first, fix on request.

---

## Notes

- **BS balance first** — if it doesn't balance, everything downstream is suspect
- **Hardcoded overrides are the #1 source of silent bugs** — search aggressively
- **Sign convention errors** (positive vs negative for cash outflows) are extremely common
- If the model uses VBA macros, note any macro-driven calculations that can't be audited from formulas alone
