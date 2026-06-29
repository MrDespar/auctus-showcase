# AUCTUS Target Matrix — Output Template
# Referenced by: skills/competitor-analysis/SKILL.md Step 7
# The agent must follow this structure exactly when composing the markdown report.

---

## Template: {SECTOR_DISPLAY_NAME} Target Matrix
**Prepared by:** AUCTUS Investment Intelligence Agent
**Date:** {YYYYMMDD}
**Sector:** {sector_slug}
**Deal Type:** Buy-and-Build Add-On

---

### Executive Summary

{3 sentences: niche overview, fragmentation level, total addressable market for
the €10m–€150m revenue band in DACH. Source any market size estimates.}

---

### Market Mapping

**Total candidates identified:** {N}
**Hard filter exclusions:** {N} ({breakdown by exclusion code})
**Final shortlist:** {N} companies

---

### Ranked Target Matrix

| Rank | Company | Country | Est. Revenue (€m) | EBITDA Margin | Ownership | AUCTUS Score | Recommendation |
|------|---------|---------|-------------------|---------------|-----------|--------------|----------------|
| 1    | ...     | ...     | ...               | ...           | ...       | ...          | ...            |
| ...  | ...     | ...     | ...               | ...           | ...       | ...          | ...            |

*Score range: 0–100. Recommendation bands: Priority Target (≥80), Active Coverage (60–79),
Monitor (40–59), Pass (<40).*

---

### Top 3 Priority Targets — Strategic Rationale

#### 1. {Company Name}
**Score:** {N}/100 | **Recommendation:** {label}

{2–3 sentences on strategic fit: why this target, what add-on value it creates,
owner succession dynamic if known, any integration considerations.}

#### 2. {Company Name}
*(same format)*

#### 3. {Company Name}
*(same format)*

---

### Market Commentary

**Fragmentation & Consolidation Opportunity**
{Paragraph 1: Quantify fragmentation. How many players in the €10m–€150m band?
What is the estimated HHI / CR5? Is consolidation already underway?}

**Buy-and-Build Thesis**
{Paragraph 2: Why does this sector suit a buy-and-build strategy? What synergies
are achievable (procurement, geographic, service-line, customer cross-sell)?}

**Key Risks & Information Gaps**
{Paragraph 3: What data was estimated vs confirmed? Which targets need outreach
for revenue verification? Any regulatory, cyclical, or competitive risks to flag?}

---

### Data Sources Used
- {source_1}: {description}
- {source_2}: {description}
- ...

### Next Steps
1. Initiate NDA outreach to Priority Targets: {company_name_list}
2. Commission desktop due diligence on top 5 ranked companies
3. Request management presentations from founders ranked 1–3

---

## CSV Schema (outputs/{sector}_{timestamp}_targets.csv)

Required columns in output CSV (must all be present):

| Column               | Type    | Description                                  |
|----------------------|---------|----------------------------------------------|
| company              | string  | Legal company name                           |
| country              | string  | ISO 2-letter country code                    |
| revenue_eur_m        | float   | Estimated TTM revenue in EUR millions        |
| revenue_confidence   | string  | HIGH / MED / LOW                             |
| ebitda_margin_pct    | float   | Estimated EBITDA margin (0.0–1.0)            |
| ownership            | string  | founder / family / management / pe / unknown |
| hard_filter_pass     | boolean | true/false                                   |
| hard_filter_fail_code| string  | Null if pass; fail code if excluded          |
| auctus_score         | float   | 0.0–100.0                                    |
| recommendation       | string  | Priority Target / Active Coverage / Monitor / Pass |
| data_source          | string  | Primary source used for this entry           |
