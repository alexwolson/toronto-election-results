# By-election scope and incumbency

Status: accepted

## Context

The dataset originally carried only general elections plus the 2023 mayoral by-election. City Open
Data also publishes council by-elections (2016 Ward 2, 2017 Ward 42, 2021 Ward 22, 2023 Ward 20,
2024 Ward 15, 2025 Ward 25) with matching voter statistics. Adding them raises two questions:
how far past the original 2023 line to go, and what incumbency means for a by-election.

## Decision

- **Include every council/mayoral by-election Open Data publishes**, extending the dataset's range
  to **2003–present** (2024/2025 by-elections cross the original 2023 boundary). Earlier mid-term
  vacancies were filled by appointment, so no council by-election data exists before 2016.
- **Incumbency is office-dependent for by-elections:**
  - A **council** by-election fills one *vacant* ward, so no candidate holds it →
    `incumbent = false` (high confidence).
  - A **mayoral** by-election is a city-wide contest that sitting councillors enter, so
    **person-based incumbency still applies** — a candidate holding any council seat is an
    incumbent (e.g. Matlow, Bradford, Perruzza in 2023).

## Consequences

- The two by-elections that share 2023 (June mayoral, city-wide; and the Ward 20 councillor,
  one ward, a different date) have different electorates, so electorate/turnout is routed **per
  contest** — by election type and office — not by `(year, ward)`.
- The winner-lineage cross-check stays general-to-general (a by-election winner takes office
  mid-term and doesn't fit that chain); by-elections are validated by the per-contest QC gates.
- The asymmetry is deliberate: a reader seeing council by-election candidates always
  `incumbent = false` while mayoral ones vary should read this, not "fix" it.
