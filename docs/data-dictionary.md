# Data dictionary — Toronto Election Results

Unified dataset of City of Toronto municipal election results, 2000–present, for **Mayor** and
**City Councillor**. Grain: **one row per candidate per contest**, ward-level. See `CONTEXT.md`
for vocabulary and `docs/adr/` for the load-bearing decisions.

## Scope

- **Elections**: general (2000, 2003, 2006, 2010, 2014, 2018, 2022) + the 2023 mayoral by-election.
- **Offices**: Mayor, City Councillor. School-trustee races excluded.
- **Grain**: ward-level (subdivision votes summed to the ward). Target variable: `vote_share`.
- **Parties**: none — Toronto ballots are non-partisan; no party/affiliation is imputed.

## Primary table — `data/out/toronto_election_results.{csv,parquet}`

Sorted by `election_year, office, ward_number, vote_rank`.

| Column | Type | Null rule | Notes |
|---|---|---|---|
| `election_year` | int | never | 2000, 2003, 2006, 2010, 2014, 2018, 2022, 2023 |
| `election_date` | date | never | actual polling date |
| `election_type` | enum | never | `general` \| `by_election` |
| `ward_system` | enum | never | `44-ward` (2000–2014) \| `25-ward` (2018+); a property of the election |
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
| `elected` | bool | never | set from authoritative winners; `argmax(votes)` QC |
| `acclaimed` | bool | never | uncontested win, no ballots |
| `incumbent` | bool | never | sitting holder at election time (person-based) |
| `incumbent_source` | enum | null if not incumbent | `prior_winner` \| `city_attendance` \| `city_voting` \| `wikipedia` |
| `incumbent_confidence` | float | never | tiered: prior-winner/City 0.90–0.95, Wikipedia 0.85 |
| `source` | enum | never | row provenance: `open_data` (2003–2023) \| `city_web_final` (2000) |
| `source_detail` | str | nullable | dataset resource id / PDF page |

### Null-rule summary

- **Acclaimed** rows: `votes`, `total_contest_votes`, `vote_share`, `vote_rank` all null; `elected=true`, `acclaimed=true`.
- **Mayor** rows: `ward_number`, `ward_name` null.
- `candidate_id` / `candidate_id_confidence` null where the fuzzy matcher makes no confident link.

## Companion outputs

- `data/out/subdivision_boundaries.parquet` — **GeoParquet**, keyed `(election_year, ward, subdivision_id)`, EPSG:4326, **2006+ only** (per ADR 0001).
- `data/out/council_composition.csv` — sitting members before each election (`election_year`, `member_name`, `candidate_id`, `arrival` = elected/by_election/appointed, `source`, `confidence`). Feeds incumbency; shipped for transparency.
- `data/out/authoritative_winners.csv` — curated winners list that sets `elected` (QC ground truth).

## Sources (per ADR 0002 and row `source`)

- **2003–2023 results**: City Open Data "Elections – Official Results" (+ By-Election Results for 2023). Read each candidate's `Total`; ignore subdivision columns.
- **2000 results**: the City's own archived final results website (`vote2000/live_final/*.htm`, via the Wayback Machine) — clean HTML, parsed deterministically. There is **no certified 2000 Clerk's declaration online**. Cross-verified candidate-by-candidate against Wikipedia. Source pages versioned in `data/reference/vote2000_html/`.
- **Incumbency 2010–2022**: City Council Meeting Attendance ∪ Voting Record datasets.
- **Incumbency 2000**: Wikipedia `(incumbent)` markers. **2003/2006**: two independent agent-compiled council rosters, reconciled (versioned in `data/reference/roster_agent_{a,b}.txt`). The bulk of incumbency is `prior_winner` (candidate won the prior in-scope election), robust to name drift.

## QC gates

`validate.py`:
- Exactly one `elected=true` per single-seat contest; every contest has a winner.
- `vote_share` sums to ~1.0 per contested contest; `total_contest_votes == sum(votes)`.
- Acclaimed contests have null votes and `elected=true`.
- No duplicate `(contest_id, candidate_name_raw)`; no negative votes.

`crosscheck_2000.py` / `crosscheck_winners.py`:
- 2000 parsed results match Wikipedia (40/44 wards candidate-level, 0 mismatches).
- Every derived councillor winner is a sitting member of the next council or a documented mid-term
  departure (`KNOWN_ACCOUNTED`) — 0 unexplained.
