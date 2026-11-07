# Build notes

How the release is built. See `docs/data-dictionary.md` for the public schema, `CONTEXT.md` for
domain language, and `docs/adr/` for load-bearing decisions. `docs/provenance.md` records what
code, AI agents and the authors each did at every stage.

## Status

The release covers completed in-scope election events within today's City of Toronto, from each
level's last general election before amalgamation (federal 1993-10-25, municipal 1994-11-14,
Ontario 1995-06-08) through the 2026-10-26 municipal general election. It covers Mayor, City
Councillor and the councils before amalgamation, trustees of the School Boards serving the area,
MPs and MPPs. It contains 8,099 Candidacies in 1,385 Contests across 80 Election events. General
elections, by-elections, acclamations and legally void results are included.

## Public artifacts

The pipeline publishes thirteen tables to `data/out/`, each as CSV and Parquet:

- `election_results.*`: modelling-ready Candidacy rows;
- `election_events.*` and `contests.*`: event and Contest dimensions;
- `electoral_districts.*`: as-run Contest geographies, with explicit missing-geometry status;
- `parties.*`: jurisdiction-scoped Party identities;
- `people.*` and `candidacy_person_links.*`: persistent, audited identity records;
- `person_external_ids.*`: Wikidata, ParlInfo and House of Commons IDs for People who sat in the
  House;
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
`council_tenures`, `reported_incumbency`, `predecessor_incumbency`, `district_geometry`, `release`,
`release_validation`, `build_manifest` and `pipeline`.

## Identity

The release has 5,078 People. 5,072 hold at least one Candidacy, and six hold only an Office
tenure from a Council roster. Each of those six was appointed to fill a vacancy and has no
candidacy in the release. 7,686 Candidacies have a confirmed Person and 413 have none: 411
were reviewed and left unresolved for insufficient evidence, and two were rejected. Five of the
413 are elected Candidacies whose proposed identities did not meet the evidence threshold. These
nulls are review outcomes, not missing results. Each held run's disposition names the later
research passes whose scope included it, so a reader can see which sources were searched.

Confirmed links come from the official record behind each Candidacy, authority-reported incumbency
continuity, Council rosters and adjudicated curations. The curations are 595 identity assertions
over 1,181 occurrences, the two 2026 career reviews (through which 21 mayoral and 28 trustee
candidates have confirmed earlier races in the release) and 1,643 occurrence-level dispositions in
`data/reference/identity_review_dispositions.csv` (1,134 confirmed, 505 unresolved and 4 rejected).
A disposition is not applied where a career review's confirmation or a person-record merge
covers the same Candidacy, but a later disposition does replace a career review's hold. No
blanket name merges are made, and a hold does not claim that two occurrences are different
people.

Without a person-specific source, two runs are joined on structure only under these rules, which
are the same for every year and office:

- Two runs for the same office type need the same, a successor or an overlapping ward or riding
  (at least about a fifth of either by area where the release has the boundaries), the same Party
  where Parties apply, no more than one general election between, a name that is not common, and
  no competing candidate of that name. Where the two runs print the name differently, the forms
  must evidently be one name: a common nickname, a middle name or initial added or dropped, the
  same words in another order, or a nickname printed beside the full name.
- A House of Commons run and an Ontario legislature run need the same riding at both levels
  within two years, the federal and Ontario parties of one name or no party at either, an
  uncommon name, and no other Person of that name in the release
  (`docs/research/federal-provincial-holds-2026-11-01.md`).
- Any other two offices need a person-specific source.

Each link's `evidence_basis` records what it rests on. Of the 7,686 confirmed links, 4,941 are a
Person's own record, the Candidacy from which the Person was built, so nothing is joined. Of the
2,745 that join a Candidacy to a Person, 355 rest on an official record (221 on incumbency that
the election authority reported, 131 on a Council roster and three on one archive record printed
twice), 1,825 on a source about the person and 565 on the structural rules alone. The basis of
each curated link is recorded in `data/reference/identity_link_basis.csv`, and a test checks the
office, Party and election-gap rules on every structural link; name commonness and ward overlap
are left to the reviewers. When the check was first run, in November 2026, 12 Persons joined
runs for different offices on results alone and 12 same-office links failed the gap or Party
rule. Sources now support the 12 Persons and three of the links, and the other nine runs are
held; see `docs/research/structural-rule-check-2026-11-07.md`.

