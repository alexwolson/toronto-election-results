# Historical Ward Geographic Names

Date: 2026-08-27

## Purpose

Make candidate histories geographically understandable by pairing every Toronto
City Council and school-board trustee ward number from 2003 onward with the
geographic name used for that election-era ward.

The public display format is `Ward <number> — <geographic name>`. The work does
not rename, reproject, or otherwise alter results before 2003. In particular,
pre-2003 occurrences in mayoral candidate histories remain exactly as they are.

## Scope

This work covers:

- Toronto City Council general elections and by-elections from 2003 through the
  current election;
- trustee general elections and by-elections administered for the Toronto
  District School Board, Toronto Catholic District School Board, Conseil
  scolaire Viamonde, and Conseil scolaire catholique MonAvenir from 2003 through
  the current election;
- every boundary regime under which those results were recorded; and
- candidate-history displays on the mayoral, council, and trustee pages, plus
  current ward headings that consume the same canonical labels.

This work does not:

- reproject results between the 44-ward and 25-ward City systems;
- invent east/west or neighbourhood distinctions that were not used at the
  time;
- alter provincial, federal, or mayoral district labels;
- enrich any result before 2003; or
- expose research provenance as badges or notes in the public interface.

## Naming policy

Council wards use the contemporaneous City geographic name. Shared names in the
44-ward system remain shared: for example, both `Ward 19 — Trinity-Spadina` and
`Ward 20 — Trinity-Spadina` are historically correct. Spelling and punctuation
follow the contemporaneous authoritative source rather than current typography.

Trustee wards use an official board-specific geographic name when one was
published. If the official material identified only `Ward <number>`, Results
derives a geographic name from the contemporaneous City wards represented by
that trustee ward. Derived names:

- use City-ward names from the same election-era boundary regime;
- preserve the source crosswalk order;
- collapse duplicate names, including paired 44-model City wards with one
  shared name; and
- separate multiple distinct areas with semicolons.

An official trustee name takes precedence over a derived composite. The
constituent City wards remain available as structured supporting data even when
an official name is displayed.

By-elections inherit the boundary regime in force on their election date.

## Canonical data ownership

The Results repository is the only owner of historical ward naming and
crosswalk logic. Backend passes the finished fields through, and Frontend only
renders them.

Results will maintain two canonical, sourced reference datasets rather than
hard-coded dictionaries:

### City ward names

One row per City ward and City boundary regime, containing at least:

- `boundary_regime`;
- `official_district_id`;
- `geographic_name`;
- source authority;
- source URL; and
- the date, election year, or validity information needed to establish that the
  source applies to the regime.

The dataset covers the 44-ward and 25-ward regimes. It records the historical
name without asserting continuity between regimes.

### Trustee ward crosswalks

One row per represented board, trustee boundary regime, and trustee ward,
containing at least:

- `represented_body`;
- `boundary_regime`;
- `official_district_id`;
- an official geographic name when one exists;
- the applicable City boundary regime;
- ordered constituent City ward identifiers;
- source authority;
- source URL; and
- applicable date, election year, or validity information.

The existing 2026 trustee crosswalk becomes part of this historical structure
rather than remaining a one-election special case.

## Source hierarchy

Mappings use authoritative contemporaneous material in this order:

1. City election ward maps and school-board reference charts;
2. official board maps, boundary determinations, and archived board material;
3. City GIS and legislative records used to corroborate or fill gaps in the
   first two source families.

Modern names are never projected backwards. Every published catalogue row must
have an authoritative source. A missing or contradictory mapping is a build
failure, not permission to guess.

## Canonical output model

The existing authority-reported district label remains intact. Enriched
district records add distinct fields with these meanings:

- `district_name`: the original canonical result label, such as `Ward 19`;
- `geographic_name`: the geographic portion, such as `Trinity-Spadina`;
- `district_display_name`: the public label, such as
  `Ward 19 — Trinity-Spadina`; and
- `name_provenance`: `official` or `derived_from_city_wards`.

For modern source rows where `district_name` already contains the number and
name, enrichment preserves it and produces the same normalized
`district_display_name`. For offices and dates outside this feature's scope,
the new enrichment fields are null and consumers continue using
`district_name`.

Source and crosswalk fields live in the reference data and district dimension;
they do not need to be repeated on every candidacy row. Feed builders join by
canonical district identity rather than repeating naming logic.

The Results district schema and affected release schemas receive explicit
version bumps. Readers must reject unknown versions rather than silently
discarding new fields.

## Build and validation

The Results build validates all of the following:

- each 2003-or-later council or trustee district resolves to exactly one
  catalogue entry;
- no catalogue key is duplicated;
- each trustee component City ward exists in the declared City boundary
  regime;
- every official or derived display label is non-empty;
- source authority and source URL are present;
- trustee names are deduplicated without changing their first-occurrence order;
- by-elections resolve against the correct active regime;
- no council or trustee result before 2003 is enriched; and
- no other office type receives a ward display label from this process.

The catalogue may contain a complete regime beyond the subset of wards that
appears in candidate histories. Completeness is measured against all canonical
2003-present council and trustee districts, not only current candidates' linked
histories.

## Release and downstream data flow

Results enriches its electoral-district dimension and emits the nullable
`district_display_name` field in each public `past_elections` occurrence. The
field is populated for in-scope council and trustee occurrences and null for
other offices and pre-2003 occurrences. Results retains `district_name` for
auditability and consumers that require the original label.

Backend accepts the new Results schema versions and passes both fields through
to its council and trustee products without interpreting boundary regimes or
constructing names.

Frontend feed types require the nullable `district_display_name` field under
the new schema. The candidate-history component renders it for in-scope council
and trustee occurrences and uses the existing `district_name` for other
offices. This null fallback is schema presentation, not historical crosswalk
logic, and keeps all geography decisions outside Frontend.

Release order remains Results, then Backend, then Frontend deployment. Polling
does not participate in this feature unless its normal release pin must be
refreshed as part of a coordinated deployment.

## Public presentation

Candidate-history entries present office and district as separate readable
elements. Examples:

- `Councillor` / `Ward 19 — Trinity-Spadina`;
- `TDSB Trustee` / `Ward 10 — Trinity-Spadina`; and
- `Viamonde Trustee` / `Ward 3 — Centre`.

Long derived trustee labels use semicolons between areas and wrap naturally
onto additional lines. The interface does not display provenance badges or
technical coverage notes. Current ward headings use the same canonical display
label when they consume an enriched district.

## Testing and acceptance criteria

Automated coverage includes:

- both 44-model Trinity-Spadina council wards;
- a TDSB ward whose constituent City wards collapse to one geographic name;
- a multi-area TCDSB ward;
- large French-board wards, including official short names where available;
- council and trustee by-elections;
- schema-version and pass-through tests in Backend and Frontend;
- responsive rendering of a long trustee label;
- proof that pre-2003 mayoral history is unchanged; and
- a completeness assertion for every canonical 2003-present council and
  trustee district.

The feature is complete when every in-scope occurrence displays a sourced
number-plus-name label, all downstream repositories consume the Results-owned
field without local crosswalks, and the coordinated test suites and production
build pass.
