# Council and trustee race map views implementation plan

**Date:** 2026-08-27  
**Design:** `docs/superpowers/specs/2026-08-27-race-map-views-design.md`  
**Primary repository:** `toronto-election-results`

## Objective

Add a purpose-built SVG map as an alternative to the existing list on the 2026
Council index and each trustee-board index. Results owns canonical current
geometry; Backend produces presentation-ready SVG paths, labels, legends, and
panel facts; Frontend renders those finished objects and manages only view and
selection state. The existing list remains the default and permanent fallback.

## Operating rules

- Map only current 2026 Council and trustee races. Do not acquire or derive
  historical trustee maps in this phase.
- Use the native current 25-ward City geometry already published by Results.
- Derive trustee polygons only from source-verified current City-ward
  memberships in the canonical crosswalk.
- Treat every board as a complete Toronto partition: no missing City wards,
  duplicates, overlaps, or gaps.
- Keep projection, simplification, label placement, and factual joins out of
  Frontend.
- Publish no partial map. A page either receives every expected feature or no
  map object.
- Reuse the existing Council attention, TDSB race-structure, and other-board
  prior-winner-share signals. Do not add modelling or predictive language.
- Preserve the existing list markup, ordering, search, sorting, copy, and links.
- Write failing contract tests before each schema or transformation change.
- Commit Results, Backend, and Frontend independently.

## Task 1: Verify all current trustee boundary memberships

### Results files

- Review and, where necessary, update
  `data/reference/trustee_ward_crosswalks.csv`.
- Add
  `docs/research/2026-trustee-map-boundary-verification.md`.
- Extend `tests/test_ward_geography.py`.

### Work

1. Freeze the current crosswalk rows for the four 2026 trustee regimes.
2. Verify the 12 TDSB memberships against the board's April 2026 approved ward
   map and retain the exact official source metadata.
3. Verify the 12 TCDSB memberships against its adopted 25-City-ward
   realignment and a current board source confirming that regime still applies.
4. Recover official 2026 determination material for Viamonde's three Toronto
   sectors and MonAvenir's two Toronto sectors.
5. Resolve the Viamonde `Toronto-Est` / `Toronto Nord-Est` naming discrepancy.
   Record polygon membership and display naming as separate findings.
6. For every board, verify that City wards 1 through 25 appear exactly once.
7. Record source URLs, dates, quotes or map readings, and any corroboration in
   the research note. Do not admit a French-board map on inference alone.

### Tests

- The current regime for each board has exactly 25 distinct component City
  wards with no duplicates.
- Expected district counts are TDSB 12, TCDSB 12, Viamonde 3, MonAvenir 2.
- Every current row carries non-empty source authority, URL, and date.
- Current official names reproduce the certified public labels after the source
  review.

### Commit

`Verify 2026 trustee boundary memberships`

## Task 2: Publish canonical current trustee geometry in Results

### Results files

- Update `src/toronto_election_results/district_geometry.py`.
- Update `src/toronto_election_results/pipeline.py` only if enrichment needs the
  loaded crosswalk explicitly.
- Update `src/toronto_election_results/release.py`,
  `src/toronto_election_results/release_validation.py`, and
  `src/toronto_election_results/release_bundle.py` as required by the district
  schema revision.
- Extend `tests/test_district_geometry.py`.
- Update `tests/test_pipeline.py`, `tests/test_release_validation.py`, and
  release fixtures.
- Rebuild `data/out/electoral_districts.csv` and
  `data/out/electoral_districts.parquet`.

### Work

1. Change `enrich_district_geometries` to accept the canonical trustee
   crosswalk, while retaining the current source override seam used by tests.
2. Load the 25 current City ward polygons once and index them by ward number.
3. For each 2026 trustee row, union its component City ward polygons and repair
   the result through the existing polygon-validity gate.
4. Populate geometry only for `*-trustee-wards-2026`. Historical trustee rows
   retain `not_acquired` and
   `school_board_district_geometry_not_acquired`.
5. Mark current trustee geometry `available` in EPSG:4326.
6. Record derived provenance with the existing City geometry
   authority/resource/year fields and add explicit
   `geometry_derivation=union_of_city_wards`,
   `geometry_membership_source_authority`,
   `geometry_membership_source_resource`, and
   `geometry_membership_source_date` fields for the crosswalk input. Do not
   concatenate the two sources into opaque prose.
7. Advance the electoral-district dataset schema and release validation.
8. Preserve Council geometry bytes and all non-geographic Results tables.

### Tests

- Current feature counts are 25 Council, 12 TDSB, 12 TCDSB, 3 Viamonde, and 2
  MonAvenir.
- Each geometry is valid, non-empty, and Polygon/MultiPolygon.
- Within each board, pairwise interior intersections have zero area within the
  chosen numerical tolerance.
