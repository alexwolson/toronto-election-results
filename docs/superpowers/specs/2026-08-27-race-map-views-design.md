# Council and Trustee Race Map Views

**Date:** 2026-08-27  
**Status:** Approved design  
**Repositories:** `toronto-election-results`, `toronto-election-poll-tracker-data`, `toronto-election-poll-tracker-backend`, `toronto-election-poll-tracker`

## Purpose

Add a map as an alternative to the existing list on the 2026 Council index and
each of the four trustee-board indexes. The map is an editorial race browser,
not a general-purpose slippy map: it shows Toronto's ward geography, encodes the
same factual signal as the list, and lets a reader inspect a ward before opening
its detail page.

The existing list remains the default and remains fully available. Detail pages
do not receive maps in this phase. Historical election maps are out of scope.

## Approved user experience

### View switch

Each Council or trustee-board index places a two-option `List / Map` control
immediately above the races. A new browser session opens in List view. Changing
the view stores one shared session-scoped preference, so Council and Trustee
indexes use the same selected view for the remainder of that browser session.
The preference is not persisted across sessions and does not affect URLs or
server-rendered defaults.

The Map option is shown only when the page has a complete, valid map object. If
map data is absent or invalid, the page remains list-only and does not show a
public technical warning.

### Map and detail panel

The approved layout is a map with a persistent detail panel:

- on desktop, the Toronto map occupies the larger left column and the panel the
  smaller right column;
- on narrow screens, the panel stacks directly below the map;
- the first race in the existing ranked list is initially selected, so the
  panel is never empty;
- pointer hover and keyboard focus temporarily preview a ward;
- pointer exit or focus exit restores the held selection;
- click, tap, Enter, or Space selects and holds a ward; and
- navigation occurs only through the panel's `View race` link.

Each ward polygon has a visible ward number and an accessible label. The panel
uses already-published race facts: district name or areas covered, signal label,
field status, candidate count, incumbent information, and the detail-page link.
The map does not introduce predictive language or new metrics.

### Map signals and legends

Maps use the same underlying signals as their corresponding lists:

- **Council:** the existing attention level;
- **TDSB:** open race, two incumbents, one incumbent, or acclaimed;
- **TCDSB, Viamonde, and MonAvenir:** the prior winner's share of votes cast,
  with a separate treatment for no comparable prior result.

Each map has a visible, plain-language legend. The three signal families use
distinct map-specific palettes. Text labels, outlines, and selection state make
the interface understandable without colour alone. The continuous trustee
scale is described as a factual prior-result comparison, not a forecast or
defeatability score.

## Chosen technical approach

Use purpose-built responsive SVG maps. Do not add MapLibre, Leaflet, a basemap,
tiles, geocoding, pan/zoom infrastructure, or an external map service.

The SVG is generated from canonical geometry upstream. The Frontend receives a
presentation-ready map object containing a shared view box, one path and label
point per race, semantic signal keys, and the exact facts needed by the detail
panel. It renders and manages selection state but performs no spatial work.

Rejected alternatives:

1. A slippy map adds a large client dependency and external style/tile concerns
   without improving a fixed set of at most 25 Toronto districts.
2. Dissolving City wards or joining map facts in the Frontend would violate the
   established rule that the Frontend displays finished products rather than
   owning data transformations.

## Repository responsibilities

### Results: canonical geography

Results owns native district geometry and trustee-to-City-ward membership.

The current 25 City ward polygons already exist in
`electoral_districts.csv`/Parquet under the
`toronto_council_25_wards` boundary regime. Results will make current trustee
geometry available by dissolving those polygons according to the canonical
2026 crosswalk:

- TDSB: 12 districts;
- TCDSB: 12 districts;
- Viamonde: 3 Toronto districts; and
- MonAvenir: 2 Toronto districts.

Only current 2026 trustee regimes are enriched. Historical trustee rows retain
their explicit `not_acquired` geometry status.

The derived geometry is the Toronto portion of each electoral district and is
appropriate to this Toronto election product. It is not presented as a map of a
board's complete service territory outside Toronto.

#### Authority and provenance

Every derived trustee polygon records both:

1. the City of Toronto source used for the current 25 City ward polygons; and
2. the official board determination or other authoritative record supporting
   the trustee-to-City-ward membership.

The TDSB's April 2026 approved map explicitly shows the new trustee boundaries
against municipal ward boundaries:
`https://www.tdsb.on.ca/Portals/0/docs/Ward%20Map.pdf`.

The TCDSB's approved realignment identifies trustee wards as combinations of
the 25 City wards:
`https://assets.tcdsb.org/TCDSB/2386752/august-2018-motions-in-review-public.pdf`.

Before implementation admits Viamonde or MonAvenir geometry, their current
Toronto-sector crosswalks must be checked against official 2026 board
determination material. The check must resolve current naming differences such
as `Toronto-Est` versus `Toronto Nord-Est`; display names remain a separate fact
from polygon membership. A French-board map is not published until this source
gate passes.

#### Geometry validation

For each current trustee board, Results must prove:

- every City ward from 1 through 25 appears exactly once;
- every trustee district has at least one City ward;
- each dissolved geometry is a valid Polygon or MultiPolygon;
- trustee polygons have no interior overlaps;
- the union of all trustee polygons equals the canonical Toronto geometry
  within a strict numerical tolerance; and
- geometry, membership, and provenance are deterministic across rebuilds.

Malformed inputs fail the Results build. A merely missing optional source leaves
the relevant geometry unavailable and prevents downstream map publication.

### Polling: dependency pin only

Polling performs no geographic processing. When a Results release changes, the
next Polling release advances its exact Results dependency pin even if polling
observations are unchanged. This preserves the verified release chain required
by Backend.

