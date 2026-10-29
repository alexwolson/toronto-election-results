# Extend coverage to the last election round before amalgamation

Status: proposed (2026-10-29). Supersedes ADR 0003's 2003 floor.

## Context

The dataset starts on January 1, 2003. Readers will ask why it starts there rather than at
amalgamation, and a 2003 start hides the question the extension can answer: who carried office
across the creation of the new City of Toronto on January 1, 1998. ADR 0003 dropped 2000 because its
results were not on Open Data, had no Clerk's declaration and no elector counts. Those limits still
hold, but they argue for null electorate columns, not for leaving the results out.

## Decision

- The Coverage window starts with the last general election of each Election authority before
  amalgamation took effect:
  - municipal: the November 14, 1994 elections in the six former municipalities, for Metropolitan
    Toronto Council and for the school boards then serving the area;
  - provincial: the June 8, 1995 Ontario general election;
  - federal: the October 25, 1993 federal general election.
- Every in-scope election from those dates onward is in scope, including 1997 and 2000 municipal,
  1999 provincial, 1997 and 2000 federal, and the by-elections between them.
- City of Toronto scope is unchanged: a Contest is in scope when its geography lies within today's
  City boundary. Metropolitan Toronto's boundary is the same as the City's, so every 1994 municipal
  Contest in Metro is in scope.
- Municipal results before 2003 come from the City's archived results pages. They carry no elector
  counts, so Eligible electors, Ballots cast and Turnout are null for those Contests. A Contest the
  archive marks "Results not available" ships as a `source_missing` placeholder.
- Utility and hydro commission contests on the archived pages stay out of scope; they are not an
  in-scope Office type.

## Consequences

- New Represented bodies: the six former municipal councils, Metropolitan Toronto Council, and the
  pre-1998 school boards. Each keeps its own Boundary regime; nothing is reprojected.
- Several of these bodies elected more than one member per ward, which needs ADR 0011.
- Incumbency across amalgamation needs ADR 0012; without it, no 1997 Candidacy can be an
  Incumbent, because none of the new bodies had a prior roster.
- The 2000 parser removed by ADR 0003 can be recovered from git history and adapted.
- Event coverage for the municipal by-elections of 1995–2002 is `uncertain` until the City's
  archive for that period is checked, as it already is for trustee by-elections before 2012.
- Mayoral career backfill rows inside the new window are removed once an official adapter
  carries the same Contest, and the career decision maps to the official Candidacy instead
  (`reuse_existing`). Kevin Clarke's 1995, 1996 and 2001 provincial rows and his 1997 federal row
  are done, as are the municipal rows for Clarke (1994 East York mayor, 2000 mayor) and Olivia
  Chow (1994 Metro Downtown, 1997 Ward 24, 2000 Ward 20).
- The municipal adapter covers 1994, 1997 and 2000 Mayor, Councillor and Metro Councillor
  Contests. Eight 1994 Contests ship as `source_missing` placeholders (North York council wards
  3–5 and five Metro wards). Where the archive lost a 1994 Metro ward label, the label comes from a
  secondary source and the row cites it; vote counts are always the archive's.
- The 2000 trustee Contests for all four School Boards are included, transcribed from the City's
  archived "Vote 2000" pages. The 1994 and 1997 school-board sections of the archive are
  incomplete (no seat counts, garbled or missing ward labels, missing contests, and French-language
  results only as partial subtotals across municipalities), so those boards wait for a complete
  published source such as the newspapers' printed results.
- Federal results before 2004 come from three official sources: Elections Canada's 1993
  Recapitulation of Votes data files (released through the U of T Map & Data Library), Elections
  Canada's 1997/2000 poll-by-poll result files, and Elections Canada's official voting results
  reports for the 1996 Etobicoke North and 1999 York West by-elections.
