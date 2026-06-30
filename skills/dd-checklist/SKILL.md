---
name: dd-checklist
version: "1.1.0"
description: >
  Generates and tracks comprehensive due diligence checklists for DACH mid-market
  PE acquisitions. Tailored to the target's sector, deal type, and complexity.
  Adds DACH-specific legal items (GmbH/AG structures, Handelsregister, GDPR) and
  buy-and-build specific items (earn-out mechanics, seller non-compete, integration risk).
triggers:
  - "dd checklist"
  - "due diligence tracker"
  - "diligence request list"
  - "what do we still need"
  - "data room review"
  - "due diligence"
  - "DD workstreams"
  - "kick off diligence"
inputs:
  required:
    - "company_name — target company name"
    - "sector — sector description"
    - "deal_type — platform | add-on | recap | carve-out"
  optional:
    - "key_concerns — known issues to prioritize"
    - "timeline — LOI / close target date"
refs:
  auctus_criteria: "config/auctus_criteria.yaml"
outputs:
  - "outputs/ic_memos/dd_checklist_{company}_{YYYYMMDD_HHMMSS}.xlsx"
  - "outputs/ic_memos/dd_checklist_{company}_{YYYYMMDD_HHMMSS}.md"
---

## AUCTUS OVERLAY — Firm-Specific Configuration
> This section overrides Anthropic defaults where firm practice differs. Read first.

AUCTUS Capital Partners AG acquires private DACH mid-market companies pursuing buy-and-build
strategies. Due diligence checklists must cover DACH-specific legal structures and
buy-and-build specific considerations not present in generic PE checklists.

### Prerequisites

`/screen-deal` — deal has passed initial screening (Pass or Further Diligence verdict).
This skill is triggered when a deal moves from screening to active diligence.

### Data Source Hierarchy

1. **User-provided data** — management presentations, data room index, CIM
2. **FactSet MCP** — public comparable data for benchmarking
3. **Web search / fetch** — regulatory requirements, sector-specific compliance

### Currency & Units

All monetary values in **EUR millions (€m)**.

### Execution Environment

Output: `outputs/ic_memos/dd_checklist_{company}_{YYYYMMDD_HHMMSS}.xlsx` (primary)
plus `dd_checklist_{company}_{YYYYMMDD_HHMMSS}.md` for in-session tracking.

### AUCTUS-Specific Rules

**DACH legal framework additions** (always include for DACH targets):

*Corporate Structure:*
- GmbH vs AG structure; Gesellschaftsvertrag / Satzung review
- Handelsregister (DE: HRB / HRA; AT: Firmenbuch; CH: Handelsregister) extract
- Gesellschafterliste (shareholder list) — current and historical
- Geschäftsführervertrag (managing director contract) terms and change-of-control provisions
- Vinkulierungsklauseln (transfer restrictions) on shares

*Tax:*
- Organschaft (fiscal unity) structures — complexity in unwinding
- Gewerbesteuer (trade tax) allocation across municipalities (DE)
- GKKB / Pillar 2 minimum tax exposure (AT/DE)
- Swiss withholding tax on dividends

*Employment / HR:*
- Betriebsrat (works council) — DE: § 613a BGB applies on asset deal transfers
- Tarifvertrag (collective bargaining agreement) coverage
- Betriebliche Altersversorgung (company pension) obligations — actuarial assessment
- GDPR / DSGVO compliance: data mapping, DPA, consent records

**Buy-and-build specific additions** (always include for platform acquisitions):

- Earn-out structure mechanics and protection covenants
- Seller non-compete (§ 74ff HGB DE): duration, geography, enforceability review
- Integration risk assessment: IT systems, culture, customer overlap
- Add-on acquisition pipeline: any existing LOIs or exclusivity agreements seller holds
- Management carve-out / equity rollover terms
- Day-1 readiness plan: legal entity standalone cost assessment

---

# Due Diligence Checklist (Anthropic Financial Services Reference)
> The complete Anthropic reference implementation follows verbatim below.
> Where it conflicts with the AUCTUS overlay above, the overlay takes precedence.

## Workflow

### Step 1: Scope the Diligence

Ask the user for:
- **Target company**: Name, sector, business model
- **Deal type**: Platform acquisition, add-on, growth equity, recap, carve-out
- **Deal size / complexity**: Determines depth of diligence
- **Key concerns**: Any known issues to prioritize (customer concentration, regulatory, environmental, etc.)
- **Timeline**: When is LOI / close targeted?

### Step 2: Generate Workstream Checklists

Generate a checklist across all major workstreams, tailored to the sector:

**Financial Due Diligence**
- Quality of earnings (QoE) — revenue and EBITDA adjustments
- Working capital analysis — normalized vs. actual, NWC seasonality, and peg mechanism
- Debt and debt-like items (including off-balance sheet liabilities)
- Capital expenditure (maintenance vs. growth, historical adequacy, and capex backlog)
- Tax structure and exposure
- Audit history, accounting policies, and related party transactions
- Pro forma adjustments (run-rate, synergies)
- Standalone cost / carve-out financials (if applicable)
- Foreign exchange (FX) exposures and hedging policies
- Capitalization table and option pool dilution

**Commercial Due Diligence**
- Market size and growth (TAM/SAM/SOM build-up methodology: bottom-up vs top-down)
- Competitive positioning and market share
- Customer analysis — concentration, retention/churn by cohort, NPS
- Unit economics — gross margin per product/service, CAC, and LTV
- Pricing power and contract structure
- Sales pipeline and backlog
- Go-to-market effectiveness

