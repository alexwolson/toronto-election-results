# Data dictionary — Toronto Election Results v2.1

The release covers completed, single-seat election contests wholly within the City of Toronto from
2003-01-01 through 2026-08-20. It also includes the official candidate-list snapshot as of
2026-08-21 for the Toronto municipal general election scheduled for 2026-10-26; its Candidacies and
Contests are marked `pending` and contain no result values. The dataset includes Mayor, City
Councillor, all four School Board Trustee systems, MP, and MPP elections. General elections,
by-elections, acclamations, and legally void contests are in scope. Poll/subdivision records are
used only to produce Contest totals and are not published.

The release contains 5,731 Candidacies, 881 Contests, and 55 Election events. Of those, 243
Candidacies in 26 Contests belong to the pending 2026 municipal event; the other 5,488 Candidacies
and 855 Contests are final. Evidence-backed Endorsement companion tables cover Mayor and City
Councillor Contests only.

See `CONTEXT.md` for canonical domain language and `docs/adr/` for design decisions.

## Primary table: `election_results`

Grain: one Candidacy in one Contest. Common Contest labels and metrics are repeated here for direct
modelling. The authoritative normalized entities remain available as companion tables.

| Column | Type | Null rule | Meaning |
|---|---|---|---|
| `candidacy_id` | string | never | Stable source-occurrence identity for this ballot appearance. |
| `person_id` | string | unresolved identity | Confirmed persistent Person; never assigned by fuzzy matching alone. |
| `event_id` | string | never | Election event foreign key. |
| `contest_id` | string | never | Contest foreign key. |
| `election_date` | date | never | Scheduled polling date; may be in the future when `result_status=pending`. |
| `election_year` | integer | never | Convenience feature derived from `election_date`. |
| `election_type` | enum | never | `general` or `by_election`. |
| `election_authority` | enum | never | `toronto_city_clerk`, `elections_canada`, or `elections_ontario`. |
| `represented_body` | enum | never | Institution whose membership the Contest fills. |
| `office_type` | enum | never | `mayor`, `councillor`, `trustee`, `mp`, or `mpp`. |
| `district_id` | string | never | Native as-run Electoral district/ward foreign key. |
| `official_district_id` | string | never | Authority's key within the represented body and Boundary regime. |
| `district_name` | string | never | Authority-reported or deterministic display label. |
| `boundary_regime` | string | never | Identifies the non-comparable geography system used for the vote. |
| `candidate_name` | string | never | Normalized display form where the source format can be interpreted safely. |
| `candidate_name_raw` | string | never | Ballot/result-source representation, preserved independently. |
| `party_id` | string | affiliation is `party` | Party foreign key. Null for independent/non-partisan/not-reported rows. |
| `party_name` | string | no Party | Canonical Party display label repeated for modelling. |
| `party_name_raw` | string | source reports none | Exact authority-reported affiliation label. |
| `party_jurisdiction` | string | never | Authority/jurisdiction in which Party identity is scoped. |
| `affiliation_status` | enum | never | `party`, `independent`, `non_partisan`, or `not_reported`. |
| `votes` | integer | pending/no poll | Certified valid candidate votes. Zero means an observed zero. |
| `total_contest_votes` | integer | pending/no poll/incomplete | Sum of valid candidate votes; Vote share denominator. |
| `vote_share` | float | pending/no poll/incomplete/zero denominator | `votes / total_contest_votes`. |
| `vote_rank` | integer | pending/no poll/incomplete | Competition rank; tied vote totals share a rank. |
| `n_candidates` | integer | never on Candidacy rows | Number of known Candidacies in the Contest. |
| `eligible_electors` | integer | pending/unavailable/inapplicable | Authority count at the stated `turnout_scope`. |
| `ballots_cast` | integer | pending/unavailable/inapplicable | Electors voting at the same scope as `eligible_electors`. |
| `turnout` | float | pending/either operand unavailable | `ballots_cast / eligible_electors`. |
| `turnout_scope` | string | turnout unavailable | Qualification/geography shared by both turnout operands. |
| `elected` | boolean | pending or unresolved official outcome | Authority-certified result; not blindly rederived from vote maximum. |
| `acclaimed` | boolean | never | True only for an official Acclamation. |
| `outcome_method` | enum | never | `pending`, `vote`, `acclamation`, `void`, or another authority disposition. |
| `result_status` | enum | never | `final` for certified/historical outcomes; `pending` for the 2026 candidate snapshot. |
| `coverage_status` | enum | never | `complete`, `partial`, or `source_missing`; independent of legal outcome. |
| `incumbent` | boolean | insufficient identity/roster evidence | Same Office type and Represented body in the last valid pre-event roster. |
| `incumbent_office_tenure_id` | string | not incumbent/unknown | Supporting Office tenure for `incumbent=true`. |
| `incumbent_reported` | boolean | authority does not report it | Unmodified source flag; the modelled `incumbent` field uses project semantics. |
| `source_authority` | string | never | Organization responsible for the row's official record. |
| `source_resource` | string | never | Official dataset/report family. |
| `source_detail` | string | never | Concrete official URL/file detail. |
| `source_candidacy_id` | string | never | Authority candidate key where one exists; otherwise the opaque occurrence key persisted in the project Candidacy ledger. |

