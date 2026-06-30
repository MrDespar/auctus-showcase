# Formula Reference

**IMPORTANT:** Use the formulas outlined in this reference document unless otherwise specified by the user.

---

## Core Linkages

```
Balance Sheet:        Assets = Liabilities + Equity
Net Income:           IS Net Income → CF Operations (starting point)
Cash Flow:            ΔCash = CFO + CFI + CFF
Cash Tie-Out:         Ending Cash (CF) = Cash (BS Asset)
Cash Monthly/Annual:  Closing Cash (Monthly) = Closing Cash (Annual)
Retained Earnings:    Prior RE + Net Income - Dividends = Ending RE
Equity Raise:         ΔCommon Stock/APIC (BS) = Equity Issuance (CFF)
Year 0 Equity:        Equity Raised (Year 0) = Beginning Equity (Year 1)
```

## Gross Profit Calculation

**IMPORTANT:** Gross Profit must be calculated from Net Revenue, not Gross Revenue.

```
Net Revenue - Cost of Revenue = Gross Profit
```

| Term | Definition |
|------|------------|
| Gross Revenue | Total revenue before any deductions |
| Net Revenue | Gross Revenue - Returns - Allowances - Discounts |
| Cost of Revenue | Direct costs attributable to production of goods/services sold |
| Gross Profit | Net Revenue - Cost of Revenue |

**Note:** Always use Net Revenue (also called "Net Sales" or simply "Revenue" on most financial statements) as the starting point for profitability calculations. Gross Revenue overstates the true top-line performance.

## Margin Formulas

```
Gross Margin %      = Gross Profit / Net Revenue
EBITDA              = EBIT + D&A  (or = Gross Profit - OpEx)
EBITDA Margin %     = EBITDA / Net Revenue

Adjusted EBITDA     = EBITDA + Non-Recurring Expenses + Management Fees + Pro Forma Adjustments
Adjusted EBITDA Margin % = Adjusted EBITDA / Net Revenue

EBIT Margin %       = EBIT / Net Revenue
Net Income Margin % = Net Income / Net Revenue

Unlevered FCF (UFCF) = EBIT - Taxes + D&A - ΔNWC - CapEx
```

## Credit Metric Formulas

```
Total Debt            = Current Portion of Debt + Long-Term Debt
Net Debt              = Total Debt - Cash
Total Debt / EBITDA   = Total Debt / EBITDA (from IS)
Net Debt / EBITDA     = Net Debt / EBITDA (from IS)
Interest Coverage     = EBITDA / Interest Expense (from IS)
Net Int Exp % Debt    = Net Interest Expense / Long-Term Debt
Debt / Total Cap      = Total Debt / (Total Debt + Total Equity)
Debt / Equity         = Total Debt / Total Equity
Current Ratio         = Total Current Assets / Total Current Liabilities
Quick Ratio           = (Total Current Assets - Inventory) / Total Current Liabilities
```

## Forecast Formulas (% of Net Revenue Method)

```
Cost of Revenue (Forecast) = Net Revenue × Cost of Revenue % Assumption
S&M (Forecast)             = Net Revenue × S&M % Assumption
G&A (Forecast)             = Net Revenue × G&A % Assumption
R&D (Forecast)             = Net Revenue × R&D % Assumption
SBC (Forecast)             = Net Revenue × SBC % Assumption
```

## Working Capital Formulas

```
Accounts Receivable
  Prior AR
  + Revenue (from IS)
  - Cash Collections (plug)
  = Ending AR
  DSO = (AR / Revenue) × 365

Inventory
  Prior Inventory
  + Purchases (plug)
  - COGS (from IS)
  = Ending Inventory
  DIO = (Inventory / COGS) × 365

Prepaid Expenses
  Prior Prepaid Expenses
  + Cash Paid for Prepaids
  - Expense Recognized (from IS)
  = Ending Prepaid Expenses

Accounts Payable
  Prior AP
  + Purchases (from Inventory calc)
  - Cash Payments (plug)
  = Ending AP
  DPO = (AP / COGS) × 365

Accrued Liabilities
  Prior Accrued Liabilities
  + Expense Recognized (from IS)
  - Cash Payments
  = Ending Accrued Liabilities

Deferred Revenue
  Prior Deferred Revenue
  + Cash Collected for Unearned Revenue
  - Revenue Recognized (from IS)
  = Ending Deferred Revenue

Net Working Capital = AR + Inventory + Prepaid Expenses - AP - Accrued Liabilities - Deferred Revenue
ΔWC = Current NWC - Prior NWC
```

