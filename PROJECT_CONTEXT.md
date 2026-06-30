# AUCTUS Intelligence Platform — Project Context

AUCTUS Capital Partners AG is the most successful PE firm in the German-speaking region by
track record (450+ majority investments, average 5× capital multiple). This platform is an
autonomous investment intelligence agent built on Claude Code that covers the full front-end
deal workflow — from first look to IC presentation — with no external SaaS dependencies.

---

## What It Is

A structured Claude Code skill library that an investment team invokes to automate research,
analysis, and deliverable generation for DACH mid-market PE. The agent (defined in `CLAUDE.md`
and `.agents/AGENTS.md`) orchestrates 22 self-contained skills, each with its own
instructions, data source hierarchy, output format, and quality rubric. Skills compose: a
single prompt triggers the agent, which chains `sector-overview` → `relative-valuation` →
`lbo-modeling` → `ic-memo` in sequence, surfacing for human approval at each artifact
boundary.

The platform is entirely LLM-native. There are no deterministic Python calculation engines —
all financial logic (DCF terminal value, LBO debt waterfalls, MOIC/IRR, 3-statement
balancing) is reasoned by the model and written to Excel as live formula strings, never as
pre-computed values. This preserves full cell-reference chains and audit trails.

---

## Active Skills (22)

**Research & Screening**
- `market-researcher` — TAM, growth drivers, competitive landscape, DACH market specifics
- `sector-overview` — market position narrative, strategic rationale, buy-and-build angle
- `screen-deal` — instant AUCTUS hard-filter check (€5–250m revenue, DACH, excluded sectors)
- `idea-generation` — surfaces acquisition targets matching a platform thesis
- `competitor-analysis` — peer mapping, positioning, scoring rubric

**Valuation**
- `dcf-valuation` — 8-sheet Excel workbook: WACC build, Bear/Base/Bull projections,
  normalised EBITDA add-backs, full EV-to-equity bridge, 4 sensitivity grids (v3.2.0)
- `lbo-modeling` — leveraged buyout with debt waterfall, sources & uses, MOIC/IRR, returns
- `relative-valuation` — trading comps and precedent transactions with AUCTUS peer filters
- `3-statement-model` — integrated P&L / balance sheet / cash flow projection
- `returns-analysis` — scenario MOIC and IRR across hold periods and exit assumptions
- `unit-economics` — revenue per customer, CAC, LTV, cohort analysis for SaaS/subscription

**Due Diligence**
- `dd-checklist` — structured commercial, financial, legal, and operational DD question set
- `value-creation-plan` — 100-day plan, operational improvement levers, buy-and-build roadmap

**Deliverables**
- `ic-memo` — 12-section Investment Committee Memorandum (.md / .docx)
- `pitch-deck` — branded AUCTUS PowerPoint with situation overview, football field, returns
- `deck-refresh` — updates an existing deck when model assumptions change
- `pitch-agent` — end-to-end pitch narrative from thesis to ask

**Infrastructure**
- `xlsx-author` — Excel workbook conventions (blue inputs / black formulas / green links,
  sensitivity grid formatting, named ranges)
- `pptx-author` — PowerPoint slide layout and shape conventions
- `audit-xls` — post-build formula integrity verification
- `ib-check-deck` — cross-checks that numbers are consistent across all deck slides
- `model-builder` — orchestrates valuation skill sequence for a full model build

---

## Slash Commands

16 slash commands in `.claude/commands/` map directly to skills for one-command invocation
inside Claude Code (`/screen-deal`, `/sector-overview`, `/ic-memo`, etc.).

---

## Hard Guardrails (enforced by CLAUDE.md)

| Rule | Value |
|---|---|
| Revenue range | €5m – €250m |
| Geography | DE, AT, CH only |
| Excluded sectors | Financial services, real estate, oil & gas |
| Currency | EUR millions throughout |
| Tax rates | DE 29.9% · AT 25.0% · CH 19.7% |
| Terminal growth ceiling | 4.0% (DACH nominal GDP) |
| Excel formulas | All derived cells are formula strings — zero hardcoded values |
| Data sourcing | FactSet primary · web fallback tagged [WEB] · never halt on data gap |

---

## What's Next

1. **FactSet MCP live integration** — the skill data source hierarchy already specifies
   FactSet as primary; connecting the MCP server will make historical financials, betas, and
   sector multiples flow in automatically without manual input.

2. **Portfolio monitoring skill** — a weekly agent run across AUCTUS's 450+ portfolio
   companies that flags operational signals (revenue deceleration, margin compression, NWC
   deterioration) worth attention. Scales what two analysts do manually across the whole book.

3. **Excel output via xlwings** — switching from openpyxl to xlwings for the valuation
   workbooks gives native autofit, real chart objects (including the football field), and
   true conditional formatting. The formula-string architecture stays identical; only the
   rendering layer changes.

4. **n8n workflow integration** — trigger the agent on inbound deal teasers (email/PDF
   upload) and route outputs back to the deal team's workflow automatically.
