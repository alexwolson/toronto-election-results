# Data dictionary — Toronto Election Results

Unified dataset of City of Toronto municipal election results, 2003–present, for **Mayor** and
**City Councillor**. Grain: **one row per candidate per contest**, ward-level. See `CONTEXT.md`
for vocabulary and `docs/adr/` for the load-bearing decisions.

## Scope

- **Elections**: general (2003, 2006, 2010, 2014, 2018, 2022) + the 2023 mayoral by-election.
  2000 was dropped (no electorate data; weaker results provenance) — see ADR 0003.
- **Offices**: Mayor, City Councillor. School-trustee races excluded.
- **Grain**: ward-level (subdivision votes summed to the ward). Target variable: `vote_share`.
- **Parties**: none — Toronto ballots are non-partisan; no party/affiliation is imputed.

## Primary table — `data/out/toronto_election_results.{csv,parquet}`

Sorted by `election_year, office, ward_number, vote_rank`.

| Column | Type | Null rule | Notes |
|---|---|---|---|
| `election_year` | int | never | 2003, 2006, 2010, 2014, 2018, 2022, 2023 |
| `election_date` | date | never | actual polling date |
| `election_type` | enum | never | `general` \| `by_election` |
| `ward_system` | enum | never | `44-ward` (2003–2014) \| `25-ward` (2018+); a property of the election |
| `office` | enum | never | `mayor` \| `councillor` |
| `ward_number` | int | null for mayor | ward number as that election used it |
| `ward_name` | str | null for mayor / where absent | e.g. "Scarborough Southwest" |
| `contest_id` | str | never | `{year}-{office}-{ward\|city}`, e.g. `2014-councillor-20`, `2003-mayor-city` |
| `candidate_name` | str | never | normalized "First Last" |
| `candidate_first_name` | str | best-effort (nullable) | split for matching |
| `candidate_last_name` | str | best-effort (nullable) | split for matching |
| `candidate_name_raw` | str | never | verbatim from source |
| `candidate_id` | str | nullable | persistent person id (fuzzy match) |
| `candidate_id_confidence` | float | null where no id | 0–1 |
| `votes` | int | **null if acclaimed** | ward-summed valid votes |
| `total_contest_votes` | int | null if acclaimed | the `vote_share` denominator, exposed |
| `vote_share` | float | null if acclaimed | `votes / total_contest_votes` |
| `vote_rank` | int | null if acclaimed | 1 = top vote-getter |
| `n_candidates` | int | never | contest size (model feature) |
| `eligible_electors` | int | never | `Total Eligible Electors` for the geography (ward for councillor, city-wide for mayor); the turnout denominator |
| `ballots_cast` | int | never | `Number Voted` (electors who cast a ballot); the turnout numerator |
| `turnout` | float | never | `ballots_cast / eligible_electors` |
| `elected` | bool | never | set from authoritative winners; `argmax(votes)` QC |
| `acclaimed` | bool | never | uncontested win, no ballots |
| `incumbent` | bool | never | sitting holder at election time (person-based) |
| `incumbent_source` | enum | null if not incumbent | `prior_winner` \| `city_attendance` \| `city_voting` \| `wikipedia` |
| `incumbent_confidence` | float | never | tiered: prior-winner/City 0.90–0.95, Wikipedia 0.85 |
| `source` | enum | never | row provenance: `open_data` |
| `source_detail` | str | nullable | dataset resource id / PDF page |

### Null-rule summary

- **Acclaimed** rows: `votes`, `total_contest_votes`, `vote_share`, `vote_rank` all null; `elected=true`, `acclaimed=true`. (`eligible_electors`/`ballots_cast`/`turnout` are still populated — the ward's electors voted for other offices.)
- **Mayor** rows: `ward_number`, `ward_name` null; electorate is the city-wide total.
- `candidate_id` / `candidate_id_confidence` null where the fuzzy matcher makes no confident link.

## Companion outputs

- `data/out/subdivision_boundaries.parquet` — **GeoParquet**, keyed `(election_year, ward, subdivision_id)`, EPSG:4326, **2006+ only** (per ADR 0001).
- `data/out/council_composition.csv` — sitting members before each election (feeds incumbency; shipped for transparency).

## Sources (per row `source`, ADR 0002/0003)

- **Results (2003–2023)**: City Open Data "Elections – Official Results" (+ By-Election Results for 2023). Read each candidate's `Total`; ignore subdivision columns.
- **Electorate/turnout (2003–2023)**: City Open Data "Elections – Voter Statistics" (+ the 2023 mayoral By-Election Voter Statistics). Sum subdivision rows to ward level; take `Total Eligible Electors` and `Number Voted`. **No 2000 file exists.**
- **Incumbency 2010–2022**: City Council Meeting Attendance ∪ Voting Record datasets. **2003/2006**: two independent agent-compiled council rosters, reconciled (versioned in `data/reference/roster_agent_{a,b}.txt`). The bulk is `prior_winner` (won the prior in-scope election), robust to name drift.

## QC gates

`validate.py`:
- Exactly one `elected=true` per single-seat contest; every contest has a winner.
- `vote_share` sums to ~1.0 per contested contest; `total_contest_votes == sum(votes)`.
- Acclaimed contests have null votes and `elected=true`.
- No duplicate `(contest_id, candidate_name_raw)`; no negative votes.
- `turnout ∈ (0, 1]`; `ballots_cast ≤ eligible_electors`; `ballots_cast ≥ total_contest_votes`.

`crosscheck_winners.py`:
- Every derived councillor winner is a sitting member of the next council or a documented mid-term departure (`KNOWN_ACCOUNTED`) — 0 unexplained.
- Voter-stats parse verified: city-wide totals match the City's published figures (2018 ≈ 41%, 2022 ≈ 30%, 2023 ≈ 37%).

## Caveats

- `eligible_electors` is not a clean cross-year population series — the Voters' List is rebuilt each cycle (e.g. 2003 counts ~300K more than 2006), and election-day additions inflate the denominator, slightly depressing apparent turnout.