## D&A Schedule Formulas

```
Capital Expenditures
  Maintenance CapEx
  + Growth CapEx
  = Total CapEx

Beginning PP&E (Gross)
  + Total CapEx
  = Ending PP&E (Gross)

Beginning Accumulated Depreciation
  + Book Depreciation Expense (Straight-Line)
  = Ending Accumulated Depreciation

PP&E (Net) = Gross PP&E - Accumulated Depreciation

Book vs. Tax Depreciation (DTL Generation)
  Tax Depreciation = Accelerated Tax Schedule (e.g., MACRS)
  Book Depreciation = Straight-Line Schedule
  Timing Difference = Tax Depreciation - Book Depreciation
  New DTL Created = Timing Difference × Tax Rate
```

## Debt Schedule Formulas

```
Cash Available for Debt Service (CADS)
  Beginning Cash
  + Free Cash Flow (before debt service)
  - Minimum Cash Balance
  = CADS

Revolving Credit Facility (Revolver)
  Revolver Draw / (Paydown) = IF(CADS < 0, MIN(Capacity - Beginning Revolver, ABS(CADS)), -MIN(Beginning Revolver, CADS))
  Ending Revolver = Beginning Revolver + Revolver Draw / (Paydown)

Term Debt (Mandatory Amortization & Cash Sweep)
  Mandatory Amortization = Initial Term Debt × Amortization %
  Excess Cash for Sweep = MAX(0, CADS - Revolver Paydown - Mandatory Amortization)
  Optional Prepayment (Cash Sweep) = MIN(Beginning Term Debt - Mandatory Amortization, Excess Cash for Sweep × Sweep %)
  Ending Term Debt = Beginning Term Debt - Mandatory Amortization - Optional Prepayment

Total Debt = Ending Revolver + Ending Term Debt

Interest Expense = (Avg Revolver × Revolver Rate) + (Avg Term Debt × Term Debt Rate)
  (Use circularity breaker toggle if #REF! errors occur)
```

## Retained Earnings Formula

```
Beginning Retained Earnings
+ Net Income (from IS)
+ Stock-Based Compensation (SBC) (from IS)
- Dividends
= Ending Retained Earnings
```

## NOL (Net Operating Loss) Schedule Formulas

```
NOL CARRYFORWARD SCHEDULE

Beginning NOL Balance (Year 1 / Formation = 0)
+ NOL Generated (if EBT < 0, then ABS(EBT), else 0)
- NOL Utilized (limited by taxable income and utilization cap)
= Ending NOL Balance

STARTING BALANCE RULE

For a new business or first modeled period:
  Beginning NOL Balance = 0
  NOL can only increase through realized losses (EBT < 0)
  NOL cannot be created from thin air or assumed

NOL UTILIZATION CALCULATION

Pre-Tax Income (EBT)
  If EBT > 0:
    NOL Available = Beginning NOL Balance
    Utilization Limit = EBT × 80%  (post-2017 federal limit)
    NOL Utilized = MIN(NOL Available, Utilization Limit)
    Taxable Income = EBT - NOL Utilized
  If EBT ≤ 0:
    NOL Utilized = 0
    Taxable Income = 0
    NOL Generated = ABS(EBT)

TAX CALCULATION WITH NOL

Taxes Payable = MAX(0, Taxable Income × Tax Rate)
  (Taxes cannot be negative; losses create NOL asset instead)

DEFERRED TAX ASSET (DTA) FOR NOL

DTA - NOL Carryforward = Ending NOL Balance × Tax Rate
ΔDTA = Current DTA - Prior DTA
  (Increase in DTA = non-cash benefit on CF)
  (Decrease in DTA = non-cash expense on CF)
```

## Balance Sheet Structure

