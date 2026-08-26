# Toronto Election Results

A unified, analysis-ready history of elections within the City of Toronto. Completed results cover
**2003-01-01 through 2026-08-20**. The scheduled **2026-10-26 Toronto municipal general election**
is also represented by the City's official candidate-list snapshot as of **2026-08-21**; those
Candidacies are explicitly pending, not results. The primary table has one row per Candidacy in a
single-seat Contest and is designed for election modelling, with `vote_share` as the main target.

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

The release contains **5,731 Candidacies in 881 Contests across 55 Election events**: 5,488 final
Candidacies in 855 completed Contests, plus 243 pending Candidacies in the 26 Contests scheduled
for 2026-10-26. The endorsement companion dataset contains **9 Endorsers, 155 audited source
assertions, 154 confirmed positive Endorsement facts, and 2,385 Endorser-by-Contest coverage
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
- `data/out/build_manifest.json` — source/artifact checksums, the completed-results cutoff, the
  pending candidate snapshot and event horizon, known archive uncertainty, and deliberately
  excluded election calls.

The City trustee by-election archive begins in 2012, so event enumeration for 2003–2011 is
explicitly marked uncertain. No known result rows are fabricated to fill that archive gap.
Trustee incumbency remains null because the result sources do not report it and a complete,
evidence-backed historical trustee roster has not been acquired.

## Development

Python managed with [`uv`](https://docs.astral.sh/uv/). Built test-first.

```sh
uv sync                                        # install deps
uv run pytest                                  # run tests
uv run python -m toronto_election_results.pipeline                  # download -> build -> QC
uv run python -m toronto_election_results.pipeline --skip-download  # reuse local raw cache
```
