# Review of near-name Persons, November 2026

The review of same-name Persons ([`same-name-review-2026-11-03.md`](same-name-review-2026-11-03.md))
covered pairs of Persons whose first and last names match. It left a second set unreviewed: 71 pairs
of Persons whose printed names are close but differ, such as a nickname and the full given name
(Mike and Michael), a given name used with or without a middle name, or surnames one letter apart
(Crisanti and Chrisanti). This review went through all 71.

The review joined 26 of the 71 pairs, in 24 person-record merges that remove 26 Persons and give a
Person to two runs that had none. It showed one pair to be different people and left 44
undetermined. The release now has 5,078 People, and the near-name listing falls from 71 pairs to 45.
Three of the merged Persons are Greg Roberts Persons that the same-name review had left
undetermined, so the number of same-name pairs falls from 103 to 100.

## Frame

[`scripts/list_near_name_pairs.py`](../../scripts/list_near_name_pairs.py) lists the pairs of distinct
Persons whose printed names are close but do not share a first and last name: the same last name
with first names that are a common nickname pair or of which one begins with the other, the same
last name with the first name of one used as a middle name of the other, the same first name with
last names one letter apart (five letters or more), or the same words in another order. Pairs of
Persons who ran in the same election are left out. At commit `2231aa7` it listed 71 pairs
([`same-name-review-2026-11-03/near_name_pairs.csv`](same-name-review-2026-11-03/near_name_pairs.csv)).

The pairs connect 134 Persons in 63 items, an item being the Persons linked by one or more pairs, so
that three or four Persons of close names were reviewed together. Each item also lists the runs
under the same names that have no Person (held runs), 12 in all.

## Method

Two agents took the items, 32 and 31 each. Their brief followed the same-name review's, with one
addition: for a near-name pair the evidence also had to account for the different printed names,
for example a source that gives both forms for one person, a profile that uses the nickname for a
run printed with the full name, or an official document that prints the name the other way. They
searched the web with a limit of 40 searches each, could read the release's earlier research and
dispositions, and had Elections Canada's occupation for every federal run. They did not use
LinkedIn, ProQuest or pages behind a login, and name-matched databases counted as leads only.

The coordinator searched ProQuest for 21 items, mostly pairs with runs before 2010 that the web
review had left undetermined. Most of the articles are from the Toronto Star, whose riding and ward
profiles describe minor candidates in a sentence or two. The others are from Metroland's York
Guardian and Etobicoke Guardian, the Cambridge Times and the Ottawa Citizen.

A script screened every near-name pair, and every held run against a Person of a close name, for
the conditions of the release's two structural rules that it could test: the office, the party,
the dates and the number of general elections between. It found 26 candidates. For a near-name
pair a structural rule applies only when the two printed names are evidently forms of one name: a
common nickname of the given name, a middle name or initial added or dropped, the same words in
another order, or a nickname printed beside the full name in one of the runs, as in "Salvatore
(Scott) Cusimano". Surnames one letter apart are not evidently one name unless a source shows that
one form is a misprint.

Every proposed join and every screened candidate went to a second agent that had done none of the
research: five agents in all, with up to eight web searches each, over 34 items. Each opened the
cited pages, checked that the quotes were there and matched the records, searched the release for
other runs or Persons a source could describe instead, read what earlier reviews wrote about the
names, and judged the evidence against the release's standard (see the Identity section of
[`docs/build-notes.md`](../build-notes.md)), including the near-name requirement above. It could not
open ProQuest, so for those articles it took the quoted words as given and checked everything
else. A join counts only if the second check accepted it. One item, Tony and Anthony Figliano, was
checked twice: first on the structural screen alone, which failed, and again with the Star articles,
which the second check accepted.

The results are in [`near-name-review-2026-11-04/`](near-name-review-2026-11-04/): `pairs.csv` gives
each pair's Persons, the web reviewer's verdict and notes, the ProQuest findings, the second check
and the outcome; `joins.csv` gives each merge with its sources and the rationale recorded in the
release.

## Results

| Path | Pairs | Joined | Different people | Undetermined |
|---|---:|---:|---:|---:|
| Web reviewer proposed a join | 22 | 17 | 0 | 5 |
| Web reviewer left undetermined | 48 | 9 | 0 | 39 |
| Web reviewer found different people | 1 | 0 | 1 | 0 |
| All | 71 | 26 | 1 | 44 |

The second check accepted 24 of the 34 items it saw. It rejected five of the web reviewers'
proposals:

- Dan and Daniel Stein (Davenport Green candidate in 2014 and 2015) and Chris and Christopher Jason
  Goodwin (Freedom Party in Toronto Centre in 2011 and 2014): no source ties the two runs, and the
  structural rules need an uncommon name.