An audit of a random sample of links
([`docs/verification/link-audit-2026-11-03.md`](verification/link-audit-2026-11-03.md)) found no
join of two different people among 120 sampled joins, which puts a one-sided 95% upper bound of
3.9% on the share of false merges. A census of the 136 joins made after that sample
([`docs/verification/link-audit-2026-11-07.md`](verification/link-audit-2026-11-07.md)) found
none either, and with the older joins weighted by the sample the bound across all 2,614 joins in
the release is 3.7%. Of 40 sampled pairs of Persons with the same first and last
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
names the roster entry, so the tenure belongs to their Person. Once every Candidacy has its
Person, the build dates each roster row from the Person's latest Council win in the term, or, for
the 17 members Council appointed to fill a vacancy, from the appointment in
`data/reference/council_appointments.csv`. Dating from an exact-name win alone missed wins printed
under another form of the name and could reach back past the term: Joe Mihevc's 2014 win in Ward
21 had dated the Ward 10 seat Council appointed him to in 2022.

A council by-election has no roster of its own. Earlier releases took the latest winner of each
ward as the council sitting at each by-election. That list kept the member whose seat had fallen
vacant, such as Rob Ford at the Ward 2 by-election of July 2016, months after his death, and
Raymond Cho at the Ward 42 by-election of February 2017, after he had left for the legislature.
It also left out members Council had appointed. It could not prove a candidate's absence, so
council by-election incumbency was null, and its 343 rows were Office tenures. The release now
drops those rows and settles each by-election once every Candidacy has its Person: a member
sitting the day before polling won a seat at the term's first general election or a by-election
since, or was appointed since, so a candidate whose Person did neither was not an incumbent. The
build fails if a candidate's Person did either. None did, so the 136 council by-election
Candidacies with a Person have `incumbent=false`, and the 17 without one stay null. A member who
left during a term now has no Office tenure for it: the general-election rosters list only the
members still sitting at the end of a term.

Three fields describe the seat behind each incumbency: whether Council appointed the member to
it (`incumbent_appointed`), its district (`incumbent_held_district_id`), and whether the member
is running for another seat (`incumbent_changed_district`). Within one Boundary regime a change
of district is a different `district_id`. Across the 2018 change from 44 council wards to 25, the
release counts the polls (voting subdivisions) of the 2014 ward: the member kept the seat if the
new ward holds more of them than any other ward. For the other boundary changes the release has
no polls of the earlier districts, so the field is null.

The roster for the November 13, 2000 general election is `data/reference/council_roster_2000.csv`.
It lists the mayor and the 57 councillors in office that day: the certified 1997 winners, the 1998
by-election winner for a third East York seat that provincial legislation added, the 1999
by-election winner after Frank Faubert's death, and the two members Council appointed in 2000, Paul
Valenti for Judy Sgro and Cesar Palacio for Dennis Fotinos. The City's list of councillors for the
1998-2000 term names these 57 and the three who left, and no one else.

The 1997 election was the amalgamated council's first, so `incumbent` is null for it, and ADR 0012's
`predecessor_incumbent` records whether a candidate sat on a council the new City replaced.
`data/reference/predecessor_rosters_1997.csv` lists the members of Metro Council and the six former
councils on 9 November 1997: the 1994 winners, less Mario Sergio and John Hastings, who left for the
legislature in 1995, plus George Mammoliti, elected to Sergio's seat, and Vincent Crisanti, appointed
to Hastings's. Of the 1997 council candidates with a Person, 81 had sat on a predecessor council and
101 had not; two of the mayoral candidates, Barbara Hall and Mel Lastman, were sitting mayors. See
`docs/research/predecessor-rosters-1997-2026-11-07.md`. The 1994 municipal elections are there to
supply this and have no incumbency of their own.

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

The results were compared, Contest by Contest, with two datasets compiled independently of the
release: Semra Sevi's federal and Ontario candidate files for the Toronto ridings (federal
elections from 1993 to 2021, Ontario from 1995 to 2018) and the Canadian Municipal Elections
Database for Toronto's mayor and council races from 1994 to 2022. Of 749 Contests, 681 agree on
every name, vote total and winner. Each difference in the other 68 was checked against the
authority's results; none is an error in the release. See
[`docs/verification/external-reconciliation-2026-11-07.md`](verification/external-reconciliation-2026-11-07.md).

District shapes cover every Council ward from 2000, every trustee ward from 2000 and every federal
and Ontario riding from 2004 and 2007 respectively; the data dictionary's `electoral_districts`
section gives the sources and the gaps. The 2000 trustee wards rest on an inference from poll
totals, set out in `scripts/derive_trustee_wards_2000.py`.

