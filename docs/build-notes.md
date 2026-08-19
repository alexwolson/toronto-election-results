# Build notes

Record of how the dataset was built. See `docs/data-dictionary.md` for the schema and
`docs/adr/` for the load-bearing decisions.

## Status: complete (2003–2023)

The unified table covers the six general elections + the 2023 mayoral by-election, with derived
winners, vote share, cross-election candidate IDs, incumbency, and electorate/turnout. QC gates
and the winner cross-check pass; voter-stats totals match the City's published figures.

Outputs (`data/out/`):
- `toronto_election_results.{csv,parquet}` — **1871 rows, 2003–2023, 28 columns**.
- `subdivision_boundaries.parquet` — 7539 subdivision polygons, 2006–2023 (GeoParquet).
- `council_composition.csv` — the incumbency reference.

## Modules (test-first)

`parse_results` (Excel, 3 layout families) · `download` (CKAN) · `candidates` (normalize + fuzzy
id) · `derive` (winner/acclamation/share/rank) · `incumbency` · `voter_statistics` (electorate +
turnout) · `geometry` (GeoParquet) · `crosscheck_winners` · `assemble` · `validate` · `pipeline`.

## Key decisions

1. **`elected`** = top vote-getter (sole candidate for acclamations). Cross-checked: every derived
   councillor winner is a sitting member of the next council or a documented mid-term departure —
   0 unexplained (`crosscheck_winners.py`, `KNOWN_ACCOUNTED`).
2. **Incumbency** (person-based, ADR 0002): `prior_winner` via `candidate_id` for the bulk (robust
   to name drift), roster for appointees. 2003/2006 rosters from two reconciled agents; 2010–2022
   from City attendance ∪ voting (appointees caught by the latest-activity rule).
3. **Electorate/turnout** (ADR 0003): from the City Voter Statistics datasets, summed to ward
   level. `eligible_electors` = Total Eligible Electors (the City's denominator); `ballots_cast` =
   Number Voted (consistent across years — rejected/declined, published only 2018+, are excluded);
   `turnout` = the ratio. Office-independent, so mayor gets the city-wide sum.
4. **2000 dropped** (ADR 0003): no electorate data exists for it, and its results had weaker
   provenance. The 2000 parser, cross-check, and archived pages were removed (in git history).

## Provenance of curated inputs (`data/reference/`)

- `roster_agent_a.txt`, `roster_agent_b.txt` — two independent 2000–2003 / 2003–2006 council
  compilations, reconciled in `incumbency.build_composition` (4 disagreements resolved: Ward 17
  Dominelli & Ward 35 Barron appointees per Agent A's City-roster cross-check; George/Giorgio
  Mammoliti kept both forms).

## Caveats

- `eligible_electors` is not a clean cross-year population series (Voters' List rebuilt each cycle;
  day-of additions inflate the denominator).
- `candidate_id` is fuzzy — same-name-different-person could merge silently; incumbency carries a
  confidence tier reflecting this.
