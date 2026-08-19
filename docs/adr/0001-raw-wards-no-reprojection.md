# Record wards as-run; do not reproject across the 2018 boundary change

Status: accepted

## Context

Toronto ran on **44 wards (2000–2014)** and **25 wards (2018–present)** with entirely
different numbering and boundaries; the two eras are not comparable. The dataset feeds a
ward-level vote-share model that spans the change. We had to decide whether to unify wards
onto one geography or keep them as each election used them.

## Decision

Store each result with the ward **exactly as that election used it**, tagged by a
`ward_system` column (`44-ward` / `25-ward`). We do **not** reproject historical results
onto the current 25-ward map. Voting-subdivision **boundary polygons** are published as a
separate companion dataset (2006 onward, the years the City provides geometry) so a
downstream model can build its own crosswalk if it wants one.

## Considered options

- **(a) Raw wards + `ward_system` tag** — chosen. Lossless, faithful, cheap.
- **(b) Raw wards + an approximate name/area crosswalk table** — deferred; the companion
  polygons let downstream build this on demand, so we don't bake an approximation in.
- **(c) Reproject all results onto the 25-ward geography** — rejected. Honest area-weighted
  reallocation needs subdivision-level vote data (which we deliberately don't carry — grain
  is ward-level) and has no subdivision geometry for 2000/2003, so it would fabricate
  precision for the earliest years.

## Consequences

- Cross-year ward comparability is **the model's job, not the dataset's** — by design.
- The results table never claims a false one-to-one ward lineage across 2014→2018.
- The companion polygon dataset only covers 2006+, so any downstream crosswalk inherits
  that floor.