### Important null semantics

- Numeric zero always means an observed zero. Missing and not-applicable values are null.
- A pending Candidacy has null votes, contest vote total, Vote share, rank, elected outcome,
  electorate, ballots cast, and turnout. Its `outcome_method` and `result_status` are both
  `pending`; no winner is inferred. The same persistent Candidacy ID is retained when certified
  results replace the pending state.
- An Acclamation has one `elected=true` row and null votes, total, share, and rank.
- A legally void Contest may have no Candidacy rows; it remains in `contests`.
- A source-missing Contest is a Contest placeholder only. No candidate or zero vote is fabricated.
- Toronto trustee turnout is null: the City's municipal-ballot participation count is not a
  board-qualified trustee measure. Mayor/Councillor composite turnout is retained and explicitly
  labelled; federal and provincial turnout is district-specific.
- A Person link is null when identity evidence is unresolved. Exact/fuzzy name similarity can
  create a review proposal but cannot create a confirmed link by itself.
- `incumbent=false` requires a confirmed Person and evidence sufficient to establish absence from
  the same-body/same-office roster. Otherwise it is null.

## Companion tables

### `election_events`

One row per officially called Election event: `event_id`, polling date/year, type, and authority.
Separately called by-elections may share a date without sharing identity. The scheduled 2026
Toronto municipal general election is present because its official candidate roster is published.

### `contests`

One row per Contest, including event/body/office/district keys, Outcome method, Result status,
Coverage status, single-seat cardinality, vote total, turnout operands/scope, and source fields.
This table also contains pending Contests with null result metrics and void/source-missing Contests
that correctly have no Candidacy row.

### `people`

The persistent identity registry: opaque `person_id`, preferred name, active/deprecated status,
visible redirect target, and creation release. A Person may be retained for exact downstream
identity resolution even when withdrawal leaves no certified Candidacy row; that does not add the
Person to an election field. A Person name never rewrites a historical ballot name.

### `person_aliases.json`

The release-owned exact-name crosswalk for downstream datasets. Names come from confirmed
Candidacies, active Person preferred names, or `data/reference/person_alias_curations.csv` with
retained evidence and rationale. A normalized name resolves only when all occurrences identify one
active Person; collisions remain published as ambiguous with a null `person_id`.

### `candidacy_person_links`

Audited occurrence-to-Person history. `link_status` is `confirmed`, `proposed`, `rejected`, or
`unresolved`; method, evidence, reviewer, and release-validity fields make merges and later
corrections visible. `proposed` means not yet adjudicated; `unresolved` may retain the reviewed
candidate Person when evidence is insufficient; `rejected` records a disproved candidate Person.
Only active confirmed links populate `election_results.person_id`.

### `parties`

One row per legal Party identity within a jurisdiction: `party_id`, jurisdiction, canonical name,
and retained source label. Party is a Candidacy relationship, never a permanent Person attribute.

