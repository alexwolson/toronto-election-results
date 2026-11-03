# Review of same-name Persons, November 2026

The audit of Person links ([`link-audit-2026-11-03.md`](link-audit-2026-11-03.md)) found that 15 of
40 sampled pairs of Persons with the same first and last name were one individual, and it merged
them. At that rate about 57 of the 152 pairs it did not sample would be missed links. This review
went through every same-name pair left in the release: the 152 the audit did not sample and the 25
sampled pairs it left undetermined. It also checked each run that an election authority flags as an
incumbent against the Person's earlier wins.

The review joined 66 of the 155 name groups, 63 in full and 3 in part, and showed two to be
different people. It also joined four 2026 trustee runs and one pair of Persons whose printed first
names differ. In all, 71 person-record merges remove 70 Persons and give a Person to six runs that
had none. The release now has 5,104 People, and the number of same-name pairs falls from 177 to 103.
Of those 103, two are known to be different people, two are in groups joined in part, and 99 are in
the 87 groups that no source settled. The incumbency check found four of the missed links and two
flags that contradict the record, which are now corrected.

## Frame

The frame is the audit's: pairs of distinct Persons whose first and last names match once middle
names and initials are dropped (`first_last` in
[`scripts/draw_link_audit_sample.py`](../../scripts/draw_link_audit_sample.py)). At commit
`0298ca6`, after the audit's fixes, the release had 177 such pairs among 321 Persons. They fall into
155 name groups, one for each first and last name. Each group also lists the runs of that name that
have no Person (held runs), 48 in all, so that a source naming one could place it.

## Method

Four agents took the 134 groups that held at least one pair outside the audit's sample. Their brief
followed the audit's, with two changes: they could read the release's earlier research and
dispositions so as not to repeat dead ends, and each federal run in their packets carried the
occupation Elections Canada lists for the candidate. They searched the web (news, Wikipedia and
archived copies of its candidate lists, party and campaign pages, candidate guides, legislature
pages and obituaries) with a limit of 40 searches each. They did not use LinkedIn, ProQuest or pages
behind a login, and name-matched databases such as the Canadian Elections Database counted as leads
only. For each group they proposed a join, said the Persons were different people, or left the group
undetermined with an estimate of how likely one individual was and the Toronto Star searches most
likely to settle it.

The coordinator then searched the Toronto Star in ProQuest for 51 groups: the 21 groups whose pairs
had all been sampled by the audit and left undetermined, and 30 groups from the web review, mostly
those its reviewers rated most likely to be one individual. The Star's riding profiles for the 1993,
1995 and 1997 elections, its ward guides for 1994, 2000, 2003 and 2006 and its news stories describe
many minor candidates in a sentence or two, often with an age and an occupation.

A script screened every pair of runs, between two Persons of a group or between a held run and a
Person of the same name anywhere in the release, for the conditions of the release's two structural
rules that it could test: the office, the party, the dates and the number of general elections
between. The second check decided the rest: whether the wards or ridings overlap, and whether the
name is common. Sixteen held runs passed the screen against a Person other than the one an earlier
review had proposed for them, and they were checked too.

Every proposed join and every screened pair went to a second agent that had done none of the
research: six agents in all, with up to eight web searches each, over 106 items. Each opened the
cited pages, checked that the quotes were there and matched the records (office, ward or riding,
year, party, placing and votes), searched the release for other runs or Persons a source could
describe instead, read what earlier reviews wrote about the names, and judged the evidence against
the release's standard (see the Identity section of [`docs/build-notes.md`](../build-notes.md)). It
could not open ProQuest, so for the Star it took the quoted words as given and checked everything
else. A shared party is not a distinctive fact under that standard, however small the party. A join
counts only if the second check accepted it.

The results are in [`same-name-review-2026-11-03/`](same-name-review-2026-11-03/): `groups.csv`
gives each group's Persons, the web reviewer's verdict and notes, the ProQuest findings, the second
check and the outcome; `joins.csv` gives each merge with its sources and the rationale recorded in
the release; `held_run_pairings.csv` gives the 16 held-run pairings.

## Results

| Path | Groups | Joined | Joined in part | Different people | Undetermined |
|---|---:|---:|---:|---:|---:|
| Audit sample only (ProQuest) | 21 | 8 | 0 | 0 | 13 |
| Web reviewer proposed a join | 47 | 45 | 0 | 0 | 2 |
| Web reviewer left undetermined | 85 | 10 | 3 | 0 | 72 |
| Web reviewer found different people | 2 | 0 | 0 | 2 | 0 |
| All | 155 | 63 | 3 | 2 | 87 |

The second check accepted 59 of the 80 items in the three main packets, and 58 of those joins were
applied. The one not applied is Franz Cauchi's: the second check found a former Wikipedia list of
Freedom Party candidates that ties his 2003 Davenport and 2006 Toronto—Danforth runs, but only in an
unofficial mirror, and without it the ridings do not overlap. It rejected the web reviewers' joins
of George Singh, where a 2022 news excerpt says Knia Singh returned to politics in 2010 without
naming the race, and of Nunzio Venuto, whose Davenport runs meet every condition of same-office
continuity except the name: a third Person of that name ran federally in 1993. The other rejections
are screened pairs whose wards or ridings do not overlap or whose name is common.

Of the 71 joins, 16 rest on the structural rules, sometimes with an occupation that agrees, and 18
wholly or partly on Toronto Star articles read in ProQuest. The others rest on other public sources:
Wikipedia and archived copies of its candidate lists, the House of Commons and Legislative Assembly
pages, party pages, candidate guides, and the occupations Elections Canada gives for two or more
runs.

