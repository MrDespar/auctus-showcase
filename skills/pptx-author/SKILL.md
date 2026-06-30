---
name: pptx-author
version: "1.1.0"
description: >
  Produces a .pptx presentation on disk using python-pptx for AUCTUS Capital Partners AG.
  Governs branding conventions, file naming, and LibreOffice validation for all AUCTUS
  PowerPoint deliverables (investment pitch decks).
triggers:
  - "build deck"
  - "write pptx"
  - "create presentation"
  - "python-pptx"
  - "pptx output"
  - "generate PowerPoint"
inputs:
  optional:
    - "company_name — for file naming and cover slide"
    - "template_path — path to firm .pptx template (default: no template)"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/pitch_decks/pitch_{company}_{YYYYMMDD_HHMMSS}.pptx"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG is a DACH-focused mid-market private equity firm. All PowerPoint
decks are generated headlessly via python-pptx. No Microsoft Office is available in this
environment. Validation is done with LibreOffice (soffice). This skill governs all AUCTUS
pitch deck authoring conventions.

### Prerequisites

None. Called by `/pitch-deck` as a sub-step. Not invoked directly by the user.

### Data Source Hierarchy

1. **FactSet MCP** — primary source for any market or financial data on slides
2. **User-provided data** — LBO compact JSON, DCF results JSON, target matrix outputs
3. **Web search / fetch** — fallback only

**NEVER** compute or estimate financial figures for slides in LLM context. All numbers
must come from `outputs/dcf_models/` or `outputs/target_matrices/` artifacts.

### Currency & Units

- All monetary values in **EUR millions (€m)** unless explicitly stated otherwise
- Ratios: `0.0x`; Percentages: `0.0%`; Negatives: `(€X.Xm)` — parentheses, no minus sign

### Execution Environment

- **python-pptx only** — no Office JS, no live PowerPoint session
- Output path: `outputs/pitch_decks/pitch_{slug}_{YYYYMMDD_HHMMSS}.pptx`
- Validate with LibreOffice before delivery:
  ```bash
  soffice --headless --convert-to pdf presentation.pptx
  pdftoppm -jpeg -r 150 presentation.pdf slide
  ```
- Always include disclaimer: *"This file was validated using LibreOffice. Please review
  in Microsoft PowerPoint before distribution, as rendering differences may exist."*

### AUCTUS Branding

| Element | Color | Notes |
|---------|-------|-------|
| Header bars | `#1F4E79` dark blue | White bold text |
| Accent / highlights | `#BDD7EE` medium blue | Key metrics |
| Body text | `#000000` black | Dark bg → white text |
| Background (body) | `#FFFFFF` white | Standard slides |
| Slide dimensions | 33.87cm × 19.05cm | 16:9 widescreen |

- **One idea per slide.** Slide title states the takeaway; body supports it.
- **Every number traces to the model.** Figures from JSON artifacts must be cited by source key.
- **10 slides exactly** for the standard AUCTUS pitch deck. Do not add or remove slides.
- **No external sends.** This skill writes a file; it never emails or uploads.

### AUCTUS-Specific Rules

- File naming: `pitch_{slug}_{YYYYMMDD_HHMMSS}.pptx`
- Quality gate: `pytest tests/test_deck_builder.py -v --tb=short` must exit 0
- Deck must have exactly 10 slides (see `/pitch-deck` SKILL.md for slide manifest)

### Quality Rubric

- **Native Editable Charts**: All financial charts (column, bar, waterfall, football field) MUST be native `python-pptx` chart objects with underlying workbook data, NEVER static PNGs, ensuring partners can edit numbers directly in PowerPoint.
- **Table Formatting**: Header rows must be shaded with AUCTUS Dark Blue (`#1F4E79`) with white bold text. Financial numbers must be right-aligned; text labels left-aligned. Table borders must use standard thin lines.
- **Footnotes & Sources**: Every slide containing market or financial data must have a source footnote positioned at the bottom left, formatted in 8pt italic text.
- **Text Formatting**: Text boxes must have proper vertical alignment (Top/Middle) and clear margins per standard IB formatting.

### Correct Patterns

**1. Native Chart Generation (Editable)**
*Overrides the default Anthropic fallback of static PNGs. Use native charts for financial data:*
```python
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData
from pptx.util import Inches

chart_data = CategoryChartData()
chart_data.categories = ['2023A', '2024E', '2025E']
chart_data.add_series('Revenue', (100.5, 115.0, 130.2))

x, y, cx, cy = Inches(0.5), Inches(2), Inches(6), Inches(4)
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, chart_data
).chart
```

**2. Standardized Table Formatting**
*Ensure financial tables meet IB/PE standards (right-aligned numbers, styled headers):*
```python
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

table = slide.shapes.add_table(rows=2, cols=2, x=Inches(0.5), y=Inches(2), cx=Inches(6), cy=Inches(1)).table

# Style header
header_cell = table.cell(0, 0)
header_cell.text = "Metric"
header_cell.fill.solid()
header_cell.fill.fore_color.rgb = RGBColor(31, 78, 121) # #1F4E79
header_cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)

# Align numbers right
num_cell = table.cell(1, 1)
num_cell.text = "€ 100.5m"
num_cell.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
```

**3. Source and Footnote Placement**
*Standardized placement for source citations:*
```python
from pptx.util import Pt
txBox = slide.shapes.add_textbox(x=Inches(0.5), y=Inches(7.0), cx=Inches(9), cy=Inches(0.5))
tf = txBox.text_frame
p = tf.paragraphs[0]
p.text = "Source: FactSet, Company Filings, AUCTUS Analysis."
p.font.size = Pt(8)
p.font.italic = True
```

---

# pptx-author (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

Use this skill when running **headless** (managed-agent / CMA mode) and you need to deliver a PowerPoint deck as a **file artifact** rather than editing a live document via `mcp__office__powerpoint_*`.

## Output contract

- Write to `./out/<name>.pptx`. Create `./out/` if it does not exist.
- Return the relative path in your final message so the orchestration layer can collect it.

## How to build the deck

Write a short Python script and run it with Bash. Use `python-pptx`:

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation("./templates/firm-template.pptx")  # if a template is provided
# or: prs = Presentation()

slide = prs.slides.add_slide(prs.slide_layouts[5])    # title-only
slide.shapes.title.text = "Valuation Summary"
# ... add tables / charts / text boxes ...

prs.save("./out/pitch-<target>.pptx")
```

## Conventions (mirror the live-Office `pitch-deck` skill)

- **One idea per slide.** Title states the takeaway; body supports it.
- **Every number traces to the model.** If a figure comes from `./out/model.xlsx`, footnote the sheet and cell.
- **Use the firm template** when one is mounted at `./templates/`; otherwise default layouts.
- **Charts**: prefer embedding a PNG rendered from the model over native pptx charts when fidelity matters.
- **No external sends.** This skill writes a file; it never emails or uploads.

## When NOT to use

If `mcp__office__powerpoint_*` tools are available (Cowork plugin mode), use those instead — they drive the user's live document with review checkpoints. This skill is the file-producing fallback for headless runs.
