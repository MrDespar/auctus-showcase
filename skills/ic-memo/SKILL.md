---
name: ic-memo
version: "2.1.0"
description: >
  Generates a formal Investment Committee Memorandum (14-section AUCTUS format) in Word
  (.docx) as primary deliverable, from deterministic model artifacts. Extends Anthropic's
  canonical IC memo format with standard PE sections (DD, MEP, ESG, Exit, VCP). All financial figures sourced
  exclusively from Python script outputs — no LLM-computed numbers.
triggers:
  - "generate IC memo"
  - "write IC memo"
  - "investment committee memo"
  - "IC memorandum"
  - "committee paper"
  - "investment brief"
  - "deal write-up"
  - "prepare IC materials"
  - "recommendation memo"
inputs:
  required:
    - "company_name — full legal name of the target company"
  optional:
    - "lbo_compact — path to LBO compact JSON (outputs/dcf_models/lbo_*_lbo_compact.json)"
    - "dcf_results — path to DCF results JSON (outputs/dcf_models/*_dcf_results.json)"
    - "target_matrix — path to target matrix Excel (outputs/target_matrices/*_targets.xlsx)"
    - "sector — sector description (default: B2B Services)"
    - "analyst — attribution string (default: AUCTUS Deal Team)"
    - "--word — flag to also generate Word (.docx)"
    - "--pdf — flag to generate PDF via pandoc/xelatex"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"

  - "outputs/ic_memos/ic_memo_{slug}_{YYYYMMDD_HHMMSS}.docx  ← PRIMARY DELIVERABLE"
  - "outputs/ic_memos/ic_memo_{slug}_{YYYYMMDD_HHMMSS}.md  ← quick review only"
  - "outputs/ic_memos/ic_memo_{slug}_{YYYYMMDD_HHMMSS}.pdf  ← optional, if pandoc available"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG produces IC memos in **Word (.docx)** format as the primary
deliverable. Markdown is permitted for quick review only. All financial tables (returns,
EV bridge, S&U) must tie — the memo generator script enforces this via balance checks.

### Prerequisites

All three model workflows should be complete before drafting the memo:
- `/lbo-modeling` → provides LBO compact JSON (entry EV, MOIC, IRR, sensitivity)
- `/dcf-valuation` → provides DCF results JSON (NPV, WACC, terminal value)
- `/competitor-analysis` or `/screen-deal` → provides target matrix (AUCTUS scoring)

If any of these model artifacts are missing, do NOT halt and ask the user for them or run in partial mode. Instead, you MUST proactively execute the missing upstream skills (`/lbo-modeling`, `/dcf-valuation`, `/competitor-analysis`) to generate the required dependencies before drafting the memo.

### Data Source Hierarchy

- **All financial figures MUST come from Python script outputs** (LBO JSON, DCF JSON, target matrix)
- **Never compute financial figures in LLM context** — not even rough estimates
- If a required figure is missing from model outputs, state "Data not yet modeled — run [workflow]"

### Currency & Units

All monetary values in **EUR millions (€m)**. IRR: `0.0%`. MOIC: `0.0×`. EV: `€m`.

### AUCTUS-Specific Rules

