---
name: xlsx-author
version: "1.1.0"
description: >
  Produces a .xlsx workbook on disk using Python/openpyxl for AUCTUS Capital Partners AG.
  All arithmetic is delegated to deterministic Python scripts; this skill governs workbook
  structure, color conventions, and output path conventions for every AUCTUS Excel deliverable.
triggers:
  - "write Excel"
  - "build workbook"
  - "create xlsx"
  - "generate Excel"
  - "openpyxl"
  - "xlsx output"
inputs:
  optional:
    - "company_name — for file naming"
    - "workflow — for output path and filename prefix (dcf, lbo, comps, etc.)"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/{workflow_folder}/{workflow}_{company}_{YYYYMMDD_HHMMSS}.xlsx"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG is a DACH-focused mid-market private equity firm. All Excel
workbooks are generated headlessly via Python/openpyxl. No Microsoft Office or Office JS
is available in this environment. This skill governs workbook authoring conventions for
every AUCTUS Excel deliverable.

### Prerequisites

None. This skill is called by other skills as a sub-step when Excel output is required.
It is not invoked directly by the user.

### Data Source Hierarchy

1. **FactSet MCP** — primary source for market data, financials, comparables
2. **User-provided data** — uploaded files, copy-pasted inputs, stated figures
3. **Web search / fetch** — fallback only when FactSet is unavailable

**NEVER** compute financial figures in LLM context. All calculations come from Python scripts.

### Currency & Units

- All monetary values in **EUR millions (€m)** unless explicitly stated otherwise
- EUR values: **2 decimal places**. Ratios/rates: **1 decimal place** (`0.0%`, `0.0x`)
- Negatives formatted as `(#,##0)` — parentheses, never minus sign
- Currency symbol: `€` (not `$`)

### Execution Environment

- **Python/openpyxl only** — no Office JS, no live Excel session
- Write formula strings to cells, never pre-computed Python values:
  ```python
  ws["C5"] = "=C4*(1+Assumptions!$B$5)"   # correct
  ws["C5"] = 12.5                           # NEVER do this
  ```
- Output path: `outputs/{workflow_folder}/{workflow}_{company}_{YYYYMMDD_HHMMSS}.xlsx`
  - DCF/sensitivity: `outputs/dcf_models/`
  - Comps/valuation: `outputs/valuation_reports/`
  - Target matrices: `outputs/target_matrices/`
  - LBO models: `outputs/dcf_models/`
  - IC memos: `outputs/ic_memos/`
  - Pitch decks: `outputs/pitch_decks/`

### AUCTUS-Specific Rules

- **File naming**: `{workflow}_{company}_{YYYYMMDD_HHMMSS}.xlsx` (never unnamed or generic)
- **Checks tab required** on all integrated financial models — includes `balance_check_eur_m`
  for LBO models (must be within ±€0.01m of zero)
- **Sensitivity grids**: 5×5 ODD dimensions only; center cell = base case highlighted `#BDD7EE`
- Run `pytest tests/test_{script}.py -v --tb=short` before declaring output complete

### IB/PE Standard Formatting Requirements
To meet vanilla IB/PE standards, workbooks must include the following advanced formatting and structure:
- **Proper Number Formats**: Use custom number strings. For example: `_(* #,##0.0_);_(* (#,##0.0);_(* "-"_);_(@_)` for EUR amounts, and `0.0%` for percentages.
- **Borders & Styling**: Top and bottom borders for totals. Double bottom borders for grand totals.
- **Layout & Panes**: Column A must be narrow (width ~2-3) as a spacer. Freeze panes (e.g., freeze at cell `C6`) so that row labels and column headers stay visible when scrolling.
- **Worksheet Structure**: Explicit separation:
  - **Cover**: Company name, project name, currency/units, date, and a scenario toggle (if applicable).
  - **Assumptions/Inputs**: All hardcoded drivers (Blue font).
  - **Scenarios/Cases**: If multiple cases, use a Scenario switch (e.g., `CHOOSE` or `INDEX/MATCH`) linked to a named range on the Cover.
  - **Calculations/Model**: The core build.
  - **Outputs/Dashboard**: Formatted summaries for export.
- **Grouping**: Group columns for historical vs. projected years. Group rows to keep the sheet clean.

---

# xlsx-author (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

Use this skill when running **headless** (managed-agent / CMA mode) and you need to deliver an Excel workbook as a **file artifact** rather than editing a live workbook via `mcp__office__excel_*`.

## Quality Rubric
A senior associate will review your work against this rubric:
1. **Separation of Concerns**: Are inputs on a separate tab or strictly isolated from calculations?
2. **Formatting**: Is column A a narrow spacer? Are panes frozen appropriately? Are row groups applied for historical vs projected periods?
3. **Number Formats**: Are custom formats applied (accounting style with hyphens for zeroes)?
4. **Borders**: Do subtotals have a single top/bottom border, and grand totals have a double bottom border?
5. **Scenario Manager**: Is there a functional scenario toggle driving the base/upside/downside cases?
6. **Blue/Black/Green Conventions**: Are fonts colored perfectly? (Blue for hardcodes, Black for calculations, Green for sheet links).

## Correct Patterns (openpyxl)

Where openpyxl implementation is non-obvious, follow these patterns:

```python
# 1. Spacer Column and Freeze Panes
ws.column_dimensions['A'].width = 3.0
ws.column_dimensions['B'].width = 35.0
ws.freeze_panes = "C6" # Freezes rows 1-5 and columns A-B

# 2. Accounting Number Format
from openpyxl.styles import NamedStyle
accounting_style = NamedStyle(name="accounting", number_format='_(* #,##0.0_);_(* (#,##0.0);_(* "-"_);_(@_)')
ws["C10"].style = accounting_style

# 3. Borders for Totals
from openpyxl.styles import Border, Side
top_border = Side(border_style="thin", color="000000")
bottom_border = Side(border_style="thin", color="000000")
double_bottom = Side(border_style="double", color="000000")

total_border = Border(top=top_border, bottom=bottom_border)
grand_total_border = Border(top=top_border, bottom=double_bottom)
ws["C20"].border = total_border

# 4. Grouping Columns (e.g., historical years)
ws.column_dimensions.group('C', 'E', hidden=False)
```

## Output contract

- Write to `./out/<name>.xlsx`. Create `./out/` if it does not exist.
- Return the relative path in your final message so the orchestration layer can collect it.

## How to build the workbook

Write a short Python script and run it with Bash. Use `openpyxl`:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
ws = wb.active; ws.title = "Inputs"
ws["B2"] = "Revenue"; ws["C2"] = 1_250_000_000
ws["C2"].font = Font(color="0000FF")           # blue = hardcoded input
calc = wb.create_sheet("DCF")
calc["C5"] = "=Inputs!C2*(1+Inputs!C3)"        # black = formula
wb.save("./out/model.xlsx")
```

## Conventions (mirror `audit-xls`)

- **Blue / black / green.** Blue = hardcoded input, black = formula, green = link to another sheet/file.
- **No hardcodes in calc cells.** Every calculation cell is a formula; every input lives on an Inputs tab.
- **Named ranges** for any value referenced from a deck or memo.
- **Balance checks.** Include a Checks tab that ties (BS balances, CF ties to cash, etc.) and surfaces TRUE/FALSE.
- **One model per file.** Do not append to an existing workbook unless explicitly asked.

## When NOT to use

If `mcp__office__excel_*` tools are available (Cowork plugin mode), use those instead — they drive the user's live workbook with review checkpoints. This skill is the file-producing fallback for headless runs.