```
ASSETS
  Cash (from CF ending cash)
  Accounts Receivable (from WC)
  Inventory (from WC)
  Prepaid Expenses (from WC)
  Total Current Assets
  
  PP&E, Net (from DA)
  Deferred Tax Asset - NOL (from NOL schedule)
  Total Non-Current Assets
  Total Assets

LIABILITIES
  Accounts Payable (from WC)
  Accrued Liabilities (from WC)
  Deferred Revenue (from WC)
  Current Portion of Debt (from Debt)
  Total Current Liabilities
  
  Revolver (from Debt)
  Long-Term Debt (from Debt)
  Deferred Tax Liability (from D&A schedule)
  Total Liabilities

EQUITY
  Common Stock
  Retained Earnings (from RE schedule)
  Total Equity

CHECK: Assets - Liabilities - Equity = 0
```

## Cash Flow Statement Structure

```
CASH FROM OPERATIONS (CFO)
  Net Income (LINK: IS)
  + D&A (LINK: DA schedule)
  + Stock-Based Compensation (SBC) (LINK: IS or Assumptions)
  - ΔDTA (Deferred Tax Asset) (LINK: NOL schedule; increase in DTA = use of cash)
  + ΔDTL (Deferred Tax Liability) (LINK: D&A schedule)
  - ΔAR (LINK: WC)
  - ΔInventory (LINK: WC)
  - ΔPrepaid Expenses (LINK: WC)
  + ΔAP (LINK: WC)
  + ΔAccrued Liabilities (LINK: WC)
  + ΔDeferred Revenue (LINK: WC)
  = CFO

CASH FROM INVESTING (CFI)
  - Maintenance CapEx (LINK: DA schedule)
  - Growth CapEx (LINK: DA schedule)
  = CFI

CASH FROM FINANCING (CFF)
  + Revolver Draw / (Paydown) (LINK: Debt)
  + Debt Issuance (LINK: Debt)
  - Debt Repayment (Mandatory & Sweep) (LINK: Debt)
  + Equity Issuance (LINK: BS Common Stock/APIC)
  - Dividends (LINK: RE schedule)
  = CFF

Net Change in Cash = CFO + CFI + CFF
Beginning Cash
+ Net Change in Cash
= Ending Cash (LINK TO: BS Cash)
```

## Income Statement Structure

```
Net Revenue
  Growth %
(-) Cost of Revenue
  % of Net Revenue
────────────────
Gross Profit (= Net Revenue - Cost of Revenue)
  Gross Margin %

(-) S&M
  % of Net Revenue
(-) G&A
  % of Net Revenue
(-) R&D
  % of Net Revenue
(-) D&A
(-) SBC
  % of Net Revenue
────────────────
EBIT
  EBIT Margin %

EBITDA
  EBITDA Margin %

(+) Non-Recurring Expenses
(+) Management Fees
(+) Pro Forma Adjustments
────────────────
Adjusted EBITDA
  Adjusted EBITDA Margin %

(-) Interest Expense
────────────────
EBT (Pre-Tax Income)
(-) NOL Utilization (from NOL schedule, reduces taxable income)
────────────────
Taxable Income
(-) Current Taxes
(-) Deferred Taxes (from DTL creation)
────────────────
Total Taxes
────────────────
Net Income
  Net Income Margin %
```

## Check Formulas

```
BS Balance Check:       = Assets - Liabilities - Equity  (must = 0)
Cash Tie-Out:           = BS Cash - CF Ending Cash       (must = 0)
RE Roll-Forward:        = Prior RE + NI + SBC - Div - BS RE  (must = 0)
DTA Tie-Out:            = NOL Schedule DTA - BS DTA      (must = 0)
Equity Raise Tie-Out:   = ΔCommon Stock/APIC (BS) - Equity Issuance (CFF)  (must = 0)
Year 0 Equity Tie-Out:  = Equity Raised (Year 0) - Beginning Equity (Year 1)  (must = 0)
Cash Monthly vs Annual: = Closing Cash (Monthly) - Closing Cash (Annual)  (must = 0)
NOL Utilization Cap:    = NOL Utilized ≤ EBT × 80%       (must be TRUE for post-2017)
NOL Non-Negative:       = Ending NOL Balance ≥ 0         (must be TRUE)
NOL Starting Balance:   = Beginning NOL (Year 1) = 0     (must be TRUE for new business)
NOL Accumulation:       = NOL increases only when EBT < 0 (losses generate NOL)
```
