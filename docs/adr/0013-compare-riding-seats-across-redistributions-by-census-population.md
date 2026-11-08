# Compare riding seats across redistributions by census population

Status: accepted (2026-11-07).

## Context

`incumbent_changed_district` says whether an incumbent ran for a seat other than the one held.
Within one Boundary regime that is a comparison of district IDs. Across a boundary change the
release asks which new district took over the held seat, and the member keeps the seat when they
run in that district. For council wards the successor is the new ward holding the most of the held
ward's polls (the City's voting subdivisions), which follows where electors live; this is set for
the 2018 council election.

Federal and Ontario ridings change at each redistribution, and the release now has their shapes
for the 1996, 2003, 2013 and 2023 federal orders and Ontario's 1999, 2007 and 2018 sets. Polls are
not available for ridings in a form that spans those orders, so 165 of the 396 riding incumbents
had no value.

## Decision

- A riding's successor is the new riding that holds the most of the held riding's population.
  Population is counted with census points: each dissemination area of the City is a point at
  Statistics Canada's representative point, weighted by the area's population. A held riding's
  people are the points inside its shape. A tie, or no people found, leaves the field null. This
  is the council rule with population for polls, and the same code
  (`incumbent_seats._main_successor`) applies it.
- Each redistribution is compared with the census it was drawn from: the 2011 Census for the
  federal 2013 Representation Order and for Ontario's 2018 ridings, which the Representation Act,
  2015 adopted from it, and the 2021 Census for the federal 2023 Representation Order.
- The points come from Statistics Canada's Geographic Attribute Files for 2011 and 2021, saved
  from their pages by hand, compiled by `scripts/build_census_population_points.py` into
  `data/reference/census_population_points.csv` (population summed from dissemination blocks,
  within census subdivision 3520005). The compiled totals equal the City's census populations
  (2,615,060 in 2011, 2,794,356 in 2021).

## Consequences

- The field is set for 56 more incumbents: the MPs at the 2015 and 2025 federal elections and the
  MPPs at the 2018 Ontario election. Three ran for another seat: Chrystia Freeland (Toronto Centre
  to University—Rosedale, 2015), Joe Daniel (Don Valley East to Don Valley North, 2015) and Michael
  Coteau (Don Valley East to Scarborough—Woburn, 2025).
- Some splits are close. Don Valley East's 2011 population divided 51.5% to the new Don Valley
  East and 48.5% to Don Valley North, which decides Joe Daniel (2015) and Michael Coteau (2018).
  Trinity—Spadina gave 53.6% to Spadina—Fort York and Scarborough Centre 54.3% to Scarborough
  Centre—Don Valley East.
- 109 riding incumbents stay null. The 2001 Census, from which the 2003 order and Ontario's 2007
  ridings were drawn, is published only on the GeoSuite CD-ROM and is not acquired, so the 2004
  MPs and 2007 MPPs (39) stay null until it is. The 1997 MPs and 1999 MPPs (44) held ridings of
  the 1987 boundaries, which have no shapes. The 26 sitting members at the 1995 Ontario election
  are known only from Elections Ontario's flag, which gives no seat.
- While adding this, a variable that held the district-to-regime map was reused for the new
  regime's districts, so a same-regime move judged after a boundary change could lose its `true`.
  No published value changed when it was fixed.
