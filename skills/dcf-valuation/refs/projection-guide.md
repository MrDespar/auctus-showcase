# DCF Projection Methodology Guide
# Referenced by: skills/dcf-valuation/SKILL.md Step 3
# Governs how the agent derives and presents 5-year projections when no pre-built
# projection file exists. All arithmetic is performed by dcf_engine.py — this guide
# defines the ASSUMPTIONS the agent should propose and explain to the user.

---

## Step 3A: Revenue Projection

### Base Case Methodology
1. Compute the 3-year historical revenue CAGR from the input financials.
2. Apply a mean-reversion adjustment toward sector long-run growth:
   - If historical CAGR > 15%: moderate down by 30% for projection period
   - If historical CAGR 5%–15%: use as-is
   - If historical CAGR < 5%: use as-is (do not artificially inflate)
3. Apply sector long-run growth as terminal phase approach:
   - Year 1–3: use adjusted historical CAGR
   - Year 4–5: linearly interpolate toward terminal growth rate

### Present to User As
```
Revenue Projection Assumptions (propose these, await approval):

Historical Revenue CAGR (3Y): {X}%
Sector Long-Run Growth Rate:  {Y}% (from wacc-assumptions.yaml)

Proposed Revenue Projections:
  Year 1: €{A}m  ({pct}% growth)
  Year 2: €{B}m  ({pct}% growth)
  Year 3: €{C}m  ({pct}% growth)
  Year 4: €{D}m  ({pct}% growth — beginning mean reversion)
  Year 5: €{E}m  ({pct}% growth)
```

---

## Step 3B: EBITDA Margin Projection

### Base Case Methodology
1. Use the average of the last 2 historical EBITDA margin years as the base.
2. Apply a modest expansion assumption only if there is clear evidence of:
   - Operating leverage at current revenue growth rate
   - Identified cost efficiencies not yet fully realized
3. Cap margin expansion at +200bps over the full 5-year period (conservative).
4. If historical margins show compression: project flat, not recovery.

### Present to User As
```
EBITDA Margin Assumptions (propose these, await approval):

Historical Average EBITDA Margin (2Y): {X}%
Proposed EBITDA Margins:
  Year 1: {A}%
  Year 2: {B}%
  Year 3: {C}%
  Year 4: {D}%
  Year 5: {E}%
Expansion rationale: {one sentence explanation}
```

---

## Step 3C: CapEx & NWC Projections

Use sector defaults from `config/financial_constants.yaml → projection_defaults`
unless the user provides specific data:
- CapEx: {capex_pct_revenue_default}% of revenue per year
- ΔNet Working Capital: {nwc_pct_revenue_default}% of revenue increment per year
- D&A: {da_pct_revenue_default}% of revenue per year

If historical CapEx data is available in the input CSV, use the 3-year average
as CapEx % of revenue instead of the default.

---

## Step 3D: Tax Rate

Use the DACH country-specific rate from `config/financial_constants.yaml → tax_rates`.
If the company operates across multiple DACH geographies, use the `default` rate (29%).

---

## Projection File Format

When writing `data/inputs/{company}_projections_approved.csv`, use this exact schema:

```csv
year,revenue,ebitda,d_and_a,capex,nwc_change,tax_rate
2027,{value},{value},{value},{value},{value},{value}
2028,{value},{value},{value},{value},{value},{value}
2029,{value},{value},{value},{value},{value},{value}
2030,{value},{value},{value},{value},{value},{value}
2031,{value},{value},{value},{value},{value},{value}
```

All monetary values in EUR millions. All rates as decimals (0.0–1.0).
nwc_change: positive = cash outflow (NWC increased, absorbed cash).

---

## Common Projection Errors to Avoid

- Never project revenue to a different currency than the input data.
- Never assume margin expansion without stated operational rationale.
- Never use a terminal growth rate higher than the sector's long-run GDP growth.
- Never present projection numbers without noting the confidence level.
- If the company is in a cyclical trough: note the cycle position in the report.
