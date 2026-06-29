# Peer Group Selection Criteria
# Referenced by: skills/relative-valuation/SKILL.md Step 1
# Defines rules for identifying valid public comparables per sector.

---

## Primary Inclusion Criteria

A company qualifies as a peer if it meets ALL of the following:
1. Operates in the same sector or a closely adjacent sub-sector
2. Revenue between €10m and €2bn (broader than target to capture listed peers)
3. Listed on a recognized European or North American exchange
4. Primarily a services business (not a conglomerate where target sector <40% of revenue)
5. LTM EBITDA data is publicly available (from Bloomberg, FactSet, or company reports)
6. Not currently in bankruptcy, restructuring, or formal M&A process (which distorts multiples)

## Exclusion Criteria

Exclude any company that meets ANY of the following:
- Publicly listed government-controlled entities (distorted capital structure)
- Companies with negative LTM EBITDA (undefined multiples)
- SPAC mergers within the last 12 months (distorted EV from trust value)
- Companies where the target sector accounts for <40% of total group revenue
- Companies with extraordinary items >20% of EBITDA in LTM (distorts comparability)

## Peer Identification Priority Order

1. Listed European pure-plays in the exact sub-sector (DACH preferred)
2. Listed European diversified companies with >60% revenue in sub-sector
3. Listed North American/Australian pure-plays (apply size adjustment note)
4. Precedent transaction multiples used as supplemental reference (Step 4)

## Minimum Peer Requirements by Situation

| Situation                              | Minimum Comps Required |
|----------------------------------------|------------------------|
| Pure-play peers available in sector    | 3                      |
| Partial match (adjacent sector needed) | 3 (note expansion)     |
| No listed EU peers; NA peers used      | 3 (note geographic gap)|
| Fewer than 3 achievable               | HALT — escalate to user|

## Adjacent Sector Expansions

When fewer than 3 primary sector peers are available, expand in this order:

| Primary Sector                  | Adjacent Expansion 1             | Adjacent Expansion 2            |
|---------------------------------|----------------------------------|---------------------------------|
| industrial_services             | facility_management              | environmental_services          |
| hvac_services                   | industrial_services              | facility_management             |
| facility_management             | industrial_services              | business_services               |
| healthcare_services             | veterinary_services              | testing_inspection_certification|
| it_services_smb                 | business_services                | testing_inspection_certification|
| testing_inspection_certification| it_services_smb                  | industrial_services             |
| veterinary_services             | healthcare_services              | —                               |
| environmental_services          | industrial_services              | facility_management             |

When using adjacent sector peers: add a comparability note in the report explaining
the expansion and any multiple adjustments warranted by sector difference.

## Data Sources for Peer Identification

1. **FactSet** (if MCP server available): `get_trading_comps` tool with sector filter
2. **Bloomberg** sector screens (manual — request analyst input if needed)
3. **Brave Search**: "[sector] publicly listed companies Europe [year] revenue"
4. **S&P Capital IQ** (manual): Comparable Company Analysis screen
5. **Fetch from investor relations pages**: for revenue/EBITDA confirmation
