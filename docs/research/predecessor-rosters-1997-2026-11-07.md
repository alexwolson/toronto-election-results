# Predecessor rosters for the 1997 election (2026-11-07)

The 1994 municipal elections are in the release to give the first election of the amalgamated
City, on 10 November 1997, its incumbency. ADR 0012 records that incumbency as
`predecessor_incumbent`: whether a Person sat, on the day before polling, in a predecessor body
for the same Office type. The 1994 elections themselves get no incumbency, since that would need
the councils elected in 1991.

`data/reference/predecessor_rosters_1997.csv` lists the members of Metropolitan Toronto Council and
the six former councils on 9 November 1997: six mayors and 100 councillors, one for each seat
filled in 1994.

## How the rosters were built

The rosters start from the 106 mayors and councillors the release has as elected in 1994. Two of
them left in 1995 to sit in the legislature, and their seats were filled:

- Mario Sergio, North York Ward 1, won Yorkview at the provincial election of 8 June 1995. George
  Mammoliti won the by-election for his seat on 21 September 1995
  ([Toronto Star, 22 September 1995](https://www.proquest.com/docview/437328398)).
- John Hastings, Etobicoke Ward 12, won Etobicoke—Rexdale at the same election. Etobicoke council
  appointed the runner-up from 1994 to save the cost of a by-election
  ([Toronto Star editorial, 21 September 1995](https://www.proquest.com/docview/437326715)). That
  was Vincent Crisanti, printed Vincent Chrisanti in the 1994 results. The City's councillor
  profile says he served "in 1995 prior to amalgamation" and was Deputy Mayor of Etobicoke
  ([City of Toronto](https://www.toronto.ca/councillors/crisanti1.htm)). His start is recorded as
  on or before 21 September 1995.

## Checks on completeness

- A search of the Toronto Star on ProQuest from 15 November 1994 to 9 November 1997 for
  by-election stories on the six councils, Metro council and the school boards, about 180
  results, found only the North York Ward 1 by-election
  (`docs/research/by-elections-1995-2011-2026-10-31.md`).
- No other 1994 winner won a federal or provincial election before November 1997.
- The release's identity research on the 1997 candidates, much of it from the Star's 1997
  profiles, was read for every mention of a council or mayoral role. It describes no candidate as
  a sitting member whom the rosters leave out, and none whom they list as a former member.

A seat vacated by resignation or death and filled by appointment, with no by-election and no
higher office involved, would not be found by these checks unless its holder ran in 1997. Such a
change could make a 1997 candidate who was appointed mid-term `false`, or one who left mid-term
`true`.

## Results

| 1997 race | `true` | `false` | null |
|---|---:|---:|---:|
| City Councillor | 81 | 101 | 11 |
| Mayor | 2 | 17 | 1 |

The nulls are Candidacies with no Person. The two mayoral incumbents are Barbara Hall, Mayor of the
former City of Toronto, and Mel Lastman, Mayor of North York. Under ADR 0012 the mayoralty counts
only the six former mayors, and the councillor races count only councillors. So the four sitting
mayors who ran for council, Doug Holyday (Etobicoke), Frank Faubert (Scarborough), Frances
Nunziata (York) and Michael Prue (East York), are `false` for council.

## School boards

The Star search found no by-election on the boards, and no source found lists their mid-term
changes. A board can fill a vacant seat by appointment, which would not appear in by-election
stories. The boards therefore have no roster, and `predecessor_incumbent` stays null for the 1997
trustee races, as `incumbent` does for every trustee election before 2026.
