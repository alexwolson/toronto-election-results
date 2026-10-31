# Data dictionary — Toronto Election Results v2.1

The release covers completed election contests wholly within the City of Toronto through
2026-10-26 (the inclusive election-date scope, not a claim that future outcomes are known). Under
ADR 0010, municipal coverage starts with the 1994-11-14 elections: the mayors and councils of East
York, Etobicoke, North York, Scarborough, the former City of Toronto and York, and Metropolitan
Toronto Council, followed by the amalgamated City's 1997 and 2000 Mayor and Councillor elections.
School trustee elections are included for 1994 (the six boards of education, the Metropolitan
Separate School Board, the Metro Toronto French Language School Council and the French-Language
Section of the Separate School Board), 1997 (the four new District School Boards) and 2000 (39
single-member wards). Those municipal results come from the City's archived results pages, which
carry no elector or ballot counts, so turnout fields are null. The archive's 1994 and 1997
school-board sections lack seat counts, ward labels and some whole Contests, and it omits eight
1994 council Contests (North York council wards 3–5 and five Metro wards, all but two acclaimed),
so those rows come from the Toronto Star's printed final results (16 November 1994 and 14 November
1997, read from ProQuest Historical Newspapers) and carry `source_authority = Toronto Star`; the
reconciliation is described in `docs/research/school-boards-1994-1997-2026-10-29.md`. The archive
also lists four 1994 North York trustee candidates under council Wards 1 and 2; those council rows
are not published. For the 1994 French-language areas shared by two municipalities, the archive
page of the municipality that ran the area gives the area's totals and the other page gives its own
share; the Star printed only the first municipality's polls. Those Contests use the archive's
totals and are `complete`, except the Metro French council's Etobicoke-City of York seat: the
archive has no Etobicoke figures, adding York's polls to the Star's figures reverses the order, and
the winner is left null (`partial`). The 1997 MonAvenir Metro 2 Contest is `partial` because the
Star and the archive disagree. The 1994 Toronto Ward 3 race carries the final judicial recount
(Mario Silva 2,979, Tony O'Donohue 2,969, Globe and Mail of 16 December 1995) in place of the
archive's election-night count; see `docs/research/partial-results-second-pass-2026-11-01.md`.
East York's 1994 council and school wards, five 1994
Toronto Board of Education wards and every 1997 council ward elected two members
(`seats_available = 2`), as did several 1994 French-language areas. Where the archive lost a 1994
Metro ward label, the label is taken from a secondary source and recorded in
`data/reference/municipal_archive_results.csv` (`district_label_source`). Under ADR 0010, provincial (MPP) coverage starts with the 1995-06-08
Ontario general election, including the 1996, 1997 and 2001 Toronto by-elections, and federal (MP)
coverage starts with the 1993-10-25 general election, including the 1996 Etobicoke North and
1999 York West by-elections.
The 1996 Etobicoke North and 1999 York West federal by-elections are pinned from Elections
Canada's official voting results reports. A District keeps one name within its Boundary regime, so federal district 35008
is Broadview—Greenwood in both 1997 and 2000, although Elections Canada ran the 2000 election
under its new name, Toronto—Danforth. It also includes the 2026-10-26 Toronto municipal general election: Candidacies come from the
City's official candidate list and vote totals from the City Clerk's Declaration of Results dated
2026-10-29 (`data/reference/results_2026_declaration.csv`, transcribed from the pinned PDF by
`scripts/transcribe_2026_declaration.py`). The declaration gives no electorate or ballots cast, so
those fields are null for 2026 until the City publishes its final voter statistics. Four officially
declared trustee Acclamations are final with null vote totals. The dataset includes Mayor, City
Councillor, all four School Board Trustee systems, MP, and MPP elections. General elections,
by-elections, acclamations, and legally void contests are in scope. Poll/subdivision records are
used only to produce Contest totals and are not published.

The release contains 8,099 Candidacies, 1,385 Contests, and 80 Election events. All Candidacies
have final results; the 2026 municipal event contributes 361 Candidacies in 55 Contests. Two void historical Contests have no Candidacy rows.
Evidence-backed Endorsement companion tables cover Mayor and City
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
| `seats_available` | integer | never | Members the Contest elects, from the source or governing statute (ADR 0011). `1` for every Contest from 2003 onward. In a multi-seat Contest voters may cast several votes, so `vote_share` is a share of votes, not voters. |
| `eligible_electors` | integer | pending/unavailable/inapplicable | Authority count at the stated `turnout_scope`. |
| `ballots_cast` | integer | pending/unavailable/inapplicable | Electors voting at the same scope as `eligible_electors`. |
| `turnout` | float | pending/either operand unavailable | `ballots_cast / eligible_electors`. |
| `turnout_scope` | string | turnout unavailable | Qualification/geography shared by both turnout operands. |
| `elected` | boolean | pending or unresolved official outcome | Authority-certified result; not blindly rederived from vote maximum. Where a source lists votes without marking winners, the top `seats_available` totals are elected and candidacies tied across the last seat stay null. A `partial` Contest whose sources cannot establish the winner leaves every Candidacy null. |
| `acclaimed` | boolean | never | True only for an official Acclamation. |
| `outcome_method` | enum | never | `pending`, `vote`, `acclamation`, `void`, or another authority disposition. |
| `result_status` | enum | never | `final` for certified/historical outcomes; `pending` for a candidate snapshot without declared results. |
| `coverage_status` | enum | never | `complete`, `partial`, or `source_missing`; independent of legal outcome. A `partial` Contest may carry null `votes` where its only source omits them. |
| `incumbent` | boolean | insufficient identity/roster evidence | Same Office type and Represented body in the last valid pre-event roster. |
| `incumbent_office_tenure_id` | string | not incumbent/unknown | Supporting Office tenure for `incumbent=true`. |
| `incumbent_reported` | boolean | authority does not report it | Unmodified source flag; the modelled `incumbent` field uses project semantics. |
| `predecessor_incumbent` | boolean | outside a first amalgamated election, or insufficient evidence | ADR 0012: `true` when the Person sat, the day before polling, in a designated predecessor body for the same Office type. Set only for the November 10, 1997 first elections of the amalgamated bodies; null until predecessor rosters are acquired. |
| `predecessor_office_tenure_id` | string | not a predecessor incumbent | Supporting predecessor Office tenure for `predecessor_incumbent=true`. |
| `source_authority` | string | never | Organization responsible for the row's record: the official authority, or `Toronto Star` where only the newspaper's printed results survive (most 1994 and 1997 trustee Contests, eight 1994 council Contests). |
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
Coverage status, `seats_available`, vote total, turnout operands/scope, and source fields.
This table also contains pending Contests with null result metrics and void/source-missing Contests
that correctly have no Candidacy row.

### `people`

The persistent identity registry: opaque `person_id`, preferred name, active/deprecated status,
visible redirect target, and creation release. An active Person without a Candidacy holds an
Office tenure needed to classify Incumbency. A Person name never rewrites a historical ballot name.

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
contains 161 assertions: 160 confirmed and one unresolved assertion whose supported target has no
published Candidacy row.

### `endorsements`

The 160 adjudicated positive facts, at one exact `(endorser_id, contest_id, candidacy_id)` edge per
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
Contest-specific search occurred. The current release contains 670 `not_applicable`, 145
`not_searched`, 1,277 `partially_searched`, 207 `comprehensive_source_found`, and 113
`source_unavailable` cells; it uses no `searched_no_endorsement_found` cells.

### `build_manifest.json`

Records the inclusive election-date coverage horizon, the pending candidate-snapshot and event horizons,
schema version, generation timestamp, source and artifact SHA-256 checksums, known archive
uncertainty, deliberately excluded election calls, in-scope results awaiting acquisition, and the
separately enumerated pending event.

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

### Career review inputs

Two cohort reviews researched the earlier candidacies of everyone on the certified 2026 Toronto
mayoral ballot and in the 2026 trustee field. `data/reference/mayoral_career_cohort_2026.csv` and
`data/reference/trustee_career_cohort_2026.csv` freeze the two fields. The review tables record
each candidate's review status and limitations, and the decision tables hold one adjudication per
earlier race found (`confirm`, `hold`, `split` or `reject`) with its identity bridge and result
source. Confirmed races inside the release become curated identity assertions in
`candidacy_person_links`. Each candidate has an independent discovery report and verification
report under `docs/research/mayoral-career/2026/` or `docs/research/trustee-career/2026/`.

The trustee review considered Toronto candidacies from 2003 onward. The mayoral review researched
each candidate's full Canadian electoral career, so some of the races it confirmed lie outside the
release's coverage, such as Olivia Chow's 1991 Metro Council race. Those decisions have
`ingestion_action` `out_of_scope` and are not published.
`data/reference/mayoral_career_occurrence_mapping.csv` maps every confirmed race inside the
coverage (`reuse_existing`) to its Candidacy. A review's `confirmed_count` counts all of its
confirmed races, including those outside the coverage.

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
- The City of Toronto's archived results pages for the 1994, 1997 and 2000 municipal elections
  (Internet Archive captures of toronto.ca and city.toronto.on.ca), transcribed by
  `scripts/transcribe_municipal_archive.py` into `data/reference/municipal_archive_results.csv`.
  The 2000 school trustee pages were transcribed by hand into
  `data/reference/vote2000_trustee_pages.csv`, with each page's capture timestamp and heading as
  shown. The 2000 trustee wards have no ward-to-council-ward crosswalk, so their districts carry
  no geographic name.
- Elections Canada official poll-result archives, official summary tables, and returning-officer
  validated contest totals when the poll-level export is not yet available.
- Elections Ontario official candidate/statistics/party CSV reports.
- City voter-statistics files for explicitly scoped municipal turnout.
- City Council attendance/voting records and reconciled historical rosters for municipal
  incumbency evidence.
- City Clerk candidate-list JSON snapshots for the 2026 Mayor and City Councillor Candidacies.
- The City Clerk's 2026 Declaration of Results (PDF), pinned with its transcription. It omits the
  winner's mark for Conseil scolaire Viamonde Ward 3; there, as the declaration itself states, the
  candidate with the most votes is elected.
- The same City roster acquisition includes all four trustee boards. The candidate snapshot date
  is the oldest of the three roster retrieval dates in Toronto time, not a fixed nomination date.
- Endorsement evidence retained with each audited assertion, using original Endorser publications
  where available and attributable contemporaneous sources where archival recovery requires them.

The City's archived "Previous elections results" index (Wayback Machine capture of 4 January 2012)
lists every election the City ran from 1998. Its by-elections are the 1998 East York Ward 1, 1999
Ward 16 Scarborough Highland Creek and 2001 Ward 31 Beaches-East York council by-elections and the
2002 TDSB Ward 1 (Etobicoke North) trustee by-election, and it lists none between 2003 and 2011.
Those four are transcribed from the City's archived pages into
`data/reference/municipal_by_elections_1995_2002.csv`, so municipal and trustee by-election
enumeration is complete from 1998. The former municipalities left no comparable index for 1995–1997.
A search of the Toronto Star found one by-election in that period, North York's Ward 1 on
21 September 1995, which is included from the Star's report. The Star gives only two of its six vote
totals, so that Contest is `partial` and four of its Candidacies have null `votes`. The period
1995–1997 stays `uncertain` in the build manifest.
Federal legacy wide files that do not provide a structured party/incumbency field retain
`not_reported`/null unless an official structured summary is joined and strictly reconciled. In
this release, 2004 party/incumbent fields are joined to Elections Canada Table 12, and 2008–2014
Toronto by-election party labels are joined to Elections Canada Historical Results. Those early
by-election pages do not report incumbency, so that source field remains null.

The August 31, 2026 Beaches–East York federal by-election uses the returning officer's validated
totals, including valid votes, rejected ballots, total ballots, and electors. It does not report
an incumbent indicator. The September 3, 2026 Scarborough Southwest provincial by-election uses
Elections Ontario's "Vote Totals From Official Tabulation" PDF, because the official CSV export
adds a by-election only with the next general election. The package reads no PDFs, so the
district totals are transcribed in `ontario.TABULATIONS` and the downloaded file is pinned by
checksum. Affiliations come from Elections Ontario's results page for the district. The
tabulation prints no elector count, so electors, ballots cast and turnout are null for that
Contest.

Elections Ontario's 2011 candidate CSV gives Willowdale's two Brown candidates each other's totals.
`ontario.VOTE_CORRECTIONS` restores 5,556 votes to Alexander Brown (NDP) and 297 to Amy Brown
(Freedom Party), following the Toronto Star's election-night table and Wikipedia's riding page.
The load fails if Elections Ontario changes either published figure. The City's 2017 Ward 42
by-election workbook prints declined, rejected and under-vote lines below the candidates; the
parser skips them. See `docs/research/result-corrections-2026-10-31.md`.

Trustee result sources do not report a structured incumbent flag, and a complete historical roster
for all four boards has not been acquired. Trustee `incumbent` is therefore null rather than
inferred from repeated names or prior winners.

## Quality gates

The build rejects election dates outside the coverage window: before each level's first general
election in scope (federal 1993-10-25, municipal 1994-11-14, Ontario 1995-06-08) or after October
26, 2026. Future dated Candidacies must remain pending relative to the validation date, except for
officially declared trustee Acclamations. Validated or certified results dated on or before
election day are in scope, including elections after August 20. Pending rows must have
`result_status=pending`, a complete official candidate roster, null result metrics, and no
Acclamation. The build also rejects broken foreign keys, duplicate stable identities,
missing persistent `source_candidacy_id` values, or disagreement between repeated
Event/Contest/Electoral district labels and their keyed dimensions. It rejects an unknown
`coverage_status`, invalid Party relationships, negative votes, non-reconciling totals/shares,
invalid Acclamation nulls, resolved Contests without exactly `seats_available` elected Candidacies (null `elected` is allowed only for
candidacies tied across the last seat), Acclamations with more candidates than seats, mismatched turnout operands, ballots
exceeding eligible electors, unsupported published Person/incumbency links, or invalid/materially
out-of-bounds available geometry. It rejects a candidate name that appears in two trustee wards of
one School Board at one Election event, because nobody can stand in two wards of one board and such
a pair means votes were filed under the wrong Contest.

Endorsement gates enforce exact Endorser, Contest, Candidacy, and optional Person foreign keys;
Mayor/City Councillor targets only; stable, unique fact edges; facts derived exactly from confirmed
assertions; and one non-contradictory coverage cell per Endorser and Contest. Source adapters also
enforce their exact event/district manifests and expected row counts against the real official
archives. All release tables are serialized to a temporary sibling directory before any output is
promoted.
