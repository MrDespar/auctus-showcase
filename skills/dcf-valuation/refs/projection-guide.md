# DCF Projection Methodology Guide
# Referenced by: skills/dcf-valuation/SKILL.md Step 2
# Version: 2.0
# Governs how the agent derives, validates, and presents projection assumptions.
# All steps must be completed before presenting the combined Assumptions Review to the user.

---

## Step 0 — Historical Ratio Analysis (MANDATORY before projecting)

Build this table from `data/inputs/{company}_financials.csv` and any balance sheet data
available. Present it as the first block of the Step 2 combined review. Projections must
be grounded in these trends — every forward assumption must be explainable by reference
to a specific line in this table.

```
Historical Ratio Analysis — {Company}

Metric                     FY{n-2}   FY{n-1}   FY{n}   2Y Avg   3Y Avg   Trend
─────────────────────────────────────────────────────────────────────────────────
Revenue (€m)
  YoY growth %
  1Y CAGR                                                          (= YoY FY{n})
  3Y CAGR (where data allows)
Gross margin %                                                               [▲/▼/─]
EBITDA margin %                                                              [▲/▼/─]
  EBITDA margin delta (bps vs. prior year)
EBIT margin %                                                                [▲/▼/─]
D&A % of revenue                                                             [▲/▼/─]
CapEx % of revenue                                                           [▲/▼/─]
CapEx / D&A ratio              (>1.0 = growth investment; <1.0 = harvest mode)
UFCF (€m)                      (NOPAT + D&A − CapEx − ΔNWC)
  FCF conversion (UFCF/EBITDA)                                               [▲/▼/─]
NWC % of revenue               (if balance sheet available)                  [▲/▼/─]
  DSO (days)                   (if AR available)
  DIO (days)                   (if inventory available)
  DPO (days)                   (if AP available)
ROIC %                         (if balance sheet available)
Effective tax rate %
```

**Trend key:** ▲ = improving/expanding  ▼ = deteriorating/compressing  ─ = stable (±50bps)

**Minimum data requirement:** 3 years for revenue and EBITDA. If fewer years are available,
note the limitation explicitly and widen the Bear/Bull scenario spreads to reflect the
increased uncertainty.

---

## Step 1A — Revenue Projection

### Methodology

Revenue is projected in two components: **organic** and **M&A contribution**. This separation
is mandatory for all AUCTUS deals given the buy-and-build mandate.

**Organic revenue:**

1. Compute historical revenue CAGR (use 3Y if available; else 1Y).
2. Apply mean-reversion toward sector long-run growth from `wacc-assumptions.yaml`:
   - Historical CAGR > 20%: moderate down 40% for projection period
   - Historical CAGR 10%–20%: moderate down 20%
   - Historical CAGR 5%–10%: use as-is
   - Historical CAGR < 5%: use as-is (do not artificially inflate)
3. Phase toward terminal growth: Year 4–5 interpolate linearly toward `tgr` from
   `config/financial_constants.yaml`.

**M&A / buy-and-build contribution:**

If `auctus_criteria.yaml → buy_and_build` applies to this target:
- Propose an explicit annual acquisition revenue contribution for FY1–FY5 in €m.
- Default assumption: 0 in FY1 (integration period), 1 small bolt-on from FY2 onward.
- Size using `addon_max_revenue_eur` from `auctus_criteria.yaml` as the ceiling per bolt-on.
- If no buy-and-build thesis: set M&A contribution to 0 for all years (leave the rows in the
  model so the analyst can populate them if the thesis evolves).

### Present to User As

```
Revenue Projection Assumptions — propose these, await confirmation

Historical 3Y CAGR (organic):        {X}%
Sector long-run growth rate:          {Y}%   (from wacc-assumptions.yaml)
Mean-reversion adjustment applied:    {Z}%   (reduction from historical CAGR)

Organic Revenue Projections:
  FY1: €{A}m  ({pct}% growth)   [Base] | €{Abear}m [Bear] | €{Abull}m [Bull]
  FY2: €{B}m  ({pct}% growth)   ...
  FY3: €{C}m  ({pct}% growth)
  FY4: €{D}m  ({pct}% growth — beginning mean reversion)
  FY5: €{E}m  ({pct}% growth — approaching terminal growth)

M&A Revenue Contribution (buy-and-build):
  FY1: €0m   (integration year, no new acquisitions assumed)
  FY2: €{bolt-on}m   (~{n} add-on at ~{multiple}x EBITDA, {revenue}m revenue)
  FY3: €{bolt-on × 2}m   (full-year contribution of FY2 bolt-on)
  FY4–FY5: same pattern or per analyst input

Total Revenue:                         organic + M&A per year

Confidence note: {one sentence on data quality / visibility into FY1}
```