### `office_tenures`

Evidence that a Person held one Office type in one Represented body, including known/approximate
dates, district where available, entry method, and source. Appointments may appear here even though
appointments are not Election results. Date-precision fields distinguish exact election dates from
unknown or reference-bounded dates; `source_authority` and `source_detail` retain the evidence.

### `electoral_districts`

One row per native `(represented_body, boundary_regime, official_district_id)` identity. Geometry
is EPSG:4326 Polygon/MultiPolygon where acquired. `geometry_status` and
`geometry_missing_reason` make unavailable historical/authority geometries explicit; missing
geometry never excludes a result. Geometry provenance records the authority, resource, concrete
source file, and source year. The CSV serializes geometry as WKT; the Parquet artifact is
GeoParquet. Current 2026 trustee polygons are exact unions of the canonical current City wards;
`geometry_derivation` and the membership-source fields record the verified crosswalk used in that
derivation. Historical trustee geometry remains explicitly unavailable. The release does not
publish subdivision-level polygons.

### `endorsers`

One row per exact Endorser. The 9-row release panel contains people, organizations, and editorial
boards; a parent, affiliate, local, owner, member, or editorial board is never treated as another
entity's alias. Core fields are `endorser_id`, `canonical_name`, `endorser_type`, optional
`person_id`, and `is_panel_endorser`. Panel-basis, eligibility, office-applicability, and evidence
fields record why and when an Endorser belongs in the systematic panel. Every approved panel
Endorser applies to both Mayor and City Councillor Contests; that scope flag neither creates an
Endorsement nor claims that a specific Contest was searched.

### `endorsement_assertions`

One row per source-specific Endorsement claim. `assertion_id` is the assertion identity;
`endorsement_id` is populated only when a confirmed assertion produces a fact. The row locates the
Endorser and Contest, the Candidacy when resolvable, the asserted candidate name, review state,
Endorsement kind, announcement date/precision, source type, and primary/secondary evidence URLs.
Review states are `proposed`, `confirmed`, `unresolved`, `rejected`, and `withdrawn`. The release
contains 155 assertions: 154 confirmed and one unresolved assertion whose supported target has no
published Candidacy row.

### `endorsements`

The 154 adjudicated positive facts, at one exact `(endorser_id, contest_id, candidacy_id)` edge per
row, with a stable `endorsement_id`. Facts are derived only from confirmed assertions and target
Mayor or City Councillor Candidacies. One Endorser may support multiple Candidacies in one Contest.
An Endorsement does not create a negative observation for any other Candidacy, and the absence of
an Endorsement row never means opposition, neutrality, or a decision not to endorse.

### `endorsement_coverage`

One row per approved Endorser and Mayor/City Councillor Contest: `endorser_id`, `contest_id`,
`coverage_state`, `assessed_through`, and `coverage_basis`. The 2,385 cells distinguish
`not_applicable`, `not_searched`, `partially_searched`, `searched_no_endorsement_found`,
`comprehensive_source_found`, and `source_unavailable`. Coverage is open-world metadata, not a set
of candidate-level negatives. Even `searched_no_endorsement_found` records only what the completed
search found; it does not assert that the Endorser opposed any Candidacy. `assessed_through` is null
for `not_searched` cells, so a release date cannot be mistaken for evidence that a historical
Contest-specific search occurred. The current release contains 643 `not_applicable`, 145
`not_searched`, 1,277 `partially_searched`, 207 `comprehensive_source_found`, and 113
`source_unavailable` cells; it uses no `searched_no_endorsement_found` cells.

### `build_manifest.json`

Records the fixed completed-results cutoff, the pending candidate-snapshot and event horizons,
schema version, generation timestamp, source and artifact SHA-256 checksums, known archive
uncertainty, deliberately excluded election calls, and the separately enumerated pending event.

### `data/reference/candidacy_identity_ledger.csv`

