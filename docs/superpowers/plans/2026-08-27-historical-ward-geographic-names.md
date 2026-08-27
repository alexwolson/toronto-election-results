# Historical ward geographic names implementation plan

**Date:** 2026-08-27  
**Design:** `docs/superpowers/specs/2026-08-27-historical-ward-geographic-names-design.md`  
**Primary repository:** `toronto-election-results`

## Objective

Publish a sourced, canonical `Ward <number> — <geographic name>` label for every
Toronto City Council and trustee district used from 2003 onward. Results owns
the historical catalogue and derivation rules; Backend passes the finished
fields through; Frontend presents them in candidate histories without local
crosswalk logic. Provincial, federal, mayoral, and pre-2003 records remain
unchanged.

## Operating rules

- Keep ward identity native to each election-era boundary regime. Never
  reproject results between the 44-ward and 25-ward systems.
- Use contemporaneous authoritative sources. Do not substitute modern names or
  inferred neighbourhood descriptions.
- Preserve the original `district_name`; add separate geographic and display
  fields.
- Use an official trustee geographic name when available. Otherwise derive a
  label from the contemporaneous City-ward crosswalk.
- Deduplicate shared City-ward names in stable first-occurrence order.
- Treat missing, contradictory, or unsourced mappings as validation failures.
- Enrich only council and trustee occurrences dated 2003-01-01 or later.
- Keep research and transformation logic in Results. Backend and Frontend may
  validate and transmit fields but must not reconstruct names.
- Develop schema changes with failing contract tests first and commit each
  repository independently.

## Task 1: Freeze the historical district inventory and reference contracts

### Results files

- Add `data/reference/city_ward_geographic_names.csv`.
- Replace the 2026-only trustee reference with
  `data/reference/trustee_ward_crosswalks.csv` covering every historical regime.
- Add `src/toronto_election_results/ward_geography.py`.
- Add `tests/test_ward_geography.py`.
- Update manifest and release-bundle reference-file declarations.

### Work

1. Generate a deterministic inventory of all unique
   `(represented_body, boundary_regime, official_district_id)` keys for council
   and trustee results dated 2003 or later.
2. Assert the current canonical inventory contains 332 in-scope district keys:
   69 City Council keys and 263 trustee keys. Treat a future count change as a
   prompt to update the sourced catalogue rather than as a permanently frozen
   production constant.
3. Define typed loaders for the City-name and trustee-crosswalk files.
4. Require unique keys, supported bodies and regimes, non-empty authoritative
   source metadata, ordered component City wards, and the approved provenance
   vocabulary.
5. Model the 2026 crosswalk through the new general loader and remove
   one-election-specific parsing once all call sites migrate.

### Tests

- Duplicate or blank keys fail.
- Unknown regimes and invalid source URLs fail.
- Component ward lists preserve source order and reject duplicates.
- A trustee component pointing to a nonexistent City ward fails.
- The in-scope canonical inventory is completely covered and contains no
  orphaned published entries.

### Commit

`Define historical ward geography contracts`

## Task 2: Source and enter the City Council ward names

### Scope

- 44 wards in `toronto_council_44_wards`.
- 25 wards in `toronto_council_25_wards`.

### Work

1. Recover the complete contemporaneous 44-model name list from City election,
   planning, GIS, or legislative records.
2. Record the current 25-model names from the applicable City ward source.
3. Preserve source spelling and punctuation, including historical hyphens.
4. Verify shared 44-model pairs explicitly rather than assuming a numerical
   pairing rule.
5. Record source authority, URL, and applicability metadata for every row.
6. Cross-check the catalogue against names already present in 2018-present
   canonical results without overwriting those source labels.

### Tests

- Exactly 44 and 25 unique rows exist for the two City regimes.
- Wards 19 and 20 both resolve to `Trinity-Spadina`.
- Modern rows reproduce the existing number-plus-name labels.
- No City name contains an invented directional or neighbourhood suffix.

### Commit

