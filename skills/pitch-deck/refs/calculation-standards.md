# Calculation Verification Reference

This file provides formulas and guidelines for verifying pre-calculated values in source data before populating templates. Source data should already contain calculated figures—use these formulas to verify accuracy.

For AUCTUS decks: all financial figures come from Python script outputs (LBO JSON, DCF JSON). Use these formulas to verify script outputs are internally consistent before populating slides.

## Contents

- [Key Verification Formulas](#key-verification-formulas)
- [Consensus Methodology](#consensus-methodology)
- [Rounding Guidelines](#rounding-guidelines)
- [Verification Checklist](#verification-checklist)
- [Red Flags to Investigate](#red-flags-to-investigate)

---

## Key Verification Formulas

### CAGR Projection

**Formula:**
```
Future Value = Present Value × (1 + CAGR)^n
```

**Variables:**
- Present Value: Current/base year value
- CAGR: Compound Annual Growth Rate (as decimal, e.g., 16.4% = 0.164)
- n: Number of years between base and target year

**Verification example:**
```
Source claims: €22.1m (2024) at 16.4% CAGR = €55.0m (2030)

Verify: 22.1 × (1.164)^6 = 22.1 × 2.488 = 55.0 ✓
```

**Calculating n (years):** Count years between base and target year. Examples: 2024→2030 = 6 years, 2025→2030 = 5 years.

### Valuation Multiples

**EV/Revenue:**
```
EV/Revenue Multiple = Enterprise Value ÷ Revenue
Implied EV = Revenue × Multiple
```

**EV/EBITDA:**
```
EV/EBITDA Multiple = Enterprise Value ÷ EBITDA
Implied EV = EBITDA × Multiple
```

**Verification example:**
```
Source claims: €43.6m deal at 9.7x EBITDA on €4.5m EBITDA

Verify: 43.6 ÷ 4.5 = 9.69 ≈ 9.7x ✓
```

### Market Share

**Formula:**
```
Market Share = (Segment Size ÷ Total Market Size) × 100
```

### Growth Rate

**Year-over-Year:**
```
YoY Growth = (Current Year - Prior Year) ÷ Prior Year × 100
```

**CAGR from endpoints:**
```
CAGR = (End Value ÷ Start Value)^(1/n) - 1
```

### IRR

IRR is the rate r such that:
```
0 = Σ [CF_t / (1 + r)^t]
```
You may compute this natively or read it from the LBO output.

### MOIC

```
MOIC = Total Proceeds ÷ Equity Invested
```
You may compute this natively or read it from the LBO output.

---

## Consensus Methodology

When source data contains multiple estimates, verify consensus calculations:

### Size Consensus (Range)

**Method:** Full min-max range across all sources

**Example:**
```
Sources: €14.9bn, €18.3bn, €21.1bn, €21.2bn, €22.1bn
Consensus: €15-22bn (rounded to nearest €1bn)
```

### CAGR Consensus (Central Cluster)

**Method:** Exclude outliers (highest and lowest), use central cluster range

**Example:**
```
Sources: 10.6%, 16.4%, 17.2%, 19.0%, 22.7%
Exclude outliers: 10.6% (low), 22.7% (high)
Central cluster: 16.4%, 17.2%, 19.0%
Consensus: 16-19% or 16-17% (conservative)
```

### Projection Consensus

**Method:** Apply consensus CAGR to midpoint of size range

**Example:**
```
Size range: €15-22bn → Midpoint: €18.5bn
CAGR consensus: 16-17%
At 16%: 18.5 × (1.16)^6 = €45.1bn
At 17%: 18.5 × (1.17)^6 = €47.5bn
Consensus projection: €45-48bn
```

---

## Rounding Guidelines

For AUCTUS decks (override Anthropic defaults):

| Value Type | AUCTUS Convention | Example |
|------------|-------------------|---------|
| EV (€m) | 2 decimal places | 43.62 → €43.62m |
| Revenue (€m) | 2 decimal places | 18.47 → €18.47m |
| EBITDA (€m) | 2 decimal places | 4.53 → €4.53m |
| IRR | 1 decimal place | 23.4% → 23.4% |
| MOIC | 1 decimal place | 2.34x → 2.3x |
| EV/EBITDA multiple | 1 decimal place | 9.69 → 9.7x |
| CAGR | 1 decimal place | 16.4% → 16.4% |
| Large market sizes (€10bn+) | Nearest €1bn | 18.47 → €18bn |

**Rounding principles:**
- Rounding should not materially change the figure — for smaller values, use finer precision
- Consistency matters more than precision — use same rounding across similar figures
- When creating ranges, round down for low end, round up for high end

---

## Verification Checklist

Before using any calculated value from source data:

### Formula Verification
- [ ] CAGR projection uses correct formula: `PV × (1 + r)^n`
- [ ] Multiples calculated as EV ÷ Metric (not reversed)
- [ ] Growth rates use correct base year in denominator
- [ ] Percentage shares sum to ~100% where applicable

### Input Verification
- [ ] Base year figures match LBO JSON / DCF JSON exactly
- [ ] IRR and MOIC read from script output, not recomputed
- [ ] Time periods (n) calculated correctly
- [ ] Currency consistent (all EUR)

### Output Verification
- [ ] Calculated result matches source's stated figure
- [ ] If mismatch, investigate methodology difference
- [ ] Rounding applied consistently
- [ ] Results are plausible (no order-of-magnitude errors)

---

## Red Flags to Investigate

**Projection mismatches:**
- Calculated projection differs from source by >5%
- Likely cause: Different base year, different CAGR, or rounding

**Multiple mismatches:**
- Calculated multiple differs from source
- Likely cause: Different metric definition (LTM vs. NTM, Revenue vs. Net Revenue)

**IRR / MOIC mismatches vs. slide:**
- Script output differs from slide — slide is wrong; script output is authoritative
- Check that slide reads from LBO compact JSON `irr_pct` / `moic` fields

**When in doubt:** Note the discrepancy in a footnote and show your calculation methodology.
