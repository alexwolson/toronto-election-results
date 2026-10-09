# Publish Suspended Campaigns for councillor candidates

Status: accepted

Amends: 0009

## Context

ADR 0009 limited Suspended Campaign curations to the 2026 mayoral field and said that extending
them to other offices would be a new decision. On October 9, 2026, CityNews reported that Frances
Nunziata, the Ward 5 incumbent, was going to end her campaign. The withdrawal deadline was
August 21, so she would stay on the certified ballot, as Chris Alexander did. The Backend's council
race cards need the date. They read the councillor field from the canonical tables, and ADR 0009
keeps the curation out of those tables.

## Decision

- **Curations may date any current City Council Candidacy:** 2026 Toronto mayoral or councillor.
  Every other check in ADR 0009 is unchanged. Trustee and other offices are still rejected.
- **Publish councillor dates in their own feed,** `council_campaign_suspensions.json`, at
  `schema_version` 1. It lists only the curated Suspended Campaigns of the pending 2026 councillor
  field: `candidacy_id`, `person_id`, `display_name`, `ward` (the ward number as a string), and
  `campaign_suspended_on`. An empty list means none is recorded, which is open-world as in
  ADR 0009. The release manifest lists the feed under `feeds` and `feed_versions`.
- **The canonical tables and `mayoral_candidates.json` stay unchanged.** A councillor date never
  reaches the mayoral feed.

## Consequences

- A Backend that needs council Suspended Campaigns reads the new feed from its pinned Results
  release and refuses a release that lacks it.
- Recording a councillor Suspended Campaign takes one curation row and a Results release.
