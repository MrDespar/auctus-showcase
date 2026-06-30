---
name: deck-refresh
version: 0.1
description: Updates a presentation with new numbers — quarterly refreshes, earnings updates, comp rolls, rebased market data. Use whenever the user asks to "update the deck with Q4 numbers", "refresh the comps", "roll this forward", "swap in the new earnings", "change all the €485m to €512m", or any request to swap figures across an existing deck without rebuilding it.
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
---

# Deck Refresh

Update numbers across the deck. The deck is the source of truth for formatting; you're only changing values.

## Environment check

This skill works in both the PowerPoint add-in and chat. Identify which you're in before starting — the edit mechanism differs, the intent doesn't:

- **Add-in** — the deck is open live; edit text runs, table cells, and chart data directly.
- **Chat** — the deck is an uploaded file; edit it by regenerating the affected slides with the new values and writing the result back.

Either way: smallest possible change, existing formatting stays intact.

This is a four-phase process and the third phase is an approval gate. Don't edit until the user has seen the plan.

## Phase 1 — Get the data

Use `ask_user_question` to find out how the new numbers are arriving:

- **Pasted mapping** — user types or pastes "revenue €485m → €512m, EBITDA €120m → €135m." The clearest case. Ensure mapping respects AUCTUS €m standard.
- **Uploaded Excel** — old/new columns, or a fresh output sheet the user wants pulled from. Read it, confirm which column is which before you trust it.
- **Just the new values** — "Q4 revenue was €512m, margins were 22%." You figure out what each one replaces. Workable, but confirm the mapping before you touch anything.

Also check for **Dates & Periods**: Explicitly ask what the new "As of" date is, what the new period headers should be (e.g., Q3'23 to Q4'23), and what source dates should read.
Also ask about **derived numbers & arithmetic**: if revenue and COGS move, gross profit changes. Margins, CAGRs, and multiples will shift. Ask the user if they want you to automatically propose these recalculations in the plan (the standard IB/PE approach) or leave them alone.

## Phase 2 — Read everything, find everything

Read every slide. For each old value, find every instance — including the ones that don't look the same:

| Variant | Example |
|---|---|
| Scale | `€485m`, `€0.485bn`, `€485,000,000` |
| Precision | `€485m`, `€485.0m`, `~€485m` |
| Unit style | `€485m`, `€485mm`, `€485 million`, `485m` |
| Embedded | "revenue grew to €485m", "a €485m business", axis labels |

*Note: Enforce EUR millions (€m) in all output per AUCTUS overlay.*

A deck that says `€485m` on slide 3, `485` on slide 8's chart axis, and `€485.0 million` in a footnote on slide 15 has three instances of the same number. Find-replace misses two of them. You shouldn't.

**Where numbers & dates hide:**
- Text boxes and Table cells
- Chart data labels, axis labels, and underlying chart source data
- Footnotes, source lines, small print (e.g., "Source: Company data as of [Date]")
- Column/Row headers (e.g., "2023E", "LTM Sep-23")
- Speaker notes, if the user cares about those

**Arithmetic Integrity (IB Standard)**: Do not just find-replace. Check the math. If inputs change, recalculate new totals, subtotals, margins, and multiples to propose in the next step.

Build a list: for each old value, every location it appears, the exact text it appears as, and what it'll become. This list is the plan.

## Phase 3 — Present the plan, get approval

**This is a destructive operation on a deck someone spent time on.** Show the full change list before editing a single thing. Format it so it's scannable:

```
€485m → €512m (Revenue)
  Slide 3  — Title box: "Revenue grew to €485m"
  Slide 8  — Chart axis label: "485"
  Slide 15 — Footnote: "€485.0 million in FY24 revenue"

Dates & Headers Roll-forward:
  Slide 3, 5, 8 — Column header: "Q3'23" → "Q4'23"
  Slide 15 — Source date: "as of Sep 2023" → "as of Dec 2023"

PROPOSED DERIVED UPDATES (Arithmetic Integrity):
  Slide 3  — Gross Profit: €200m → €215m (Calculated from new Rev & COGS)
  Slide 3  — EBITDA Margin: 24.7% → 26.3% (Calculated)
  Slide 3  — "+15% YoY" → "+17% YoY" (Calculated based on new €512m base)

FLAGGED NARRATIVE — text no longer matches numbers:
  Slide 7 — "margins compressed" (New margin actually expanded to 26.3%. Propose changing to "margins expanded")
```

The flagged/proposed section matters. You're catching the second-order effects the user would've missed at 11pm. If the mapping says `€485m → €512m`, the corresponding growth rate is probably wrong now. Flag it and propose the recalculated number; don't silently leave it.

Use `ask_user_question` for the approval: proceed as shown, proceed but skip the flagged items, or let them revise the mapping first.

## Phase 4 — Execute, preserve, report

For each change, make the smallest edit that accomplishes it. How that happens depends on your environment:

- **Add-in** — edit the specific run, cell, or chart series directly in the live deck.
- **Chat** — regenerate the affected slide with the new value in place, preserving every other element exactly as it was, and write it back to the file.

Either way, the standard is the same:

- **Text in a shape** — change the value, leave font/size/color/bold state exactly as they were. If `€485m` is 14pt navy bold inside a sentence, `€512m` is 14pt navy bold inside the same sentence.
- **Table cell** — change the cell, leave the table alone. Ensure rounded parts sum to the rounded total.
- **Chart data** — update the underlying series values. *Crucially, check the chart axis bounds. If the new data exceeds the old hardcoded max/min bounds, adjust the axis bounds accordingly to provide ~10% headroom.*

Don't reformat anything you didn't need to touch. The deck's existing style is correct by definition; you're a surgeon, not a renovator.

After the last edit, report what actually happened:

```
Updated 11 values across 8 slides.

Changed:
  [the list from Phase 3, now past-tense]

Still flagged — did NOT change:
  Slide 7 — "12% market share" (derived; confirm separately)
```

Run standard visual verification checks on every edited slide:
- **Overflow**: A number that got longer (`€485m` → `€1,205m`) might push a table column width.
- **Chart Bounds**: Verify bars/lines aren't breaking out of the plot area.

## What you're not doing

- **Not recalculating without permission** — derived numbers are the user's call. You propose, they approve.
- **Not touching formatting** — Values change; style stays. 

## Correct Patterns

**Handling Axis Adjustment:**
```python
# BAD: Leaving axis as is, bar will break out of chart
chart.series[0].values = new_values

# GOOD: Adjusting the axis max to provide ~10% headroom
chart.series[0].values = new_values
chart.value_axis.maximum_scale = max(new_values) * 1.1
```

**Handling Rounding Plugs:**
```python
# When displaying rounded parts that must sum to a rounded total
parts = [10.4, 20.4] # True sum = 30.8
rounded_parts = [10, 20] # Sum = 30
rounded_total = 31 # round(30.8)
# Add plug to largest part to fix
rounded_parts[1] += (rounded_total - sum(rounded_parts)) # [10, 21]
```

## Quality Rubric

- **Date Completeness**: Did you identify and update all "as of" dates, column headers, and source footnotes?
- **Arithmetic Integrity**: Did you recalculate all totals, subtotals, margins, multiples, and CAGRs affected by base value changes?
- **Chart Integrity**: Did you update the underlying chart data (not just labels) and scale the axes appropriately?
- **Narrative Consistency**: Did you flag and propose updates for text descriptors (e.g., "grew", "compressed") invalidated by new numbers?
- **AUCTUS Overlay**: Are all monetary values in EUR millions (€m)?