---

## Step 1B — EBITDA Margin Projection

### Methodology

1. Use the 2-year historical EBITDA margin average as the Base Case Year 1 starting point.
2. Assess operating leverage: is there evidence of margin expansion at current growth rates?
   Look at the margin delta row in the historical analysis (bps/year).
3. Apply expansion assumption only if at least ONE of the following is true:
   - Historical margin trend is ▲ (expanding)
   - A specific operational improvement can be named (e.g., shared services from platform,
     procurement savings, headcount efficiency at scale, pricing power from buy-and-build)
   - Sector benchmarks show higher normalized margins than current (cite benchmark source)
4. If margin trend is ▼ (compressing): project flat for Year 1–2; recovery only from Year 3
   with explicit rationale.

### Margin Expansion Flag Rules

- **Expansion ≤ 200bps total over 5 years:** No flag required.
- **Expansion 200–500bps total:** Add note `[OPERATIONAL_RATIONALE_REQUIRED]` in the
  projection file. The rationale must be one concrete sentence (not "operational improvements").
- **Expansion > 500bps total:** Add flag `[HIGH_EXPANSION_ASSUMPTION]`. This requires
  written sign-off from the deal team and must reference a specific value creation plan
  or precedent (e.g., "based on platform integration savings of €Xm per annum from FY2").
  Do NOT refuse to project this expansion — flag it and proceed. The analyst decides.

There is **no hard cap** on margin expansion. The ceiling is operational credibility,
not an arbitrary bps limit.

### Present to User As

```
EBITDA Margin Assumptions — propose these, await confirmation

Historical 2Y Avg EBITDA Margin:      {X}%
Historical margin trend:              {▲/▼/─}  ({bps delta}/year)

Proposed EBITDA Margins:
  FY1: {A}%   [Bear: {Abear}%  |  Base: {A}%  |  Bull: {Abull}%]
  FY2: {B}%   ...
  FY3: {C}%
  FY4: {D}%
  FY5: {E}%

Total expansion over 5Y (Base):       {X} bps
Expansion rationale:                  {one concrete sentence — not "operational improvements"}
Flag:                                 {NONE / OPERATIONAL_RATIONALE_REQUIRED / HIGH_EXPANSION_ASSUMPTION}
```

---

## Step 1C — CapEx and D&A Projection

### Preferred Method: Depreciation Schedule

If opening PP&E net book value is available:

1. Set opening net PP&E = last historical year closing balance.
2. For each projection year:
   - CapEx additions = Revenue × CapEx% (from historical 3Y avg or sector default)
   - Depreciation on new assets = CapEx additions / asset_life_years (default 10 years)
   - Depreciation on existing assets = prior D&A × (1 − 1/asset_life_years) [declining]
   - Total D&A = new asset depreciation + existing asset depreciation
   - Closing PP&E = opening + CapEx − D&A

**CapEx% starting point:** Use historical 3Y average. If unavailable, use sector default
from `config/financial_constants.yaml → projection_defaults.capex_pct_revenue_default` (4.0%).

**Asset life:** Default 10 years. Adjust for sector (e.g., IT services: 5 years; facility
management: 15 years). Note the assumption.

### Fallback Method: Flat Percentages

If no PP&E data is available, use flat % of revenue:
- CapEx: `capex_pct_revenue_default` from `financial_constants.yaml`
- D&A: `da_pct_revenue_default` from `financial_constants.yaml`
- Tag both `[ESTIMATED — no PP&E data; using sector default]`

### Present to User As

```
CapEx & D&A Assumptions — propose these, await confirmation

Method:                              {Depreciation Schedule | Flat % fallback [ESTIMATED]}
Historical 3Y avg CapEx % revenue:   {X}%
Proposed CapEx % revenue (FY1–5):    {A}%, {B}%, {C}%, {D}%, {E}%

D&A method: {Schedule | Flat %}
  [If Schedule] Asset life assumed:  {N} years
  FY1 D&A (from schedule):           €{X}m  ({pct}% of revenue)
  FY5 D&A (from schedule):           €{X}m  ({pct}% of revenue)
  [Note if D&A grows faster than CapEx — implies capital intensity compressing]

CapEx / D&A ratio check:             FY1: {X}x  FY5: {X}x  (>1x = growth investment)
```