- Each board union is topologically equal to the canonical current City union.
- Every trustee polygon equals the union of its declared City wards.
- Historical trustee, federal, provincial, and unsupported rows remain null.
- A missing or malformed City source never creates derived trustee geometry.
- Two clean pipeline rebuilds produce deterministic geometry and provenance.

### Commit

`Publish current trustee district geometry`

## Task 3: Define the Backend race-map contract and SVG transformation

### Backend files

- Add `backend/model/race_map.py`.
- Add `tests/model/test_race_map.py` and focused geometry fixtures.
- Update `backend/release_inputs.py` and `tests/test_release_inputs.py`.
- Update `pyproject.toml` only if the implementation needs an additional direct
  dependency; existing GeoPandas and Shapely should be sufficient.

### Work

1. Hydrate Results `electoral_districts.parquet` alongside the existing CSV and
   expose it as `ReleaseInputPaths.electoral_districts_parquet`.
2. Define typed map serializers for:
   - shared `view_box`;
   - ordered `features`;
   - `ward_id`, accessible name, SVG `path`, label coordinates, semantic signal
     key, nullable numeric `signal_value`, and presentation-ready panel;
   - visible plain-language legend entries.
3. Read GeoParquet with its CRS intact and select one complete current district
   regime by represented body.
4. Project all maps into NAD83 / UTM zone 17N (`EPSG:26917`), preserve aspect
   ratio, add a stable outer margin, and normalize to `0 0 1000 720`.
5. Apply topology-preserving simplification before path serialization. Choose
   the tolerance through visual inspection, then freeze it in tests.
6. Serialize Polygon and MultiPolygon exteriors and holes into fixed-precision
   SVG path commands with stable ring and feature ordering.
7. Calculate inside-polygon label anchors with `shapely.ops.polylabel` at a
   frozen tolerance. Backend, not Frontend, resolves downtown offsets and any
   leader-line endpoints.
8. Validate exact feature inventory, unique IDs, finite coordinates, supported
   signal keys, non-empty panel fields, and an uncompressed map size under 250
   KB.
9. Return `None` for an optional map only when its complete geometry input is
   unavailable. Raise on malformed or partially matched input.

### Tests

- Polygon, MultiPolygon, island, and interior-hole fixtures serialize correctly.
- Paths and label points are deterministic and remain within the view box.
- Label anchors lie within their source geometry.
- Simplification preserves topology and feature adjacency.
- Shuffled input rows produce byte-identical output.
- Partial, duplicate, non-finite, or mismatched features fail.
- Payload size and fixed numeric precision are enforced.

### Commit

`Define presentation-ready race maps`

## Task 4: Add the Council map to the Backend feed

### Backend files

- Update `backend/model/council_snapshot.py`.
- Update `scripts/build_council_snapshot.py`.
- Update `backend/release_bundle.py` if its feed checks name the council schema.
- Extend `tests/model/test_council_snapshot.py` and script-level tests.

### Work

1. Pass hydrated GeoParquet into the council snapshot builder.
2. Build exactly 25 map features in the same default attention order used by
   the list.
3. Emit semantic signal keys `open`, `high`, `elevated`, and `quiet` using the
   existing attention classification without changing its thresholds.
4. Attach the finished panel heading, ward geographic name, attention label,
   incumbent/open-seat summary, candidate count, and `/wards/<n>` URL.
5. Emit a stable plain-language Council legend.
6. Add optional `map` to the council race-card root and advance its schema from
   7 to 8.
7. Keep every non-map council field byte-for-byte equivalent to the prior build.

### Tests

- All 25 current ward IDs match the existing `wards` keys exactly.
- Feature order matches the default attention-ranked list.
- Signal keys match existing attention classifications.
- Panel facts and URLs match the corresponding ward card.
- Missing complete geometry omits the map; partial geometry fails.
- Council non-map regression fixtures do not change.

### Commit

`Publish Council race map`

## Task 5: Add trustee maps to the Backend feed

### Backend files

- Update `backend/model/trustee_race_card.py`.
- Update `scripts/build_trustee_snapshot.py`.
- Extend `tests/model/test_trustee_snapshot.py`.
- Update release tests and fixtures.

### Work

1. Pass GeoParquet into trustee race-card construction.
2. Add one optional map object to each board, with features in that board's
   existing ranked list order.
3. For TDSB, emit `open`, `two_incumbents`, `one_incumbent`, and `acclaimed`
   using the existing field-structure categories and labels.
4. For TCDSB, Viamonde, and MonAvenir, emit the numeric prior winner's vote share
   when a comparable result exists and a distinct `no_comparable_result`
   semantic key otherwise. Preserve the existing factual caveat.
5. Attach finished panel geography/areas, field status, candidate count,
   incumbent summary, and `/trustees/<board>/<ward>` URL.
6. Emit a categorical TDSB legend and factual vote-share gradient legend for
   the other boards.
