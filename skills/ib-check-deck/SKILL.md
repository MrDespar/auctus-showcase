---
name: ib-check-deck
description: Investment banking presentation quality checker. Reviews a pitch deck or client-ready presentation for (1) number consistency across slides, (2) data-narrative alignment, (3) language polish against IB standards, (4) financial formatting and sourcing, (5) visual and formatting QC. Use whenever the user asks to review, check, QC, proof, or do a final pass on a deck, pitch, or client materials — including requests like "check my numbers", "reconcile figures across slides", "is this client-ready", or "what am I missing before I send this out".
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
version: 1.1
---

# IB Deck Checker

Perform comprehensive QC on the presentation across five dimensions. Read every slide, then report findings.

## Environment check

This skill works in both the PowerPoint add-in and chat. Identify which you're in before starting:

- **Add-in** — read from the live open deck.
- **Chat** — read from the uploaded `.pptx` file.

This is read-and-report only — no edits — so the workflow is identical in both.

## Workflow

### Read the deck

Pull text from every slide, keeping track of which slide each line came from. You'll need slide-level attribution for every finding ("$500M appears on slides 3 and 8, but slide 15 shows $485M"). A deck with 30 slides is too much to hold in working memory reliably — write the extracted text to a file so the number-checking script can process it.

The script expects markdown-ish input with slide markers. Format as:

```
## Slide 1
[slide 1 text content]

## Slide 2
[slide 2 text content]
```

### 1. Number consistency & Calculations

Run the extraction script on what you collected:

```bash
python skills/ib-check-deck/scripts/extract_numbers.py /tmp/deck_content.md --check
```

It normalizes units and flags when the same metric category shows conflicting values on different slides. 

Beyond what the script flags, manually verify calculations:
- Totals and subtotals must sum correctly (e.g., in a capital structure or use of funds table).
- Percentages must add up to 100% where applicable.
- Growth rates (CAGR, YoY) must match the underlying endpoints.

### 2. Data-narrative alignment

Map claims to the data that's supposed to support them.
- Trend statements ("declining margins") → does the chart actually go that direction?
- Market position claims ("#1 player") → revenue and share data support it?
- Plausibility — "#1 in a $100B market" with $200M revenue is 0.2% share; that's not #1.

### 3. Financial Formatting Conventions

Ensure strict adherence to financial presentation standards and AUCTUS rules:
- **Currency & Units**: All monetary values must be in EUR millions, denoted as `€m` (per AUCTUS rules). Flag any use of `$`, `MM`, `M`, or other currencies unless explicitly requested as a non-core exception.
- **Negative Numbers**: Must be enclosed in parentheses, e.g., `(15.0)` instead of `-15.0`.
- **Date Conventions**: Ensure consistent use of historical vs projected periods (e.g., `FY22A`, `FY23E`).
- **Metric Precision**: Ensure clear distinction between `EBITDA` and `Adj. EBITDA`.

### 4. Language polish & Proofreading

IB decks have a professional register. Scan for anything that breaks it: casual phrasing, contractions, exclamation points, vague quantifiers.
- See `references/ib-terminology.md` for replacement patterns.
- **Proofreading**: Scan for typographical errors, double spaces, and spelling mistakes. Ensure consistent bullet punctuation (either all bullets end with a period, or none do). Verify consistent title capitalization (e.g., Title Case vs Sentence case). Define acronyms on first use.

### 5. Visual, Sourcing, and Formatting QC

Run standard visual verification checks on each slide:
- **Footnote & Sourcing Tie-out**: Verify every chart, table, and external data point has a source citation. Check that footnote numbers in the text correctly correspond to the footnotes at the bottom of the slide.
- **Formatting QC**: Look for typography inconsistencies, number formatting drift, date format drift, orphaned text, missing axis labels, overlaps, and contrast issues.

## Quality Rubric

Apply this rubric to guarantee client-ready output:
- **Number Consistency**: Are all figures across slides identical and mathematically sound?
- **Narrative Alignment**: Does the text accurately reflect the data charts and tables?
- **Financial Formatting**: Are negative numbers in parentheses? Is the currency `€m`? Are dates labeled with `A` or `E`?
- **Sourcing**: Are all external data points and charts properly sourced with matching footnotes?
- **Language & Proofing**: Is the tone professional? Are bullet styles, spacing, and capitalization consistent?

## Correct Patterns

When validating findings, use these patterns:

**Checking Dates & Periods**:
- *Correct*: `FY22A`, `FY23E`, `LTM Q3'23`
- *Incorrect*: `2022`, `23 est.`, `last 12 months`

**Checking Currencies (AUCTUS Standard)**:
- *Correct*: `€15.5m`, `€250m`
- *Incorrect*: `15.5M EUR`, `€15.5MM`, `$20m`

**Checking Negatives**:
- *Correct*: `(4.2%)`, `€(10.5)m`
- *Incorrect*: `-4.2%`, `-€10.5m`

**Growth Metrics**:
- *Correct*: `CAGR`, `YoY`
- *Incorrect*: `CAGR growth`, `year over year`

## Output

Use `references/report-format.md` as the structure. Categorize by severity:

- **Critical** — number mismatches, calculation errors, factual errors, data contradicting narrative. These block client delivery.
- **Important** — language, missing sources, financial formatting drift, terminology issues. Should fix.
- **Minor** — font sizes, spacing, bullet punctuation, date formats. Polish.

Lead with criticals. If there aren't any, say so explicitly — "no number inconsistencies found" is a finding, not an absence of one.