The City's archived index of past results lists every election it ran from 1998, so event
enumeration is complete from 1998. The former municipalities left no comparable index, so their
by-elections from 1995 to 1997 are marked uncertain; a search of the Toronto Star found one, North
York Ward 1 in 1995, which is included. No result rows are invented for a gap. Geometry is never
treated as required for district identity, and poll/subdivision-level results and boundaries are
outside the release scope.

Trustee incumbency is recorded only for the 20 sitting trustees who ran in 2026. Every other
trustee `incumbent` stays null until a complete historical roster is acquired.

Federal incumbency comes from the House of Commons membership in
`data/reference/house_of_commons_members.csv`: one row per member's term in each Parliament from
the 35th to the 45th, with the riding and the first and last days of the term. The 36th Parliament
on come from the House of Commons members export and the 35th from ParlInfo, the Library of
Parliament's database of parliamentarians; `scripts/build_house_of_commons_members.py` builds the
file. For each federal event after 1993 the sitting roster is every member whose term covers the
day before dissolution, or the day before polling for a by-election, in any riding. Each Toronto
term is tied to the Person who won that seat on the day the term began; every Toronto winner from
1993 on has such a term, which becomes that Person's Office tenure with the House's dates. A
confirmed Person is then `incumbent=true` if they hold a sitting term and `false` otherwise. The
build fails if a candidate's name fits a sitting member who is not their Person, so a namesake
elsewhere in Canada cannot become an incumbent or a non-incumbent unreviewed; no candidate's name
does. Of the 1,743 federal Candidacies, 206 are incumbents, 1,242 are not, and 295 are null: the
214 at the 1993 general election and 81 with no Person.

The 1993 federal and 1994 municipal elections, the first of their levels in the release, are there
to give the next elections their incumbency and have none of their own; it would need the 34th
Parliament and the councils elected in 1991.

Ontario incumbency from 1996 on comes the same way from the Legislative Assembly's membership in
`data/reference/ontario_legislature_members.csv`: one row per member's riding term in each
Parliament from the 36th, from the profiles on ola.org. ola.org serves those pages only to a
browser, so `scripts/ola_members.js` reads them in one and saves a file that
`scripts/build_ontario_members.py` turns into the reference table. Read on 7 November 2026, it
holds 1,086 terms of 431 members. The roster rules are the House's, with two additions. A term
that begins when a riding is renamed during a Parliament extends the tenure of the member's
election, as when Broadview—Greenwood became Toronto—Danforth in 2000. And a member whose term no
winner in the release began can be tied to a Person, or set apart from one, only by sources named
in `ontario_rosters.py`: John Tory, who sat for Dufferin—Peel—Wellington—Grey from a 2005
by-election and ran in Don Valley West in 2007, is tied to his Person, and Dave Smith of
Peterborough—Kawartha is set apart from David Smith of Scarborough Centre, since the two sat
together from 2022. Every Toronto winner from 1995 on has a term. The roster disagrees with
Elections Ontario's flags for two Candidacies, both sitting members the flags missed: Morley Kells
in 1999 and Brad Duguid in 2011. The 1995 general election, the first Ontario election in the
release, comes before the 36th Parliament and keeps Elections Ontario's own incumbent flags, which
the release uses only where every Candidacy of an event has a flag and every flagged incumbent has
a confirmed Person.

Elections Canada's raw incumbent marker is preserved as `incumbent_reported` but is not used: it
marks some former MPs who no longer held office. Two flags that contradict the record are
corrected by pinned corrections that fail the load if the source changes: Elections Canada's 2015
file marks Natalie Hunt, the Green candidate in Don Valley West, as an incumbent beside the sitting
member, and Elections Ontario's 1999 file marks John Sewell, who never sat in the legislature. See
[`docs/verification/same-name-review-2026-11-03.md`](verification/same-name-review-2026-11-03.md).

The House of Commons publishes its member lists on its website, whose Important Notices set out
the terms for reproducing its content, and ParlInfo is the Library of Parliament's. The release
keeps only the facts it uses from them: each member's name, riding, province, caucus and dates of
service, with the House's person ID and the source of each row.

The Legislative Assembly of Ontario's terms of use
(<https://www.ola.org/en/office-assembly/copyright-privacy>) let anyone display, print and
reproduce the Assembly's materials without charge where the use is reasonable, fair and
non-commercial and credits the Assembly. The release keeps only facts from the member profiles:
each member's name, riding, party and dates of service, with the profile's URL as the source of
each row.
