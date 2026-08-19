# Build notes

Record of how the dataset was built. See `docs/data-dictionary.md` for the schema and
`docs/adr/` for the load-bearing decisions.

## Status: complete (2000–2023)

The unified table covers all seven general elections + the 2023 mayoral by-election, with derived
winners, vote share, cross-election candidate IDs, and incumbency. **92 tests green; QC gates and
the winner cross-check both pass.**

Outputs (`data/out/`):
- `toronto_election_results.{csv,parquet}` — **2038 rows, 278 contests, 1478 unique candidates**.
- `subdivision_boundaries.parquet` — 7539 subdivision polygons, 2006–2023 (GeoParquet).
- `council_composition.csv` — the incumbency reference (sitting members before each election).

## Modules (test-first)

`parse_results` (Excel, 3 layout families) · `parse_2000` (archived City HTML) · `download` (CKAN)
· `candidates` (normalize + fuzzy id) · `derive` (winner/acclamation/share/rank) · `incumbency`
· `geometry` (GeoParquet) · `crosscheck_2000` / `crosscheck_winners` (Wikipedia + roster QA) ·
`assemble` (orchestrator) · `validate` (QC) · `pipeline` (one-command runner).

## Key decisions during the build

1. **`elected`** derived as top vote-getter (sole candidate for acclamations). **Cross-checked**:
   every derived councillor winner is a sitting member of the next council or a documented mid-term
   departure — 0 unexplained discrepancies (`crosscheck_winners.py`; departures in `KNOWN_ACCOUNTED`).
2. **2000** is not in Open Data and has no Clerk's-declaration PDF. Sourced by **deterministically
   parsing the City's archived results website** (`vote2000/live_final/*.htm`, Wayback), not agent
   transcription — the pages are clean HTML. Cross-checked candidate-by-candidate against Wikipedia:
   **40/44 wards, 0 mismatches** (4 template wards win-verified). `source = city_web_final`.
3. **Names**: 2000 is given-first (`MEL LASTMAN`), Excel is surname-first (`Crisanti Vincent`) —
   `normalize_name(order=…)` handles both. Identity via token-sorted key + rapidfuzz.
4. **Incumbency** (person-based, ADR 0002), two paths:
   - **Prior-winner** (primary): candidate's `candidate_id` was `elected` in the prior in-scope
     election. Rides on the fuzzy identity, so it survives name drift (`Norm`/`Norman`,
     `A.A.`/`Adrian`). `incumbent_source = prior_winner`.
   - **Roster** (appointees + 2000): 2000 from Wikipedia `(incumbent)` markers; 2003/2006 from
     **two independent agents' rosters, reconciled** (both name forms kept so variants match);
     2010–2022 from City attendance ∪ voting (appointees caught by the latest-activity rule).
   - 2023 (mayoral by-election): mayoralty vacant, but sitting 2022 councillors who ran (Matlow,
     Bradford, Perruzza) are person-based incumbents via prior-winner.
   Confidence is tiered: prior-winner 0.95, City 0.95/0.90, Wikipedia 0.85.

## Provenance of curated inputs (`data/reference/`)

- `vote2000_html/` — the 45 archived City result pages (source of record for 2000).
- `wikipedia_2000.wikitext` — 2000 cross-check + incumbent markers.
- `roster_agent_a.txt`, `roster_agent_b.txt` — the two independent 2000–2003 / 2003–2006 council
  compilations (reconciled in `incumbency.build_composition`; 4 disagreements, all resolved:
  Ward 17 Dominelli & Ward 35 Barron appointees per Agent A's City-roster cross-check;
  George/Giorgio Mammoliti kept both).