- Ram Maharaj (TDSB Ward 4 in 2006, 2010 and 2018) and Rameshdath Maharaj (the same ward in 2022):
  Ram is not evidently a form of Rameshdath, and no source gives both.
- Francesco and Frank D'Amico (TCDSB Ward 6 from 2006): a second Frank D'Amico, a 2003 TDSB
  candidate kept apart by earlier reviews, rules out the structural rules.
- Antonio and Tony Loureiro (1994 separate school board and 1997 TCDSB): no source gives the extent
  of the 1997 TCDSB Ward 10, so the ward overlap is not shown.

Of the 24 joins, 12 rest on public sources found on the web: Wikipedia articles and candidate lists,
the Globe and Mail, the Catholic Register and The Local. Seven rest on articles read in ProQuest,
and five on same-office continuity. Some examples:

- The Toronto Star of 10 January 2002 says the TDSB trustee Sam Basra ran for the Progressive
  Conservatives in Etobicoke North in 1997 as Sam Basran and later dropped the "n".
- The Star's 1993 and 1997 riding stories describe the Progressive Conservative candidate in York
  South—Weston and then York Centre, Tony and then Anthony Figliano, as a land development
  consultant, aged 42 and then 46.
- The Star and Elections Canada describe the Natural Law candidate in four races from 1993 to 1997,
  printed Greg W. Roberts, Greg Roberts and Gregory Wayne Roberts, as a truck or transport driver,
  and the 1995 profile says he "ran federally in 1993".
- The York Guardian ties Stephen (or Steve) Halicki's 2003 provincial run to his 2004 federal one,
  and a 2005 story ties the 2006 Conservative candidate to the 2004 run. The held 2006 run now has a
  Person.
- Wikipedia's profile of the 2006 mayoral candidate Mitch Gold says he ran for the Toronto Board of
  Education in 1994, which joins the 1994 run printed Mitchell Gold and gives the held 2006 run a
  Person.
- The Star of 23 May 1997 names the sitting North York councillor Gina Severino and the long-time
  North York trustee Bob Churchill as candidates in the North York-Humber race, which the City's
  table prints as Serverino and Churchhill.

The pair of different people is Sarah Thompson, the Marxist-Leninist candidate whom Elections
Canada lists as an educator in 2008 and 2011, and Sarah Thomson, the publisher of the Women's Post
and Ontario Liberal candidate in 2011.

Undetermined is not a finding that two Persons are different people. For most of the 44
undetermined pairs the only records are result listings. Some are likely one individual on the
evidence found but fall short of the standard: Jim Mackay, the 1994 Scarborough
trustee for Ward 14, and the 1997 Scarborough Malvern council candidate whom the Star spells Mackay
and the City Mackey; Barbara Carter, a businesswoman running for the Scarborough board in 1994, and
the owner of a landscaping business who ran in the 1999 Ward 16 by-election; and Jim McLeod, a
registered nurse and Green candidate in Scarborough West in 1993, and James MacLeod, a health care
worker running for the Scarborough board in 1994.

## Held runs

Two of the 12 held runs now have a Person: Steve Halicki's 2006 York South—Weston run and Mitch
Gold's 2006 mayoral run. The other ten stay held. Three of them are in items whose Persons were
joined, but no source names the held run: Anthony Figliano's 1997 TCDSB Ward 10 run (the Star
called that candidate a real estate appraiser), Jose Perez's 1994 York Ward 3 run and Baquie
Ghazi's 2018 TDSB Ward 10 run. The other seven are in items left undetermined.

## Data notes

Sources found in the review disagree with the release on four totals. The release keeps the
official figures:

- Wikipedia gives Danny Goldstick 119 votes in York South—Weston in 1993, where Elections Canada's
  file has 62.
- Wikipedia's 2022 results give Catherine Habus 2,218 votes in Ward 2, where the City has 2,318.
- Wikipedia's Go Vegan article gives Paulo Figueiras 308 votes in Trinity—Spadina in 2014, where
  Elections Ontario has 307; its percentage matches 307.
- Wikipedia puts Dave Johnson's 1999 margin in Don Valley East at about 2,500, where Elections
  Ontario's totals give 3,038.

The Star's 2002 story says Sam Basra also ran in the 1997 municipal election as Sam Basran, for the
trustee seat he later won. The release has no 1997 run of either name.

## Limitations

The research and the second check were done by AI agents, and every verdict's sources and notes
are in the results files. The second check could not open ProQuest. One web reviewer read two
unofficial Wikipedia mirrors as leads; no join rests on them. The fetch tool refused some pages for
want of a search result carrying their URL; the reviewers found most of them again through a
search, but The Local's 2026 Ward 1 guide, which may settle Nathen Mazri and Nathen Masri, was not
read. The second check of Shelley and Shel Goldstein also found a film-credits site listing both
names for one actor; it is an aggregator, so the join rests on the Star, the York Guardian and
Elections Canada instead.
