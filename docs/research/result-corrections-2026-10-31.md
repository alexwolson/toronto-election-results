# Two result corrections (2026-10-31)

The 2010–2017 backlog review (`backlog-2010-2017-2026-10-31.md`) turned up two faults in published
results. Both are fixed in the adapters, so a rebuild from the same sources gives the corrected
figures.

## 2017 Ward 42 by-election: ballot-accounting lines

The City's poll-by-poll workbook for the 13 February 2017 Ward 42 by-election prints three lines
between the last candidate and the Totals row: "Declined Ballots" (4), "Rejected Ballots (Over
Votes)" (3) and "Under Votes" (7). The parser skipped only lines containing "total", so earlier
releases published these lines as three Candidacies, each with its own Person, and the contest had
32 candidates against the 29 in the City's declaration.

`parse_results._parse_ward_sheet`, which reads the mayor and councillor workbooks, now also skips
a line that names ballots or under/over votes. In the workbooks the build reads, it removes these
three lines and nothing else, and no other published candidate name contains those words. The 2024
and 2025 by-election workbooks give their declined and rejected ballot counts on a Read Me sheet
that has no candidate table, so they were never read as candidates. The 29 candidate totals add up
to 10,418, and the sheet's Totals cell is 10,432, which is that sum plus the three accounting
lines. The workbook is now a test fixture.

The three Candidacies are retired. Their ledger rows were deleted, their rows were stripped from
`election_results.csv` and `candidacy_person_links.csv`, and their People were removed from
`people.csv` before the rebuild. The prior build manifest's checksums for those three files and
the ledger were re-recorded so that the prior-registry checks accept the edited release. The
three Person IDs are withdrawn, because none held another Candidacy and there is no Person to
redirect them to. The manifest's expected count for the event is now 29.

| Candidacy | Person | Line in the workbook | Published name |
|---|---|---|---|
| `can_c48ca266532a54518a81be14b8066684` | `per_00b0b71d92ce5b758026b915b3f28190` | Declined Ballots | Ballots Declined |
| `can_6ccad1456b815f7aa35d020b3198ef6b` | `per_42006f4bda515db7a457e16135d04899` | Rejected Ballots (Over Votes) | Ballots (Over Votes) Rejected |
| `can_c213f6d4397f50d0af5b551ebebb0c07` | `per_66fe9c126e6555948e27b0150dc52a4e` | Under Votes | Votes Under |

## Willowdale, 2011 provincial election: swapped totals

Elections Ontario's 2011 candidate CSV (report group 3, output 499) gives the Freedom Party's Amy
Brown 5,556 votes (12.85%) and the NDP's Alexander Brown 297 (0.69%). Two independent sources give
the reverse:

