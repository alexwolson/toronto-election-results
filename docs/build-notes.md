# Build notes

How the release is built. See `docs/data-dictionary.md` for the public schema, `CONTEXT.md` for
domain language, and `docs/adr/` for load-bearing decisions.

## Status

The release covers completed in-scope election events within today's City of Toronto, from each
level's last general election before amalgamation (federal 1993-10-25, municipal 1994-11-14,
Ontario 1995-06-08) through the 2026-10-26 municipal general election. It covers Mayor, City
Councillor and the councils before amalgamation, trustees of the School Boards serving the area,
MPs and MPPs. It contains 8,099 Candidacies in 1,385 Contests across 80 Election events. General
elections, by-elections, acclamations and legally void results are included.

## Public artifacts

The pipeline publishes twelve tables to `data/out/`, each as CSV and Parquet:

- `election_results.*`: modelling-ready Candidacy rows;
- `election_events.*` and `contests.*`: event and Contest dimensions;
- `electoral_districts.*`: as-run Contest geographies, with explicit missing-geometry status;
- `parties.*`: jurisdiction-scoped Party identities;
- `people.*` and `candidacy_person_links.*`: persistent, audited identity records;
- `office_tenures.*`: evidence used to derive same-office incumbency; and
- `endorsers.*`, `endorsement_assertions.*`, `endorsements.*` and `endorsement_coverage.*`: the
  endorsement companion tables.

`build_manifest.json` records the coverage window, source and artifact checksums, row counts,
known archive uncertainty and deliberately excluded calls. Release files are fully serialized in a
temporary sibling directory before per-file atomic promotion; a promotion error restores the
previous artifact set.

On every registry-backed rebuild, the pipeline verifies the prior `people.csv`,
`candidacy_person_links.csv`, and `election_results.csv` bytes against that release's manifest
before treating them as operational identity history. It fails closed if a file or closed link row
was changed. It also verifies the canonical Candidacy ledger against the prior manifest before
assigning IDs and refuses to recreate a missing ledger after a ledger-backed release. The ledger
advances atomically before public artifact promotion, so an old release remains a valid subset if
promotion fails. Because a changed ledger cannot be distinguished from lost correction history
using only the prior checksum, an interruption after either ledger or artifact promotion but before
the new manifest is published is deliberately not auto-recovered: restore the prior release and
ledger, or explicitly reconcile and rebuild the interrupted release before running the pipeline
again.

## Build and validation

Run:

```sh
uv run python -m toronto_election_results.pipeline
uv run python -m toronto_election_results.pipeline --skip-download
```

The second command reuses the local official-source cache. The pipeline normalizes each authority
adapter, assigns persistent Candidacy occurrences, builds the relational dimensions, attaches
confirmed Person links, derives incumbency, adds available Contest-level geometry, and applies the
release-wide quality gates before publication. Two cached builds in a row produce identical
artifacts apart from the manifest's timestamps.

The quality gates cover primary and foreign keys; the coverage window; agreement of denormalized
Event, Contest and Electoral district labels; Party links; coverage status; outcome and vote
reconciliation; turnout; evidence-backed incumbency; active confirmed Person links; and geometry
validity and City containment.

The main modules are the source adapters (`municipal`, `municipal_archive`, `trustees`, `federal`,
`federal_historical`, `ontario` and `pending_candidates`), `schema`, `candidacy_ledger`,
`identity_review`, `identity_curations`, `identity_dispositions`, `municipal_rosters`,
`reported_incumbency`, `predecessor_incumbency`, `district_geometry`, `release`,
`release_validation`, `build_manifest` and `pipeline`.

## Identity

The release has 5,198 People. 5,193 hold at least one Candidacy, and five hold only an Office
tenure from a Council roster. Each of those five was appointed to fill a vacancy and has no
candidacy in the release. 7,554 Candidacies have a confirmed Person and 545 have none: 544
were reviewed and left unresolved for insufficient evidence, and one was rejected. Seven of the
545 are elected Candidacies whose proposed identities did not meet the evidence threshold. These
nulls are review outcomes, not missing results.

Confirmed links come from the official record behind each Candidacy, authority-reported incumbency
continuity, Council rosters and adjudicated curations. The curations are 472 identity assertions
over 1,032 occurrences, the two 2026 career reviews (21 mayoral and 28 trustee candidates have
confirmed earlier races in the release) and 1,633 occurrence-level dispositions in
`data/reference/identity_review_dispositions.csv` (1,005 confirmed, 625 unresolved and 3 rejected).
A disposition is not applied where a career review or a person-record merge covers the same
Candidacy. No blanket name merges are made, and a hold does not claim that two occurrences are
different people.

The Council roster step matches each roster member to a Candidacy by exact name. It reads the
1997–2002 archive names given name first, as the archive printed them. A roster entry that no
Candidacy matches is a councillor appointed to fill a vacancy whose other races are in the
release, or a member whom the City's attendance and voting records list under another form of
their name, such as A.A. Heaps for Adrian Heaps. The identity assertion for each of these people
names the roster entry, so the tenure belongs to their Person.

## Provenance and known uncertainty

Official authority files remain under `data/raw/` and normalized cache inputs under
`data/interim/`. The project-owned `data/reference/` files retain audited identity and roster
evidence; the build manifest includes those inputs where they affect the release.

The City's 2010 TCDSB poll-by-poll workbook prints three City-ward blocks on another trustee ward's
sheet. The trustee adapter assigns each general-election block to the ward whose candidate roster
it lists, and every general-election trustee Contest from 2003 to 2022 matches the Clerk's
declaration. A release gate rejects a candidate name that appears in two trustee wards of one
board at one event. See `docs/research/tcdsb-2010-ward-assignment-2026-10-29.md`.

The City's poll-by-poll files print names surname first with no comma, so the parser cannot split
a multi-word surname by rule, and the 2016 TDSB Ward 14 by-election file prints its names given
name first. `data/reference/candidate_name_curations.csv` sets the display order of 38 such
Candidacies from the Clerk's declarations of results, which print every name given name first,
and of one name the 1997 archive page printed in reverse. A
curation may only reorder the words of `candidate_name_raw`, and the build fails if the parser
already produces it. The other two-word surname-first rows agree with the alphabetical order of
their source files, and the other names of three or more words agree with the declarations.

The City's 2017 Ward 42 by-election workbook prints declined, rejected and under-vote lines below
the candidates, and the council parser skips them. Elections Ontario's 2011 candidate CSV swaps the
totals of Willowdale's two Brown candidates; a pinned correction in the Ontario adapter restores
them and fails if the source figures change. See `docs/research/result-corrections-2026-10-31.md`.

The City's archived index of past results lists every election it ran from 1998, so event
enumeration is complete from 1998. The former municipalities left no comparable index, so their
by-elections from 1995 to 1997 are marked uncertain; a search of the Toronto Star found one, North
York Ward 1 in 1995, which is included. No result rows are invented for a gap. Geometry is never
treated as required for district identity, and poll/subdivision-level results and boundaries are
outside the release scope.

Trustee incumbency is recorded only for the 20 sitting trustees who ran in 2026. Every other
trustee `incumbent` stays null until a complete historical roster is acquired.

Elections Canada's raw incumbent marker is preserved as `incumbent_reported`, but it is not treated
as final-sitting-roster evidence: the source marks some former MPs who no longer held office.
Modelled federal incumbency is therefore true only when a confirmed Person's prior election win has
not been superseded within that parliamentary cycle. Federal non-incumbents stay null because those
event rosters are intentionally incomplete.