---

## Step 1D — NWC Projection

### Preferred Method: DSO / DIO / DPO (Balance Sheet Drivers)

If historical AR, inventory, and AP are available:

1. Compute historical DSO, DIO, DPO from the Historicals sheet.
2. Use 2-year average as the base case assumption.
3. For PE value creation scenarios: model DSO reduction as an operational improvement
   (e.g., Bear: DSO stays flat; Base: DSO −5 days by FY3; Bull: DSO −10 days by FY3).

```
AR(t)        = Revenue(t) × DSO / 365
Inventory(t) = COGS(t) × DIO / 365     [0 if no inventory]
AP(t)        = COGS(t) × DPO / 365
NWC(t)       = AR(t) + Inventory(t) − AP(t)
ΔNWC(t)      = NWC(t) − NWC(t−1)      [positive = cash outflow]
```

### Fallback Method: % of Revenue Change

If no balance sheet data is available:

```
NWC(t)  = Revenue(t) × nwc_pct_revenue
ΔNWC(t) = NWC(t) − NWC(t−1)
```

Use `nwc_pct_revenue_default` (8.0%) from `financial_constants.yaml`. Tag `[ESTIMATED]`.

Note: this method cannot model working capital efficiency improvements as a value creation
lever. Flag this limitation in the Checks sheet.

### Present to User As

```
NWC Assumptions — propose these, await confirmation

Method:                              {DSO/DIO/DPO | Flat % [ESTIMATED]}

[If DSO/DIO/DPO method:]
  Historical 2Y avg DSO (days):      {X}
  Historical 2Y avg DIO (days):      {X}   (0 = no inventory)
  Historical 2Y avg DPO (days):      {X}
  Proposed Base Case DSO (days):     FY1={A}  FY3={B}  FY5={C}
    WC improvement thesis:           {none | -X days DSO by FY3 = €Xm cash release}

[If Flat % method:]
  NWC % of revenue:                  {X}%   [ESTIMATED]
  Implied ΔNWC as % of ΔRevenue:    ~{Y}%
```

---

## Step 1E — Tax Rate

Use the DACH country-specific rate from `config/financial_constants.yaml → tax_rates`:
- Germany: 29.9%
- Austria: 25.0%
- Switzerland: 19.7% (Zurich-equivalent; note canton variation)
- Multi-DACH or unknown: 29.0% default

If the company has significant operations outside DACH: use the blended effective tax rate
from the most recent historical year (tag `[EFFECTIVE_RATE_FROM_HISTORICALS]`).

---

## Projection File Format

When writing `data/inputs/{company}_projections_approved.csv`:

```csv
year,revenue_organic,revenue_ma,revenue_total,ebitda,d_and_a,capex,nwc_change,tax_rate,expansion_flag
2027,{organic},{ma},{total},{ebitda},{da},{capex},{nwc},{tax},{NONE|OPERATIONAL_RATIONALE_REQUIRED|HIGH_EXPANSION_ASSUMPTION}
2028,...
2029,...
2030,...
2031,...
```

All monetary values in EUR millions. All rates as decimals. nwc_change: positive = cash outflow.
M&A revenue column: 0 if no buy-and-build. This column feeds the Projections sheet M&A row.

---

## Common Projection Errors to Avoid

- **Projecting without historical analysis first.** Every assumption must trace to a trend or
  a stated rationale — not to a generic "sector growth rate."
- **Single composite revenue growth rate.** Organic and M&A must be separated. A buy-and-build
  model that buries acquisition revenue in a blended growth % cannot be audited.
- **Margin expansion without stated rationale.** "Operating leverage" is not a rationale.
  Name the lever: shared procurement, headcount efficiency at scale, pricing power, etc.
- **Flat D&A % when PP&E data is available.** Use the schedule; it's more accurate and captures
  the real tax shield dynamics.
- **NWC as flat % when balance sheet data is available.** The DSO/DIO/DPO method enables
  modelling of working capital efficiency as a value creation lever — don't discard that.
- **Terminal growth above sector long-run GDP.** Check against `financial_constants.yaml → terminal_growth.ceiling` (4.0%). Hard cap. Never exceed.
- **Projecting revenue to a different currency than the input data.** All values stay in €m.
- **Omitting the expansion flag.** If Base Case margin expansion > 200bps, the flag is mandatory.
  Flag first, justify in the projection file, proceed — don't cap the assumption.
- **Halting if FactSet unavailable.** Use web data with [WEB] tags. Proceed.
