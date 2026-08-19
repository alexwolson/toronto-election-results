# Toronto Election Results

A unified, analysis-ready dataset of City of Toronto municipal election results, **2003–present**,
for **Mayor** and **City Councillor** races — built to feed an election model.

- **Grain**: one row per candidate per contest, ward-level. Target: `vote_share`.
- **Coverage**: general elections 2003, 2006, 2010, 2014, 2018, 2022 + the 2023 mayoral by-election.
- **Per contest**: derived winner, incumbency, and electorate/turnout (`eligible_electors`, `ballots_cast`, `turnout`).
- **Non-partisan**: no party labels (none exist on Toronto ballots); none imputed.

## Documentation

- [`CONTEXT.md`](./CONTEXT.md) — domain glossary (the canonical vocabulary).
- [`docs/data-dictionary.md`](./docs/data-dictionary.md) — full schema, sources, and QC gates.
- [`docs/adr/`](./docs/adr/) — the load-bearing design decisions:
  - `0001` — record wards as-run; no reprojection across the 2018 boundary change.
  - `0002` — derive incumbency from council-attendance data + Wikipedia.
  - `0003` — drop 2000; add electorate/turnout from the Voter Statistics datasets.

## Outputs

- `data/out/toronto_election_results.{csv,parquet}` — the primary table.
- `data/out/subdivision_boundaries.parquet` — voting-subdivision polygons, 2006+ (GeoParquet).
- `data/out/council_composition.csv` — incumbency reference.

## Development

Python managed with [`uv`](https://docs.astral.sh/uv/). Built test-first.

```sh
uv sync                                        # install deps
uv run pytest                                  # run tests
uv run python -m toronto_election_results.pipeline   # download -> build -> QC
```