Project-owned source-occurrence registry used as a build input. It records the immutable public
`candidacy_id`, its authority or project occurrence key, Contest identity, the active source-name
locator, and release-validity history. The initial project occurrence key is derived from source
position, never from a candidate name. Later name-only corrections close the old locator and append
a new one with a reason; an existing Contest cannot silently gain, lose, or rename a Candidacy. The
ledger is included among the checksummed build-manifest sources.

### `data/reference/identity_review_dispositions.csv`

One row per adjudicated machine-proposed Candidacy-to-Person link. It records `candidacy_id`, the
reviewed `target_person_id`, final `decision`, confidence, rationale, evidence URLs, and reviewer.
`confirmed` closes the proposal and publishes the Person on the modelling table; `unresolved`
closes the proposal but keeps `election_results.person_id` null because evidence was insufficient;
`rejected` closes a contradicted proposal and likewise remains null. The table is a checksummed
build input and is replayed idempotently against the append-only link history.

### Endorsement curation inputs

`data/reference/endorser_panel_curations.csv` records the approved panel, exact Person locators for
individual Endorsers, eligibility/applicability rules, and panel evidence.
`data/reference/endorsement_assertion_curations.csv` records the exact Contest/Candidacy locators,
review disposition, dates, source type, and evidence URLs behind the published assertions.
`data/reference/endorsement_coverage_curations.csv` records independently verified search work at
exact Endorser-by-Contest or Endorser-by-event/office grain, with evidence and research-report
provenance. All three are checksummed build inputs; exact locators fail closed instead of falling
back to name matching or blanket historical coverage claims.

## Sources and known coverage limits

- City of Toronto Open Data official general/by-election results and Clerk declarations for Mayor,
  Councillor, and all four trustee systems.
- Elections Canada official poll-result archives and available official summary tables.
- Elections Ontario official candidate/statistics/party CSV reports.
- City voter-statistics files for explicitly scoped municipal turnout.
- City Council attendance/voting records and reconciled historical rosters for municipal
  incumbency evidence.
- City Clerk candidate-list JSON snapshots for pending 2026 Mayor and City Councillor Candidacies.
- Endorsement evidence retained with each audited assertion, using original Endorser publications
  where available and attributable contemporaneous sources where archival recovery requires them.

The City trustee by-election index begins in 2012. Event enumeration for 2003–2011 is therefore
marked `uncertain`; this is an archive-level limitation, not a license to invent event placeholders.
Federal legacy wide files that do not provide a structured party/incumbency field retain
`not_reported`/null unless an official structured summary is joined and strictly reconciled. In
this release, 2004 party/incumbent fields are joined to Elections Canada Table 12, and 2008–2014
Toronto by-election party labels are joined to Elections Canada Historical Results. Those early
by-election pages do not report incumbency, so that source field remains null.

Trustee result sources do not report a structured incumbent flag, and a complete historical roster
for all four boards has not been acquired. Trustee `incumbent` is therefore null rather than
inferred from repeated names or prior winners.

## Quality gates

The build fails on completed election dates outside 2003-01-01 through 2026-08-20, or on a
post-cutoff Candidacy that is not the explicitly allowed pending 2026-10-26 municipal event. Pending
rows must have `result_status=pending`, a complete official candidate roster, null result metrics,
and no Acclamation. The build also rejects broken foreign keys, duplicate stable identities,
missing persistent `source_candidacy_id` values, or disagreement between repeated
Event/Contest/Electoral district labels and their keyed dimensions. It rejects invalid Party
relationships, negative votes, non-reconciling totals/shares, invalid Acclamation nulls, resolved
single-seat Contests without exactly one elected Candidacy, mismatched turnout operands, ballots
exceeding eligible electors, unsupported published Person/incumbency links, or invalid/materially
out-of-bounds available geometry.

Endorsement gates enforce exact Endorser, Contest, Candidacy, and optional Person foreign keys;
Mayor/City Councillor targets only; stable, unique fact edges; facts derived exactly from confirmed
assertions; and one non-contradictory coverage cell per Endorser and Contest. Source adapters also
enforce their exact event/district manifests and expected row counts against the real official
archives. All release tables are serialized to a temporary sibling directory before any output is
promoted.