- The Toronto Star's election-night table of 7 October 2011, page R2
  ([ProQuest 896533488](https://www.proquest.com/docview/896533488)), with 269 of 288 polls
  reporting: Alexander Brown, NDP, 4,743; Amy Brown, FP, 269.
- [Wikipedia's Willowdale riding page](https://en.wikipedia.org/wiki/Willowdale_(provincial_electoral_district)):
  Alexander Brown 5,556 (12.85%), Amy Brown 297 (0.69%).

Elections Ontario's PDF return could not be fetched for this check.

`ontario.VOTE_CORRECTIONS` pins both rows. The load checks that the CSV still prints 5,556 for Amy
Brown and 297 for Alexander Brown before it swaps them back, and it fails if either figure changes
or either row disappears, so a corrected upstream file will be noticed. The winner, David Zimmer,
and the other three totals are unchanged.

## Other contests with two candidates of one surname

The Willowdale swap is between two candidates who share a surname, so every other Contest with two
or more candidates of one surname was checked against a second source. Matching on the last word of
the published name gives 28 groups in 23 Contests, Willowdale included. The other 22 Contests agree
with the second source.

| Contest | Candidates and votes | Checked against |
|---|---|---|
| 1993 federal, Etobicoke North | Roy MacLaren (Liberal) 28,119; Jane MacLaren (PC) 4,936 | [Canadian Elections Database](https://canadianelectionsdatabase.ca/candidates/jane-maclaren/) |
| 1994 council, Toronto Ward 1 | Bill Roberts 1,725; Greg Roberts 168 | [Wikipedia, 1994](https://en.wikipedia.org/wiki/1994_Toronto_municipal_election) |
| 1997 council, Ward 11 | Kim Scott 4,742; Allen Scott 4,369 | [Wikipedia, 1997](https://en.wikipedia.org/wiki/1997_Toronto_municipal_election) |
| 1997 council, Ward 18 | Terry Singh 1,812; Jasmine Singh 871; George B. Singh 339 | Wikipedia, 1997 |
| 1997 council, Ward 20 | Mario Silva 10,252; Martin Silva 8,329 | Wikipedia, 1997 |
| 2000 council, Ward 22 | Michael Walker 11,542; Jim Walker 4,822 | [Wikipedia, 2000](https://en.wikipedia.org/wiki/2000_Toronto_municipal_election) |
| 2000 council, Ward 30 | Jack Layton 8,671; Jeff Layton 627 | Wikipedia, 2000 |
| 2006 council, Ward 41 | Chin Lee 5,501; Min Lee 139 | [Wikipedia, 2006](https://en.wikipedia.org/wiki/2006_Toronto_municipal_election) |
| 2010 Viamonde trustee, Ward 4 | Luc Lalonde 297; Christopher Lalonde 175 | Clerk's declaration |
| 2014 council, Ward 38 | Rajesh Shah 405; Tushar Shah 185 | [Wikipedia, 2014](https://en.wikipedia.org/wiki/2014_Toronto_municipal_election) |
| 2018 provincial, Scarborough North | Dwayne Morgan (NDP) 8,320; Sean Morgan (Libertarian) 318 | [Wikipedia riding page](https://en.wikipedia.org/wiki/Scarborough_North_(provincial_electoral_district)) |
| 2018 provincial, Spadina–Fort York | Iris Yu (PC) 10,834; Queenie Yu (Stop the New Sex-Ed Agenda) 86 | [Wikipedia riding page](https://en.wikipedia.org/wiki/Spadina%E2%80%94Fort_York_(provincial_electoral_district)) |
| 2018 council, Ward 18 | Winston Park 593; Chung Jin Park 101 | [Wikipedia, 2018](https://en.wikipedia.org/wiki/2018_Toronto_municipal_election) |
| 2018 TDSB trustee, Ward 19 | Zakir Patel 3,725; Baldev Patel 1,361 | Clerk's declaration |
| 2019 federal, Scarborough North | Shaun Chen (Liberal) 20,911; Yan Chen (NDP) 5,039 | [Wikipedia riding page](https://en.wikipedia.org/wiki/Scarborough_North_(federal_electoral_district)) |
| 2022 council, Ward 1 | Kristian Santos 613; Ricardo Santos 421 | [Wikipedia, 2022](https://en.wikipedia.org/wiki/2022_Toronto_municipal_election) |
| 2022 council, Ward 22 | Nick Mantas 8,228; Antonios Mantas 1,841 | Wikipedia, 2022 |
| 2022 mayor | Monowar Hossain 1,840; Soaad Hossain 1,670 | [Wikipedia, 2022 mayoral](https://en.wikipedia.org/wiki/2022_Toronto_mayoral_election) |
| 2022 TCDSB trustee, Ward 5 | Maria Rizzo 5,122; Domenic Rizzo 853 | Clerk's declaration |
| 2023 mayoral by-election | Jamie Atkinson 361; Darren Atkinson 192; Knia Singh 246; Partap Dua Singh 132 | [Wikipedia, 2023 by-election](https://en.wikipedia.org/wiki/2023_Toronto_mayoral_by-election) |
| 2024 federal by-election, Toronto–St. Paul's | Daniel Gagnon 8, Donald Gagnon 7; Anthony Hamel 9, Felix-Antoine Hamel 0; Julie St-Amand 13, Pascal St-Amand 9; Darcy Vanderwater 4, Gavin Vanderwater 3 | [Elections Canada, Table 12](https://www.elections.ca/res/rep/off/ovr_2024b/58/table12E.html) |
| 2026 mayor | Olivia Chow 532,201; Braeden Chow 8,102; Leila Yohannes 206; Henoke Yohannes 157 | The Clerk's 2026 declaration (PDF) |

The three trustee Contests are covered by the earlier reconciliation of every 2003–2022
general-election trustee Contest against the Clerk's declarations, which matched each one by
candidate and vote count (`tcdsb-2010-ward-assignment-2026-10-29.md`). Wikipedia's 1993 table for
Etobicoke North gives the PC candidate the Reform candidate's total (9,470) and differs from the
official file in several other rows, so it was not used.