The two groups of different people are Doug Ford, whose 1995 Etobicoke-Humber run is his father Doug
Ford Sr.'s, and Michael Yorke, where the council and NDP candidate was a carpenter and union
organizer and the trustee candidate a travel agent, and the two ran in different races in 1994.

For 62 of the 87 undetermined groups the web reviewer gave an estimate: 32 at 75 per cent or more
likely to be one individual, 23 between 50 and 75 per cent, and 7 below 50. These stay separate
Persons because no source ties them. Seven groups with common names were not searched, as the brief
directed.

## Held runs

Six held runs now have a Person. Birinder Singh Ahluwalia's 2022 Willowdale run continues his 2018
run there once that run joins his federal Willowdale runs, and Diana-De Maxted's 2001 Ward 31
by-election run is named on Wikipedia's page on the 2014 mayoral election. The other four are 2026
trustee runs that the August career reviews held because no source tied the 2026 candidate to an
earlier run. The Local's 2026 ward guides, whose trustee sections were added on 14 October, make
that tie: Darren Frake's 2022 Ward 20 run, Celine DiNova's 2022 Ward 11 run and Gus Stefanis's 2025
Ward 11 by-election run are each named with the placing in the record, and Sal Piccininni is
described as a former TCDSB trustee until 2018 (the guide's ward number and first year differ from
the record, which has him elected for Ward 3 from 1997). The coordinator read the four guides as
well. Of the 16 screened pairings of held runs, the other 12 fail a condition, most often because
the hold's own target carries the same name.

## Incumbency flags

In the published release, Elections Canada and Elections Ontario flag 392 runs as incumbents (203
federal, 189 provincial). Seven of those after each body's first general election belonged to a
Person with no earlier win in that body. Four were missed links: Joseph Cordiano's 1995 Lawrence run
(printed Joseph) and his York South—Weston runs (printed JOE), John McKay's 1997 run (printed John
N. McKay), Morley Kells's 2003 and 2010 runs, and Sarmite Bulte's 1997 and 2000 runs, which an
earlier curation had left apart from her 2004 and 2006 runs although its source, the House of
Commons page, lists all four. Cordiano's pair is outside the same-name frame because the first names
differ; a second agent checked it against the Legislative Assembly's page for him. The remaining
case is John Tory's 2007 run, flagged because he first won a 2005 by-election outside Toronto.

The other two were wrong flags. Elections Ontario's 1999 file marks John Sewell, an independent in
Toronto Centre—Rosedale, as a member of the previous legislature; he never sat in it, and the flag
had given him an MPP tenure. Elections Canada's 2015 file for Don Valley West marks both John
Carmichael, the sitting member, and Natalie Hunt, the Green candidate. Pinned corrections in the
Ontario and federal adapters set both flags to false, and the load fails if either source changes.

The build also stops carrying an incumbency hold forward once its run is no longer flagged. The
published release had 63 such holds; 27 remain, 24 of them for sitting members at the 1995 Ontario
election, the first in the release, and three for members whose earlier win is printed under another
form of their name.

## Other fixes

- John Steele's 2003 Parkdale—High Park run is held. The audit found that its only tie to his other
  runs was a name-matched database. A review hold can now replace a link the build made
  automatically, as here, but not a curated one. The rationales of his 1994 and 2000 mayoral links
  now cite Elections Canada's 2006 occupation instead of the database.
- Elections Ontario's candidates file for the 2006 Parkdale—High Park by-election codes Jim McIntosh
  as Liberal, beside the Liberal Sylvia Watson, while its party list for that by-election names the
  Ontario Libertarian Party and no candidate carries that code. Wikipedia's riding page gives
  McIntosh as the Libertarian. A pinned correction in the Ontario adapter recodes him, and no
  Contest now has two candidates of one party.

## Leads not followed

- Dan Goldstick's 2004 Toronto Centre run: Elections Canada gives him as a university teacher in
  2000 and 2004, and the 2000 run is now in Danny Goldstick's Person. The printed names differ, so
  the pair is outside this frame.
- Kostadinos Stefanis and Gus Stefanis, Arnold Kwok and Kingsley Arnold Kwok: near-name pairs that
  may be one individual.
- Philip Fernandez's held federal runs, whose occupations in Elections Canada's files (literacy
  worker, adult educator, teacher) suggest one career.
- The three Nunzio Venuto Persons, which look like one Libertarian career.

[`scripts/list_near_name_pairs.py`](../../scripts/list_near_name_pairs.py) lists the pairs of
distinct Persons whose printed names are close but do not share a first and last name: a common
nickname pair, a first name used as a middle name, surnames one letter apart, or the same words in
another order. On this release it lists 71 pairs
([`same-name-review-2026-11-03/near_name_pairs.csv`](same-name-review-2026-11-03/near_name_pairs.csv)).
They have not been reviewed.

## Limitations

The research and the second check were done by AI agents, and every verdict's sources, quotes and
notes are in the results files so that a reader can check them. The second check could not open
ProQuest. Some agents read pages by downloading them with the shell instead of the fetch tool, three
of them pages the fetch tool had refused, and one used an unofficial mirror. The joins that rested
on those pages were either confirmed from other sources or, for the mirror, not applied. For five
joins the deciding source was found by the second check itself rather than by the research agents:
the four 2026 trustee joins and Ray Scott's. The coordinator read those sources as well.

Undetermined is not a finding that two Persons are different people. Most undetermined groups are
minor candidates for whom the only records are result listings, and the web reviewers rated many of
them as likely one individual.