**Legal Due Diligence**
- Corporate structure and org chart
- Material contracts (customer, supplier, partnership) with focus on change of control provisions
- Real estate leases and ownership documents
- Litigation history and pending claims
- IP portfolio, protection, and open source software (OSS) licenses (if tech)
- Regulatory compliance, including anti-bribery/corruption (FCPA/UKBA/local equivalent)
- Employment agreements and non-competes
- Data privacy / cybersecurity liability history

**Operational Due Diligence**
- Management team assessment
- Organizational structure and key person risk
- IT systems and infrastructure
- Supply chain, supplier concentration, and vendor dependencies
- Facilities, real estate, capacity utilization, and bottleneck analysis
- Disaster recovery and business continuity plans
- Insurance coverage (adequacy and historical claims)

**HR / People Due Diligence**
- Org chart and headcount trends
- Compensation benchmarking, incentive equity, and bonus plans
- Benefits and pension obligations
- Key employee retention risk, employee turnover rates, and exit interview themes
- Misclassification of contractors (e.g., 1099 vs W2 equivalent, Scheinselbstständigkeit)
- Culture assessment
- Union/labor agreements
- Diversity, Equity & Inclusion metrics / reporting (if required)

**IT / Technology Due Diligence** (for tech-enabled businesses)
- Technology stack, architecture, and third-party API dependency risk
- Technical debt assessment and open-source software (OSS) audits / code scans
- Cybersecurity posture and disaster recovery/backup testing
- Data privacy compliance (GDPR, CCPA, SOC2)
- Product roadmap and R&D spend
- Scalability assessment and cloud vs on-prem infrastructure costs / optimization

**Environmental / ESG** (where applicable)
- Phase I / Phase II Environmental Site Assessments (ESA) and environmental liabilities
- Regulatory compliance history
- ESG risks and opportunities, including supply chain ESG compliance
- Scope 1, 2, 3 carbon footprint / emissions (key for European funds / SFDR)

### Step 3: Status Tracking

For each item, track:

| Item | Workstream | Priority | Status | Owner | Notes |
|------|-----------|----------|--------|-------|-------|
| QoE report | Financial | P0 | Pending | | |
| Customer interviews | Commercial | P0 | In Progress | | 3 of 10 complete |

Status options: Not Started → Requested → Received → In Review → Complete → Red Flag

### Step 4: Red Flag Summary

Maintain a running list of red flags discovered during diligence:
- What was found
- Which workstream
- Severity (deal-breaker / significant / manageable)
- Mitigant or path to resolution
- Impact on valuation or deal terms

### Step 5: Output

- Excel workbook with tabs per workstream (default)
- Summary dashboard: % complete by workstream, outstanding items, red flags
- Weekly status update format for deal team

## Sector-Specific Additions

Automatically add relevant items based on sector:
- **Software/SaaS**: ARR quality, cohort analysis, hosting costs, SOC2
- **Healthcare**: Regulatory approvals, reimbursement risk, payor mix
- **Industrial**: Equipment condition, environmental remediation, safety record
- **Financial services**: Regulatory capital, compliance history, credit quality
- **Consumer**: Brand health, channel mix, seasonality, inventory management

## Important Notes

- Prioritize P0 items that are gating to LOI or close
- Flag items where the seller is slow to respond — may indicate issues
- Cross-reference data room contents against the checklist to identify gaps
- Update the checklist as diligence progresses — it's a living document

## Quality Rubric

- **Comprehensiveness**: Does the generated checklist contain standard IB/PE diligence vectors like NWC peg mechanism, unit economics (LTV/CAC, cohort analysis), and change of control provisions?
- **DACH Specificity**: Are all AUCTUS overlay DACH specific structures (Handelsregister, GmbH vs AG, GmbH-Gesetz considerations, Scheinselbstständigkeit, Betriebsrat, GDPR) included where appropriate?
- **Buy-and-Build Focus**: Does it address earn-outs, day-1 readiness, and pipeline integration?
- **Actionability**: Are diligence vectors tied to priority (P0, P1, P2), owner, and status?
- **ESG/SFDR Rigor**: For European deals, are carbon footprint (Scope 1/2/3) and supply chain ESG checks correctly scoped?

## Correct Patterns

### Due Diligence Data Structure
When exporting diligence checklists programmatically to Excel or Markdown, structure the data as a list of dictionaries with normalized keys to ensure consistent tracking across updates.
```python
import pandas as pd

# Standard tracking format
dd_items = [
    {
        "Workstream": "Financial",
        "Category": "NWC",
        "Item": "Monthly NWC analysis (historical vs normalized) to determine peg",
        "Priority": "P0",
        "Status": "Requested",
        "Owner": "KPMG",
        "Notes": "Require raw trial balances to perform seasonality analysis"
    },
    {
        "Workstream": "Legal",
        "Category": "Corporate",
        "Item": "Handelsregisterauszug and Gesellschafterliste",
        "Priority": "P0",
        "Status": "Received",
        "Owner": "Legal Counsel",
        "Notes": "Clear on AG vs GmbH structure"
    }
]

df = pd.DataFrame(dd_items)
df.to_excel("outputs/ic_memos/dd_checklist_CompanyX.xlsx", index=False)
```