7. Advance the trustee race-card schema from 2 to 3.
8. Keep candidate histories, acclamation language, sorting, and non-map signals
   unchanged.

### Tests

- Exact map counts are 12, 12, 3, and 2 by board.
- Feature IDs and order match each board's existing ward inventory.
- TDSB keys match existing race structure.
- Other-board values equal the canonical prior-result share and do not use a
  score or prediction.
- Panel facts and URLs match the corresponding trustee race.
- One board's absent complete geometry omits only that board's map; partial
  geometry fails the build.

### Commit

`Publish trustee race maps`

## Task 6: Validate and render map objects in Frontend

### Frontend files

- Update `src/types/feeds.ts`.
- Update `src/lib/feeds.ts` and `src/lib/feeds.test.ts`.
- Add `src/components/race-view-switcher.tsx`.
- Add `src/components/race-map.tsx` and
  `src/components/race-map.test.tsx`.
- Update `src/components/wards-browser.tsx`.
- Update `src/app/wards/page.tsx`.
- Update `src/app/trustees/[board]/page.tsx`.
- Update `src/app/globals.css`.
- Update `src/lib/council.test.ts`, `src/lib/trustees.test.tsx`, and release
  fixtures.

### Work

1. Add the normative race-map types and accept Council schema 8 and Trustee
   schema 3.
2. Validate view box, complete feature inventory, finite coordinates, SVG path
   syntax boundaries, semantic keys, legend entries, panel facts, and internal
   detail-page URLs. Treat `map` as optional; discard a malformed optional map
   while retaining the valid base feed.
3. Implement a reusable client view switcher whose server-rendered state is
   List. Read and write one namespaced `sessionStorage` preference after
   hydration, with an in-memory fallback when storage is unavailable.
4. Preserve the existing list as a rendered child. Do not rebuild trustee list
   facts in the client.
5. In Map view, hide list-only search/sort controls and show all map features.
   Returning to List restores the component's current search and sort state.
6. Render the responsive SVG and persistent panel approved in the design:
   larger map/smaller panel on desktop, stacked on mobile.
7. Initialize held selection from the first Backend feature. Implement
   temporary hover/focus preview, restoration on exit, and click/tap/Enter/Space
   held selection. Navigate only through the panel link.
8. Render Backend label anchors and any leader lines; do not calculate placement
   in JavaScript.
9. Add separate CSS-variable palettes for Council attention, TDSB structure,
   and the other-board vote-share gradient. Include visible textual legends,
   selection/focus outlines, high-contrast boundaries, and reduced-motion
   handling.
10. Announce held selection changes through a restrained live region; do not
    announce pointer-only previews.
11. Hide the Map option entirely when a page lacks a validated map.

### Tests

- List is the server and fresh-session default.
- One session preference carries between Council and Trustee switchers.
- Storage exceptions fall back without breaking the switch.
- Mouse, focus, click, Enter, and Space follow preview/held-selection rules.
- Preview exit restores the held ward.
- Panel copy and detail link update from the selected feature.
- Maps expose accessible ward names, visible legends, and pressed/selected
  control states.
- Missing or malformed optional maps leave the existing list unchanged.
- Council search/sort state survives toggling.
- Existing list rendering tests continue to pass.

### Commit

`Render Council and trustee race maps`

## Task 7: End-to-end verification, review, and release

### Work

1. Run the complete Results suite and rebuild canonical district artifacts.
2. Audit the five current geometry inventories and provenance report.
3. Build Results release assets from a clean commit.
4. Build a Polling release pinned to the exact Results release, even if polling
   observations are unchanged.
5. Hydrate Backend from those exact releases, run its complete suite, build all
   race feeds, and publish the Backend release.
6. Refresh Frontend fixtures from the built feeds; run its complete tests, lint
   changed files, and build with the real production release resolver.
7. Preview Council and all four board maps locally at desktop and mobile widths.
8. Inspect downtown Council labels, island/multipolygon handling, TDSB merged
   wards, both French-board maps, legends, keyboard behaviour, and list fallback.
9. Present the local preview and source/coverage summary for approval.
10. After approval, fast-forward each repository's `main`, push, publish the
    coordinated Results → Polling → Backend chain, and run `vercel --prod`.

### Acceptance gate

- All five current map inventories are complete and topologically valid.
- French-board memberships have current authoritative sources.
- Frontend performs no spatial transformation or factual join.
- Every map stays below 250 KB uncompressed and renders without an external map
  service.
- List remains the fresh-session default and is unchanged when map data is
  absent.
- Mouse, touch, and keyboard exploration work at desktop and mobile widths.
- Public legends accurately describe existing factual signals and contain no
  forecast or defeatability language for trustees.
- All repository suites and the production build pass.

### Release order

1. Results release containing canonical current trustee geometry.
2. Polling release pinned to that exact Results release.
3. Backend release pinned to both exact upstream releases.
4. Frontend production deployment resolving the coordinated release chain.
