# Build notes

Record of how the v2 relational release is built. See `docs/data-dictionary.md` for the public
schema, `CONTEXT.md` for domain language, and `docs/adr/` for load-bearing decisions.

## Status: complete through 2026-08-20

The release covers completed in-scope Toronto election events from 2003-01-01 through 2026-08-20,
plus registered candidates for the pending 2026 municipal election: Mayor, City Councillor,
trustees for all four publicly funded School Boards, MPs, and MPPs. It contains 5,731 Candidacies
in 881 Contests across 55 Election events. General elections, by-elections, acclamations, and
legally void results are retained; pending registrations are distinguished from final results.

## Public artifacts

The pipeline publishes eight tables to `data/out/`, each as CSV and Parquet:

- `election_results.*` — modelling-ready Candidacy rows;
- `election_events.*` and `contests.*` — event and Contest dimensions;
- `electoral_districts.*` — as-run Contest geographies, with explicit missing-geometry status;
- `parties.*` — jurisdiction-scoped Party identities;
- `people.*` and `candidacy_person_links.*` — persistent, audited identity records; and
- `office_tenures.*` — evidence used to derive same-office incumbency.

`build_manifest.json` records the fixed cutoff, source and artifact checksums, row counts, known
archive uncertainty, and deliberately excluded calls. Release files are fully serialized in a
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

The deleted v1 files `toronto_election_results.*`, `subdivision_boundaries.parquet`, and
`council_composition.csv` are not release artifacts. Their old command-line publishers and checks
are retired and direct maintainers to the v2 pipeline.

## Build and validation

Run:

```sh
uv run python -m toronto_election_results.pipeline
uv run python -m toronto_election_results.pipeline --skip-download
```

The second command reuses the local official-source cache. The pipeline normalizes each authority
adapter, assigns persistent Candidacy occurrences, builds the relational dimensions, attaches
confirmed Person links, derives incumbency, adds available Contest-level geometry, and applies the
release-wide quality gates before publication.

The quality gates cover primary/foreign keys; fixed election-date cutoff; agreement of denormalized
Event, Contest, and Electoral district labels; Party links; outcome and vote reconciliation;
turnout; evidence-backed incumbency; active confirmed Person links; and geometry validity and City
containment.

Core v2 modules are `municipal`, `trustees`, `federal`, `ontario`, `schema`, `candidacy_ledger`,
`identity_review`, `identity_dispositions`, `reported_incumbency`, `district_geometry`, `release`,
`release_validation`, `build_manifest`, and `pipeline`.

## Provenance and known uncertainty

Official authority files remain under `data/raw/` and normalized cache inputs under
`data/interim/`. The project-owned `data/reference/` files retain audited identity and roster
evidence; the build manifest includes those inputs where they affect the release.

The pre-batch current-code baseline had 198 identity-curation assertions, 589 occurrence pins, and
1,111 unresolved Candidacies. An initial downstream complaint led to priority evidence curation;
the workflow used lightweight evidence agents, independent adjudicators, and a collision/complement
audit before accepting links. The exact-scope batch independently accepted 179 occurrence links
across 173 existing People (62 federal MP, 54 Ontario/trustee, and 63 municipal). This produced 371
curation assertions and 768 unique occurrence pins, with 932 proposals left for explicit review.

Every one of those 932 proposals then received an occurrence-level independent disposition stored
in `data/reference/identity_review_dispositions.csv`. Later evidence-backed curations can supersede
and remove a now-stale disposition while retaining the durable curation evidence. A later
downstream council-history audit supplied explicit candidate-history evidence for 34 previously
held occurrences; those holds were re-reviewed independently and revised without deleting their
earlier review history. A second, outcome-consequential council audit then reviewed 12
former-officeholder cases: nine additional links were confirmed immediately. A targeted follow-up
subsequently found explicit bridges for David Caplan, Avtar Minhas, and Christopher Mammoliti,
completing all 12. A separate candidate-controlled biography and official-record audit linked
Chloe Brown's 2016 and 2026 council Candidacies to her 2022 and 2023 mayoral Candidacies while
preserving the exact `Chloe-Marie Brown` ballot names. The current dispositions are 143 confirmed,
783 reviewed but left unresolved for insufficient identity
evidence, and five rejected because same-event candidate collisions contradicted the proposed
Person. The completed-event review has no active `proposed` links; 77 proposed links belong only to
pending 2026 Candidacies and remain null until adjudicated. Across final and pending rows, 866
Candidacies have null Person IDs. Those nulls are review outcomes or pending proposals, not missing
election results. No blanket name merges were made, and the workflow does not claim that a hold
proves two occurrences are different people. Seven elected Candidacies remain null because their
proposed identities did not meet the evidence threshold.

The link-history table also retains 33 older null-Person bootstrap review flags for reported
incumbents that lacked a safe prior elected match. Those flags coexist with a confirmed Person link
and do not create additional nulls in `election_results`; this is why the active `unresolved` link
row count is 817 rather than 783.

Two unchanged cached builds produced byte-identical Candidacy-ledger and public CSV/Parquet
artifacts. The build manifest checksums the disposition table alongside the official and curated
source inputs.

Toronto's trustee by-election archive begins in 2012, so event enumeration for 2003–2011 is marked
uncertain. No result rows are invented for that gap. Trustee incumbency remains null until a
complete, evidence-backed historical roster is acquired. Geometry is never treated as required for
district identity, and poll/subdivision-level results and boundaries are outside the release scope.

Elections Canada's raw incumbent marker is preserved as `incumbent_reported`, but it is not treated
as final-sitting-roster evidence: the source marks some former MPs who no longer held office.
Modelled federal incumbency is therefore true only when a confirmed Person's prior election win has
not been superseded within that parliamentary cycle. Federal non-members remain null because those
event rosters are intentionally incomplete, and the 2004 general election has no modelled true
incumbents until an independently evidenced pre-dissolution roster is added.