`Catalogue historical City ward names`

## Task 3: Source and enter all trustee ward crosswalks

### Scope

Cover all observed trustee regimes for 2003, 2006, 2010, 2014, 2018, 2022, and
2026:

- TDSB: 22 wards in each pre-2026 regime and 12 wards in 2026;
- TCDSB: 12 wards in each regime;
- Viamonde: 3 Toronto wards in each regime; and
- MonAvenir: 2 Toronto wards in each regime.

### Work

1. Locate contemporaneous City reference charts, election maps, board boundary
   determinations, archived board maps, and corroborating City GIS or
   legislative records.
2. Record each trustee ward's applicable City boundary regime and ordered City
   ward identifiers.
3. Record an official board-specific geographic name where the authority
   supplied one.
4. For unnamed trustee wards, derive the geographic name from the canonical City
   names, collapsing duplicates in stable order and joining distinct areas with
   semicolons.
5. Verify whether apparently unchanged regimes truly reuse the same boundaries;
   repeat the sourced mapping under each canonical regime key without inferring
   continuity from the ward number alone.
6. Confirm by-election regimes against their election dates.
7. Produce a human-readable coverage report listing every official and derived
   label with its source for review.

### Tests

- All 263 canonical trustee district keys resolve exactly once.
- A paired 44-model TDSB crosswalk collapses to one geographic name.
- A multi-area TCDSB label retains ordered, semicolon-separated names.
- Official Viamonde and MonAvenir names override long derived composites while
  retaining their component wards.
- 2012, 2016, 2023, and 2025 trustee by-elections resolve to the correct regime.

### Commit

`Catalogue historical trustee ward geographies`

## Task 4: Enrich canonical Results districts and public feeds

### Results files

- Update `src/toronto_election_results/schema.py`.
- Update `src/toronto_election_results/release.py` and
  `src/toronto_election_results/release_validation.py`.
- Update `src/toronto_election_results/pipeline.py`.
- Update `src/toronto_election_results/frontend_feeds.py`.
- Update `src/toronto_election_results/pending_candidates.py`.
- Update `src/toronto_election_results/release_bundle.py`.
- Replace remaining `trustee_2026.py` call sites with the general geography
  module.
- Update Results fixtures, documentation, and affected tests.

### Work

1. Enrich the electoral-district dimension with nullable
   `geographic_name`, `district_display_name`, and `name_provenance` fields.
2. Populate those fields only for 2003-present council and trustee districts.
3. Preserve existing `district_name` values byte-for-byte.
4. Pass the enriched district dimension into history-feed construction and emit
   nullable `district_display_name` on every `past_elections` object.
5. Populate the new history field only for in-scope occurrences; leave it null
   for other offices and pre-2003 occurrences.
6. Use the same catalogue for current council and trustee display labels so
   pending-candidate construction no longer owns a separate ward-name mapping.
7. Advance the Results mayoral feed from schema 4 to 5 and trustee feed from
   schema 2 to 3. Advance affected dataset and release-manifest schemas.
8. Include the new reference datasets and enriched electoral-district artifact
   in the Results release bundle.

### Tests

- Canonical `district_name` values do not change.
- Enriched district keys match the catalogue and provenance.
- Every in-scope public history occurrence contains the expected display label.
- MP, MPP, mayor, and pre-2003 history display fields remain null.
- Olivia Chow's pre-2003 occurrences remain unchanged.
- Results builds twice to byte-identical catalogue-derived outputs.
- Release validation rejects missing fields, bad provenance, and unknown schema
  versions.

### Commit

`Publish historical ward geographic names`

## Task 5: Pass the Results-owned labels through Backend

### Backend files

- Update `backend/release_inputs.py` to hydrate the Results
  `electoral_districts.csv` artifact.
- Update `scripts/build_council_snapshot.py`.
- Update `backend/model/council_hints.py` and
  `backend/model/council_snapshot.py`.
