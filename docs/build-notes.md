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

The release has 5,078 People. 5,073 hold at least one Candidacy, and five hold only an Office
tenure from a Council roster. Each of those five was appointed to fill a vacancy and has no
candidacy in the release. 7,695 Candidacies have a confirmed Person and 404 have none: 402
were reviewed and left unresolved for insufficient evidence, and two were rejected. Five of the
404 are elected Candidacies whose proposed identities did not meet the evidence threshold. These
nulls are review outcomes, not missing results. Each held run's disposition names the later
research passes whose scope included it, so a reader can see which sources were searched.

Confirmed links come from the official record behind each Candidacy, authority-reported incumbency
continuity, Council rosters and adjudicated curations. The curations are 596 identity assertions
over 1,184 occurrences, the two 2026 career reviews (through which 21 mayoral and 28 trustee
candidates have confirmed earlier races in the release) and 1,639 occurrence-level dispositions in
`data/reference/identity_review_dispositions.csv` (1,139 confirmed, 496 unresolved and 4 rejected).
A disposition is not applied where a career review's confirmation or a person-record merge
covers the same Candidacy, but a later disposition does replace a career review's hold. No
blanket name merges are made, and a hold does not claim that two occurrences are different
people. Without a person-specific source, two runs for the same office are linked on structure
under one test for every year and office: the same, a successor or an overlapping ward or riding
(at least about a fifth of either by area where the release has the boundaries), the same party
where parties apply, no more than one general election between, a name that is not common, and
no competing candidate of that name. Where the two runs print the name differently, the two forms
must evidently be one name: a common nickname, a middle name or initial added or dropped, the same
words in another order, or a nickname printed beside the full name. A House of Commons run and an Ontario legislature run are
linked without a person-specific source only under the narrow rule in
`docs/research/federal-provincial-holds-2026-11-01.md`: the same riding at both levels within two
years, the federal and Ontario parties of one name or no party at either, an uncommon name, and
no other Person of that name in the release.

An audit of a random sample of links
([`docs/verification/link-audit-2026-11-03.md`](verification/link-audit-2026-11-03.md)) found no
join of two different people among 120 sampled joins, which puts a one-sided 95% upper bound of
3.9% on the share of false merges. Of 40 sampled pairs of Persons with the same first and last
name, 15 were one individual, and those have been merged. A review of all 177 same-name pairs
that remained
([`docs/verification/same-name-review-2026-11-03.md`](verification/same-name-review-2026-11-03.md))
joined 66 of their 155 name groups under the same standard and a second check. A review of the 71
pairs of Persons whose printed names are close but differ
([`docs/verification/near-name-review-2026-11-04.md`](verification/near-name-review-2026-11-04.md))
then joined 26 of them in 24 merges, among them three Greg Roberts Persons that the same-name review
had left apart, found one pair to be different people and left 44 undetermined. That leaves 100
same-name pairs (96 in groups that no source settled, two in groups joined in part and two that are
different people) and 45 near-name pairs.

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
Its 2006 Parkdale—High Park by-election file codes the Libertarian Jim McIntosh as Liberal, beside
the Liberal candidate; a pinned correction recodes him.

The City's archived index of past results lists every election it ran from 1998, so event
enumeration is complete from 1998. The former municipalities left no comparable index, so their
by-elections from 1995 to 1997 are marked uncertain; a search of the Toronto Star found one, North
York Ward 1 in 1995, which is included. No result rows are invented for a gap. Geometry is never
treated as required for district identity, and poll/subdivision-level results and boundaries are
outside the release scope.

Trustee incumbency is recorded only for the 20 sitting trustees who ran in 2026. Every other
trustee `incumbent` stays null until a complete historical roster is acquired.

Elections Canada's raw incumbent marker is preserved as `incumbent_reported`, but it is not treated
as final-sitting-roster evidence: the source marks some former MPs who no longer held office. Two
flags that contradict the record are corrected by pinned corrections that fail the load if the
source changes: Elections Canada's 2015 file marks Natalie Hunt, the Green candidate in Don Valley
West, as an incumbent beside the sitting member, and Elections Ontario's 1999 file marks John
Sewell, who never sat in the legislature. See
[`docs/verification/same-name-review-2026-11-03.md`](verification/same-name-review-2026-11-03.md).
Modelled federal incumbency is therefore true only when a confirmed Person's prior election win has
not been superseded within that parliamentary cycle. Federal non-incumbents stay null because those
event rosters are intentionally incomplete.
