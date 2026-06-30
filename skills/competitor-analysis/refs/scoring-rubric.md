# AUCTUS Target Scoring Rubric
# Referenced by: skills/competitor-analysis/SKILL.md Step 5 (hard filters) and Step 6 (scoring)
# This file is the data reference. The skill file contains the process steps.

---

## Section 1: Hard Filters

These are binary pass/fail. A company failing ANY single criterion is excluded.

| Filter                  | Pass Condition                                              | Fail Code |
|-------------------------|-------------------------------------------------------------|-----------|
| Revenue floor           | TTM revenue ≥ €10m (or credible estimate ≥ €10m)           | REV_LOW   |
| Revenue ceiling         | TTM revenue ≤ €150m (or credible estimate ≤ €150m)         | REV_HIGH  |
| Geography               | HQ or primary operations in geographies_allowed list        | GEO_FAIL  |
| Sector exclusion        | NOT in excluded_sectors list                                | SEC_EXCL  |
| Ownership accessibility | Not publicly listed; not majority PE-owned (for add-ons)   | OWN_FAIL  |
| Operationally active    | Company appears to be trading (website live, employees >5)  | INACT     |

If revenue data is unavailable, use the following proxies:
- Headcount 10–50 → estimated revenue €2m–€15m (flag as LOW_CONFIDENCE)
- Headcount 50–200 → estimated revenue €10m–€60m (flag as MED_CONFIDENCE)
- Headcount 200–600 → estimated revenue €40m–€150m (flag as MED_CONFIDENCE)
- Headcount >600 → estimated revenue >€150m → likely EXCLUDE (flag for verification)

---

## Section 2: Scoring Matrix

Weight assignments are loaded at runtime from `config/auctus_criteria.yaml → scoring_weights`.
Scoring is applied only to companies that passed all hard filters.

### Dimension 1: Revenue in Sweet Spot (weight: 0.15)
Score is relative to AUCTUS's preferred acquisition size band.

| Revenue Range     | Score |
|-------------------|-------|
| €20m – €80m       | 100   |
| €10m – €20m       | 70    |
| €80m – €120m      | 70    |
| €120m – €150m     | 40    |

### Dimension 2: Founder/Family Ownership (weight: 0.20)
Ownership type signals deal accessibility and cultural fit.

| Ownership Type               | Score |
|------------------------------|-------|
| Founder-owned (active)       | 100   |
| Family-owned (2nd generation)| 85    |
| Management-owned (MBO)       | 75    |
| Mixed (founder + PE minority) | 50   |
| PE-majority owned            | 20    |
| Unknown                      | 30    |

### Dimension 3: Market Fragmentation (weight: 0.20)
The opportunity for a buy-and-build roll-up strategy.

| Fragmentation Signal                                          | Score |
|---------------------------------------------------------------|-------|
| Market has 20+ companies in €10m–€150m band in DACH          | 100   |
| Market has 10–20 comparable companies in DACH                 | 75    |
| Market has 5–10 comparable companies in DACH                  | 50    |
| Fewer than 5 comparables; market may be consolidating already | 25    |

### Dimension 4: Recurring Revenue (weight: 0.15)
Contracted or recurring revenue reduces cash flow volatility.

| Recurring Revenue %      | Score |
|--------------------------|-------|
| ≥60% recurring/contracted | 100  |
| 40%–60%                  | 75    |
| 20%–40%                  | 50    |
| <20% or unknown          | 25    |

### Dimension 5: EBITDA Margin Quality (weight: 0.15)
Normalized EBITDA margin signals business quality.

| EBITDA Margin        | Score |
|----------------------|-------|
| ≥20%                 | 100   |
| 15%–20%              | 85    |
| 10%–15%              | 65    |
| <10%                | 10    |

### Dimension 6: DACH Geographic Concentration (weight: 0.10)
Focus on core geography improves operational integration ease.

| DACH Revenue Share | Score |
|--------------------|-------|
| ≥80% DACH          | 100   |
| 60%–80%            | 75    |
| 40%–60%            | 50    |
| <40%               | 25    |

### Dimension 7: Customer Concentration (weight: 0.05)
Low concentration = lower key-customer risk.

| Top Customer Revenue Share | Score |
|----------------------------|-------|
| <10%                       | 100   |
| 10%–20%                    | 75    |
| 20%–30% (hard filter edge) | 40    |
| Unknown                    | 40    |

---

## Section 3: Revenue Estimation Methodology

When public revenue data is unavailable, use this waterfall:
1. Companies House / Handelsregister (DE/AT/CH) — filed accounts (most reliable)
2. Creditreform / Bisnode revenue estimate
3. LinkedIn headcount + sector revenue-per-employee multiplier (see table below)
4. Website traffic / employee review count as last resort (LOW_CONFIDENCE flag)

**Revenue-per-employee multipliers by sector (€k per FTE):**

| Sector                          | Low   | Mid   | High  |
|---------------------------------|-------|-------|-------|
| Industrial services             | 80    | 120   | 180   |
| Facility management             | 60    | 90    | 130   |
| HVAC services                   | 90    | 130   | 190   |
| Healthcare services             | 70    | 110   | 160   |
| IT services SMB                 | 120   | 180   | 280   |
| Testing/inspection/certification| 100   | 150   | 220   |
| Veterinary services             | 80    | 120   | 170   |