### Backend: presentation-ready map objects

Backend reads the exact Results district geometry pinned by the release
manifest and converts current race polygons into deterministic SVG coordinates.
It owns:

- projection into a Toronto-wide planar coordinate system;
- topology-preserving simplification suitable for the web;
- normalization into a shared SVG view box;
- representative label points that lie inside each polygon;
- association with the existing race signal;
- plain panel facts and detail-page URL; and
- all-or-nothing validation for each Council or board map.

Map objects are embedded in the existing Council and Trustee race-card feeds so
the tabular and geographic representations cannot resolve from different
Backend releases. The feed schema versions advance.

The common conceptual shape is:

```json
{
  "view_box": "0 0 1000 720",
  "features": [
    {
      "ward_id": "11",
      "accessible_name": "Ward 11, Toronto-Danforth and Don Valley areas",
      "path": "M…Z",
      "label_x": 612.4,
      "label_y": 388.1,
      "signal_key": "two_incumbents",
      "panel": {
        "heading": "Ward 11",
        "geography": ["Toronto-Danforth", "Don Valley West"],
        "signal_label": "Two incumbents",
        "field_status": "2 candidates",
        "incumbent_summary": "…",
        "href": "/trustees/tdsb/11"
      }
    }
  ],
  "legend": [
    {"key": "two_incumbents", "label": "Two incumbents"}
  ]
}
```

The field names and responsibilities shown above are the minimum public
contract. The implementation plan may add validated fields but must not rename
these fields or move spatial work downstream. Styling values such as literal
colours remain Frontend concerns; Backend emits semantic keys and factual
labels.

Backend rejects a map unless feature IDs exactly match the page's complete race
inventory. It does not publish a partial object. SVG numbers use fixed precision
and stable feature ordering. Simplification must preserve topology and visible
islands while keeping each embedded map comfortably below 250 KB uncompressed.

### Frontend: rendering and interaction

Frontend validates the new map object as part of its normal feed parsing and
renders it through a reusable client component. Spatial joins, projection,
geometry simplification, and label placement are prohibited in Frontend.

The component owns only presentation state:

- List versus Map for the current session;
- held selection;
- temporary pointer/focus preview; and
- responsive rendering.

It maps semantic signal keys to CSS custom properties, supplies visible legends
and focus/selection outlines, and uses SVG links/buttons with clear accessible
names. Ward numbers remain legible at normal desktop and mobile widths. Dense
downtown labels may use short leader lines or carefully offset label positions
provided by Backend, but never overlap invisibly or rely on hover alone.

Server-rendered output remains List view. The client enhances it after hydration
using `sessionStorage`; this avoids server/client disagreement and keeps the
list available when JavaScript is unavailable. The session preference is shared
under one namespaced key and is treated as optional—storage failures fall back
to List without surfacing an error.

## Failure behaviour

- Results source or topology failure: no canonical geometry is released.
- Backend geometry or inventory failure: that page's entire map object is
  omitted and the release validator records the failure; partial maps are never
  serialized.
- Frontend schema failure for a map object: the object is ignored and the page
  remains list-only.
- Session storage failure: List is the default and switching still works for
  the lifetime of the mounted component.
- No public `map unavailable` or technical coverage message is added.

The existing list is therefore the permanent safe fallback.

## Accessibility

- `List / Map` is a labelled control with an unambiguous selected state.
- Every ward is reachable by keyboard and has an accessible name containing its
  ward number and geographic label.
- Focus preview and selection use visibly different outlines.
- Enter and Space select; navigation remains a conventional link in the panel.
- Legends include text labels and do not rely on hue alone.
- The detail panel announces selection changes through a restrained live region
  without announcing pointer-only previews.
- Reduced-motion preferences disable nonessential transitions.
- The underlying List view remains available at all times.

## Testing and acceptance

### Results

- Unit tests for dissolving each board's current crosswalk.
- Exact membership, feature-count, coverage, overlap, validity, and provenance
  assertions.
- Regression tests proving historical trustee geometry remains unavailable.
- Deterministic rebuild comparison for geometry and provenance fields.

### Backend

- Tests for projection, topology-preserving simplification, view-box
  normalization, fixed numeric precision, and inside-polygon label points.
- Exact feature counts: Council 25, TDSB 12, TCDSB 12, Viamonde 3, MonAvenir 2.
- Tests that race IDs, signals, panel facts, and URLs match the tabular inventory.
- Tests for deterministic serialization, payload budgets, and all-or-nothing
  omission on invalid input.
- Release-schema and manifest tests.

### Frontend

- Feed validation for valid, missing, partial, and malformed map objects.
- List default and one shared session-scoped preference.
- Mouse, touch-equivalent click, Enter, Space, and focus-preview behaviour.
- Selection restoration after temporary preview.
- Panel facts, links, legends, semantic classes, and list-only fallback.
- Accessible names and selected/focused states.
- Browser review at desktop and mobile widths, with special attention to the
  downtown Council cluster and the smallest trustee districts.

### Release and deployment

Publish in dependency order:

1. Results with canonical current trustee geometry;
2. Polling with an exact pin to that Results release;
3. Backend with completed map objects and exact upstream pins; and
4. Frontend production deployment resolving the complete release chain.

Production acceptance requires every automated suite to pass, all five map
inventories to validate, List view to remain unchanged, and the production build
to resolve only the new coordinated releases.

## Explicit non-goals

- Historical election maps.
- Maps on individual race detail pages.
- Address lookup or `My elections` functionality.
- Basemap tiles, roads, schools, polling subdivisions, or neighbourhood layers.
- Pan/zoom as a required interaction.
- Geographic modelling or data transformation in Frontend.
- New attention, defeatability, or forecasting metrics.
