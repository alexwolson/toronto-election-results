# 2026 Toronto trustee map boundary verification

**Reviewed:** 2026-08-27  
**Scope:** Current Toronto portions of the TDSB, TCDSB, Viamonde, and MonAvenir electoral districts

## Decision

The canonical 2026 trustee-to-City-ward crosswalk is sufficient to derive the
Toronto map polygons for all four boards. The City of Toronto's official
**2026 Municipal Election – School Board Reference Chart**, updated April 23,
2026, directly enumerates every trustee ward and its corresponding current City
wards for all four boards:

https://www.toronto.ca/wp-content/uploads/2026/04/9600-2026-School-board-ward-reference-chart.pdf

The rows in `data/reference/trustee_ward_crosswalks.csv` reproduce that chart.
For each board, City wards 1 through 25 occur exactly once. A trustee polygon can
therefore be constructed without approximation by unioning the corresponding
canonical City ward polygons.

These are maps of the Toronto portion of each electoral district. They are not
maps of either French-language board's full service territory outside Toronto.

## Board verification

### TDSB

The City chart specifies 12 wards and their component City wards. The TDSB's
own **Approved Trustee Ward Structure (12 Wards)**, produced by Strategy &
Planning in April 2026, independently maps the same structure over municipal
ward boundaries:

https://www.tdsb.on.ca/Portals/0/docs/Ward%20Map.pdf

The 12 canonical rows match the City chart exactly.

### TCDSB

The City chart specifies 12 wards and their component City wards. This is
consistent with the TCDSB's approved realignment to the 25-City-ward model,
which describes trustee wards as individual City wards or explicit City-ward
groups:

https://assets.tcdsb.org/TCDSB/2386752/august-2018-motions-in-review-public.pdf

The 12 canonical rows match the current City chart exactly.

### Viamonde

The City chart specifies three Toronto districts:

- Ward 2 — Est: City wards 6, 15, 16, 17, 18, and 20 through 25;
- Ward 3 — Centre: City wards 10 through 14 and 19; and
- Ward 4 — Ouest: City wards 1 through 5 and 7 through 9.

The canonical rows match those memberships and official chart labels exactly.
Viamonde's 2026 board-apportionment material uses `Toronto Nord-Est` in a
population table, while its public election page and the City election chart use
`Toronto-Est`/`Est`. This is a naming distinction, not a conflicting boundary
membership. For Toronto's certified municipal-election presentation, the City
chart's `Est`, `Centre`, and `Ouest` labels remain canonical.

Board apportionment material:
https://csviamonde.ca/fileadmin/viamonde/Documentation_Conseil/Documents_PUB_17_avril_2026.pdf

Board election page:
https://csviamonde.ca/gouvernance/elections

### MonAvenir

The City chart specifies two Toronto districts:

- Ward 3 — Toronto Ouest: City wards 1 through 13 plus 18; and
- Ward 4 — Toronto Est: City wards 14 through 17 and 19 through 25.

The canonical rows match those memberships and official labels exactly.
MonAvenir's public election material also uses `Toronto Ouest` and
`Toronto Est` for its Toronto races:

https://cscmonavenir.ca/elections/

## Admission gate

All four current board crosswalks pass the source gate for derived Toronto map
geometry. Geometry generation must additionally prove complete coverage,
zero-area interior overlap, and equality with the canonical Toronto union.
Historical trustee geometry remains out of scope and explicitly unavailable.