**14-section structure + conditional appendix** (AUCTUS standard — extends Anthropic's 9-section format):

| # | Section | Source data |
|---|---------|-------------|
| 1 | Executive Summary | All model outputs |
| 2 | Company Overview | User-supplied or target matrix |
| 3 | Management & Equity Incentives (MEP) | Deal terms & structure |
| 4 | Industry & Market | Sector context |
| 5 | Due Diligence Summary | 3rd-party DD reports (FDD, CDD, LDD, TDD) |
| 6 | Financial Analysis | DCF cashflows Excel + LBO projections Excel |
| 7 | Investment Thesis & Value Creation Plan | Sector context + Buy-and-build strategy |
| 8 | Deal Terms & Structure | LBO compact JSON → entry EV, equity, debt |
| 9 | Returns Analysis | DCF EV + LBO MOIC/IRR |
| 10| Exit Strategy | Strategic & Sponsor buyer universe |
| 11| ESG & Sustainability | ESG DD & SFDR compliance |
| 12| Risk Factors | Derived from model outputs |
| 13| Recommendation | Combined signal from all models |
| 14| Appendix — Model Assumptions | All parameter inputs used (only if model was run) |

**Quality gate**: All 13 sections (and the 14th Appendix if LBO/DCF model run) must be present in the output.
Word (.docx) file must be >1,000 bytes.

**Balance checks** (enforced by script, not manually):
- S&U table: sources = uses (within ±€0.01m)
- EBITDA bridge: values tie to LBO projection model
- Returns math: IRR / MOIC consistent with LBO compact JSON

**Balanced presentation**: IC members will find risks themselves. Present bull and bear
cases honestly. Do not minimize risks to support the recommendation.

**Missing inputs**: Ask for them before proceeding; do not make assumptions on deal terms
or returns figures.

---

## STEP 1 — LOCATE MODEL ARTIFACTS

Find the most recent output files for the target company:

```bash
ls -t outputs/dcf_models/lbo_{slug}_*_lbo_compact.json | head -1
ls -t outputs/dcf_models/{slug}_*_dcf_results.json     | head -1
ls -t outputs/target_matrices/*_targets.xlsx           | head -1
```

Record the resolved paths. If no LBO compact JSON is found, check whether a DCF results
JSON exists alone — the memo generator can operate in DCF-only mode. If neither model
artifact is found, stop and ask the user to run the relevant valuation workflow first.

## STEP 2 — GENERATE MEMO

Compile the memo document natively in context based on the model artifacts retrieved. Use python-docx or markdown to write the .docx file if possible.

```bash
pandoc outputs/ic_memos/{memo_file}.md \
  -o outputs/ic_memos/{memo_file}.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2.5cm \
  -V fontsize=11pt
```

## STEP 4 — QUALITY GATE

Run: `pytest tests/test_memo_generator.py -v --tb=short`
Must exit 0.
Verify:
  - Output Word (.docx) is non-empty (>1,000 bytes)
  - All 13 section headers + conditional Appendix are present:
    1. Executive Summary, 2. Company Overview, 3. Management & Equity Incentives (MEP),
    4. Industry & Market, 5. Due Diligence Summary, 6. Financial Analysis,
    7. Investment Thesis & Value Creation Plan, 8. Deal Terms & Structure,
    9. Returns Analysis, 10. Exit Strategy, 11. ESG & Sustainability,
    12. Risk Factors, 13. Recommendation,
    (14. Appendix — Model Assumptions if model run)

Append completion entry to `logs/agent_activity.log`.

## QUALITY RUBRIC

- **Due Diligence Coverage**: Summarizes findings across FDD (QoE, NWC, Net Debt), CDD, LDD, and TDD. Flags any deal-breakers.
- **MEP Sizing**: Clearly defines management rollover, sweet equity allocation, and vesting terms (time/performance).
- **Value Creation & Buy-and-Build**: Details 100-day plan, identified operational levers, and a quantified add-on target pipeline (crucial for AUCTUS).
- **Exit Strategy**: Outlines specific strategic buyers and financial sponsors for a hypothetical exit in Year 4/5, including expected exit multiples.
- **ESG Compliance**: Assesses SFDR Article 8/9 classification, climate risks, and governance gaps.

## CORRECT PATTERNS

```python
# Pattern: Using python-docx to generate sectioned Word documents robustly
from docx import Document
from docx.shared import Pt

def add_ic_section(doc: Document, title: str, content: str, level: int = 1):
    heading = doc.add_heading(title, level=level)
    # Ensure headings stay with the next paragraph
    heading.paragraph_format.keep_with_next = True
    for paragraph in content.split('\n\n'):
        if paragraph.strip():
            p = doc.add_paragraph(paragraph.strip())
            p.style.font.size = Pt(10)

# Pattern: Parsing JSON inputs safely and injecting into memo
import json
def inject_exit_strategy():
    try:
        with open('outputs/dcf_models/lbo_compact.json', 'r') as f:
            lbo_data = json.load(f)
        exit_mult = lbo_data.get('exit_multiple', 'N/A')
    except Exception:
        exit_mult = 'N/A'
    
    return f"Projected Exit Multiple: {exit_mult}x\nPotential Strategic Acquirers: [...]"
```

## EXIT CONDITION

Deliver paths to:
  1. Word memo (.docx) — PRIMARY
  2. Markdown IC memo — quick review
  3. PDF (if pandoc was available)

State explicitly: company name, run date, which model inputs were used (LBO / DCF / target matrix).

---

# Investment Committee Memo (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.
> Key AUCTUS addition beyond Anthropic's 9 sections: Appendix — Model Assumptions (conditional).

## Workflow

### Step 1: Gather Inputs

Collect from the user (or from prior analysis in the session):

- Company overview and business description
- Industry/market context
- Historical financials (3-5 years)
- Management assessment
- Deal terms (price, structure, financing)
- Due diligence findings (commercial, financial, legal, operational)
- Value creation plan / 100-day plan
- Returns analysis (base, upside, downside)

### Step 2: Draft Memo Structure

Standard IC memo format:

**I. Executive Summary** (1 page)
- Company description, deal rationale, key terms
- Recommendation and headline returns
- Top 3 risks and mitigants

**II. Company Overview** (1-2 pages)
- Business description, products/services
- Customer base and go-to-market
- Competitive positioning
- Management team

**III. Industry & Market** (1 page)
- Market size and growth
- Competitive landscape
- Secular trends / tailwinds
- Regulatory environment

**IV. Financial Analysis** (2-3 pages)
- Historical performance (revenue, EBITDA, margins, cash flow)
- Quality of earnings adjustments
- Working capital analysis
- Capex requirements

**V. Investment Thesis** (1 page)
- Why this is an attractive investment (3-5 pillars)
- Value creation levers (organic growth, margin expansion, M&A, multiple expansion)
- 100-day priorities

**VI. Deal Terms & Structure** (1 page)
- Enterprise value and implied multiples
- Sources & uses
- Capital structure / leverage
- Key legal terms

**VII. Returns Analysis** (1 page)
- Base, upside, and downside scenarios
- IRR and MOIC across scenarios
- Key assumptions driving returns
- Sensitivity analysis

**VIII. Risk Factors** (1 page)
- Key risks ranked by severity and likelihood
- Mitigants for each risk
- Deal-breaker risks (if any)

**IX. Recommendation**
- Clear recommendation: Proceed / Pass / Conditional proceed
- Key conditions or next steps

### Step 3: Output Format

- Default: Word document (.docx) with professional formatting
- Alternative: Markdown for quick review
- Include tables for financials and returns, not just prose

## Important Notes

- IC memos should be factual and balanced — present both bull and bear cases honestly
- Don't minimize risks. IC members will find them anyway; credibility matters
- Use the firm's standard memo template if the user provides one
- Financial tables should tie — check that EBITDA bridges, S&U balances, and returns math is consistent
- Ask for missing inputs rather than making assumptions on deal terms or returns
