# Toronto Election Results

A unified, analysis-ready history of elections within the City of Toronto. The inclusive
election-date coverage window runs through **2026-10-26** and begins with the last general election
before amalgamation for each level of government (ADR 0010): the **1994-11-14 municipal elections**
(the six former municipalities and Metropolitan Toronto), the **1995-06-08 Ontario general
election** and the **1993-10-25 federal general election**. Municipal coverage before 2003 is
Mayor, Councillor and Metro Councillor, plus the 1994, 1997 and 2000 School Board trustee
elections and the by-elections held between them. Where the City's archived results pages are
incomplete (most 1994 and 1997 school-board races and eight 1994 council races), results come from
the Toronto Star's printed final results.
Only validated or certified
outcomes are published as final; future elections retain pending results. The
**2026-10-26 Toronto municipal general election** comes from the City's certified candidate list
and the City Clerk's Declaration of Results of **2026-10-29**, which gives each candidate's vote
total. Its electorate and ballots cast stay null until the City publishes the final voter
statistics. Four Trustees declared elected by acclamation on August 24 are final results with null
vote totals. The primary table has one row per
Candidacy and is designed for election modelling, with `vote_share` as the main target. Every
Contest from 2003 onward elects one member; `seats_available` records the seat count so that
multi-member wards from before amalgamation (ADR 0011) can be filtered or modelled separately.

Coverage includes:

- Mayor and City Councillor;
- trustees for all four publicly funded School Boards;
- Members of Parliament in Toronto-contained federal districts; and
- Members of Provincial Parliament in Toronto-contained provincial districts.

General elections, by-elections, acclamations, and legally void contests are represented. Results
retain the district and boundary regime under which votes were cast; they are never projected onto
a common modern map. Party affiliation is attached to each Candidacy where an authority reports
it. Persistent Person links are evidence-backed and auditable; machine-generated identity
proposals are never published as confirmed links without adjudication. Insufficient,
contradictory, or newly queued matches remain unlinked instead of becoming fuzzy merges.

Mayor and City Councillor Contests also have evidence-backed endorsement companion tables.
Endorsements are positive, open-world facts: an absent fact never means that an Endorser opposed or
declined to endorse a Candidacy. Separate Endorser-by-Contest coverage records say how completely
each approved Endorser was searched.

The release contains **8,099 Candidacies in 1,385 Contests across 80 Election events**, all with
final results, including the 361 Candidacies in 55 Contests of the 2026-10-26 municipal election. Two void historical Contests have no Candidacy rows. The endorsement companion dataset contains **9 Endorsers, 161 audited source
assertions, 160 confirmed positive Endorsement facts, and 3,078 Endorser-by-Contest coverage
records**.

## Documentation

- [`CONTEXT.md`](./CONTEXT.md) — domain glossary (the canonical vocabulary).
- [`docs/data-dictionary.md`](./docs/data-dictionary.md) — full schema, sources, and QC gates.
- [`docs/adr/`](./docs/adr/) — the load-bearing design decisions:
  - `0001` — record wards as-run; no reprojection across the 2018 boundary change.
  - `0002` — historical municipal roster sources (superseded for identity semantics).
  - `0003` — drop 2000; add electorate/turnout from the Voter Statistics datasets.
  - `0004` — by-election scope and (office-dependent) incumbency.
  - `0005` — incumbency means holding the same office category; cross-office history is downstream.
  - `0006` — one cross-office results table, preserving every electoral geography as run.
  - `0007` — persistent Person identities, linked separately from individual Candidacies.
  - `0008` — model Endorsements as open-world, evidence-backed positive facts.
  - `0009` — record Suspended Campaigns as evidence-backed candidate facts.

Candidate-submitted campaign websites supplement the official roster through
`data/reference/campaign_url_curations.csv`. Each reviewed link targets an exact Candidacy
and records first-party evidence, verification date, and rationale. The pipeline applies
these links to `election_results.campaign_url` and tracks the curation file in the build manifest;
refreshing the official roster preserves the reviewed additions.

Suspended Campaigns are recorded in `data/reference/campaign_suspension_curations.csv`. Each row
dates the day a 2026 mayoral candidate publicly ended the campaign after the withdrawal deadline,
with evidence, verification date, and rationale. The City's roster still lists such a Candidacy as
Active, so the release publishes the date only as `campaign_suspended_on` in
`mayoral_candidates.json`; the canonical tables are unchanged. The build manifest tracks the
curation file, and the release refuses to build without it.

## Outputs

Every table is written as CSV and Parquet unless noted otherwise:

- `data/out/election_results.*` — modelling-ready Candidacy rows;
- `data/out/election_events.*` and `data/out/contests.*`;
- `data/out/people.*` and `data/out/candidacy_person_links.*`;
- `data/out/parties.*` and `data/out/office_tenures.*`;
- `data/out/electoral_districts.*` — native Contest-level geometry where available, with explicit
  missing-geometry status otherwise;
- `data/out/endorsers.*` — exact people, organizations, and editorial boards in the approved panel;
- `data/out/endorsement_assertions.*` — sourced claims and their review states;
- `data/out/endorsements.*` — confirmed positive Endorser-to-Candidacy facts;
- `data/out/endorsement_coverage.*` — open-world search state for every approved
  Endorser-by-Contest cell; and
- `data/out/build_manifest.json` — source/artifact checksums, the inclusive election-date horizon,
  the pending candidate snapshot, known archive uncertainty, deliberately excluded election calls,
  and in-scope results awaiting acquisition.

The City's archived index of past results lists every election it ran from 1998, so by-election
enumeration is complete from 1998. The former municipalities left no such index, so event
enumeration for 1995–1997 is marked uncertain; a search of the Toronto Star found one by-election
in that period (North York Ward 1, 1995), which is included. No result rows are fabricated to fill
an archive gap.
Trustee incumbency remains null because the result sources do not report it and a complete,
evidence-backed historical trustee roster has not been acquired.

## Development

Python managed with [`uv`](https://docs.astral.sh/uv/). Built test-first.

```sh
uv sync                                        # install deps
uv run pytest                                  # run tests
uv run python -m toronto_election_results.pipeline                  # download -> build -> QC
uv run python -m toronto_election_results.pipeline --skip-download  # reuse local raw cache
uv run python -m toronto_election_results.pipeline --skip-download --refresh-candidates
```

Use `--refresh-candidates` to overwrite all three City candidate rosters while reusing the
historical-result cache. The build manifest derives its candidate snapshot date from the oldest
of those three source retrieval times in Toronto time. Scheme-less `www.` campaign links in the
official roster receive an HTTPS scheme; other unsupported or malformed links still fail validation.
