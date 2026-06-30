# Public Filings Data Extraction (DACH / SEC) Reference

**When to Use:** Only reference this file when a model template specifically requires pulling data from SEC filings (Annual Report, Quarterly Report). For templates that provide data directly or use other data sources, this reference is not needed.

---

## Extracting Data from Public Filings (Annual/Quarterly Reports)

When populating a model template with public company data, extract financials directly from SEC filings.

### Step 1: Locate the Filing

1. Use DACH Registries (Unternehmensregister/Bundesanzeiger) or SEC EDGAR for US listed peers.
2. Locate Jahresabschluss (Annual) or Quartalsmitteilung (Quarterly).

### Step 2: Identify Filing Currency

Before extracting data, identify the reporting currency:
- Check the cover page or header for reporting currency
- Look at statement headers (e.g., "in thousands of Euros")
- Review Note 1 (Summary of Significant Accounting Policies)

**Common Currency Indicators**

| Indicator | Currency |
|-----------|----------|
| €, EUR | Euro |
| £, GBP | British Pound |
| ¥, JPY | Japanese Yen |
| ¥, CNY, RMB | Chinese Yuan |
| CHF | Swiss Franc |
| CAD, C$ | Canadian Dollar |

Set model currency to match filing; document in Assumptions tab.

### Step 3: Navigate to Financial Statements

Within the Annual Report or Quarterly Report, locate:
- **Financial Statements section** (Annual Report) or **Financial Statements section** (Quarterly Report): Financial Statements
- Key sections to extract:
  - Consolidated Statements of Operations (Income Statement)
  - Consolidated Balance Sheets
  - Consolidated Statements of Cash Flows
  - Notes to Financial Statements (for schedule details)

### Step 4: Data Extraction Mapping

**Income Statement (from Consolidated Statements of Operations)**

| Filing Line Item | Model Line Item |
|------------------|-----------------|
| Net revenues / Net sales | Revenue |
| Cost of goods sold | COGS |
| Selling, general and administrative | SG&A |
| Depreciation and amortization | D&A |
| Interest expense, net | Interest Expense |
| Income tax expense | Taxes |
| Net income | Net Income |

**Balance Sheet (from Consolidated Balance Sheets)**

| Filing Line Item | Model Line Item |
|------------------|-----------------|
| Cash and cash equivalents | Cash |
| Accounts receivable, net | AR |
| Inventories | Inventory |
| Property, plant and equipment, net | PP&E (Net) |
| Total assets | Total Assets |
| Accounts payable | AP |
| Short-term debt / Current portion of LT debt | Current Debt |
| Long-term debt | LT Debt |
| Retained earnings | Retained Earnings |
| Total stockholders' equity | Total Equity |

**Cash Flow Statement (from Consolidated Statements of Cash Flows)**

| Filing Line Item | Model Line Item |
|------------------|-----------------|
| Net income | Net Income |
| Depreciation and amortization | D&A |
| Changes in accounts receivable | ΔAR |
| Changes in inventories | ΔInventory |
| Changes in accounts payable | ΔAP |
| Capital expenditures | CapEx |
| Proceeds from issuance of common stock | Equity Issuance |
| Proceeds from / Repayments of debt | Debt activity |
| Dividends paid | Dividends |

### Step 5: Extract Supporting Detail from Notes

For schedules, pull from Notes to Financial Statements:
- **Note: Debt** → Maturity schedule, interest rates, covenants
- **Note: Property, Plant & Equipment** → Gross PP&E, accumulated depreciation, useful lives
- **Note: Revenue** → Segment breakdowns, geographic splits
- **Note: Leases** → Operating vs. finance lease obligations

### Step 6: Historical Data Requirements

Extract 3 years of historical data minimum:
- Annual Report provides 3 years of IS/CF, 2 years of BS
- For 3rd year BS, pull from prior year's Annual Report
- Use Quarterly Reports to fill in quarterly granularity if needed

### Data Extraction Checklist

- Identify reporting currency and scale (thousands, millions)
- 3 years historical Income Statement
- 3 years historical Cash Flow Statement
- 3 years historical Balance Sheet
- Verify IS Net Income = CF starting Net Income (each year)
- Verify BS Cash = CF Ending Cash (each year)
- Extract debt maturity schedule from notes
- Extract D&A detail or useful life assumptions
- Note any non-recurring / one-time items to normalize

### Handling Common Filing Variations

| Variation | How to Handle |
|-----------|---------------|
| D&A embedded in COGS/SG&A | Pull D&A from Cash Flow Statement |
| "Other" line items are material | Check notes for breakdown |
| Restatements | Use restated figures, note in assumptions |
| Fiscal year ≠ calendar year | Label with fiscal year end (e.g., FYE Jan 2025) |
| Non-EUR reporting currency | Adapt model currency to match filing |