- Update `backend/model/trustee_race_card.py`.
- Update `backend/model/mayoral_candidate_ids.py`.
- Update Backend fixtures and focused model/release tests.

### Work

1. Add the Results electoral-district dimension to the pinned release-input
   contract.
2. Join council history rows to the Results-owned district display field by
   canonical `district_id`; extend `CandidacyRecord` with that key and do not
   derive from ward numbers or names.
3. Replace `load_ward_names` and the CDI-owned current ward-name input with the
   Results electoral-district display lookup, so current council headings and
   historical council rows share one naming source.
4. Extend `CandidacyRecord` and `PastElection` with nullable
   `district_display_name`, preserving it through serialization.
5. Carry the new field through the trustee feed unchanged.
6. Accept Results mayoral schema 5 and trustee schema 3.
7. Advance Backend council race cards from schema 6 to 7 and trustee race cards
   from schema 1 to 2.
8. Keep hint calculations, race categorization, and all modelling behaviour
   unchanged.

### Tests

- Council history uses the district dimension and fails on a missing district
  key.
- Trustee and mayoral labels survive byte-for-byte pass-through.
- No Backend function constructs a geographic label.
- Historical hints and trustee attention signals remain unchanged.
- Unknown Results and Backend schema versions fail visibly.

### Commit

`Pass through historical ward names`

## Task 6: Render number-plus-name history labels in Frontend

### Frontend files

- Update `src/types/feeds.ts`.
- Update `src/lib/feeds.ts` and `src/lib/feeds.test.ts`.
- Update `src/components/candidate-history.tsx`.
- Update `src/app/globals.css`.
- Update candidate-page rendering tests and local fixtures.

### Work

1. Add required nullable `district_display_name` to `PastElection`.
2. Accept Results mayoral schema 5, Backend trustee schema 2, and Backend council
   schema 7.
3. Validate that council and trustee occurrences dated 2003 or later have a
   non-null display name while other occurrences may keep it null.
4. Render `district_display_name` for in-scope ward history and fall back to
   `district_name` for other offices.
5. Present the office and district as separate elements rather than one
   comma-joined string.
6. Allow long trustee labels to wrap naturally and retain semicolon separators
   without adding provenance badges or technical notes.
7. Use canonical current display labels in council and trustee headings.

### Tests

- Council, TDSB, TCDSB, Viamonde, and MonAvenir history examples render their
  number-plus-name labels.
- A long derived trustee name remains readable at desktop and mobile widths.
- Provincial, federal, mayoral, and pre-2003 rows retain their existing labels.
- Invalid or missing new-schema fields reject the feed.
- Candidate history ordering, result copy, vote share, and link presentation do
  not change.

### Commit

`Display historical ward geographic names`

## Task 7: End-to-end verification, review, and release

### Work

1. Run the complete Results suite and rebuild all canonical and public artifacts.
2. Produce and inspect the coverage report for all 332 in-scope district keys.
3. Build Backend from the new pinned Results release and run its complete suite.
4. Refresh Frontend fixtures from the generated releases, run its complete test
   suite, lint changed files, and build production assets.
5. Preview representative mayoral, council, TDSB, TCDSB, Viamonde, and MonAvenir
   candidate histories locally at desktop and mobile widths.
6. Confirm pre-2003 mayoral rows are visually and structurally unchanged.
7. Present the local preview and coverage summary for approval.
8. After approval, commit any final fixture-only changes, push the three affected
   repositories, publish Results and Backend releases in dependency order, and
   deploy Frontend so Vercel resolves the new releases.

### Acceptance gate

- All 332 canonical in-scope district keys have sourced display labels.
- No out-of-scope occurrence is enriched.
- Results owns all historical naming and crosswalk logic.
- Backend and Frontend contain no historical ward-name dictionaries.
- All repository test suites and the production build pass.
- Public history rows remain readable for the longest trustee label.

### Release order

1. Results release.
2. Backend release pinned to that Results release and the current compatible
   Polling release.
3. Frontend production deployment resolving the new Results and Backend
   releases.
