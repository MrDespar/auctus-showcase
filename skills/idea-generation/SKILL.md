---
name: idea-generation
version: "1.1.0"
description: >
  Systematic investment idea sourcing and screening for AUCTUS Capital Partners AG. 
  Focuses on identifying private equity buyout platforms, buy-and-build opportunities, 
  and add-on acquisitions in the DACH mid-market.
triggers:
  - "idea generation"
  - "find ideas"
  - "what looks interesting"
  - "screen for targets"
  - "new ideas"
  - "pitch me a platform"
  - "market mapping"
inputs:
  optional:
    - "Deal Type: Platform, add-on, carve-out, roll-up"
    - "Theme/Sector: specific thematic angle or industry"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG uses this skill to proactively identify private equity buyout platforms and add-on acquisitions in the DACH mid-market.

### Data Source Hierarchy

1. **FactSet MCP** — primary for screening financials and identifying targets.
2. **User-provided data**
3. **Web search / fetch** — DACH registry sources (Creditreform, Bisnode, Handelsregister)

### AUCTUS-Specific Rules

**Hard Filters**:
- Revenue: €5m–€250m
- Geography: DACH (DE, AT, CH) primary; NL/BE/FR/IT/SE/DK/NO secondary.
- Excluded sectors: Financial services, real estate, oil & gas.
- Currency: EUR (€m).

**Screening Focus**:
We screen for buy-and-build platform potential or strategic add-ons. 
- High market fragmentation (top 5 share < 40%).
- Founder/family-owned or carve-outs preferred over VC/PE-backed.
- Strong EBITDA margins and cash conversion.

---

# Idea Generation (Private Equity & Investment Banking Standards)
> The complete IB/PE reference implementation follows below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Define Search Criteria

Ask the user for parameters:
- **Deal Type**: Platform buyout, add-on acquisition, carve-out, or growth equity
- **Target Size**: Enterprise Value, Revenue, or EBITDA ranges
- **Sector/Sub-sector**: Specific industries or niches
- **Ownership Structure**: Founder/family-owned, corporate orphan/carve-out, sponsor-to-sponsor (PE-owned)
- **Geography**: Primary regions and secondary expansion targets
- **Investment Theme**: Specific thematic angle (e.g., healthcare IT, industrial automation, succession planning)

### Step 2: Private Equity Screening Criteria

Run screens based on the deal type and thesis:

**Platform Buyout Screen**
- Stable, recurring or highly predictable revenue
- High EBITDA margins (>15%) and strong free cash flow conversion (>70%)
- Low customer and supplier concentration
- Defensible market position with high barriers to entry
- Low cyclicality and limited exposure to exogenous shocks
- Scalable platform with robust IT and management infrastructure

**Buy-and-Build (Roll-Up) Screen**
- Highly fragmented market (no clear dominant player, top 5 share < 40%)
- Multiple smaller targets available for add-on acquisitions
- Opportunities for multiple arbitrage (buying small at 5x, selling combined at 9x)
- Centralizable back-office synergies (IT, HR, finance, procurement)
- Standardized product or service offering

**LBO / Cash Cow Screen**
- Very stable cash flows with minimal volatility
- Low maintenance CapEx / Revenue (< 3%)
- Working capital efficiency
- Strong asset base for debt collateralization (tangible assets)
- Substantial debt capacity (can support 4.0x+ Net Debt / EBITDA)
- Opportunities for operational turnaround or cost rationalization

**Corporate Carve-Out Screen**
- Non-core divisions of large conglomerates
- Underperforming or ignored subsidiaries (margins below corporate average)
- Potential for margin expansion through standalone optimization
- Dedicated management teams (or easily installable interim leadership)

**Add-On Acquisition Screen**
- Direct competitors (horizontal integration for market share and pricing power)
- Supply chain targets (vertical integration to capture margin)
- Geographic expansion (entering new regional markets)
- Product/Service expansion (cross-selling capabilities to existing customer base)
- Revenue and cost synergy potential

### Step 3: Thematic Sweep & Market Mapping

For thematic ideas, research the theme and identify beneficiaries:
1. **Define the thesis** (e.g., "Aging demographics driving demand for specialized outpatient clinics")
2. **Map the value chain** — identify service providers, software vendors, and equipment manufacturers.
3. **Screen for fragmentation** — look for clusters of independent operators.
4. **Identify ownership** — filter for privately held, founder-owned businesses facing succession issues.

### Step 4: Idea Presentation

For each idea that passes the screen, present:

**[Company Name] — [Deal Type] — [One-Line Thesis]**

| Metric | Value | vs. Sector Median |
|--------|-------|-------------------|
| LTM Revenue | | |
| LTM EBITDA | | |
| EBITDA Margin | | |
| Estimated EV | | |
| CapEx / Sales | | |
| Target Ownership | | |

**Investment Thesis (3-5 bullets):**
- Why this is an attractive target
- Primary value creation levers (e.g., multiple arbitrage, cost synergies, pricing optimization)
- LBO viability and debt capacity

**Key Risks & Diligence Focus:**
- What could break the deal (e.g., customer concentration, key-person risk, tech debt)
- Required areas for commercial and financial diligence

**Suggested Next Steps:**
- Build high-level LBO model? Proceed to teaser generation? Request management call?

### Step 5: Output

- Shortlist of 3-5 high-conviction targets with summary profiles
- Documentation of screening criteria and data sources used
- Peer comparison matrix and market map
- Recommended prioritization for outreach or deeper diligence

## Quality Rubric

To ensure the highest quality of output, check against these criteria:
- **Financial Rigor**: Are metrics focused on PE standards (EBITDA, FCF, CapEx) rather than public market metrics (P/E, short interest, dividend yield)?
- **Actionability**: Are the identified targets realistically actionable (e.g., correct ownership structure, appropriate size)?
- **Thesis Clarity**: Does the investment thesis clearly articulate the value creation plan (synergies, roll-up, operational improvement)?
- **Constraint Adherence**: Did you strictly obey the AUCTUS hard filters (Revenue €5m-€250m, DACH region, no excluded sectors)?
- **Data Sourcing**: Are the numbers grounded in FactSet data or registry fetches, rather than hallucinations? If a number is unknown, is it flagged as `[UNSOURCED]`?

## Correct Patterns

**1. FactSet MCP Prompting for Private Companies**
When using the FactSet MCP to screen for private targets, explicitly specify the required criteria to avoid broadly irrelevant results:
```text
GOOD: "Screen for private companies in Germany, Austria, and Switzerland (DACH) operating in the software sector, with LTM Revenue between €5M and €250M, excluding venture-backed entities."

BAD: "Find me software companies in Europe with good margins."
```

**2. Handling Missing Private Company Data**
If precise EBITDA or CapEx data is missing for a private target, clearly state it rather than estimating blindly:
```markdown
GOOD:
- LTM Revenue: €45m (Creditreform 2024)
- LTM EBITDA: [UNSOURCED - typically 15-20% for sector]

BAD:
- LTM EBITDA: €8m (assumed based on peers)
```

## Important Notes

- Screens surface candidates, not conclusions — every screen output needs fundamental work.
- The best buy-and-build platforms often come from fragmented sectors with aging founders (succession planning).
- Contrarian ideas need a catalyst — identifying a good company is not enough, there must be a reason it is available for acquisition now.
- Track idea hit rates over time — which screens and approaches produce the best targets?
